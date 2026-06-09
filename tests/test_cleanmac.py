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


if __name__ == "__main__":
    unittest.main(verbosity=2)
