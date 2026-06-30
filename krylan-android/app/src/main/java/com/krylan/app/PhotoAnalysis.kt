// Поиск похожих и размытых фото без тяжёлых ML-зависимостей.
// Похожие: perceptual hash (dHash 8x9 → 64 бита) + расстояние Хэмминга.
// Размытые: дисперсия Лапласиана на маленьком grayscale-битмапе.
// Всё считается по сильно уменьшенному битмапу из ContentResolver — память и CPU под контролем.
package com.krylan.app

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri

/**
 * Результат анализа одного фото: исходный [file], perceptual-hash [hash] (64 бита, 0 если не удалось
 * декодировать) и оценка резкости [sharpness] (дисперсия Лапласиана; меньше — размытее).
 */
data class PhotoSignature(
    val file: MediaFile,
    val hash: Long,
    val sharpness: Double,
    val decoded: Boolean,
)

/** Группа похожих фото (расстояние Хэмминга <= порога). «Лучший» = первый (самый резкий). */
data class SimilarGroup(val photos: List<PhotoSignature>)

object PhotoAnalysis {

    /** Порог расстояния Хэмминга для «похожих» (0..64). ~5-10 — близкие/серийные кадры. */
    const val SIMILAR_THRESHOLD = 10

    /** Порог дисперсии Лапласиана: ниже — считаем фото размытым. Подобрано эмпирически для 8-битного grayscale. */
    const val BLUR_THRESHOLD = 120.0

    /**
     * Декодирует фото в маленький битмап и считает подпись (hash + резкость).
     * Декодирование с inSampleSize по фактическим размерам — без загрузки полного кадра в память.
     * Любая ошибка декодирования → decoded=false (фото просто не участвует в группировке/блюре).
     */
    fun signatureOf(ctx: Context, file: MediaFile): PhotoSignature {
        val bmp = decodeSmall(ctx, file.uri, target = 64)
            ?: return PhotoSignature(file, 0L, 0.0, decoded = false)
        return try {
            val hash = dHash(bmp)
            val sharp = laplacianVariance(bmp)
            PhotoSignature(file, hash, sharp, decoded = true)
        } finally {
            bmp.recycle()
        }
    }

    /**
     * Группирует подписи по близости хэшей (Хэмминг <= [threshold]).
     * Жадная кластеризация: каждое фото добавляется в первый подходящий кластер, иначе создаёт новый.
     * Внутри группы сортируем по убыванию резкости — первым идёт «лучший» (самый чёткий) кадр.
     * Возвращаем только группы из 2+ фото, по убыванию размера группы.
     */
    fun groupSimilar(
        signatures: List<PhotoSignature>,
        threshold: Int = SIMILAR_THRESHOLD,
    ): List<SimilarGroup> {
        val valid = signatures.filter { it.decoded }
        val clusters = mutableListOf<MutableList<PhotoSignature>>()
        for (sig in valid) {
            val cluster = clusters.firstOrNull { c -> hamming(c[0].hash, sig.hash) <= threshold }
            if (cluster != null) cluster.add(sig) else clusters.add(mutableListOf(sig))
        }
        return clusters
            .filter { it.size > 1 }
            .map { c -> SimilarGroup(c.sortedByDescending { it.sharpness }) }
            .sortedByDescending { it.photos.size }
    }

    /** Размытые фото: декодированные с резкостью ниже порога, от самых размытых к менее. */
    fun blurry(
        signatures: List<PhotoSignature>,
        threshold: Double = BLUR_THRESHOLD,
    ): List<PhotoSignature> =
        signatures.filter { it.decoded && it.sharpness < threshold }
            .sortedBy { it.sharpness }

    // --- Декодирование ---

    /** Декодирует uri в битмап с длинной стороной ~[target] px (через inSampleSize). */
    private fun decodeSmall(ctx: Context, uri: Uri, target: Int): Bitmap? {
        return try {
            // Шаг 1: читаем только размеры.
            val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            ctx.contentResolver.openInputStream(uri)?.use {
                BitmapFactory.decodeStream(it, null, bounds)
            }
            val w = bounds.outWidth
            val h = bounds.outHeight
            if (w <= 0 || h <= 0) return null
            // Шаг 2: подбираем степень-двойки уменьшения.
            var sample = 1
            val longer = maxOf(w, h)
            while (longer / (sample * 2) >= target) sample *= 2
            val opts = BitmapFactory.Options().apply {
                inSampleSize = sample
                inPreferredConfig = Bitmap.Config.ARGB_8888
            }
            ctx.contentResolver.openInputStream(uri)?.use {
                BitmapFactory.decodeStream(it, null, opts)
            }
        } catch (_: Exception) {
            null
        } catch (_: OutOfMemoryError) {
            null
        }
    }

    // --- Perceptual hash (dHash) ---

    /**
     * dHash: уменьшаем до 9x8 grayscale, для каждой строки сравниваем соседние пиксели —
     * 8x8 = 64 бита. Устойчив к масштабу/яркости, отличает реально разные кадры.
     */
    private fun dHash(src: Bitmap): Long {
        val w = 9; val h = 8
        val small = Bitmap.createScaledBitmap(src, w, h, true)
        var hash = 0L
        var bit = 0
        try {
            for (y in 0 until h) {
                for (x in 0 until w - 1) {
                    val left = gray(small.getPixel(x, y))
                    val right = gray(small.getPixel(x + 1, y))
                    if (left > right) hash = hash or (1L shl bit)
                    bit++
                }
            }
        } finally {
            if (small != src) small.recycle()
        }
        return hash
    }

    /** Расстояние Хэмминга между двумя 64-битными хэшами. */
    fun hamming(a: Long, b: Long): Int = java.lang.Long.bitCount(a xor b)

    // --- Резкость (дисперсия Лапласиана) ---

    /**
     * Резкость через дисперсию Лапласиана. Уменьшаем до grayscale 32x32, прогоняем
     * ядро Лапласиана (4-связное), считаем дисперсию откликов. Размытое фото даёт малую дисперсию.
     */
    private fun laplacianVariance(src: Bitmap): Double {
        val n = 32
        val small = Bitmap.createScaledBitmap(src, n, n, true)
        try {
            val g = IntArray(n * n)
            for (y in 0 until n) for (x in 0 until n) g[y * n + x] = gray(small.getPixel(x, y))
            val responses = ArrayList<Double>((n - 2) * (n - 2))
            for (y in 1 until n - 1) {
                for (x in 1 until n - 1) {
                    val c = g[y * n + x]
                    val lap = (g[(y - 1) * n + x] + g[(y + 1) * n + x] +
                        g[y * n + (x - 1)] + g[y * n + (x + 1)] - 4 * c).toDouble()
                    responses.add(lap)
                }
            }
            if (responses.isEmpty()) return 0.0
            val mean = responses.average()
            return responses.sumOf { (it - mean) * (it - mean) } / responses.size
        } finally {
            if (small != src) small.recycle()
        }
    }

    /** Яркость пикселя 0..255 (целочисленный приближённый luma). */
    private fun gray(pixel: Int): Int {
        val r = (pixel shr 16) and 0xFF
        val gg = (pixel shr 8) and 0xFF
        val b = pixel and 0xFF
        return (r * 299 + gg * 587 + b * 114) / 1000
    }
}
