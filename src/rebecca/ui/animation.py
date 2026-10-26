"""Загрузка готовых кадров; никакого поведения или перемещения окна."""

from dataclasses import dataclass
import json
import logging
from pathlib import Path

from PySide6.QtGui import QPixmap

from rebecca.ui.sprite_renderer import (
    DEFAULT_SPRITES_DIR, PIXELS, STATES, create_placeholder, load_sprite,
    read_png, scale_sprite, validate_scale,
)


logger = logging.getLogger(__name__)
ANIMATED_STATES = ("idle", "walk")
MAX_FRAMES = 32
MAX_MANIFEST_BYTES = 65536


@dataclass(frozen=True)
class SpriteAnimation:
    frames: tuple[QPixmap, ...]
    fps: int


def load_animation(state: str, scale: int, sprites_dir: Path | None = None) -> SpriteAnimation:
    if state not in STATES:
        raise ValueError(f"Неизвестное состояние: {state}")
    validate_scale(scale)
    directory = DEFAULT_SPRITES_DIR if sprites_dir is None else Path(sprites_dir)
    manifest = directory.parent / "animations.json"
    if state in ANIMATED_STATES and manifest.is_file():
        try:
            with manifest.open("rb") as stream:
                raw = stream.read(MAX_MANIFEST_BYTES + 1)
            if len(raw) > MAX_MANIFEST_BYTES:
                raise ValueError("манифест больше 64 КиБ")
            data = json.loads(raw)
            if (not isinstance(data, dict) or type(data.get("version")) is not int
                    or data["version"] != 1 or not isinstance(data.get("animations"), dict)):
                raise ValueError("ожидается version=1 и объект animations")
            if state in data["animations"]:
                entry = data["animations"][state]
                if not isinstance(entry, dict):
                    raise ValueError("описание состояния должно быть объектом")
                fps, paths = entry.get("fps"), entry.get("frames")
                if type(fps) is not int or not 1 <= fps <= 30:
                    raise ValueError("fps должен быть целым числом от 1 до 30")
                if not isinstance(paths, list) or not 1 <= len(paths) <= MAX_FRAMES:
                    raise ValueError("нужно от 1 до 32 кадров")
                frames: list[QPixmap] = []
                root = directory.resolve()
                for name in paths:
                    if not isinstance(name, str):
                        raise ValueError("имя кадра должно быть строкой")
                    path = (root / name).resolve()
                    if not path.is_relative_to(root) or path.suffix.lower() != ".png":
                        raise ValueError("кадр должен быть PNG внутри папки sprites")
                    source = read_png(path)
                    if source is None:
                        raise ValueError(f"не удалось загрузить кадр {name}")
                    frame = scale_sprite(source, scale)
                    if frames and frame.size() != frames[0].size():
                        raise ValueError("все кадры должны иметь одинаковый размер холста")
                    frames.append(frame)
                return SpriteAnimation(tuple(frames), fps)
        except (OSError, ValueError) as error:
            logger.warning("Анимация %s: %s; используется одиночный PNG.", state, error)
    return SpriteAnimation((load_sprite(state, scale, directory),), 1)


def load_demo_animation(state: str, scale: int) -> SpriteAnimation:
    """Явно включаемый тест на старой фигуре, не меняющий PNG пользователя."""
    if state not in ANIMATED_STATES:
        raise ValueError("Демонстрация поддерживает только idle и walk")
    validate_scale(scale)
    base = create_placeholder(scale)
    if state == "idle":
        blink = create_placeholder(scale, pixels=tuple(row.replace("E", "S") for row in PIXELS))
        return SpriteAnimation((base, base, blink, base), 4)
    step = list(PIXELS)
    for y in range(18, 22):
        step[y] = ".....S....S....."
    step[22] = step[23] = "....BB....BB...."
    stride = create_placeholder(scale, pixels=tuple(step))
    return SpriteAnimation((base, stride), 6)
