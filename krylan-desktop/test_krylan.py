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


if __name__ == "__main__":
    unittest.main()
