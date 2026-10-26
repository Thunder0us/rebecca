"""Загрузка одиночных PNG и чёткое масштабирование без изменения оригиналов."""

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImageReader, QPixmap


STATES = ("idle", "walk", "sleep", "angry", "happy", "sit")
DEFAULT_SPRITES_DIR = Path(__file__).resolve().parents[3] / "assets" / "sprites"
MAX_SOURCE_WIDTH = 64
MAX_SOURCE_HEIGHT = 96
MIN_SCALE = 1
MAX_SCALE = 4
logger = logging.getLogger(__name__)


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


def validate_scale(scale: int) -> None:
    if type(scale) is not int or not MIN_SCALE <= scale <= MAX_SCALE:
        raise ValueError(f"Масштаб должен быть целым числом от {MIN_SCALE} до {MAX_SCALE}")


def scale_sprite(source: QPixmap, scale: int) -> QPixmap:
    validate_scale(scale)
    return source.scaled(
        source.width() * scale,
        source.height() * scale,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.FastTransformation,  # Nearest Neighbor
    )


def create_placeholder(scale: int = SCALE) -> QPixmap:
    pixmap = QPixmap(len(PIXELS[0]), len(PIXELS))
    pixmap.fill(Qt.GlobalColor.transparent)
    image = pixmap.toImage()
    for y, row in enumerate(PIXELS):
        for x, pixel in enumerate(row):
            if pixel != ".":
                image.setPixelColor(x, y, QColor(PALETTE[pixel]))
    return scale_sprite(QPixmap.fromImage(image), scale)


def load_sprite(
    state: str = "idle", scale: int = SCALE, sprites_dir: Path | None = None
) -> QPixmap:
    """Каждое состояние — один кадр. Нет файла/непригодный PNG → запасная фигура."""
    if state not in STATES:
        raise ValueError(f"Неизвестное состояние: {state}")
    validate_scale(scale)
    directory = DEFAULT_SPRITES_DIR if sprites_dir is None else Path(sprites_dir)
    path = directory / f"{state}.png"
    if not path.is_file():
        logger.warning("Спрайт %s отсутствует; используется временная фигурка.", path)
        return create_placeholder(scale)
    reader = QImageReader(str(path), b"png")
    reader.setAutoDetectImageFormat(False)
    size = reader.size()
    reason = "файл отсутствует или не читается как PNG"
    if size.isValid():
        if size.width() > MAX_SOURCE_WIDTH or size.height() > MAX_SOURCE_HEIGHT:
            reason = f"размер больше {MAX_SOURCE_WIDTH}×{MAX_SOURCE_HEIGHT}"
        else:
            image = reader.read()
            if not image.isNull():
                if not image.hasAlphaChannel():
                    reason = "нет альфа-канала прозрачности"
                elif not any(
                    image.pixelColor(x, y).alpha() > 0
                    for y in range(image.height()) for x in range(image.width())
                ):
                    reason = "изображение полностью прозрачно"
                else:
                    return scale_sprite(QPixmap.fromImage(image), scale)
    logger.warning("Спрайт %s: %s; используется временная фигурка.", path, reason)
    return create_placeholder(scale)
