"""Логика трея без настоящей панели Windows; доступность подставляется в тестах."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from rebecca.ui.character_window import CharacterWindow
from rebecca.ui.tray import create_tray


class TrayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.window = CharacterWindow(sprites_dir=Path(self.directory.name))
        self.window.show_character()
        self.tray = None

    def tearDown(self):
        if self.tray is not None:
            self.tray.hide()
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()
        self.directory.cleanup()

    def test_without_tray_hiding_is_disabled_and_window_stays_visible(self):
        with patch.object(QSystemTrayIcon, "isSystemTrayAvailable", return_value=False):
            with self.assertLogs("rebecca.ui.tray", level="WARNING"):
                self.assertIsNone(create_tray(self.window))
            self.assertFalse(self.window.context_menu.visibility_action.isEnabled())
            self.window.toggle_visibility()
            self.assertTrue(self.window.isVisible())

    def test_tray_has_icon_and_shares_the_same_menu(self):
        with patch.object(QSystemTrayIcon, "isSystemTrayAvailable", return_value=True):
            self.tray = create_tray(self.window)
            self.assertTrue(self.tray.isVisible())
            self.assertFalse(self.tray.icon().isNull())
            self.assertIs(self.tray.contextMenu(), self.window.context_menu)
            self.assertTrue(self.window.context_menu.visibility_action.isEnabled())

    def test_hide_and_restore_preserve_position_and_pause(self):
        with patch.object(QSystemTrayIcon, "isSystemTrayAvailable", return_value=True):
            self.tray = create_tray(self.window)
            self.window.move(120, 130)
            self.window.context_menu.pause_action.trigger()
            self.window.context_menu.visibility_action.trigger()
            self.assertFalse(self.window.isVisible())
            self.assertTrue(self.tray.isVisible())
            self.assertEqual(self.window.context_menu.visibility_action.text(), "Показать")
            self.window.context_menu.visibility_action.trigger()
            self.assertTrue(self.window.isVisible())
            self.assertEqual((self.window.x(), self.window.y()), (120, 130))
            self.assertEqual(self.window.context_menu.pause_action.text(), "Продолжить")

    def test_double_click_restores_window_to_visible_work_area(self):
        with patch.object(QSystemTrayIcon, "isSystemTrayAvailable", return_value=True):
            self.tray = create_tray(self.window)
            self.window.toggle_visibility()
            self.window.move(-100000, -100000)
            self.tray.activated.emit(QSystemTrayIcon.ActivationReason.DoubleClick)
            self.assertTrue(self.window.isVisible())
            self.assertTrue(self.app.primaryScreen().availableGeometry().contains(self.window.geometry()))

    def test_tray_loss_prevents_new_hiding(self):
        with patch.object(QSystemTrayIcon, "isSystemTrayAvailable", return_value=True):
            self.tray = create_tray(self.window)
        with patch.object(QSystemTrayIcon, "isSystemTrayAvailable", return_value=False):
            self.window.context_menu.aboutToShow.emit()
            self.assertFalse(self.window.context_menu.visibility_action.isEnabled())
            self.window.toggle_visibility()
            self.assertTrue(self.window.isVisible())

    def test_exit_from_tray_while_hidden_ends_process_loop_and_removes_icon(self):
        timed_out = []
        watchdog = QTimer()
        watchdog.setSingleShot(True)
        watchdog.timeout.connect(lambda: (timed_out.append(True), self.app.quit()))
        with patch.object(QSystemTrayIcon, "isSystemTrayAvailable", return_value=True):
            self.tray = create_tray(self.window)
            self.window.toggle_visibility()
            self.assertFalse(self.window.isVisible())
            watchdog.start(2000)
            QTimer.singleShot(0, self.window.context_menu.exit_action.trigger)
            self.assertEqual(self.app.exec(), 0)
            watchdog.stop()
        self.assertFalse(timed_out)
        self.assertFalse(self.window.isVisible())
        self.assertFalse(self.tray.isVisible())


if __name__ == "__main__":
    unittest.main()
