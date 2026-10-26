"""Создание приложения; никаких фоновых сервисов или сетевых запросов."""

import sys

from PySide6.QtWidgets import QApplication

from rebecca.ui.character_window import CharacterWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Rebecca Desktop Companion")
    screen = app.primaryScreen()
    if screen is None:
        print("Не найден экран для отображения персонажа.", file=sys.stderr)
        return 1
    window = CharacterWindow()
    window.place_above_taskbar(screen.availableGeometry())
    window.show()
    return app.exec()
