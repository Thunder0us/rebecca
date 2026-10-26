"""Окно размером с фигуру, а не с экран; обычные локальные события Qt."""

from pathlib import Path
from collections.abc import Callable

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QContextMenuEvent, QIcon, QMouseEvent, QPaintEvent, QPainter, QScreen
from PySide6.QtWidgets import QApplication, QWidget

from rebecca.ui.sprite_renderer import SCALE, load_sprite
from rebecca.platform.displays import clamp_to_work_area
from rebecca.ui.menu import CharacterMenu


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
        self.setWindowIcon(QIcon(self._sprite))
        self._drag_offset: QPoint | None = None
        self._paused = False
        self._can_hide: Callable[[], bool] = lambda: False
        self._menu = CharacterMenu(self, self.toggle_pause, self.toggle_visibility, self.exit_application)
        self._menu.aboutToShow.connect(self._sync_menu)
        self._sync_menu()
        app = QApplication.instance()
        app.screenAdded.connect(self._watch_screen)
        app.screenRemoved.connect(self._screen_removed)
        for screen in app.screens():
            self._watch_screen(screen)

    @property
    def context_menu(self) -> CharacterMenu:
        return self._menu

    def set_hide_available(self, can_hide: Callable[[], bool]) -> None:
        self._can_hide = can_hide
        self._sync_menu()

    def _sync_menu(self) -> None:
        self._menu.sync(self._paused, self.isVisible(), self._can_hide())

    def toggle_pause(self) -> None:
        self._paused = not self._paused
        self._drag_offset = None
        self._sync_menu()

    def toggle_visibility(self) -> None:
        if self.isVisible():
            if self._can_hide():
                self._drag_offset = None
                self.hide()
        else:
            self.show_character()
        self._sync_menu()

    def show_character(self) -> None:
        self.ensure_visible()
        self.show()  # WA_ShowWithoutActivating сохраняет фокус другого приложения.
        self._sync_menu()

    def exit_application(self) -> None:
        self.close()
        # Закрытие Tool-окна само по себе не завершает цикл QApplication.
        QApplication.quit()

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
        if event.button() == Qt.MouseButton.LeftButton and not self._paused:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self._paused and self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
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
