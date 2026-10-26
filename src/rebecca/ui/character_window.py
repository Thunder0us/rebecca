"""Окно размером с фигуру, а не с экран; обычные локальные события Qt."""

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QContextMenuEvent, QPaintEvent, QPainter
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from rebecca.ui.sprite_renderer import create_placeholder


class CharacterWindow(QWidget):
    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setWindowTitle("Ребекка — прототип")
        self._sprite = create_placeholder()
        self.setFixedSize(self._sprite.size())
        self._menu = QMenu(self)
        exit_action = self._menu.addAction("Выход", self.close)
        # Закрытие Tool-окна само по себе не завершает цикл QApplication.
        exit_action.triggered.connect(QApplication.quit)

    def place_above_taskbar(self, work_area: QRect) -> None:
        # availableGeometry исключает панель задач; координаты могут быть отрицательными.
        x = work_area.x() + (work_area.width() - self.width()) // 2
        y = work_area.y() + work_area.height() - self.height()
        self.move(x, y)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._sprite)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        self._menu.popup(event.globalPos())
        event.accept()
