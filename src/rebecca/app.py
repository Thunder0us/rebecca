"""Создание приложения; никаких фоновых сервисов или сетевых запросов."""

import argparse
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from rebecca.ui.character_window import CharacterWindow
from rebecca.ui.sprite_renderer import MAX_SCALE, MIN_SCALE, SCALE, STATES


def main() -> int:
    parser = argparse.ArgumentParser(description="Ребекка — просмотр статичного PNG-спрайта")
    parser.add_argument("--state", choices=STATES, default="idle", help="изображение состояния")
    parser.add_argument("--scale", type=int, choices=range(MIN_SCALE, MAX_SCALE + 1),
                        default=SCALE, help="целочисленный масштаб пикселей (по умолчанию 4)")
    parser.add_argument("--sprites-dir", type=Path,
                        help="папка PNG; по умолчанию assets/sprites в исходном проекте")
    args = parser.parse_args()
    app = QApplication([sys.argv[0]])
    app.setApplicationName("Rebecca Desktop Companion")
    screen = app.primaryScreen()
    if screen is None:
        print("Не найден экран для отображения персонажа.", file=sys.stderr)
        return 1
    window = CharacterWindow(args.state, args.scale, args.sprites_dir)
    window.place_above_taskbar(screen.availableGeometry())
    window.show()
    return app.exec()
