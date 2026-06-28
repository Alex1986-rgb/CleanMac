# Юнит-тесты KRYLAN Desktop. Запуск из каталога krylan-desktop:
#   python -m unittest test_krylan -v
import os
import shutil
import tempfile
import time
import unittest

import krylan


class TestHuman(unittest.TestCase):
    def test_units(self):
        self.assertEqual(krylan.human(0), "0 Б")
        self.assertEqual(krylan.human(512), "512 Б")
        self.assertEqual(krylan.human(1024), "1.0 КБ")
        self.assertEqual(krylan.human(1536), "1.5 КБ")
        self.assertEqual(krylan.human(1024 ** 2), "1.0 МБ")
        self.assertEqual(krylan.human(1024 ** 3), "1.0 ГБ")


class TestLoadColor(unittest.TestCase):
    def test_thresholds(self):
        self.assertEqual(krylan.load_color(10), krylan.GREEN)
        self.assertEqual(krylan.load_color(59), krylan.GREEN)
        self.assertEqual(krylan.load_color(60), krylan.YELLOW)
        self.assertEqual(krylan.load_color(84), krylan.YELLOW)
        self.assertEqual(krylan.load_color(85), krylan.RED)
        self.assertEqual(krylan.load_color(100), krylan.RED)


class TestDirSize(unittest.TestCase):
    def test_counts_files(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        with open(os.path.join(d, "a"), "wb") as f:
            f.write(b"x" * 100)
        os.makedirs(os.path.join(d, "sub"))
        with open(os.path.join(d, "sub", "b"), "wb") as f:
            f.write(b"y" * 50)
        self.assertEqual(krylan.dir_size(d), 150)

    def test_missing_path(self):
        self.assertEqual(krylan.dir_size("/no/such/path/krylan"), 0)


class TestFindEmptyDirs(unittest.TestCase):
    def test_nested_and_parents(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        os.makedirs(os.path.join(base, "empty1"))
        os.makedirs(os.path.join(base, "empty2", "emptysub"))
        os.makedirs(os.path.join(base, "full"))
        with open(os.path.join(base, "full", "a.txt"), "w") as f:
            f.write("x")
        res = krylan.find_empty_dirs([base])
        rel = {p.replace(base + os.sep, "") for p in res}
        self.assertIn("empty1", rel)
        self.assertIn(os.path.join("empty2", "emptysub"), rel)
        self.assertIn("empty2", rel)               # родитель с только пустыми детьми
        self.assertNotIn("full", rel)              # содержит файл

    def test_skips_hidden(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        os.makedirs(os.path.join(base, ".git"))
        res = krylan.find_empty_dirs([base])
        self.assertFalse(any(".git" in p for p in res))


class TestFindDuplicates(unittest.TestCase):
    def test_detects_identical(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        payload = b"K" * (2 * 1024 * 1024)         # >1 МБ, иначе пропускается
        for name in ("one.bin", "two.bin", "three.bin"):
            with open(os.path.join(base, name), "wb") as f:
                f.write(payload)
        with open(os.path.join(base, "unique.bin"), "wb") as f:
            f.write(b"Q" * (2 * 1024 * 1024))
        groups, extras, wasted = krylan.find_duplicates([base])
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(extras), 2)           # 3 копии → 2 лишних
        self.assertEqual(wasted, 2 * len(payload))

    def test_no_false_positive(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        for i, name in enumerate(("a.bin", "b.bin")):
            with open(os.path.join(base, name), "wb") as f:
                f.write(bytes([i]) * (2 * 1024 * 1024))
        groups, extras, wasted = krylan.find_duplicates([base])
        self.assertEqual(groups, [])
        self.assertEqual(extras, [])


class TestBrokenFiles(unittest.TestCase):
    def test_finds_zero_and_symlink(self):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        dl = os.path.join(home, "Downloads")
        os.makedirs(dl)
        # пустой файл (0 байт)
        empty = os.path.join(dl, "empty.txt")
        open(empty, "w").close()
        # нормальный файл с содержимым
        normal = os.path.join(dl, "normal.txt")
        with open(normal, "w") as f:
            f.write("hello")
        # битый симлинк → несуществующая цель
        broken = os.path.join(dl, "broken.lnk")
        os.symlink(os.path.join(dl, "no-such-target"), broken)

        orig = krylan.HOME
        krylan.HOME = home
        try:
            res = krylan.find_broken_files()
        finally:
            krylan.HOME = orig

        kinds = {(k, os.path.basename(p)) for k, p in res}
        self.assertIn(("zero", "empty.txt"), kinds)
        self.assertIn(("symlink", "broken.lnk"), kinds)
        # нормальный файл не трогаем
        self.assertFalse(any(os.path.basename(p) == "normal.txt" for _, p in res))

    def test_ignores_hidden_and_valid_symlink(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        # скрытый пустой файл — пропускается
        open(os.path.join(base, ".hidden"), "w").close()
        # рабочий симлинк на существующий файл — не битый
        target = os.path.join(base, "real.txt")
        with open(target, "w") as f:
            f.write("data")
        os.symlink(target, os.path.join(base, "good.lnk"))
        res = krylan.find_broken_files([base])
        self.assertEqual(res, [])


class TestOldDownloads(unittest.TestCase):
    def test_age_filter(self):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        dl = os.path.join(home, "Downloads")
        os.makedirs(dl)
        old = os.path.join(dl, "old.txt")
        new = os.path.join(dl, "new.txt")
        for p in (old, new):
            with open(p, "w") as f:
                f.write("x")
        long_ago = time.time() - 400 * 86400
        os.utime(old, (long_ago, long_ago))
        orig = krylan.HOME
        krylan.HOME = home
        try:
            names = {os.path.basename(p) for _, p in krylan.old_downloads(days=180)}
        finally:
            krylan.HOME = orig
        self.assertIn("old.txt", names)
        self.assertNotIn("new.txt", names)


class TestGrowthReport(unittest.TestCase):
    def test_first_then_diff(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        snap = os.path.join(d, "snap.json")
        sub = os.path.join(d, "data")
        os.makedirs(sub)
        with open(os.path.join(sub, "a"), "wb") as f:
            f.write(b"x" * 1000)
        orig = krylan.take_snapshot
        krylan.take_snapshot = lambda bases=None: {sub: krylan.dir_size(sub)}
        try:
            changes, is_first = krylan.growth_report(snapshot_file=snap)
            self.assertTrue(is_first)
            # дописываем данные → второй прогон видит рост
            with open(os.path.join(sub, "b"), "wb") as f:
                f.write(b"y" * 500)
            changes, is_first = krylan.growth_report(snapshot_file=snap)
            self.assertFalse(is_first)
            delta = dict((p, dl) for dl, p, _, _ in changes)[sub]
            self.assertEqual(delta, 500)
        finally:
            krylan.take_snapshot = orig


class TestDiskAdvice(unittest.TestCase):
    def test_levels(self):
        self.assertEqual(krylan.disk_advice(30, 30)[0][0], krylan.GREEN)
        self.assertEqual(krylan.disk_advice(95, 40)[0][0], krylan.RED)
        self.assertTrue(any("Память" in t for _, t in krylan.disk_advice(50, 88)))
        self.assertTrue(any("заряд" in t.lower() for _, t in krylan.disk_advice(50, 50, 15)))
        self.assertEqual(krylan.disk_advice(50, 50, None)[0][0], krylan.GREEN)


class TestCleanupTargets(unittest.TestCase):
    def test_returns_existing_dirs(self):
        for name, path in krylan.cleanup_targets():
            self.assertTrue(os.path.isdir(path), f"{name}: {path} должен существовать")


class TestPrivacyTargets(unittest.TestCase):
    def test_returns_list_of_existing_files(self):
        for b, item, p in krylan.privacy_targets():
            self.assertTrue(os.path.isfile(p))
            self.assertIsInstance(b, str)
            self.assertIsInstance(item, str)


class TestSoftwareUpdater(unittest.TestCase):
    def test_brew_outdated_paren(self):
        txt = "wget (1.21.3) < 1.21.4\nnode (20.1.0) < 20.2.0\n"
        self.assertEqual(krylan.parse_brew_outdated(txt),
                         [("wget", "1.21.3", "1.21.4"), ("node", "20.1.0", "20.2.0")])

    def test_brew_outdated_plain(self):
        txt = "git 2.39.0 < 2.40.0\n"
        self.assertEqual(krylan.parse_brew_outdated(txt), [("git", "2.39.0", "2.40.0")])

    def test_brew_empty(self):
        self.assertEqual(krylan.parse_brew_outdated(""), [])

    def test_apt_upgradable(self):
        txt = ("Listing...\n"
               "vim/jammy-updates 2:8.2.3995 amd64 [upgradable from: 2:8.2.3000]\n"
               "curl/jammy 7.81.0 amd64 [upgradable from: 7.80.0]\n")
        self.assertEqual(krylan.parse_apt_upgradable(txt),
                         [("vim", "2:8.2.3000", "2:8.2.3995"), ("curl", "7.80.0", "7.81.0")])

    def test_apt_ignores_header(self):
        self.assertEqual(krylan.parse_apt_upgradable("Listing...\n"), [])

    def test_winget_upgrade(self):
        txt = ("Name              Id                 Version   Available  Source\n"
               "-------------------------------------------------------------------\n"
               "Mozilla Firefox   Mozilla.Firefox    120.0     121.0      winget\n"
               "7-Zip             7zip.7zip          22.01     23.01      winget\n")
        self.assertEqual(krylan.parse_winget_upgrade(txt),
                         [("Mozilla Firefox", "120.0", "121.0"), ("7-Zip", "22.01", "23.01")])

    def test_winget_no_separator(self):
        self.assertEqual(krylan.parse_winget_upgrade("garbage line only\n"), [])

class TestHtmlReport(unittest.TestCase):
    def test_structure_and_escaping(self):
        html = krylan.build_html_report(
            "KRYLAN — отчёт",
            [("Система", [("CPU", "12%"), ("Диск", "80% занято")]),
             ("Кэши", [("Chrome <cache>", "1.5 ГБ")])],
            generated="2026-06-27 10:00")
        self.assertIn("<!doctype html>", html)
        self.assertIn("KRYLAN — отчёт", html)
        self.assertIn("2026-06-27 10:00", html)
        self.assertIn("12%", html)
        # значение с угловыми скобками экранируется
        self.assertIn("Chrome &lt;cache&gt;", html)
        self.assertNotIn("<cache>", html)
        self.assertTrue(html.strip().endswith("</html>"))

    def test_empty_sections(self):
        html = krylan.build_html_report("T", [])
        self.assertIn("</html>", html)


class TestFocusCandidates(unittest.TestCase):
    """Режим фокуса — чистый фильтр кандидатов на обратимую паузу."""

    def _procs(self):
        # имена из чёрного списка обеих ОС + обычные приложения
        return [
            {"name": "Telegram", "pid": 101, "cpu": 3.0, "mem": 500 * 1024 * 1024},
            {"name": "Google Chrome", "pid": 102, "cpu": 12.0, "mem": 900 * 1024 * 1024},
            {"name": "Spotify", "pid": 103, "cpu": 1.0, "mem": 300 * 1024 * 1024},
            {"name": "kernel_task", "pid": 1, "cpu": 5.0, "mem": 100 * 1024 * 1024},
            {"name": "WindowServer", "pid": 90, "cpu": 8.0, "mem": 200 * 1024 * 1024},
            {"name": "Finder", "pid": 91, "cpu": 0.5, "mem": 120 * 1024 * 1024},
            {"name": "python", "pid": 200, "cpu": 0.0, "mem": 50 * 1024 * 1024},
            {"name": "Python", "pid": 201, "cpu": 0.0, "mem": 50 * 1024 * 1024},
            {"name": "explorer.exe", "pid": 300, "cpu": 0.0, "mem": 80 * 1024 * 1024},
            {"name": "System", "pid": 4, "cpu": 0.0, "mem": 10 * 1024 * 1024},
            {"name": "MyApp", "pid": 999, "cpu": 0.0, "mem": 0},   # сам KRYLAN (self_pid)
        ]

    def test_blacklist_and_self_excluded(self):
        cand = krylan.focus_candidates(self._procs(), self_pid=999)
        names = {c["name"] for c in cand}
        pids = {c["pid"] for c in cand}
        # системные имена отфильтрованы (на любой ОС жёстко чёрные)
        for bad in ("kernel_task", "WindowServer", "Finder", "python", "Python"):
            self.assertNotIn(bad, names, f"{bad} не должен быть кандидатом")
        # свой PID исключён
        self.assertNotIn(999, pids)
        self.assertNotIn("MyApp", names)
        # обычные приложения остаются
        self.assertIn("Telegram", names)
        self.assertIn("Google Chrome", names)
        self.assertIn("Spotify", names)

    def test_sorted_by_mem_desc(self):
        cand = krylan.focus_candidates(self._procs(), self_pid=999)
        mems = [c["mem"] for c in cand]
        self.assertEqual(mems, sorted(mems, reverse=True))
        # самый тяжёлый — Chrome (900 МБ)
        self.assertEqual(cand[0]["name"], "Google Chrome")

    def test_case_insensitive_blacklist(self):
        procs = [{"name": "FINDER", "pid": 5, "cpu": 0, "mem": 1},
                 {"name": "LaunchD", "pid": 6, "cpu": 0, "mem": 2}]
        cand = krylan.focus_candidates(procs, self_pid=999)
        self.assertEqual(cand, [])

    def test_skips_records_without_name_or_pid(self):
        procs = [{"name": "", "pid": 10, "cpu": 0, "mem": 5},
                 {"name": "NoPid", "pid": None, "cpu": 0, "mem": 5},
                 {"name": "Good", "pid": 11, "cpu": 0, "mem": 5}]
        cand = krylan.focus_candidates(procs, self_pid=999)
        self.assertEqual([c["name"] for c in cand], ["Good"])

    def test_accepts_namedtuple_like_objects(self):
        from collections import namedtuple
        Proc = namedtuple("Proc", "name pid cpu mem")
        procs = [Proc("Chrome", 1, 5.0, 800),
                 Proc("Finder", 2, 1.0, 100),
                 Proc("Notes", 3, 0.5, 400)]
        cand = krylan.focus_candidates(procs, self_pid=999)
        names = [c.name for c in cand]
        self.assertEqual(names, ["Chrome", "Notes"])   # Finder отфильтрован, сортировка по mem

    def test_default_self_pid_uses_getpid(self):
        # запись с текущим PID процесса-теста должна быть отфильтрована
        procs = [{"name": "Self", "pid": os.getpid(), "cpu": 0, "mem": 999},
                 {"name": "Other", "pid": os.getpid() + 1, "cpu": 0, "mem": 1}]
        cand = krylan.focus_candidates(procs)   # self_pid не передан → os.getpid()
        self.assertEqual([c["name"] for c in cand], ["Other"])


class TestSimilarImages(unittest.TestCase):
    """Похожие изображения (perceptual hash / dHash)."""

    def setUp(self):
        try:
            from PIL import Image  # noqa: F401
        except ImportError:
            self.skipTest("Pillow не установлен")

    def _make(self, path, fill, mods=None):
        from PIL import Image
        im = Image.new("RGB", (64, 64), fill)
        px = im.load()
        # градиент, чтобы dhash был содержательным (не нулевым)
        for y in range(64):
            for x in range(64):
                px[x, y] = ((x * 4) % 256, (y * 4) % 256, fill[2])
        for (mx, my, mc) in (mods or []):
            px[mx, my] = mc
        im.save(path)
        return im

    def test_dhash_returns_int(self):
        im = self._make(os.path.join(tempfile.mkdtemp(), "a.png"), (10, 20, 30))
        h = krylan.dhash(im)
        self.assertIsInstance(h, int)

    def test_hamming(self):
        self.assertEqual(krylan.hamming(0b1010, 0b1010), 0)
        self.assertEqual(krylan.hamming(0b1010, 0b1011), 1)
        self.assertEqual(krylan.hamming(0b0000, 0b1111), 4)

    def test_close_small_distance_far_large(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        # два почти одинаковых (отличаются парой пикселей)
        a = self._make(os.path.join(d, "a.png"), (10, 20, 30))
        b = self._make(os.path.join(d, "b.png"), (10, 20, 30),
                       mods=[(1, 1, (0, 0, 0)), (2, 2, (255, 255, 255))])
        # явно другое — другой узор
        from PIL import Image
        c_img = Image.new("RGB", (64, 64))
        cpx = c_img.load()
        for y in range(64):
            for x in range(64):
                cpx[x, y] = ((y * 8) % 256, 255 - (x * 4) % 256, 128)
        c_img.save(os.path.join(d, "c.png"))
        ha, hb, hc = krylan.dhash(a), krylan.dhash(b), krylan.dhash(c_img)
        self.assertLessEqual(krylan.hamming(ha, hb), 10)
        self.assertGreater(krylan.hamming(ha, hc), 10)

    def test_find_similar_images_groups(self):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        desktop = os.path.join(home, "Desktop")
        os.makedirs(desktop)
        self._make(os.path.join(desktop, "a.png"), (10, 20, 30))
        self._make(os.path.join(desktop, "b.png"), (10, 20, 30),
                   mods=[(1, 1, (0, 0, 0)), (2, 2, (255, 255, 255))])
        from PIL import Image
        c_img = Image.new("RGB", (64, 64))
        cpx = c_img.load()
        for y in range(64):
            for x in range(64):
                cpx[x, y] = ((y * 8) % 256, 255 - (x * 4) % 256, 128)
        c_img.save(os.path.join(desktop, "c.png"))
        old_home = krylan.HOME
        krylan.HOME = home
        try:
            groups = krylan.find_similar_images(threshold=10)
        finally:
            krylan.HOME = old_home
        # ровно одна группа из двух близких
        self.assertEqual(len(groups), 1)
        names = {os.path.basename(p) for p in groups[0]}
        self.assertEqual(names, {"a.png", "b.png"})


class TestOsLabel(unittest.TestCase):
    """os_label: техническое имя ОС → человекочитаемое."""

    def test_known_systems(self):
        orig = krylan.SYSTEM
        try:
            krylan.SYSTEM = "Darwin"
            self.assertEqual(krylan.os_label(), "macOS")
            krylan.SYSTEM = "Windows"
            self.assertEqual(krylan.os_label(), "Windows")
            krylan.SYSTEM = "Linux"
            self.assertEqual(krylan.os_label(), "Linux")
        finally:
            krylan.SYSTEM = orig

    def test_unknown_system_passthrough(self):
        orig = krylan.SYSTEM
        try:
            krylan.SYSTEM = "FreeBSD"
            self.assertEqual(krylan.os_label(), "FreeBSD")  # незнакомое — как есть
        finally:
            krylan.SYSTEM = orig


class TestTrashDir(unittest.TestCase):
    """trash_dir: путь к Корзине зависит от ОС; Windows → None (только WinAPI)."""

    def test_per_os(self):
        orig_sys, orig_home = krylan.SYSTEM, krylan.HOME
        try:
            krylan.HOME = "/home/tester"
            krylan.SYSTEM = "Darwin"
            self.assertEqual(krylan.trash_dir(), "/home/tester/.Trash")
            krylan.SYSTEM = "Linux"
            self.assertEqual(krylan.trash_dir(), "/home/tester/.local/share/Trash/files")
            krylan.SYSTEM = "Windows"
            self.assertIsNone(krylan.trash_dir())
        finally:
            krylan.SYSTEM, krylan.HOME = orig_sys, orig_home


class TestPathProtection(unittest.TestCase):
    """is_protected / safe_trash: защита от удаления пустых/относительных путей
    и стандартных папок домашнего каталога. Удаление остаётся обратимым (Корзина)."""

    def test_empty_and_relative_protected(self):
        for p in ("", ".", "..", "relative/sub", "sub/file.txt"):
            self.assertTrue(krylan.is_protected(p), f"{p!r} должен быть защищён")

    def test_home_and_standard_dirs_protected(self):
        orig = krylan.HOME
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        krylan.HOME = home
        try:
            self.assertTrue(krylan.is_protected(home))                       # сам HOME
            for d in ("Downloads", "Desktop", "Documents", "Library", ".cache"):
                self.assertTrue(krylan.is_protected(os.path.join(home, d)),
                                f"{d} должен быть защищён")
            self.assertTrue(krylan.is_protected("/"))                         # корень тома
            # файл ВНУТРИ стандартной папки — удалять можно
            self.assertFalse(krylan.is_protected(os.path.join(home, "Downloads", "junk.bin")))
        finally:
            krylan.HOME = orig

    def test_safe_trash_refuses_protected(self):
        orig = krylan.HOME
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        krylan.HOME = home
        try:
            # защищённый путь не уходит в Корзину, даже если существует
            os.makedirs(os.path.join(home, "Downloads"), exist_ok=True)
            self.assertFalse(krylan.safe_trash(os.path.join(home, "Downloads")))
            self.assertFalse(krylan.safe_trash("."))
            self.assertFalse(krylan.safe_trash(""))
            # папка Downloads на месте — её не тронули
            self.assertTrue(os.path.isdir(os.path.join(home, "Downloads")))
        finally:
            krylan.HOME = orig

    def test_safe_trash_moves_real_file(self):
        # обычный файл внутри пользовательской папки реально уходит в Корзину
        orig = krylan.HOME
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        krylan.HOME = home
        sub = os.path.join(home, "Downloads")
        os.makedirs(sub)
        f = os.path.join(sub, "junk.bin")
        with open(f, "wb") as fh:
            fh.write(b"x" * 10)
        try:
            self.assertTrue(krylan.safe_trash(f))
            self.assertFalse(os.path.exists(f), "файл должен исчезнуть из исходного места")
        finally:
            krylan.HOME = orig


class TestBlend(unittest.TestCase):
    """_blend: линейная интерполяция hex-цветов с клампом t в [0,1]."""

    def test_endpoints(self):
        self.assertEqual(krylan._blend("#000000", "#ffffff", 0.0), "#000000")
        self.assertEqual(krylan._blend("#000000", "#ffffff", 1.0), "#ffffff")

    def test_midpoint(self):
        self.assertEqual(krylan._blend("#000000", "#ffffff", 0.5), "#7f7f7f")

    def test_clamps_out_of_range(self):
        # t<0 трактуется как 0, t>1 как 1 — не выходит за границы цвета
        self.assertEqual(krylan._blend("#101010", "#ffffff", -5), "#101010")
        self.assertEqual(krylan._blend("#101010", "#ffffff", 9), "#ffffff")

    def test_valid_hex_output(self):
        out = krylan._blend("#37d39a", "#11151d", 0.3)
        self.assertEqual(len(out), 7)
        int(out[1:], 16)  # не бросает — валидный hex


class TestTakeSnapshot(unittest.TestCase):
    """take_snapshot: {путь: размер} только для существующих каталогов."""

    def test_only_existing_dirs_with_sizes(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        a = os.path.join(d, "a")
        os.makedirs(a)
        with open(os.path.join(a, "f.bin"), "wb") as f:
            f.write(b"z" * 700)
        missing = os.path.join(d, "ghost")
        snap = krylan.take_snapshot([a, missing])
        self.assertEqual(snap, {a: 700})        # ghost отсутствует → не в снимке
        self.assertNotIn(missing, snap)

    def test_empty_when_none_exist(self):
        snap = krylan.take_snapshot(["/no/such/x", "/no/such/y"])
        self.assertEqual(snap, {})


class TestCleanCachesHeadless(unittest.TestCase):
    """clean_caches_headless(dry=True): считает объём, НИЧЕГО не удаляет."""

    def test_dry_run_reports_without_deleting(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        f = os.path.join(d, "cache.bin")
        with open(f, "wb") as fh:
            fh.write(b"q" * 1234)
        orig = krylan.cleanup_targets
        krylan.cleanup_targets = lambda: [("TestCache", d)]
        try:
            freed, lines = krylan.clean_caches_headless(dry=True)
        finally:
            krylan.cleanup_targets = orig
        self.assertEqual(freed, 1234)
        self.assertTrue(any("TestCache" in ln for ln in lines))
        self.assertTrue(os.path.exists(f), "dry-run не должен удалять файлы")


class TestOptimizeAllPlan(unittest.TestCase):
    """optimize_all_plan(dry=True): собирает шаги и байты, НИЧЕГО не удаляет."""

    def _setup_home(self):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        # кэш-цель с файлом
        cache = os.path.join(home, "cache")
        os.makedirs(cache)
        with open(os.path.join(cache, "c.bin"), "wb") as f:
            f.write(b"c" * 2000)
        # пустая папка в Downloads
        dl = os.path.join(home, "Downloads")
        os.makedirs(os.path.join(dl, "emptydir"))
        # нулевой (битый) файл на Desktop
        desk = os.path.join(home, "Desktop")
        os.makedirs(desk)
        open(os.path.join(desk, "zero.txt"), "w").close()
        return home, cache

    def test_dry_run_collects_steps_without_deleting(self):
        home, cache = self._setup_home()
        orig_home, orig_targets = krylan.HOME, krylan.cleanup_targets
        krylan.HOME = home
        krylan.cleanup_targets = lambda: [("AppCache", cache)]
        emitted = []
        try:
            plan = krylan.optimize_all_plan(dry=True, emit=emitted.append)
        finally:
            krylan.HOME, krylan.cleanup_targets = orig_home, orig_targets
        # первые три безопасных шага (кэши/пустые/битые) всегда присутствуют;
        # дальше — ОС-зависимые шаги, их число варьируется по устройству
        self.assertGreaterEqual(len(plan["steps"]), 3)
        self.assertTrue(any("Кэши и логи" in s for s in plan["steps"][:3]))
        self.assertTrue(any("Пустые папки" in s for s in plan["steps"][:3]))
        self.assertTrue(any("Битые" in s for s in plan["steps"][:3]))
        # прогресс прокинут через emit для каждого выполненного шага
        self.assertEqual(emitted, plan["steps"])
        # кэш посчитан в освобождённых байтах
        self.assertEqual(plan["details"]["caches"], 2000)
        self.assertGreaterEqual(plan["freed"], 2000)
        # найдена пустая папка и битый файл
        self.assertEqual(plan["details"]["empty_dirs"], 1)
        self.assertEqual(plan["details"]["broken"], 1)
        # dry-run ничего не удаляет
        self.assertTrue(os.path.exists(os.path.join(cache, "c.bin")))
        self.assertTrue(os.path.isdir(os.path.join(home, "Downloads", "emptydir")))
        self.assertTrue(os.path.exists(os.path.join(home, "Desktop", "zero.txt")))

    def test_skips_running_browser_cache(self):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        ch = os.path.join(home, "chrome_cache")
        os.makedirs(ch)
        with open(os.path.join(ch, "x"), "wb") as f:
            f.write(b"x" * 500)
        orig_home, orig_targets = krylan.HOME, krylan.cleanup_targets
        krylan.HOME = home
        krylan.cleanup_targets = lambda: [("Кэш Chrome", ch)]
        try:
            plan = krylan.optimize_all_plan(dry=True, browsers_running={"Chrome"})
        finally:
            krylan.HOME, krylan.cleanup_targets = orig_home, orig_targets
        # кэш Chrome пропущен → не учтён в байтах, есть запись в skipped
        self.assertEqual(plan["details"]["caches"], 0)
        self.assertTrue(any("Chrome" in s for s in plan["skipped"]))

    def test_is_browser_cache_detection(self):
        self.assertEqual(krylan._is_browser_cache("Кэш Chrome"), "Chrome")
        self.assertEqual(krylan._is_browser_cache("Кэш Microsoft Edge"), "Edge")
        self.assertIsNone(krylan._is_browser_cache("Временные файлы"))


class TestDiskMaintenancePlan(unittest.TestCase):
    """disk_maintenance_plan: чистая функция плана обслуживания накопителя."""

    def test_windows_ssd_trim(self):
        # defrag требует прав администратора → с admin выполняем TRIM (/L)
        cmd, label, do = krylan.disk_maintenance_plan("Windows", "SSD", True)
        self.assertTrue(do)
        self.assertIn("defrag", cmd)
        self.assertIn("/L", cmd)                 # TRIM-режим, НЕ дефраг
        self.assertNotIn("/O", cmd)

    def test_windows_hdd_defrag(self):
        cmd, label, do = krylan.disk_maintenance_plan("Windows", "HDD", True)
        self.assertTrue(do)
        self.assertIn("/O", cmd)                 # дефраг только для HDD

    def test_windows_ssd_needs_admin(self):
        # без прав администратора defrag /L пропускается с понятной пометкой
        cmd, label, do = krylan.disk_maintenance_plan("Windows", "SSD", False)
        self.assertFalse(do)
        self.assertIsNone(cmd)
        self.assertIn("администратор", label.lower())

    def test_windows_hdd_needs_admin(self):
        cmd, label, do = krylan.disk_maintenance_plan("Windows", "HDD", False)
        self.assertFalse(do)
        self.assertIsNone(cmd)
        self.assertIn("администратор", label.lower())

    def test_linux_ssd_trim_needs_root(self):
        # без root → пропуск с причиной, команда не выполняется
        cmd, label, do = krylan.disk_maintenance_plan("Linux", "SSD", False)
        self.assertFalse(do)
        self.assertIsNone(cmd)
        self.assertIn("root", label.lower())
        # с root → выполняем fstrim
        cmd, label, do = krylan.disk_maintenance_plan("Linux", "SSD", True)
        self.assertTrue(do)
        self.assertIn("fstrim", cmd)

    def test_linux_hdd_no_defrag(self):
        cmd, label, do = krylan.disk_maintenance_plan("Linux", "HDD", True)
        self.assertFalse(do)                     # ext4/btrfs: дефраг не нужен
        self.assertIsNone(cmd)

    def test_macos_ssd_skip_auto(self):
        cmd, label, do = krylan.disk_maintenance_plan("Darwin", "SSD", True)
        self.assertFalse(do)                     # TRIM автоматический → только пометка
        self.assertIsNone(cmd)

    def test_macos_hdd_skip(self):
        cmd, label, do = krylan.disk_maintenance_plan("Darwin", "HDD", False)
        self.assertFalse(do)                     # APFS не дефрагментируется

    def test_unknown_media_skipped(self):
        cmd, label, do = krylan.disk_maintenance_plan("Linux", None, True)
        self.assertFalse(do)
        self.assertIsNone(cmd)

    def test_ssd_never_defragmented(self):
        # ключевое правило безопасности: ни на одной ОС SSD не получает /O
        for system in ("Windows", "Darwin", "Linux"):
            for root in (True, False):
                cmd, label, do = krylan.disk_maintenance_plan(system, "SSD", root)
                if cmd:
                    self.assertNotIn("/O", cmd, f"{system}/SSD не должен дефрагментироваться")


class TestDnsFlushPlan(unittest.TestCase):
    def test_per_os_command(self):
        self.assertEqual(krylan.dns_flush_plan("Windows")[0], ["ipconfig", "/flushdns"])
        self.assertIn("dscacheutil", krylan.dns_flush_plan("Darwin")[0])
        self.assertIn("resolvectl", krylan.dns_flush_plan("Linux")[0])


class TestRunHelper(unittest.TestCase):
    """run(): безопасная обёртка subprocess — никогда не бросает."""

    def test_missing_binary_returns_nonzero(self):
        r = krylan.run(["krylan-no-such-binary-xyz"])
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "")

    def test_real_command_runs(self):
        r = krylan.run(["echo", "hi"])
        self.assertEqual(r.returncode, 0)
        self.assertIn("hi", r.stdout)


class TestOptimizePlanExtendedSafety(unittest.TestCase):
    """Расширенный план: дополнительные ОС-шаги, БЕЗ небезопасных действий."""

    def _setup_home(self):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        cache = os.path.join(home, "cache")
        os.makedirs(cache)
        with open(os.path.join(cache, "c.bin"), "wb") as f:
            f.write(b"c" * 2000)
        return home, cache

    def test_dry_run_no_unsafe_steps(self):
        home, cache = self._setup_home()
        orig_home, orig_targets = krylan.HOME, krylan.cleanup_targets
        # детект/права делаем детерминированными, чтобы не зависеть от хоста
        orig_media, orig_root = krylan.detect_media_type, krylan.has_root
        krylan.HOME = home
        krylan.cleanup_targets = lambda: [("AppCache", cache)]
        krylan.detect_media_type = lambda: "SSD"
        krylan.has_root = lambda: False
        try:
            plan = krylan.optimize_all_plan(dry=True)
        finally:
            (krylan.HOME, krylan.cleanup_targets,
             krylan.detect_media_type, krylan.has_root) = (
                orig_home, orig_targets, orig_media, orig_root)
        blob = " ".join(plan["steps"] + plan["skipped"]).lower()
        # НЕТ небезопасных операций: дефраг SSD, очистка Корзины, реестр, службы
        self.assertNotIn("/o", " ".join(plan["steps"]).lower())  # SSD не дефрагментируется
        # перемещение В Корзину безопасно; запрещены: очистка Корзины, реестр, службы
        for forbidden in ("очистить корзин", "очистка корзин", "empty trash",
                          "реестр", "registry", "остановить служб", "stop service"):
            self.assertNotIn(forbidden, blob, f"небезопасный шаг: {forbidden}")
        # план структурирован
        self.assertIn("media_type", plan["details"])
        self.assertIsInstance(plan["skipped"], list)

    def test_dry_run_does_not_delete(self):
        home, cache = self._setup_home()
        orig_home, orig_targets = krylan.HOME, krylan.cleanup_targets
        orig_media, orig_root = krylan.detect_media_type, krylan.has_root
        krylan.HOME = home
        krylan.cleanup_targets = lambda: [("AppCache", cache)]
        krylan.detect_media_type = lambda: None
        krylan.has_root = lambda: False
        try:
            krylan.optimize_all_plan(dry=True)
        finally:
            (krylan.HOME, krylan.cleanup_targets,
             krylan.detect_media_type, krylan.has_root) = (
                orig_home, orig_targets, orig_media, orig_root)
        self.assertTrue(os.path.exists(os.path.join(cache, "c.bin")))


class TestParsePhysicalDiskMediaType(unittest.TestCase):
    """Парсер вывода PowerShell Get-PhysicalDisk … MediaType (Windows)."""

    def test_format_list_ssd(self):
        txt = "\nMediaType : SSD\n\n"
        self.assertEqual(krylan.parse_physicaldisk_mediatype(txt), "SSD")

    def test_format_list_hdd(self):
        txt = "MediaType : HDD\n"
        self.assertEqual(krylan.parse_physicaldisk_mediatype(txt), "HDD")

    def test_unspecified_is_none(self):
        txt = "MediaType : Unspecified\n"
        self.assertIsNone(krylan.parse_physicaldisk_mediatype(txt))

    def test_numeric_enum(self):
        # старые сборки могут отдавать числовой enum: 4=SSD, 3=HDD
        self.assertEqual(krylan.parse_physicaldisk_mediatype("MediaType : 4"), "SSD")
        self.assertEqual(krylan.parse_physicaldisk_mediatype("MediaType : 3"), "HDD")

    def test_plain_value_no_colon(self):
        self.assertEqual(krylan.parse_physicaldisk_mediatype("SSD\n"), "SSD")

    def test_mixed_prefers_explicit_over_unspecified(self):
        # внешний HDD "Unspecified" + системный SSD → SSD выигрывает
        txt = "MediaType : Unspecified\n\nMediaType : SSD\n"
        self.assertEqual(krylan.parse_physicaldisk_mediatype(txt), "SSD")

    def test_empty_is_none(self):
        self.assertIsNone(krylan.parse_physicaldisk_mediatype(""))
        self.assertIsNone(krylan.parse_physicaldisk_mediatype("   \n\n"))


class TestNoWindowKwargs(unittest.TestCase):
    """_no_window_kwargs: прячет консоль только на Windows, иначе пусто."""

    def test_non_windows_empty(self):
        orig = krylan.SYSTEM
        try:
            for sysname in ("Darwin", "Linux"):
                krylan.SYSTEM = sysname
                self.assertEqual(krylan._no_window_kwargs(), {})
        finally:
            krylan.SYSTEM = orig

    def test_windows_sets_creationflags(self):
        # на Windows должен попасть creationflags с CREATE_NO_WINDOW (0x08000000).
        # На Mac у subprocess нет CREATE_NO_WINDOW/STARTUPINFO — проверяем,
        # что функция не падает и отдаёт корректный флаг через getattr-fallback.
        orig = krylan.SYSTEM
        try:
            krylan.SYSTEM = "Windows"
            kw = krylan._no_window_kwargs()
            self.assertIn("creationflags", kw)
            self.assertTrue(kw["creationflags"] & 0x08000000)
        finally:
            krylan.SYSTEM = orig


class TestWindowsPaths(unittest.TestCase):
    """cleanup_targets / privacy_targets / thumbnail_targets на Windows:
    пути строятся из env (TEMP/LOCALAPPDATA/APPDATA), без unix-путей."""

    def _patch_windows_env(self, home):
        # типовое окружение Windows-пользователя
        local = os.path.join(home, "AppData", "Local")
        roam = os.path.join(home, "AppData", "Roaming")
        temp = os.path.join(local, "Temp")
        for p in (local, roam, temp):
            os.makedirs(p, exist_ok=True)
        env = {"TEMP": temp, "LOCALAPPDATA": local, "APPDATA": roam,
               "USERPROFILE": home, "SystemDrive": "C:"}
        return env, local, roam, temp

    def test_cleanup_targets_use_env(self):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        env, local, roam, temp = self._patch_windows_env(home)
        orig_sys, orig_home, orig_env = krylan.SYSTEM, krylan.HOME, os.environ.copy()
        try:
            krylan.SYSTEM = "Windows"
            krylan.HOME = home
            os.environ.update(env)
            targets = krylan.cleanup_targets()
            paths = [p for _n, p in targets]
            # TEMP существует → присутствует в целях; нет unix-путей
            self.assertTrue(any(p == temp for p in paths))
            for _n, p in targets:
                self.assertFalse(p.startswith("/dev"))
                self.assertNotIn("/.cache", p)
                self.assertTrue(os.path.isdir(p))
        finally:
            krylan.SYSTEM, krylan.HOME = orig_sys, orig_home
            os.environ.clear(); os.environ.update(orig_env)

    def test_thumbnail_targets_windows_glob(self):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        env, local, roam, temp = self._patch_windows_env(home)
        expl = os.path.join(local, "Microsoft", "Windows", "Explorer")
        os.makedirs(expl, exist_ok=True)
        db = os.path.join(expl, "thumbcache_1024.db")
        open(db, "w").close()
        orig_sys, orig_home, orig_env = krylan.SYSTEM, krylan.HOME, os.environ.copy()
        try:
            krylan.SYSTEM = "Windows"
            krylan.HOME = home
            os.environ.update(env)
            tg = krylan.thumbnail_targets()
            self.assertIn(db, tg)
        finally:
            krylan.SYSTEM, krylan.HOME = orig_sys, orig_home
            os.environ.clear(); os.environ.update(orig_env)

    def test_privacy_targets_windows_no_unix_paths(self):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        env, local, roam, temp = self._patch_windows_env(home)
        # создаём один реальный след: Chrome History
        chrome = os.path.join(local, "Google", "Chrome", "User Data", "Default")
        os.makedirs(chrome, exist_ok=True)
        hist = os.path.join(chrome, "History")
        open(hist, "w").close()
        orig_sys, orig_home, orig_env = krylan.SYSTEM, krylan.HOME, os.environ.copy()
        try:
            krylan.SYSTEM = "Windows"
            krylan.HOME = home
            os.environ.update(env)
            tg = krylan.privacy_targets()
            paths = [p for _b, _i, p in tg]
            self.assertIn(hist, paths)
            for p in paths:
                self.assertNotIn("/.config", p)
                self.assertNotIn("/Library/", p)
        finally:
            krylan.SYSTEM, krylan.HOME = orig_sys, orig_home
            os.environ.clear(); os.environ.update(orig_env)


class TestDnsFlushWindows(unittest.TestCase):
    def test_windows_flushdns_no_console(self):
        cmd, label = krylan.dns_flush_plan("Windows")
        self.assertEqual(cmd, ["ipconfig", "/flushdns"])
        self.assertIn("flushdns", label)


class TestScheduleNoScheduler(unittest.TestCase):
    """Регрессия: если планировщик (crontab/launchctl/schtasks) отсутствует,
    schedule_enable/disable не должны ронять Tk-callback FileNotFoundError —
    обязаны вернуть False, а не выбросить исключение."""

    def setUp(self):
        import subprocess
        self._sub = subprocess
        self._orig_run = subprocess.run
        # Linux-ветка вызывает subprocess.run сразу (без записи plist на диск),
        # поэтому подмена SYSTEM избегает побочных эффектов на тест-машине.
        self._orig_system = krylan.SYSTEM
        krylan.SYSTEM = "Linux"

        def boom(*a, **k):
            raise FileNotFoundError("scheduler binary missing")
        subprocess.run = boom

    def tearDown(self):
        self._sub.run = self._orig_run
        krylan.SYSTEM = self._orig_system

    def test_enable_does_not_raise(self):
        self.assertFalse(krylan.schedule_enable())

    def test_disable_does_not_raise(self):
        self.assertFalse(krylan.schedule_disable())


class TestParseChromiumExtension(unittest.TestCase):
    def test_plain_name(self):
        man = {"name": "uBlock Origin", "version": "1.0"}
        self.assertEqual(krylan.parse_chromium_extension(man), "uBlock Origin")

    def test_name_with_whitespace(self):
        man = {"name": "  Dark Reader  "}
        self.assertEqual(krylan.parse_chromium_extension(man), "Dark Reader")

    def test_msg_resolved_from_messages(self):
        man = {"name": "__MSG_appName__", "default_locale": "en"}
        msgs = {"appName": {"message": "Awesome Extension"}}
        self.assertEqual(krylan.parse_chromium_extension(man, msgs), "Awesome Extension")

    def test_msg_case_insensitive_key(self):
        man = {"name": "__MSG_appName__"}
        msgs = {"appname": {"message": "Lower Key Ext"}}
        self.assertEqual(krylan.parse_chromium_extension(man, msgs), "Lower Key Ext")

    def test_msg_without_messages_falls_back_to_key(self):
        man = {"name": "__MSG_extName__"}
        self.assertEqual(krylan.parse_chromium_extension(man, None), "extName")

    def test_msg_missing_entry_falls_back_to_key(self):
        man = {"name": "__MSG_extName__"}
        self.assertEqual(krylan.parse_chromium_extension(man, {"other": {"message": "x"}}), "extName")

    def test_no_name(self):
        self.assertEqual(krylan.parse_chromium_extension({"version": "1.0"}), "")

    def test_empty_name(self):
        self.assertEqual(krylan.parse_chromium_extension({"name": "   "}), "")

    def test_non_dict_manifest(self):
        self.assertEqual(krylan.parse_chromium_extension(None), "")


class TestListBrowserExtensions(unittest.TestCase):
    def test_returns_list_and_graceful(self):
        # На любой ОС без падений; элементы — кортежи из 3 строк.
        res = krylan.list_browser_extensions()
        self.assertIsInstance(res, list)
        for item in res:
            self.assertEqual(len(item), 3)
            browser, name, ext_id = item
            self.assertIsInstance(browser, str)
            self.assertIsInstance(name, str)
            self.assertIsInstance(ext_id, str)

    def test_reads_real_chromium_layout(self):
        # Создаём фейковый профиль Chrome и проверяем разбор имени из manifest.
        import json
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        ext_id = "abcdefghijklmnopabcdefghijklmnop"
        vdir = os.path.join(base, "Default", "Extensions", ext_id, "2.1.0")
        os.makedirs(vdir)
        with open(os.path.join(vdir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump({"name": "Test Ext", "version": "2.1.0"}, f)

        orig = krylan._chromium_ext_profiles
        orig_system = krylan.SYSTEM
        krylan._chromium_ext_profiles = lambda: [("Chrome", base)]
        krylan.SYSTEM = "NoSuchOS"  # отключаем Firefox-ветку (пути не существуют)
        try:
            res = krylan.list_browser_extensions()
        finally:
            krylan._chromium_ext_profiles = orig
            krylan.SYSTEM = orig_system
        self.assertIn(("Chrome", "Test Ext", ext_id), res)

    def test_msg_name_resolved_from_locales(self):
        import json
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        ext_id = "msgextidmsgextidmsgextidmsgextid"
        vdir = os.path.join(base, "Default", "Extensions", ext_id, "1.0")
        os.makedirs(os.path.join(vdir, "_locales", "en"))
        with open(os.path.join(vdir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump({"name": "__MSG_appName__", "default_locale": "en"}, f)
        with open(os.path.join(vdir, "_locales", "en", "messages.json"), "w", encoding="utf-8") as f:
            json.dump({"appName": {"message": "Localized Name"}}, f)

        orig = krylan._chromium_ext_profiles
        orig_system = krylan.SYSTEM
        krylan._chromium_ext_profiles = lambda: [("Chrome", base)]
        krylan.SYSTEM = "NoSuchOS"
        try:
            res = krylan.list_browser_extensions()
        finally:
            krylan._chromium_ext_profiles = orig
            krylan.SYSTEM = orig_system
        self.assertIn(("Chrome", "Localized Name", ext_id), res)


class TestOptimizePreview(unittest.TestCase):
    """optimize_preview: строго read-only «сухой» отчёт. Ничего не удаляет,
    возвращает корректный план для SSD/HDD/без-root."""

    def _setup_home(self):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        cache = os.path.join(home, "cache")
        os.makedirs(cache)
        with open(os.path.join(cache, "c.bin"), "wb") as f:
            f.write(b"c" * 2000)
        os.makedirs(os.path.join(home, "Downloads", "emptydir"))
        desk = os.path.join(home, "Desktop")
        os.makedirs(desk)
        open(os.path.join(desk, "zero.txt"), "w").close()
        return home, cache

    def _patch(self, home, cache):
        self._orig_home = krylan.HOME
        self._orig_targets = krylan.cleanup_targets
        self._orig_thumbs = krylan.thumbnail_targets
        krylan.HOME = home
        krylan.cleanup_targets = lambda: [("AppCache", cache)]
        krylan.thumbnail_targets = lambda: []   # детерминизм: миниатюр нет
        self.addCleanup(self._restore)

    def _restore(self):
        krylan.HOME = self._orig_home
        krylan.cleanup_targets = self._orig_targets
        krylan.thumbnail_targets = self._orig_thumbs

    def test_read_only_does_not_delete(self):
        home, cache = self._setup_home()
        self._patch(home, cache)
        plan = krylan.optimize_preview("Darwin", "SSD", True)
        # ничего не удалено
        self.assertTrue(os.path.exists(os.path.join(cache, "c.bin")))
        self.assertTrue(os.path.isdir(os.path.join(home, "Downloads", "emptydir")))
        self.assertTrue(os.path.exists(os.path.join(home, "Desktop", "zero.txt")))
        # подсчёты корректны
        self.assertEqual(plan["details"]["caches"], 2000)
        self.assertEqual(plan["details"]["empty_dirs"], 1)
        self.assertEqual(plan["details"]["broken"], 1)
        self.assertGreaterEqual(plan["freed_est"], 2000)
        # структура отчёта
        self.assertIn("will_do", plan)
        self.assertIn("skipped", plan)
        self.assertTrue(any("Кэши и логи" in s for s in plan["will_do"]))
        self.assertTrue(any("Пустые папки" in s for s in plan["will_do"]))
        self.assertTrue(any("Битые" in s for s in plan["will_do"]))

    def test_macos_ssd_plan(self):
        home, cache = self._setup_home()
        self._patch(home, cache)
        plan = krylan.optimize_preview("Darwin", "SSD", True)
        # SSD на macOS: TRIM автоматический → в пропусках, НЕ дефрагментируется
        self.assertTrue(any("TRIM" in s and "автоматич" in s for s in plan["skipped"]))
        self.assertFalse(any("defrag" in s.lower() for s in plan["will_do"]))
        # с root: purge будет выполнен
        self.assertTrue(any("purge" in s for s in plan["will_do"]))

    def test_linux_hdd_no_root(self):
        home, cache = self._setup_home()
        self._patch(home, cache)
        plan = krylan.optimize_preview("Linux", "HDD", False)
        # HDD Linux: дефраг не требуется → пропуск
        self.assertTrue(any("HDD" in s for s in plan["skipped"]))
        # без root: apt/журналы и глубокая очистка памяти пропущены
        self.assertTrue(any("apt" in s and "root" in s.lower() for s in plan["skipped"]))
        self.assertTrue(any("памяти" in s and "root" in s.lower() for s in plan["skipped"]))
        # sync (без root) попадает в «будет сделано»
        self.assertTrue(any("sync" in s for s in plan["will_do"]))

    def test_windows_ssd_root(self):
        home, cache = self._setup_home()
        self._patch(home, cache)
        plan = krylan.optimize_preview("Windows", "SSD", True)
        # Windows + admin: TRIM (defrag /L) попадает в план «будет сделано»
        self.assertTrue(any("TRIM" in s for s in plan["will_do"]))
        # на Windows безопасного освобождения памяти нет → пропуск
        self.assertTrue(any("Windows" in s for s in plan["skipped"]))

    def test_unknown_media_skips_maintenance(self):
        home, cache = self._setup_home()
        self._patch(home, cache)
        plan = krylan.optimize_preview("Linux", None, True)
        self.assertTrue(any("не определ" in s for s in plan["skipped"]))

    def test_running_browser_cache_skipped(self):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        ch = os.path.join(home, "chrome_cache")
        os.makedirs(ch)
        with open(os.path.join(ch, "x"), "wb") as f:
            f.write(b"x" * 500)
        orig_home, orig_targets, orig_thumbs = (
            krylan.HOME, krylan.cleanup_targets, krylan.thumbnail_targets)
        krylan.HOME = home
        krylan.cleanup_targets = lambda: [("Кэш Chrome", ch)]
        krylan.thumbnail_targets = lambda: []
        try:
            plan = krylan.optimize_preview("Darwin", "SSD", True,
                                           browsers_running={"Chrome"})
        finally:
            krylan.HOME, krylan.cleanup_targets, krylan.thumbnail_targets = (
                orig_home, orig_targets, orig_thumbs)
        self.assertEqual(plan["details"]["caches"], 0)
        self.assertTrue(any("Chrome" in s for s in plan["skipped"]))
        # read-only: файл на месте
        self.assertTrue(os.path.exists(os.path.join(ch, "x")))


class TestShredFile(unittest.TestCase):
    """shred_file: НЕОБРАТИМОЕ затирание обычного файла (перезапись + удаление).
    Защищает симлинки/каталоги/защищённые пути — их не трогает."""

    def test_wipes_and_removes_real_file(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        f = os.path.join(d, "secret.bin")
        with open(f, "wb") as fh:
            fh.write(b"sensitive-data" * 100)
        self.assertTrue(krylan.shred_file(f))
        # файл должен исчезнуть (не Корзина — безвозвратно)
        self.assertFalse(os.path.exists(f))

    def test_multiple_passes(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        f = os.path.join(d, "multi.bin")
        with open(f, "wb") as fh:
            fh.write(b"x" * 5000)
        self.assertTrue(krylan.shred_file(f, passes=3))
        self.assertFalse(os.path.exists(f))

    def test_empty_file_ok(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        f = os.path.join(d, "zero.bin")
        open(f, "w").close()
        self.assertTrue(krylan.shred_file(f))
        self.assertFalse(os.path.exists(f))

    def test_missing_file_returns_false(self):
        self.assertFalse(krylan.shred_file("/no/such/krylan/shred/target.bin"))

    def test_directory_returns_false_and_intact(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        sub = os.path.join(d, "adir")
        os.makedirs(sub)
        with open(os.path.join(sub, "keep.txt"), "wb") as fh:
            fh.write(b"keep")
        # каталог не затирается → False, содержимое цело
        self.assertFalse(krylan.shred_file(sub))
        self.assertTrue(os.path.isdir(sub))
        self.assertTrue(os.path.isfile(os.path.join(sub, "keep.txt")))

    def test_symlink_not_followed_target_intact(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        target = os.path.join(d, "real.bin")
        payload = b"do-not-touch" * 50
        with open(target, "wb") as fh:
            fh.write(payload)
        link = os.path.join(d, "link.bin")
        os.symlink(target, link)
        # по симлинку не идём → False, и ни ссылка, ни цель не затёрты
        self.assertFalse(krylan.shred_file(link))
        self.assertTrue(os.path.islink(link))
        self.assertTrue(os.path.isfile(target))
        with open(target, "rb") as fh:
            self.assertEqual(fh.read(), payload)   # цель не повреждена

    def test_protected_path_refused(self):
        orig = krylan.HOME
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        krylan.HOME = home
        try:
            # сам HOME и стандартные папки — защищены, shred их не трогает
            self.assertFalse(krylan.shred_file(home))
            dl = os.path.join(home, "Downloads")
            os.makedirs(dl)
            self.assertFalse(krylan.shred_file(dl))
            self.assertTrue(os.path.isdir(dl), "защищённая папка должна остаться")
            # относительный/пустой путь — тоже защищён
            self.assertFalse(krylan.shred_file(""))
            self.assertFalse(krylan.shred_file("relative/file.bin"))
        finally:
            krylan.HOME = orig

    def test_passes_clamped(self):
        # passes вне диапазона не должен ронять функцию; файл затирается
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        for passes in (0, -5, 99, "bad"):
            f = os.path.join(d, f"p_{passes}.bin")
            with open(f, "wb") as fh:
                fh.write(b"data")
            self.assertTrue(krylan.shred_file(f, passes=passes))
            self.assertFalse(os.path.exists(f))


class TestStartupApproved(unittest.TestCase):
    def test_enabled_even_first_byte(self):
        # первый байт чётный (0x02) → включено
        blob = bytes([0x02, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        self.assertIs(krylan.parse_startup_approved(blob), True)

    def test_enabled_zero_first_byte(self):
        self.assertIs(krylan.parse_startup_approved(bytes([0x00] + [0]*11)), True)

    def test_disabled_odd_first_byte(self):
        # первый байт нечётный (0x03) → отключено
        blob = bytes([0x03, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        self.assertIs(krylan.parse_startup_approved(blob), False)

    def test_accepts_list_of_ints(self):
        self.assertIs(krylan.parse_startup_approved([6, 0, 0]), True)
        self.assertIs(krylan.parse_startup_approved([7, 0, 0]), False)

    def test_empty_or_none(self):
        self.assertIsNone(krylan.parse_startup_approved(b""))
        self.assertIsNone(krylan.parse_startup_approved([]))
        self.assertIsNone(krylan.parse_startup_approved(None))


class TestDiskCheck(unittest.TestCase):
    def test_no_errors_chkdsk(self):
        txt = ("Windows has scanned the file system and found no problems.\n"
               "No further action is required.\n")
        r = krylan.parse_disk_check(txt)
        self.assertIs(r["errors"], False)
        self.assertTrue(r["summary"])

    def test_no_errors_verifyvolume(self):
        txt = "Verifying volume.\nThe volume appears to be OK.\n"
        self.assertIs(krylan.parse_disk_check(txt)["errors"], False)

    def test_errors_found_chkdsk(self):
        txt = ("Windows found problems with the file system.\n"
               "Run CHKDSK with the /F (fix) option to correct these.\n")
        self.assertIs(krylan.parse_disk_check(txt)["errors"], True)

    def test_errors_corruption(self):
        txt = "The volume was found to be corrupt and unusable.\n"
        self.assertIs(krylan.parse_disk_check(txt)["errors"], True)

    def test_errors_take_priority_over_ok(self):
        # если в выводе есть и «ок», и «проблемы» — считаем как ошибки
        txt = "The volume appears to be OK\nbut errors found on the volume.\n"
        self.assertIs(krylan.parse_disk_check(txt)["errors"], True)

    def test_empty_unknown(self):
        self.assertIsNone(krylan.parse_disk_check("")["errors"])
        self.assertIsNone(krylan.parse_disk_check("   \n  ")["errors"])

    def test_unrecognized_unknown(self):
        self.assertIsNone(krylan.parse_disk_check("some unrelated text")["errors"])


class TestParseJournalDiskUsage(unittest.TestCase):
    """parse_journal_disk_usage: текст `journalctl --disk-usage` → байты."""

    def test_gigabytes(self):
        txt = "Archived and active journals take up 1.2G in the file system."
        self.assertEqual(krylan.parse_journal_disk_usage(txt), int(1.2 * 1024**3))

    def test_megabytes_with_b(self):
        txt = "Journals take up 512.0M in the file system."
        self.assertEqual(krylan.parse_journal_disk_usage(txt), int(512.0 * 1024**2))

    def test_iec_suffix(self):
        # "1.5GiB" — IEC-форма тоже разбирается
        self.assertEqual(krylan.parse_journal_disk_usage("take up 1.5GiB ..."),
                         int(1.5 * 1024**3))

    def test_comma_decimal(self):
        # локали с запятой как десятичным разделителем
        self.assertEqual(krylan.parse_journal_disk_usage("1,5G in fs"),
                         int(1.5 * 1024**3))

    def test_plain_bytes(self):
        self.assertEqual(krylan.parse_journal_disk_usage("take up 4096B"), 4096)

    def test_empty_and_garbage(self):
        self.assertIsNone(krylan.parse_journal_disk_usage(""))
        self.assertIsNone(krylan.parse_journal_disk_usage(None))
        self.assertIsNone(krylan.parse_journal_disk_usage("no numbers here"))


class TestJournaldVacuum(unittest.TestCase):
    """journald_vacuum: на не-Linux пропуск; на Linux без root — пометка прав."""

    def test_non_linux_skips(self):
        orig = krylan.SYSTEM
        try:
            krylan.SYSTEM = "Darwin"
            size, label, did = krylan.journald_vacuum(dry=False)
            self.assertIsNone(size)
            self.assertEqual(label, "")
            self.assertFalse(did)
        finally:
            krylan.SYSTEM = orig

    def test_linux_dry_run_does_not_vacuum(self):
        # dry: читает размер, НЕ вызывает vacuum, did=False
        orig_sys, orig_run = krylan.SYSTEM, krylan.run
        calls = []

        def fake_run(args, timeout=60):
            calls.append(args)
            import subprocess
            if args[:2] == ["journalctl", "--disk-usage"]:
                return subprocess.CompletedProcess(args, 0, "Journals take up 300.0M in fs.", "")
            return subprocess.CompletedProcess(args, 0, "", "")

        try:
            krylan.SYSTEM = "Linux"
            krylan.run = fake_run
            size, label, did = krylan.journald_vacuum(dry=True)
        finally:
            krylan.SYSTEM, krylan.run = orig_sys, orig_run
        self.assertEqual(size, int(300.0 * 1024**2))
        self.assertFalse(did)
        # никакого --vacuum-size в dry-режиме
        self.assertFalse(any("--vacuum-size=100M" in a for a in calls))

    def test_linux_no_root_marks_needs_privileges(self):
        orig_sys, orig_run, orig_root = krylan.SYSTEM, krylan.run, krylan.has_root
        calls = []

        def fake_run(args, timeout=60):
            calls.append(args)
            import subprocess
            if args[:2] == ["journalctl", "--disk-usage"]:
                return subprocess.CompletedProcess(args, 0, "take up 1.0G in fs", "")
            return subprocess.CompletedProcess(args, 0, "", "")

        try:
            krylan.SYSTEM = "Linux"
            krylan.run = fake_run
            krylan.has_root = lambda: False
            size, label, did = krylan.journald_vacuum(dry=False)
        finally:
            krylan.SYSTEM, krylan.run, krylan.has_root = orig_sys, orig_run, orig_root
        self.assertFalse(did)
        self.assertIn("root", label.lower())
        # без root vacuum НЕ выполняется (bounded-команда не зовётся)
        self.assertFalse(any("--vacuum-size=100M" in a for a in calls))

    def test_linux_root_vacuums_bounded(self):
        orig_sys, orig_run, orig_root = krylan.SYSTEM, krylan.run, krylan.has_root
        calls = []

        def fake_run(args, timeout=60):
            calls.append(args)
            import subprocess
            if args[:2] == ["journalctl", "--disk-usage"]:
                return subprocess.CompletedProcess(args, 0, "take up 2.0G in fs", "")
            return subprocess.CompletedProcess(args, 0, "", "")

        try:
            krylan.SYSTEM = "Linux"
            krylan.run = fake_run
            krylan.has_root = lambda: True
            size, label, did = krylan.journald_vacuum(dry=False)
        finally:
            krylan.SYSTEM, krylan.run, krylan.has_root = orig_sys, orig_run, orig_root
        self.assertTrue(did)
        # bounded: оставляет 100М, НЕ полный wipe (--rotate/--vacuum-time не используем)
        self.assertTrue(any(a == ["journalctl", "--vacuum-size=100M"] for a in calls))


class TestFindBrokenShortcuts(unittest.TestCase):
    """find_broken_shortcuts: .desktop с несуществующей целью → найден;
    с существующей → нет. Не дублирует find_broken_files (0-байт/симлинки)."""

    def _write(self, path, text):
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def test_desktop_broken_and_valid(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        # битый: Exec указывает на несуществующий бинарь
        self._write(os.path.join(base, "broken.desktop"),
                    "[Desktop Entry]\nType=Application\nName=Broken\n"
                    "Exec=/no/such/krylan/binary-xyz --flag\n")
        # рабочий: Exec на существующий бинарь (sh почти всегда в PATH/абс. пути)
        real = "/bin/sh" if os.path.exists("/bin/sh") else sys.executable
        self._write(os.path.join(base, "good.desktop"),
                    "[Desktop Entry]\nType=Application\nName=Good\n"
                    "Exec=%s\n" % real)
        res = krylan.find_broken_shortcuts([base])
        names = {os.path.basename(p) for _k, p in res}
        self.assertIn("broken.desktop", names)
        self.assertNotIn("good.desktop", names)

    def test_tryexec_priority(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        # TryExec на отсутствующий путь → битый, даже если Exec валиден
        self._write(os.path.join(base, "t.desktop"),
                    "[Desktop Entry]\nTryExec=/no/such/krylan/try\nExec=/bin/sh\n")
        res = krylan.find_broken_shortcuts([base])
        self.assertIn("t.desktop", {os.path.basename(p) for _k, p in res})

    def test_url_link_broken(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        # Link на несуществующий локальный путь → битый
        self._write(os.path.join(base, "link.desktop"),
                    "[Desktop Entry]\nType=Link\nURL=file:///no/such/krylan/target\n")
        # http-ссылка считается рабочей (не локальная)
        self._write(os.path.join(base, "web.desktop"),
                    "[Desktop Entry]\nType=Link\nURL=https://example.com\n")
        res = krylan.find_broken_shortcuts([base])
        names = {os.path.basename(p) for _k, p in res}
        self.assertIn("link.desktop", names)
        self.assertNotIn("web.desktop", names)

    def test_empty_lnk(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        open(os.path.join(base, "empty.lnk"), "w").close()        # 0 байт → битый
        with open(os.path.join(base, "ok.lnk"), "wb") as f:
            f.write(b"L\x00\x00\x00")                              # не пустой → не трогаем
        res = krylan.find_broken_shortcuts([base])
        names = {os.path.basename(p) for _k, p in res}
        self.assertIn("empty.lnk", names)
        self.assertNotIn("ok.lnk", names)

    def test_no_false_positive_on_plain_files(self):
        # не-ярлыки игнорируются полностью
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        with open(os.path.join(base, "doc.txt"), "w") as f:
            f.write("hello")
        self.assertEqual(krylan.find_broken_shortcuts([base]), [])


class TestScanBigOld(unittest.TestCase):
    """scan_big_old: фильтр размер≥N МБ И возраст≥M дней на temp-дереве."""

    def _mk(self, path, mb, age_days, now):
        with open(path, "wb") as f:
            f.write(b"x" * (mb * 1024 * 1024))
        t = now - age_days * 86400
        os.utime(path, (t, t))

    def test_size_and_age_filter(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        import time
        now = time.time()
        # большой + старый → попадает
        self._mk(os.path.join(base, "big_old.bin"), 3, 400, now)
        # большой, но свежий → нет (возраст < порога)
        self._mk(os.path.join(base, "big_new.bin"), 3, 10, now)
        # маленький, но старый → нет (размер < порога)
        self._mk(os.path.join(base, "small_old.bin"), 1, 400, now)
        res = krylan.scan_big_old(base, min_mb=2, min_days=180, now=now)
        names = {os.path.basename(p) for _s, p, _a in res}
        self.assertIn("big_old.bin", names)
        self.assertNotIn("big_new.bin", names)
        self.assertNotIn("small_old.bin", names)

    def test_sorted_by_size_desc_with_age(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        import time
        now = time.time()
        self._mk(os.path.join(base, "a.bin"), 2, 300, now)
        self._mk(os.path.join(base, "b.bin"), 5, 300, now)
        res = krylan.scan_big_old(base, min_mb=2, min_days=180, now=now)
        sizes = [s for s, _p, _a in res]
        self.assertEqual(sizes, sorted(sizes, reverse=True))
        self.assertEqual(os.path.basename(res[0][1]), "b.bin")   # 5 МБ первым
        # возраст вычислен в днях (≈300)
        self.assertTrue(all(290 <= a <= 310 for _s, _p, a in res))

    def test_skips_symlinks(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        import time
        now = time.time()
        target = os.path.join(base, "real.bin")
        self._mk(target, 3, 400, now)
        link = os.path.join(base, "link.bin")
        os.symlink(target, link)
        res = krylan.scan_big_old(base, min_mb=2, min_days=180, now=now)
        names = [os.path.basename(p) for _s, p, _a in res]
        self.assertIn("real.bin", names)
        self.assertNotIn("link.bin", names)   # симлинк не считаем

    def test_top_limit(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        import time
        now = time.time()
        for i in range(4):
            self._mk(os.path.join(base, f"f{i}.bin"), 2 + i, 400, now)
        res = krylan.scan_big_old(base, min_mb=2, min_days=180, top=2, now=now)
        self.assertEqual(len(res), 2)   # только топ-2 по размеру

    def test_missing_base(self):
        self.assertEqual(krylan.scan_big_old("/no/such/krylan/path", 1, 1), [])


if __name__ == "__main__":
    unittest.main()
