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


if __name__ == "__main__":
    unittest.main()
