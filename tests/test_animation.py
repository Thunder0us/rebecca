"""Загрузка кадров, реальный таймер Qt и сохранение геометрии окна."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import QEventLoop, Qt, QTimer
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from rebecca.ui.animation import load_animation, load_demo_animation
from rebecca.ui.character_window import CharacterWindow


class AnimationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.sprites = self.root / "sprites"
        self.sprites.mkdir()
        self.window = None
        self.write_png("idle.png", "red")
        self.write_png("walk.png", "blue")

    def tearDown(self):
        if self.window is not None:
            self.window.close()
            self.window.deleteLater()
            self.app.processEvents()
        self.temp.cleanup()

    def write_png(self, name, color, width=4):
        image = QImage(width, 6, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        image.setPixelColor(1, 1, QColor(color))
        path = self.sprites / name
        path.parent.mkdir(parents=True, exist_ok=True)
        self.assertTrue(image.save(str(path), "PNG"))

    def manifest(self, entries):
        (self.root / "animations.json").write_text(
            json.dumps({"version": 1, "animations": entries}), encoding="utf-8")

    def add_frames(self):
        self.write_png("idle/00.png", "green")
        self.write_png("idle/01.png", "blue")
        self.manifest({"idle": {"fps": 8, "frames": ["idle/00.png", "idle/01.png"]}})

    def make_window(self, **kwargs):
        self.window = CharacterWindow(sprites_dir=self.sprites, scale=2, **kwargs)
        self.window.show_character()
        return self.window

    def test_no_manifest_preserves_all_existing_single_png_states(self):
        for state, color in (("idle", "red"), ("walk", "blue")):
            animation = load_animation(state, 2, self.sprites)
            self.assertEqual(len(animation.frames), 1)
            self.assertEqual(animation.frames[0].toImage().pixelColor(2, 2), QColor(color))

    def test_manifest_loads_idle_and_walk_in_explicit_order_with_scaling(self):
        self.add_frames()
        self.manifest({
            "idle": {"fps": 4, "frames": ["idle/01.png", "idle/00.png"]},
            "walk": {"fps": 8, "frames": ["idle/00.png", "idle/01.png"]},
        })
        for state, fps, first in (("idle", 4, "blue"), ("walk", 8, "green")):
            clip = load_animation(state, 3, self.sprites)
            self.assertEqual(clip.fps, fps)
            self.assertEqual(len(clip.frames), 2)
            self.assertEqual((clip.frames[0].width(), clip.frames[0].height()), (12, 18))
            self.assertEqual(clip.frames[0].toImage().pixelColor(3, 3), QColor(first))
            self.assertEqual(clip.frames[0].toImage().pixelColor(0, 0).alpha(), 0)

    def test_bad_manifest_entries_fall_back_to_single_png(self):
        entries = (
            [], {}, {"fps": 0, "frames": ["idle.png"]},
            {"fps": 31, "frames": ["idle.png"]}, {"fps": True, "frames": ["idle.png"]},
            {"fps": 8, "frames": []}, {"fps": 8, "frames": ["idle.png"] * 33},
            {"fps": 8, "frames": [123]}, {"fps": 8, "frames": ["missing.png"]},
            {"fps": 8, "frames": ["../outside.png"]},
        )
        for entry in entries:
            with self.subTest(entry=entry):
                self.manifest({"idle": entry})
                with self.assertLogs("rebecca.ui.animation", level="WARNING"):
                    clip = load_animation("idle", 1, self.sprites)
                self.assertEqual(len(clip.frames), 1)
                self.assertEqual(clip.frames[0].toImage().pixelColor(1, 1), QColor("red"))

    def test_bad_json_version_and_oversized_manifest_fall_back(self):
        for raw in ("{broken", "[]", '{"version": 2, "animations": {}}', " " * 65537):
            with self.subTest(raw=raw[:20]):
                (self.root / "animations.json").write_text(raw, encoding="utf-8")
                with self.assertLogs("rebecca.ui.animation", level="WARNING"):
                    clip = load_animation("idle", 1, self.sprites)
                self.assertEqual(len(clip.frames), 1)

    def test_mismatched_and_corrupt_frames_do_not_mix_with_valid_frames(self):
        self.add_frames()
        self.write_png("idle/01.png", "blue", width=5)
        with self.assertLogs("rebecca.ui.animation", level="WARNING"):
            clip = load_animation("idle", 1, self.sprites)
        self.assertEqual(len(clip.frames), 1)
        (self.sprites / "idle/01.png").write_bytes(b"broken")
        with self.assertLogs("rebecca.ui.animation", level="WARNING"):
            clip = load_animation("idle", 1, self.sprites)
        self.assertEqual(len(clip.frames), 1)

    def test_missing_static_and_animation_files_use_original_placeholder(self):
        clip = load_animation("sleep", 2, self.sprites)
        self.assertEqual((clip.frames[0].width(), clip.frames[0].height()), (32, 48))

    def test_demo_has_distinct_frames_and_does_not_modify_user_png(self):
        before = (self.sprites / "idle.png").read_bytes()
        for state in ("idle", "walk"):
            demo = load_demo_animation(state, 2)
            self.assertGreater(len(demo.frames), 1)
            self.assertTrue(any(frame.toImage() != demo.frames[0].toImage() for frame in demo.frames))
            self.assertTrue(all(frame.size() == demo.frames[0].size() for frame in demo.frames))
        self.assertEqual((self.sprites / "idle.png").read_bytes(), before)

    def test_frames_wrap_without_reading_files_or_moving_window(self):
        self.add_frames()
        window = self.make_window()
        geometry = window.geometry()
        first = window._sprite.toImage()
        with patch("rebecca.ui.animation.read_png", side_effect=AssertionError("повторная загрузка")):
            window._advance_frame()
            self.assertNotEqual(window._sprite.toImage(), first)
            window._advance_frame()
        self.assertEqual(window._sprite.toImage(), first)
        self.assertEqual(window.geometry(), geometry)

    def test_pause_hide_restore_and_close_control_one_timer(self):
        self.add_frames()
        window = self.make_window()
        self.assertEqual(len(window.findChildren(QTimer)), 1)
        self.assertTrue(window._animation_timer.isActive())
        window.context_menu.pause_action.trigger()
        self.assertFalse(window._animation_timer.isActive())
        index = window._frame_index
        window._advance_frame()
        self.assertEqual(window._frame_index, index)
        window.set_hide_available(lambda: True)
        window.toggle_visibility()
        window.show_character()
        self.assertFalse(window._animation_timer.isActive())  # пауза сохранена
        window.toggle_pause()
        self.assertTrue(window._animation_timer.isActive())
        window.toggle_visibility()
        self.assertFalse(window._animation_timer.isActive())
        window._advance_frame()
        self.assertEqual(window._frame_index, index)
        window.show_character()
        self.assertTrue(window._animation_timer.isActive())
        window.close()
        self.assertFalse(window._animation_timer.isActive())

    def test_single_png_does_not_start_a_timer(self):
        window = self.make_window()
        self.assertFalse(window._animation_timer.isActive())

    def test_real_qt_timer_advances_a_frame(self):
        self.add_frames()
        window = self.make_window()
        first = window._sprite.toImage()
        loop = QEventLoop()
        window._animation_timer.timeout.connect(loop.quit)
        watchdog = QTimer()
        watchdog.setSingleShot(True)
        watchdog.timeout.connect(loop.quit)
        watchdog.start(2000)
        loop.exec()
        self.assertNotEqual(window._sprite.toImage(), first)
        self.assertTrue(watchdog.isActive(), "Таймер анимации не сработал")
        watchdog.stop()

    def test_flip_mirrors_actual_painted_pixels_without_changing_geometry(self):
        window = self.make_window()
        geometry = window.geometry()
        original = window.grab().toImage()
        window.context_menu.flip_action.trigger()
        mirrored = window.grab().toImage()
        self.assertEqual(window.geometry(), geometry)
        for y in range(original.height()):
            for x in range(original.width()):
                self.assertEqual(original.pixelColor(x, y),
                                 mirrored.pixelColor(original.width() - 1 - x, y))
        window.context_menu.flip_action.trigger()
        self.assertEqual(window.grab().toImage(), original)


if __name__ == "__main__":
    unittest.main()
