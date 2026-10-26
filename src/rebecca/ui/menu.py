"""Общее меню фигурки и значка в трее."""

from collections.abc import Callable

from PySide6.QtWidgets import QMenu, QWidget


class CharacterMenu(QMenu):
    def __init__(self, parent: QWidget, toggle_pause: Callable[[], None],
                 toggle_visibility: Callable[[], None], exit_app: Callable[[], None],
                 toggle_facing: Callable[[], None]) -> None:
        super().__init__(parent)
        self.pause_action = self.addAction("Пауза", toggle_pause)
        self.visibility_action = self.addAction("Скрыть", toggle_visibility)
        self.flip_action = self.addAction("Развернуть", toggle_facing)
        self.addSeparator()
        self.exit_action = self.addAction("Выход", exit_app)

    def sync(self, paused: bool, visible: bool, can_hide: bool) -> None:
        self.pause_action.setText("Продолжить" if paused else "Пауза")
        self.visibility_action.setText("Скрыть" if visible else "Показать")
        self.visibility_action.setEnabled(not visible or can_hide)
