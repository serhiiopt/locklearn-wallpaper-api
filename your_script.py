from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Return a clean, readable sans-serif font at the requested size."""
    font_candidates = [
        "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ]
    for path in font_candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _pick_text_color(image: Image.Image, box: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    """Choose solid text color (black or white) with good contrast in the given box."""
    region = image.crop(box)
    thumb = region.copy()
    thumb.thumbnail((64, 64))
    pixels = list(thumb.getdata())
    if not pixels:
        return (255, 255, 255, 255)

    r_avg = sum(p[0] for p in pixels) / len(pixels)
    g_avg = sum(p[1] for p in pixels) / len(pixels)
    b_avg = sum(p[2] for p in pixels) / len(pixels)
    luminance = 0.2126 * r_avg + 0.7152 * g_avg + 0.0722 * b_avg

    if luminance < 140:
        return (255, 255, 255, 255)
    return (0, 0, 0, 255)


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    """Simple word-wrapping for a single string."""
    if not text:
        return []
    tokens = text.split(" ")
    lines: list[str] = []
    current = ""
    for token in tokens:
        test = token if not current else current + " " + token
        bbox = draw.textbbox((0, 0), test, font=font)
        width = bbox[2] - bbox[0]
        if width <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = token
    if current:
        lines.append(current)
    return lines


def create_wallpaper(word: str, meaning: str) -> Image.Image:
    """
    Generate a wallpaper image with a single word and its translation/meaning.
    Returns a Pillow Image object (RGBA or RGB).
    """
    base_path = BASE_DIR / "default_pic.webp"
    image = Image.open(base_path).convert("RGBA")
    draw = ImageDraw.Draw(image)

    width, height = image.size

    # Fixed minimum readable sizes (match your tuning)
    main_size = 76
    main_font = _get_font(main_size)
    trans_font = _get_font(int(main_size * 0.6))

    # Layout
    margin_x = max(int(width * 0.08), 16)
    margin_y = max(int(height * 0.08), 32)
    x = margin_x
    y = margin_y
    max_text_width = width - 2 * margin_x

    # Choose color based on the band where text will be
    text_region_box = (
        margin_x,
        margin_y,
        width - margin_x,
        min(height - margin_y, margin_y + int(height * 0.6)),
    )
    fill_color = _pick_text_color(image, box=text_region_box)

    # Main word (possibly wrapped)
    main_lines = _wrap_text(draw, word, main_font, max_text_width)
    line_gap_main = int(main_size * 0.2)

    for line in main_lines:
        bbox = draw.textbbox((0, 0), line, font=main_font)
        line_h = bbox[3] - bbox[1]
        draw.text((x, y), line, font=main_font, fill=fill_color)
        y += line_h + line_gap_main

    # Meaning/translation below
    if meaning:
        y += int(main_size * 0.1)
        trans_lines = _wrap_text(draw, meaning, trans_font, max_text_width)
        line_gap_tr = int(trans_font.size * 0.2)
        for line in trans_lines:
            bbox = draw.textbbox((0, 0), line, font=trans_font)
            line_h = bbox[3] - bbox[1]
            draw.text((x, y), line, font=trans_font, fill=fill_color)
            y += line_h + line_gap_tr

    return image

