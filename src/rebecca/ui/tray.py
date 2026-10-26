"""Системный трей Qt, без Win32 и внешних изображений."""

import logging

from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from rebecca.ui.character_window import CharacterWindow


class CharacterTray(QSystemTrayIcon):
    def __init__(self, window: CharacterWindow) -> None:
        super().__init__(window.windowIcon(), window)
        self._window = window
        self.setToolTip("Ребекка — ПКМ: меню; двойной клик: показать")
        self.setContextMenu(window.context_menu)
        self.activated.connect(self._on_activated)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._window.show_character()


def create_tray(window: CharacterWindow) -> CharacterTray | None:
    if not QSystemTrayIcon.isSystemTrayAvailable():
        logging.getLogger(__name__).warning("Системный трей недоступен; скрытие фигурки отключено.")
        return None
    tray = CharacterTray(window)
    tray.show()
    window.set_hide_available(lambda: tray.isVisible() and QSystemTrayIcon.isSystemTrayAvailable())
    QApplication.instance().aboutToQuit.connect(tray.hide)
    return tray
