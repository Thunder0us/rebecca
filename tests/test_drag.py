"""События drag и границы проверяются без настоящего Windows-дисплея."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QRect, QSize, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from rebecca.platform.displays import clamp_to_work_area
from rebecca.ui.character_window import CharacterWindow


class WorkAreaTests(unittest.TestCase):
    def test_all_edges_and_negative_coordinates(self):
        area = QRect(-1920, -200, 1920, 1040)
        size = QSize(64, 96)
        for requested, expected in (
            (QPoint(-2000, -300), QPoint(-1920, -200)),
            (QPoint(100, 1000), QPoint(-64, 744)),
            (QPoint(-500, 100), QPoint(-500, 100)),
        ):
            with self.subTest(requested=requested):
                actual = clamp_to_work_area(requested, size, area)
                self.assertEqual(actual, expected)
                self.assertTrue(area.contains(QRect(actual, size)))

    def test_tiny_work_area_anchors_window_at_visible_origin(self):
        self.assertEqual(
            clamp_to_work_area(QPoint(500, 500), QSize(64, 96), QRect(10, 20, 30, 40)),
            QPoint(10, 20),
        )


class DragTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = CharacterWindow()
        self.window.move(100, 100)

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def send_mouse(self, kind, global_pos, button, buttons):
        local = global_pos - self.window.pos()
        event = QMouseEvent(kind, QPointF(local), QPointF(global_pos), button, buttons,
                            Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(self.window, event)

    def press(self, position):
        self.send_mouse(QEvent.Type.MouseButtonPress, position,
                        Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton)

    def move(self, position, buttons=Qt.MouseButton.LeftButton):
        self.send_mouse(QEvent.Type.MouseMove, position, Qt.MouseButton.NoButton, buttons)

    def release(self, position):
        self.send_mouse(QEvent.Type.MouseButtonRelease, position,
                        Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton)

    def test_drag_preserves_grab_offset_and_stops_on_release(self):
        self.press(QPoint(115, 120))
        self.assertEqual(self.window.pos(), QPoint(100, 100))
        self.move(QPoint(215, 220))
        self.assertEqual(self.window.pos(), QPoint(200, 200))
        self.release(QPoint(225, 230))
        self.assertEqual(self.window.pos(), QPoint(210, 210))
        self.move(QPoint(300, 300))
        self.assertEqual(self.window.pos(), QPoint(210, 210))

    def test_drag_is_clamped_to_work_area(self):
        self.press(QPoint(115, 120))
        self.move(QPoint(100000, 100000))
        area = self.app.primaryScreen().availableGeometry()
        self.assertTrue(area.contains(self.window.geometry()))
        self.assertEqual(self.window.geometry().bottomRight(), area.bottomRight())
        self.release(QPoint(-100000, -100000))
        self.assertEqual(self.window.pos(), area.topLeft())

    def test_drag_uses_screen_under_cursor(self):
        area = QRect(-1920, -200, 1920, 1040)
        screen = SimpleNamespace(availableGeometry=lambda: area)
        self.press(QPoint(115, 120))
        with patch.object(QApplication, "screenAt", return_value=screen):
            self.move(QPoint(-500, 100))
            self.assertEqual(self.window.pos(), QPoint(-515, 80))
            self.release(QPoint(-10, 100))
        self.assertTrue(area.contains(self.window.geometry()))

    def test_right_button_does_not_drag(self):
        self.send_mouse(QEvent.Type.MouseButtonPress, QPoint(115, 120),
                        Qt.MouseButton.RightButton, Qt.MouseButton.RightButton)
        self.move(QPoint(215, 220), Qt.MouseButton.RightButton)
        self.assertEqual(self.window.pos(), QPoint(100, 100))

    def test_lost_left_button_does_not_leave_drag_active(self):
        self.press(QPoint(115, 120))
        self.move(QPoint(215, 220), Qt.MouseButton.NoButton)
        self.move(QPoint(300, 300))
        self.assertEqual(self.window.pos(), QPoint(100, 100))

    def test_missing_screen_restores_visibility(self):
        self.window.move(-5000, -5000)
        # Ни центр окна, ни курсор не обязаны попадать на подключённый экран.
        with patch.object(QApplication, "screenAt", return_value=None):
            self.window.ensure_visible()
        area = self.app.primaryScreen().availableGeometry()
        self.assertTrue(area.contains(self.window.geometry()))

    def test_work_area_signal_restores_visibility(self):
        class FakeScreen(QObject):
            availableGeometryChanged = Signal(QRect)

            def availableGeometry(self):
                return QRect(0, 0, 320, 240)

        screen = FakeScreen()
        self.window._watch_screen(screen)
        self.window.move(300, 220)
        with patch.object(QApplication, "screenAt", return_value=screen):
            screen.availableGeometryChanged.emit(screen.availableGeometry())
        self.assertTrue(screen.availableGeometry().contains(self.window.geometry()))

    def test_screen_removal_cancels_drag_and_restores_visibility(self):
        self.press(QPoint(115, 120))
        self.window.move(-5000, -5000)
        self.window._screen_removed(self.app.primaryScreen())
        self.app.processEvents()
        self.assertTrue(self.app.primaryScreen().availableGeometry().contains(self.window.geometry()))
        previous = self.window.pos()
        self.move(previous + QPoint(100, 100))
        self.assertEqual(self.window.pos(), previous)


if __name__ == "__main__":
    unittest.main()
