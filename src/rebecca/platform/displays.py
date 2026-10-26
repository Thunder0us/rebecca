"""Ограничение позиции рабочей областью в логических координатах Qt."""

from PySide6.QtCore import QPoint, QRect, QSize


def clamp_to_work_area(position: QPoint, size: QSize, area: QRect) -> QPoint:
    """Удерживает всё окно внутри area, включая экраны с отрицательным началом."""
    max_x = area.x() + max(0, area.width() - size.width())
    max_y = area.y() + max(0, area.height() - size.height())
    return QPoint(
        max(area.x(), min(position.x(), max_x)),
        max(area.y(), min(position.y(), max_y)),
    )
