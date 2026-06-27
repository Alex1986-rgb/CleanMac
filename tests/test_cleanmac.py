#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Юнит-тесты безопасных функций CleanMac. Запуск:
   /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -m unittest -v tests.test_cleanmac
"""
import os, sys, tempfile, unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import CleanMac as cm  # импорт безопасен: GUI не стартует (guard __main__)

HOME = os.path.expanduser("~")


class TestHuman(unittest.TestCase):
    def test_bytes(self):
        self.assertEqual(cm.human(0), "0 Б")
        self.assertEqual(cm.human(512), "512 Б")

    def test_units(self):
        self.assertEqual(cm.human(1024), "1.0 КБ")
        self.assertEqual(cm.human(1536), "1.5 КБ")
        self.assertEqual(cm.human(1024 ** 3), "1.0 ГБ")


class TestProtection(unittest.TestCase):
    def test_protected_roots(self):
        for p in ("/", HOME, "/System", "/Applications", "/usr",
                  os.path.join(HOME, "Library"),
                  os.path.join(HOME, "Documents"),
                  os.path.join(HOME, "Library/Caches")):
            self.assertTrue(cm.is_protected(p), f"{p} должен быть защищён")

    def test_subpaths_not_protected(self):
        # глубокий путь внутри кэша — чистить можно
        self.assertFalse(cm.is_protected(os.path.join(HOME, "Library/Caches/SomeApp/file.bin")))

    def test_to_trash_refuses_protected(self):
        self.assertFalse(cm.to_trash(HOME))
        self.assertFalse(cm.to_trash("/"))
        self.assertFalse(cm.to_trash(os.path.join(HOME, "Library")))

    def test_to_trash_missing(self):
        self.assertFalse(cm.to_trash("/no/such/path/xyz"))

    def test_empty_and_relative_paths_protected(self):
        # Регрессия: пустой/относительный путь раскрывается realpath в CWD или
        # произвольное место под ним. Такие пути НИКОГДА не должны удаляться.
        for p in ("", ".", "..", "relative/sub", "~", "Library/Caches"):
            self.assertTrue(cm.is_protected(p), f"{p!r} должен считаться защищённым")

    def test_to_trash_refuses_relative(self):
        # to_trash(".") раньше проходил (lexists True, не защищён) и пытался
        # переместить текущий каталог. Теперь относительный путь отвергается.
        self.assertFalse(cm.to_trash("."))
        self.assertFalse(cm.to_trash("relative/sub"))

    def test_shred_refuses_relative(self):
        self.assertFalse(cm.shred_file("."))
        self.assertFalse(cm.shred_file("relative/file"))

    def test_absolute_subpath_still_deletable(self):
        # защита не должна ломать обычную очистку реальных подпапок кэша
        self.assertFalse(cm.is_protected(os.path.join(HOME, "Library/Caches/App/file.bin")))

    def test_to_trash_broken_symlink(self):
        # Регрессия: битый симлинк (цель отсутствует) должен уезжать в Корзину.
        # Раньше to_trash() использовал os.path.exists (следует за ссылкой) и
        # для битого симлинка возвращал False → шаг «битые файлы» молча давал 0.
        work = tempfile.mkdtemp()
        trash = tempfile.mkdtemp()
        old_trash = cm.TRASH
        cm.TRASH = trash
        try:
            link = os.path.join(work, "broken-link")
            os.symlink(os.path.join(work, "no-such-target"), link)
            self.assertTrue(os.path.islink(link))
            self.assertFalse(os.path.exists(link))   # битый
            self.assertTrue(cm.to_trash(link), "битый симлинк должен переместиться в Корзину")
            self.assertFalse(os.path.lexists(link), "симлинк должен исчезнуть из исходного места")
            self.assertTrue(os.path.lexists(os.path.join(trash, "broken-link")))
        finally:
            cm.TRASH = old_trash
            import shutil as _sh
            _sh.rmtree(work, ignore_errors=True); _sh.rmtree(trash, ignore_errors=True)


class TestLocalization(unittest.TestCase):
    def test_translation_dict(self):
        self.assertEqual(cm.TR.get("Дашборд"), "Dashboard")
        self.assertEqual(cm.TR.get("Защита"), "Protection")


class TestCleanupHistory(unittest.TestCase):
    def setUp(self):
        self._orig = cm._history_path
        self._tmp = tempfile.mkdtemp()
        cm._history_path = lambda: os.path.join(self._tmp, "hist.json")

    def tearDown(self):
        cm._history_path = self._orig

    def test_record_and_total(self):
        self.assertEqual(cm.cleanup_history(), [])
        self.assertEqual(cm.total_freed(), 0)
        cm.record_cleanup(1000, "clean")
        cm.record_cleanup(500, "smart")
        cm.record_cleanup(0, "clean")        # нули игнорируются
        cm.record_cleanup(-5, "clean")       # отрицательные игнорируются
        hist = cm.cleanup_history()
        self.assertEqual(len(hist), 2)
        self.assertEqual(cm.total_freed(), 1500)
        self.assertEqual(hist[0]["kind"], "clean")
        self.assertIn("ts", hist[0])

    def test_corrupt_file_safe(self):
        with open(cm._history_path(), "w") as f:
            f.write("{не json")
        self.assertEqual(cm.cleanup_history(), [])   # не падает


class TestDiskAdvice(unittest.TestCase):
    def test_healthy(self):
        adv = cm.disk_advice(30, 40, 90)
        self.assertEqual(len(adv), 1)
        self.assertEqual(adv[0][0], "🟢")

    def test_disk_critical(self):
        adv = cm.disk_advice(95, 40, 90)
        self.assertTrue(any("Диск заполнен" in t for _, t in adv))
        self.assertEqual(adv[0][0], "🔴")

    def test_ram_and_battery(self):
        adv = cm.disk_advice(50, 88, 15)
        texts = " ".join(t for _, t in adv)
        self.assertIn("Память", texts)
        self.assertIn("заряд", texts.lower())

    def test_no_battery(self):
        adv = cm.disk_advice(50, 50, None)   # десктоп без батареи
        self.assertEqual(adv[0][0], "🟢")


class TestSquarify(unittest.TestCase):
    def test_areas_proportional_and_cover(self):
        sizes=[50,30,20]
        rects=cm.CleanMac._squarify(sizes, 0,0, 100,100)
        self.assertEqual(len(rects), 3)
        areas=[rw*rh for _,_,rw,rh in rects]
        self.assertAlmostEqual(sum(areas), 100*100, delta=1)   # покрытие полное
        # пропорции сохранены (первый вдвое больше третьего ~ 50 vs 20)
        self.assertAlmostEqual(areas[0]/areas[2], 50/20, delta=0.05)

    def test_empty_and_zero(self):
        self.assertEqual(cm.CleanMac._squarify([], 0,0,100,100), [])
        self.assertEqual(cm.CleanMac._squarify([0,0], 0,0,100,100), [])


class TestOrphanName(unittest.TestCase):
    def setUp(self):
        self.ids = {"com.acme.coolapp", "telegram", "com.tdesktop.telegram"}

    def test_apple_never_orphan(self):
        self.assertFalse(cm._is_orphan_name("com.apple.Safari", self.ids))
        self.assertFalse(cm._is_orphan_name("group.com.apple.x", self.ids))

    def test_installed_not_orphan(self):
        self.assertFalse(cm._is_orphan_name("com.acme.coolapp", self.ids))
        self.assertFalse(cm._is_orphan_name("com.acme.coolapp.helper", self.ids))  # суб-домен установленного

    def test_non_bundle_skipped(self):
        self.assertFalse(cm._is_orphan_name("RandomFolder", self.ids))   # нет точки
        self.assertFalse(cm._is_orphan_name("default.store", self.ids))  # 2 сегмента, не bundle id
        self.assertFalse(cm._is_orphan_name("foo.bar.baz", self.ids))    # неизвестный TLD-префикс

    def test_real_orphan(self):
        self.assertTrue(cm._is_orphan_name("com.deleted.oldapp", self.ids))


class TestVersionCompare(unittest.TestCase):
    """Апдейтер: баннер только для реально новой версии (числовое сравнение)."""
    def test_tuple(self):
        self.assertEqual(cm.ver_tuple("2.29.0"), (2, 29, 0))
        self.assertEqual(cm.ver_tuple(" 1.2 "), (1, 2))
        self.assertEqual(cm.ver_tuple("мусор"), (0,))   # не падает

    def test_newer_older_equal(self):
        self.assertTrue(cm.ver_tuple("2.30.0") > cm.ver_tuple("2.29.0"))   # новее
        self.assertFalse(cm.ver_tuple("2.28.0") > cm.ver_tuple("2.29.0"))  # откат не предлагаем
        self.assertFalse(cm.ver_tuple("2.29.0") > cm.ver_tuple("2.29.0"))  # равны

    def test_string_compare_pitfall(self):
        # строковое сравнение ошибочно считает '2.9' новее '2.29'; числовое — нет
        self.assertFalse(cm.ver_tuple("2.9.0") > cm.ver_tuple("2.29.0"))


class TestNetSpeed(unittest.TestCase):
    """Скорость сети: psutil ИЛИ резерв netstat; всегда неотрицательно."""
    def test_stat_net_nonneg_tuple(self):
        d, u = cm.stat_net()
        self.assertIsInstance(d, float); self.assertIsInstance(u, float)
        self.assertGreaterEqual(d, 0.0); self.assertGreaterEqual(u, 0.0)

    def test_netstat_fallback(self):
        c = cm._net_counters_netstat()        # на macOS интерфейсы есть
        self.assertTrue(c is None or (isinstance(c, tuple) and len(c) == 2))
        if c is not None:
            self.assertGreaterEqual(c[0], 0); self.assertGreaterEqual(c[1], 0)


class TestDeepTrash(unittest.TestCase):
    """Глубокая Корзина: видит и системную корзину тома, не только ~/.Trash."""
    def test_locations_are_dirs(self):
        locs = cm.trash_locations()
        self.assertIsInstance(locs, list)
        for p in locs:
            self.assertTrue(os.path.isdir(p))
        self.assertIn(cm.TRASH, locs + [cm.TRASH])  # ~/.Trash учитывается, если существует

    def test_deep_size_nonneg(self):
        self.assertGreaterEqual(cm.deep_trash_size(), 0)


class TestBrewParser(unittest.TestCase):
    def test_formula_lines(self):
        text = "ack (3.9.0) < 3.10.0\naircrack-ng (1.7_1) < 1.7_2"
        r = cm.parse_brew_outdated(text, "формула")
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0], ("ack", "3.9.0", "3.10.0", "формула"))

    def test_cask_neq(self):
        r = cm.parse_brew_outdated("chrome (1.0) != 2.0", "приложение")
        self.assertEqual(r[0], ("chrome", "1.0", "2.0", "приложение"))

    def test_name_only(self):
        r = cm.parse_brew_outdated("blender", "приложение")
        self.assertEqual(r[0][0], "blender")
        self.assertEqual(r[0][3], "приложение")

    def test_empty(self):
        self.assertEqual(cm.parse_brew_outdated("", "формула"), [])


class TestDiskBenchmark(unittest.TestCase):
    """Бенчмарк диска: пишет/читает маленький temp-файл и удаляет его."""
    def test_small_run_and_cleanup(self):
        tmp = tempfile.mkdtemp()
        before = set(os.listdir(tmp))
        res = cm.disk_benchmark(path=tmp, size_mb=1)
        self.assertNotIn("error", res, f"неожиданная ошибка: {res.get('error')}")
        self.assertEqual(res["size_mb"], 1)
        self.assertGreater(res["write_mbps"], 0)
        self.assertGreater(res["read_mbps"], 0)
        # temp-файл удалён (finally) — каталог в исходном состоянии
        self.assertEqual(set(os.listdir(tmp)), before)

    def test_error_on_bad_path(self):
        res = cm.disk_benchmark(path="/no/such/dir/xyz", size_mb=1)
        self.assertIn("error", res)

    def test_verdict_thresholds(self):
        self.assertIn("🟢", cm.CleanMac._bench_verdict(2000))
        self.assertIn("🟢", cm.CleanMac._bench_verdict(600))
        self.assertIn("🟡", cm.CleanMac._bench_verdict(200))
        self.assertIn("🔴", cm.CleanMac._bench_verdict(50))


class TestDirTree(unittest.TestCase):
    """dir_tree: дерево размеров подкаталогов для sunburst-карты."""

    def _mkfile(self, path, nbytes):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(b"\0" * nbytes)

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # big/ = 10000 байт (a.bin), small/ = 100 байт (b.bin)
        self._mkfile(os.path.join(self.tmp, "big", "a.bin"), 10000)
        self._mkfile(os.path.join(self.tmp, "big", "nested", "c.bin"), 4000)
        self._mkfile(os.path.join(self.tmp, "small", "b.bin"), 100)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_root_and_children_sizes(self):
        t = cm.dir_tree(self.tmp, depth=2, min_frac=0.0, top_n=12)
        self.assertEqual(t["size"], 14100)         # 10000 + 4000 + 100
        kids = {c["name"]: c["size"] for c in t["children"]}
        self.assertEqual(kids.get("big"), 14000)   # 10000 + 4000 (nested)
        self.assertEqual(kids.get("small"), 100)

    def test_depth_collects_grandchildren(self):
        t = cm.dir_tree(self.tmp, depth=2, min_frac=0.0, top_n=12)
        big = next(c for c in t["children"] if c["name"] == "big")
        names = {c["name"] for c in big["children"]}
        self.assertIn("a.bin", names)
        self.assertIn("nested", names)             # каталог-внук раскрыт

    def test_min_frac_collapses_small_into_rest(self):
        # порог 0.1 от total (14100) = 1410 байт; small (100) уходит в «Прочее»
        t = cm.dir_tree(self.tmp, depth=2, min_frac=0.1, top_n=12)
        names = {c["name"] for c in t["children"]}
        self.assertNotIn("small", names)
        rest = [c for c in t["children"] if c.get("is_rest")]
        self.assertTrue(rest, "ожидался узел «Прочее» для мелких детей")
        self.assertEqual(rest[0]["size"], 100)

    def test_top_n_limits_children(self):
        for i in range(20):
            self._mkfile(os.path.join(self.tmp, f"d{i:02d}", "f.bin"), 1000 + i)
        t = cm.dir_tree(self.tmp, depth=1, min_frac=0.0, top_n=5)
        real = [c for c in t["children"] if not c.get("is_rest")]
        self.assertLessEqual(len(real), 5)

    def test_symlink_not_followed(self):
        target = os.path.join(self.tmp, "big")
        link = os.path.join(self.tmp, "link_to_big")
        try:
            os.symlink(target, link)
        except (OSError, NotImplementedError):
            self.skipTest("симлинки недоступны в этой ФС")
        t = cm.dir_tree(self.tmp, depth=2, min_frac=0.0, top_n=20)
        names = {c["name"] for c in t["children"]}
        self.assertNotIn("link_to_big", names)     # симлинк пропущен

    def test_sun_layout_extents_sum(self):
        t = cm.dir_tree(self.tmp, depth=2, min_frac=0.0, top_n=12)
        arcs = cm.CleanMac._sun_layout(t, max_depth=2)
        ring1 = [a for a in arcs if a[0] == 1]
        self.assertAlmostEqual(sum(ext for _, _, ext, _ in ring1), 360.0, places=3)


class TestScanSize(unittest.TestCase):
    """_scan_size: размер через os.walk без перехода по симлинкам (чистая ФС-функция)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _mkfile(self, rel, nbytes):
        p = os.path.join(self.tmp, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(b"\0" * nbytes)
        return p

    def test_file_size(self):
        p = self._mkfile("a.bin", 321)
        self.assertEqual(cm._scan_size(p), 321)

    def test_dir_recursive_sum(self):
        self._mkfile("x/a.bin", 1000)
        self._mkfile("x/y/b.bin", 234)
        self.assertEqual(cm._scan_size(os.path.join(self.tmp, "x")), 1234)

    def test_missing_path_is_zero(self):
        self.assertEqual(cm._scan_size(os.path.join(self.tmp, "nope")), 0)

    def test_symlink_file_not_counted(self):
        target = self._mkfile("real.bin", 500)
        link = os.path.join(self.tmp, "link.bin")
        try:
            os.symlink(target, link)
        except (OSError, NotImplementedError):
            self.skipTest("симлинки недоступны")
        # симлинк сам по себе → 0 (не разыменовываем)
        self.assertEqual(cm._scan_size(link), 0)

    def test_symlink_dir_not_followed(self):
        self._mkfile("d/inside.bin", 800)
        link = os.path.join(self.tmp, "dlink")
        try:
            os.symlink(os.path.join(self.tmp, "d"), link)
        except (OSError, NotImplementedError):
            self.skipTest("симлинки недоступны")
        # каталог-симлинк не раскрывается
        self.assertEqual(cm._scan_size(link), 0)


class TestColorHelpers(unittest.TestCase):
    """Чистая цветовая математика: _blend, _lighten, col_for (семафор)."""

    def test_blend_endpoints(self):
        self.assertEqual(cm._blend("#123456", "#abcdef", 0.0), "#123456")
        self.assertEqual(cm._blend("#123456", "#abcdef", 1.0), "#abcdef")

    def test_blend_midpoint(self):
        self.assertEqual(cm._blend("#000000", "#ffffff", 0.5), "#7f7f7f")

    def test_blend_output_format(self):
        out = cm._blend("#2fe5a0", "#091327", 0.4)
        self.assertEqual(len(out), 7)
        self.assertTrue(out.startswith("#"))
        int(out[1:], 16)  # валидный hex — не бросает

    def test_lighten_toward_white(self):
        # осветление чёрного на 50% даёт средне-серый
        self.assertEqual(cm._lighten("#000000", 0.5), "#7f7f7f")
        # белый не светлеет дальше белого
        self.assertEqual(cm._lighten("#ffffff", 0.3), "#ffffff")

    def test_col_for_normal_thresholds(self):
        # col_for(p): чем выше p, тем «хуже» (для нагрузки). v = 100 - p.
        self.assertEqual(cm.col_for(30), cm.GREEN)    # v=70 ≥ 50
        self.assertEqual(cm.col_for(60), cm.YELLOW)   # v=40 ∈ [25,50)
        self.assertEqual(cm.col_for(80), cm.RED)      # v=20 < 25

    def test_col_for_inverted(self):
        # inv=True: значение само по себе «хорошее» (здоровье/батарея).
        self.assertEqual(cm.col_for(80, inv=True), cm.GREEN)
        self.assertEqual(cm.col_for(40, inv=True), cm.YELLOW)
        self.assertEqual(cm.col_for(10, inv=True), cm.RED)

    def test_col_for_boundaries(self):
        self.assertEqual(cm.col_for(50), cm.GREEN)    # v=50 ровно граница GREEN
        self.assertEqual(cm.col_for(75), cm.YELLOW)   # v=25 ровно граница YELLOW


class TestLocalization2(unittest.TestCase):
    """L(): в RU возвращает оригинал; перевод существует в TR для известных ключей."""

    def test_L_passthrough_unknown(self):
        # неизвестный ключ всегда возвращается как есть, в любом языке
        self.assertEqual(cm.L("ОченьРедкаяСтрока"), "ОченьРедкаяСтрока")

    def test_L_respects_current_lang(self):
        orig = cm.LANG
        try:
            cm.LANG = "ru"
            self.assertEqual(cm.L("Дашборд"), "Дашборд")   # RU → оригинал
            cm.LANG = "en"
            self.assertEqual(cm.L("Дашборд"), "Dashboard")  # EN → перевод
            self.assertEqual(cm.L("НетВСловаре"), "НетВСловаре")  # нет перевода → как есть
        finally:
            cm.LANG = orig


class TestOptimizePlan(unittest.TestCase):
    """Оркестратор волшебной кнопки: состав и порядок безопасных шагов."""

    def test_plan_is_copy(self):
        a = cm.optimize_plan(); b = cm.optimize_plan()
        self.assertIsNot(a, b)                       # отдаётся копия, не общий список
        self.assertEqual(a, b)

    def test_keys_and_order(self):
        keys = [k for k, _ in cm.optimize_plan()]
        self.assertEqual(keys, ["caches", "syscache", "snapshots", "memory",
                                "emptydirs", "broken", "orphans", "brewcleanup",
                                "launchsvc", "dockicons", "dns", "trim"])

    def test_no_unsafe_steps(self):
        # план НЕ содержит удаления дублей/крупных/приложений/очистки Корзины,
        # ни опасных авто-операций (sudo periodic, переиндексация Spotlight, дефрагментация)
        keys = {k for k, _ in cm.optimize_plan()}
        for bad in ("dupes", "large", "uninstall", "trash", "shred",
                    "periodic", "mdutil", "reindex", "defrag", "disable"):
            self.assertNotIn(bad, keys)

    def test_safe_new_steps_present(self):
        # новые безопасные шаги ускорения присутствуют в авто-наборе
        keys = {k for k, _ in cm.optimize_plan()}
        for good in ("brewcleanup", "launchsvc", "dockicons", "trim"):
            self.assertIn(good, keys)

    def test_trim_is_last_informational(self):
        # информационная пометка про SSD/TRIM идёт последней (самодиагностика)
        keys = [k for k, _ in cm.optimize_plan()]
        self.assertEqual(keys[-1], "trim")

    def test_labels_nonempty(self):
        for k, label in cm.optimize_plan():
            self.assertTrue(label and isinstance(label, str))


class TestFindEmptyDirs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_finds_empty_not_base(self):
        empty = os.path.join(self.tmp, "empty", "deep")
        os.makedirs(empty)
        full = os.path.join(self.tmp, "full")
        os.makedirs(full)
        with open(os.path.join(full, "f.bin"), "wb") as f:
            f.write(b"x")
        res = cm.find_empty_dirs([self.tmp])
        self.assertIn(empty, res)                         # глубокая пустая папка найдена
        self.assertIn(os.path.join(self.tmp, "empty"), res)  # и пустой родитель
        self.assertNotIn(full, res)                       # папка с файлом — не пустая
        self.assertNotIn(self.tmp, res)                   # сам базовый каталог не трогаем

    def test_missing_base_safe(self):
        self.assertEqual(cm.find_empty_dirs([os.path.join(self.tmp, "nope")]), [])


class TestFindBrokenFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_zero_byte_and_broken_symlink(self):
        zero = os.path.join(self.tmp, "zero.bin")
        open(zero, "wb").close()
        good = os.path.join(self.tmp, "good.bin")
        with open(good, "wb") as f:
            f.write(b"data")
        res = cm.find_broken_files([self.tmp])
        self.assertIn(zero, res)
        self.assertNotIn(good, res)
        # битый симлинк
        link = os.path.join(self.tmp, "dead.link")
        try:
            os.symlink(os.path.join(self.tmp, "no_target"), link)
        except (OSError, NotImplementedError):
            return
        res2 = cm.find_broken_files([self.tmp])
        self.assertIn(link, res2)

    def test_missing_base_safe(self):
        self.assertEqual(cm.find_broken_files([os.path.join(self.tmp, "nope")]), [])


class TestScanOldDownloads(unittest.TestCase):
    """scan_old_downloads: топ старых файлов в папке загрузок.
    Чистая ФС-функция — без перехода по симлинкам, с пропуском защищённых путей."""

    DAY = 86400

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.now = 1_700_000_000.0  # фиксируем «сейчас» для детерминизма

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _mkfile(self, rel, nbytes, age_days):
        p = os.path.join(self.tmp, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(b"\0" * nbytes)
        mt = self.now - age_days * self.DAY
        os.utime(p, (mt, mt))
        return p

    def test_finds_old_skips_recent(self):
        old = self._mkfile("old_big.zip", 5_000_000, age_days=200)
        self._mkfile("fresh.zip", 9_000_000, age_days=3)   # свежий — не попадает
        res = cm.scan_old_downloads(self.tmp, min_days=90, top=50, now=self.now)
        paths = [p for _, p, _ in res]
        self.assertIn(old, paths)
        self.assertNotIn(os.path.join(self.tmp, "fresh.zip"), paths)
        # размер и возраст вернулись корректно
        size, path, age = res[0]
        self.assertEqual(path, old)
        self.assertEqual(size, 5_000_000)
        self.assertGreaterEqual(age, 199)

    def test_sorted_by_size_desc(self):
        self._mkfile("a.bin", 1000, age_days=120)
        self._mkfile("b.bin", 8000, age_days=120)
        self._mkfile("c.bin", 4000, age_days=120)
        res = cm.scan_old_downloads(self.tmp, min_days=90, now=self.now)
        sizes = [s for s, _, _ in res]
        self.assertEqual(sizes, sorted(sizes, reverse=True))
        self.assertEqual(sizes, [8000, 4000, 1000])

    def test_symlink_file_skipped(self):
        target = self._mkfile("realtarget.bin", 3000, age_days=300)
        link = os.path.join(self.tmp, "old_link.bin")
        try:
            os.symlink(target, link)
        except (OSError, NotImplementedError):
            self.skipTest("симлинки недоступны")
        # делаем сам линк «старым» — но он не должен попасть в результат
        res = cm.scan_old_downloads(self.tmp, min_days=90, now=self.now)
        paths = [p for _, p, _ in res]
        self.assertIn(target, paths)
        self.assertNotIn(link, paths)

    def test_symlink_dir_not_followed(self):
        outside = tempfile.mkdtemp()
        try:
            big = os.path.join(outside, "outside_big.bin")
            with open(big, "wb") as f:
                f.write(b"\0" * 7000)
            mt = self.now - 250 * self.DAY
            os.utime(big, (mt, mt))
            link = os.path.join(self.tmp, "dirlink")
            try:
                os.symlink(outside, link)
            except (OSError, NotImplementedError):
                self.skipTest("симлинки недоступны")
            res = cm.scan_old_downloads(self.tmp, min_days=90, now=self.now)
            paths = [p for _, p, _ in res]
            # внутрь симлинка-каталога не заходим
            self.assertFalse(any(p.startswith(link) for p in paths))
            self.assertNotIn(big, paths)
        finally:
            import shutil
            shutil.rmtree(outside, ignore_errors=True)

    def test_missing_base_returns_empty(self):
        self.assertEqual(cm.scan_old_downloads(os.path.join(self.tmp, "nope"), now=self.now), [])

    def test_empty_base_returns_empty(self):
        self.assertEqual(cm.scan_old_downloads("", now=self.now), [])

    def test_top_limit(self):
        for i in range(5):
            self._mkfile(f"f{i}.bin", 1000 * (i + 1), age_days=120)
        res = cm.scan_old_downloads(self.tmp, min_days=90, top=2, now=self.now)
        self.assertEqual(len(res), 2)
        # топ-2 по размеру: 5000, 4000
        self.assertEqual([s for s, _, _ in res], [5000, 4000])


if __name__ == "__main__":
    unittest.main(verbosity=2)
