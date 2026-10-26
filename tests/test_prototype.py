"""Проверки Qt без Windows; нативное поведение проверяется вручную."""

import unittest
from pathlib import Path
import tempfile

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import QApplication, QMenu

from rebecca.ui.character_window import CharacterWindow
from rebecca.ui.sprite_renderer import create_placeholder


class PrototypeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.sprites = tempfile.TemporaryDirectory()
        self.window = CharacterWindow(sprites_dir=Path(self.sprites.name))

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()
        self.sprites.cleanup()

    def test_window_is_small_frameless_and_does_not_request_focus(self):
        self.assertEqual((self.window.width(), self.window.height()), (64, 96))
        self.assertTrue(self.window.windowFlags() & Qt.WindowType.FramelessWindowHint)
        self.assertTrue(self.window.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus)
        self.assertTrue(self.window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
        self.assertTrue(self.window.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating))

    def test_pixel_art_has_transparency_and_solid_pixels(self):
        image = create_placeholder().toImage()
        self.assertEqual(image.pixelColor(0, 0).alpha(), 0)
        self.assertEqual(image.pixelColor(24, 16).alpha(), 255)
        self.assertEqual(image.pixelColor(24, 16), image.pixelColor(27, 19))

    def test_position_respects_work_area_including_negative_origins(self):
        for area in (QRect(0, 0, 1920, 1040), QRect(-1920, -200, 1920, 1040)):
            with self.subTest(area=area):
                self.window.place_above_taskbar(area)
                self.assertTrue(area.contains(self.window.geometry()))
                self.assertEqual(self.window.geometry().bottom(), area.bottom())
                self.assertLessEqual(abs(self.window.geometry().center().x() - area.center().x()), 1)

    def test_right_click_menu_exit_ends_event_loop(self):
        # Предохранитель: тест упадёт, если «Выход» не завершит приложение.
        timed_out = []
        watchdog = QTimer()
        watchdog.setSingleShot(True)
        watchdog.timeout.connect(lambda: (timed_out.append(True), self.app.quit()))

        def open_menu_and_exit():
            event = QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse,
                QPoint(32, 48),
                self.window.mapToGlobal(QPoint(32, 48)),
            )
            QApplication.sendEvent(self.window, event)
            menu = self.window.findChild(QMenu)
            self.assertTrue(menu.isVisible())
            self.assertEqual([action.text() for action in menu.actions() if not action.isSeparator()],
                             ["Пауза", "Скрыть", "Выход"])
            # Как при выборе пункта пользователем, сначала закрывается popup.
            menu.close()
            self.window.context_menu.exit_action.trigger()

        self.window.show()
        watchdog.start(2000)
        QTimer.singleShot(0, open_menu_and_exit)
        self.assertEqual(self.app.exec(), 0)
        watchdog.stop()
        self.assertFalse(timed_out, "Выход не завершил цикл Qt")
        self.assertFalse(self.window.isVisible())


if __name__ == "__main__":
    unittest.main()
