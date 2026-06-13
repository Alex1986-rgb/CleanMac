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


if __name__ == "__main__":
    unittest.main(verbosity=2)
