"""PNG создаются только во временной папке; готовые ассеты для тестов не нужны."""

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from rebecca.ui.character_window import CharacterWindow
from rebecca.ui.sprite_renderer import STATES, create_placeholder, load_sprite


class SpriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write_png(self, state="idle", color="#ff4080", width=4, height=6):
        image = QImage(width, height, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        image.setPixelColor(1, 1, QColor(color))
        image.setPixelColor(2, 1, QColor(20, 70, 90, 128))
        self.assertTrue(image.save(str(self.directory / f"{state}.png"), "PNG"))
        return image

    def test_all_six_states_load_their_own_file(self):
        for index, state in enumerate(STATES):
            color = QColor(20 + index * 30, 90, 120)
            self.write_png(state, color.name())
            loaded = load_sprite(state, 1, self.directory).toImage()
            self.assertEqual(loaded.pixelColor(1, 1), color)
            self.assertEqual((loaded.width(), loaded.height()), (4, 6))

    def test_integer_scales_preserve_every_pixel_including_alpha(self):
        original = self.write_png()
        path = self.directory / "idle.png"
        digest = hashlib.sha256(path.read_bytes()).digest()
        for scale in (1, 2, 3, 4, 1):
            result = load_sprite("idle", scale, self.directory).toImage()
            self.assertEqual((result.width(), result.height()), (4 * scale, 6 * scale))
            for y in range(result.height()):
                for x in range(result.width()):
                    # QColor может хранить дробную точность после premultiplied-alpha Qt;
                    # сравниваем исходные 8-битные RGBA, как в файле PNG.
                    self.assertEqual(result.pixelColor(x, y).getRgb(),
                                     original.pixelColor(x // scale, y // scale).getRgb())
        self.assertEqual(hashlib.sha256(path.read_bytes()).digest(), digest)

    def assert_fallback(self, state="idle", scale=2):
        with self.assertLogs("rebecca.ui.sprite_renderer", level="WARNING"):
            result = load_sprite(state, scale, self.directory)
        self.assertEqual(result.toImage(), create_placeholder(scale).toImage())

    def test_missing_state_uses_placeholder_even_if_idle_exists(self):
        self.write_png()
        self.assert_fallback("sleep")

    def test_missing_directory_uses_scaled_placeholder(self):
        with self.assertLogs("rebecca.ui.sprite_renderer", level="WARNING"):
            result = load_sprite("idle", 3, self.directory / "absent")
        self.assertEqual(result.toImage(), create_placeholder(3).toImage())

    def test_corrupt_png_uses_placeholder(self):
        (self.directory / "idle.png").write_bytes(b"not a png")
        self.assert_fallback()

    def test_png_without_alpha_uses_placeholder(self):
        image = QImage(4, 6, QImage.Format.Format_RGB32)
        image.fill(QColor("red"))
        self.assertTrue(image.save(str(self.directory / "idle.png"), "PNG"))
        self.assert_fallback()

    def test_fully_transparent_png_uses_visible_placeholder(self):
        image = QImage(4, 6, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        self.assertTrue(image.save(str(self.directory / "idle.png"), "PNG"))
        self.assert_fallback()

    def test_large_png_cannot_create_large_window(self):
        self.write_png(width=65, height=96)
        self.assert_fallback()
        self.write_png(width=64, height=97)
        self.assert_fallback()

    def test_maximum_supported_source_loads(self):
        self.write_png(width=64, height=96)
        result = load_sprite("idle", 2, self.directory)
        self.assertEqual((result.width(), result.height()), (128, 192))

    def test_invalid_state_and_scale_are_rejected(self):
        for scale in (0, -1, 5, 1.5, True, "2"):
            with self.subTest(scale=scale), self.assertRaises(ValueError):
                load_sprite("idle", scale, self.directory)
        with self.assertRaises(ValueError):
            load_sprite("../outside", 1, self.directory)

    def test_default_directory_does_not_depend_on_current_directory(self):
        self.write_png()
        previous = Path.cwd()
        try:
            os.chdir(self.directory.parent)
            with patch("rebecca.ui.sprite_renderer.DEFAULT_SPRITES_DIR", self.directory):
                result = load_sprite("idle", 1)
            self.assertEqual((result.width(), result.height()), (4, 6))
        finally:
            os.chdir(previous)

    def test_window_matches_png_size_and_feet_stay_above_taskbar(self):
        self.write_png("sit", width=32, height=48)
        window = CharacterWindow("sit", 3, self.directory)
        try:
            area = QRect(-1920, 0, 1920, 1040)
            window.place_above_taskbar(area)
            self.assertEqual((window.width(), window.height()), (96, 144))
            self.assertTrue(area.contains(window.geometry()))
            self.assertEqual(window.geometry().bottom(), area.bottom())
            self.assertTrue(window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
        finally:
            window.close()
            window.deleteLater()
            self.app.processEvents()

    def test_cli_help_and_invalid_scale(self):
        result = subprocess.run([sys.executable, "-m", "rebecca", "--help"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--sprites-dir", result.stdout)
        self.assertIn("happy", result.stdout)
        result = subprocess.run([sys.executable, "-m", "rebecca", "--scale", "0"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
