"""Окно размером с фигуру, а не с экран; обычные локальные события Qt."""

from pathlib import Path

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QContextMenuEvent, QMouseEvent, QPaintEvent, QPainter, QScreen
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from rebecca.ui.sprite_renderer import SCALE, load_sprite
from rebecca.platform.displays import clamp_to_work_area


class CharacterWindow(QWidget):
    def __init__(
        self, state: str = "idle", scale: int = SCALE, sprites_dir: Path | None = None
    ) -> None:
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
        # Позволяет сбросить drag, если Qt получил движение уже без зажатой кнопки.
        self.setMouseTracking(True)
        self.setWindowTitle("Ребекка — прототип")
        self._sprite = load_sprite(state, scale, sprites_dir)
        self.setFixedSize(self._sprite.size())
        self._menu = QMenu(self)
        exit_action = self._menu.addAction("Выход", self.close)
        # Закрытие Tool-окна само по себе не завершает цикл QApplication.
        exit_action.triggered.connect(QApplication.quit)
        self._drag_offset: QPoint | None = None
        app = QApplication.instance()
        app.screenAdded.connect(self._watch_screen)
        app.screenRemoved.connect(self._screen_removed)
        for screen in app.screens():
            self._watch_screen(screen)

    def _watch_screen(self, screen: QScreen) -> None:
        screen.availableGeometryChanged.connect(self.ensure_visible)

    def _screen_removed(self, screen: QScreen) -> None:
        self._drag_offset = None
        # Qt должен сначала обновить список подключённых экранов.
        QTimer.singleShot(0, self.ensure_visible)

    def ensure_visible(self) -> None:
        app = QApplication.instance()
        screen = app.screenAt(self.geometry().center()) or app.primaryScreen()
        if screen is not None:
            self.move(clamp_to_work_area(self.pos(), self.size(), screen.availableGeometry()))

    def _drag_to(self, global_position: QPoint) -> None:
        app = QApplication.instance()
        screen = app.screenAt(global_position) or app.primaryScreen()
        if screen is not None and self._drag_offset is not None:
            position = global_position - self._drag_offset
            self.move(clamp_to_work_area(position, self.size(), screen.availableGeometry()))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self._drag_to(event.globalPosition().toPoint())
            event.accept()
        else:
            # Например, если отпускание кнопки произошло при смене активного окна.
            self._drag_offset = None
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._drag_offset is not None:
            self._drag_to(event.globalPosition().toPoint())
            self._drag_offset = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def place_above_taskbar(self, work_area: QRect) -> None:
        # availableGeometry исключает панель задач; координаты могут быть отрицательными.
        x = work_area.x() + (work_area.width() - self.width()) // 2
        y = work_area.y() + work_area.height() - self.height()
        self.move(x, y)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.drawPixmap(0, 0, self._sprite)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        self._menu.popup(event.globalPos())
        event.accept()
