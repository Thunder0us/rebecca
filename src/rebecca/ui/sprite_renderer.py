"""Оригинальная временная фигура 16×24, без внешних ассетов."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap


PIXELS = (
    ".....HHHHHH.....",
    "....HHHHHHHH....",
    "...HHHHHHHHHH...",
    "...HHSSSSSSHH...",
    "..HHHSESSSEHHH..",
    "..HHHSSSSSSHHH..",
    "..HHHSSMMSSHHH..",
    "..HHHHSSSSHHHH..",
    "..HHHHHSSHHHHH..",
    "..HH.DDDDDD.HH..",
    ".....DDDDDD.....",
    "....SDDDDDDS....",
    "....SDDDDDDS....",
    "....SDDDDDDS....",
    "....S.DDDD.S....",
    "....S.DDDD.S....",
    "......PPPP......",
    "......PPPP......",
    "......S..S......",
    "......S..S......",
    "......S..S......",
    "......B..B......",
    ".....BB..BB.....",
    ".....BB..BB.....",
)
PALETTE = {
    "H": "#6ad6b2",  # волосы
    "S": "#f5cfbd",  # кожа
    "E": "#db477a",  # глаза
    "M": "#9b526b",
    "D": "#30364b",  # одежда
    "P": "#694a75",
    "B": "#252b3d",  # ботинки
}
SCALE = 4


def create_placeholder() -> QPixmap:
    pixmap = QPixmap(len(PIXELS[0]), len(PIXELS))
    pixmap.fill(Qt.GlobalColor.transparent)
    image = pixmap.toImage()
    for y, row in enumerate(PIXELS):
        for x, pixel in enumerate(row):
            if pixel != ".":
                image.setPixelColor(x, y, QColor(PALETTE[pixel]))
    return QPixmap.fromImage(image).scaled(
        image.width() * SCALE,
        image.height() * SCALE,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.FastTransformation,
    )
