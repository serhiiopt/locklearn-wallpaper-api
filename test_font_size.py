from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BASE_DIR = Path(__file__).resolve().parent


def get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """
    Try to load a TrueType font at the given size.
    Falls back to Pillow's default bitmap font if needed.
    """
    font_candidates = [
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


def render_word_in_sizes(
    word: str,
    sizes: list[int],
    output_name: str = "font_size_test_on_wallpaper.webp",
) -> str:
    """
    Render the same word multiple times in different font sizes
    directly onto the original wallpaper image.
    """
    # Load original wallpaper
    wallpaper_path = BASE_DIR / "default_pic.webp"
    img = Image.open(wallpaper_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    width, height = img.size
    margin_x = 50
    margin_y = 100

    y = margin_y
    for size in sizes:
        font = get_font(size)
        label = f"{word}  (size {size})"

        bbox = draw.textbbox((0, 0), label, font=font)
        text_h = bbox[3] - bbox[1]

        x = margin_x
        # simple dark outline for visibility
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            draw.text((x + dx, y + dy), label, font=font, fill=(0, 0, 0, 255))
        draw.text((x, y), label, font=font, fill=(255, 255, 255, 255))

        y += text_h + int(size * 0.6)
        if y > height - margin_y:
            break

    output_path = BASE_DIR / output_name
    img.save(output_path)
    return str(output_path)


if __name__ == "__main__":
    word = "Apfel"
    sizes = list(range(8, 81, 2))  # 8, 10, 12, ..., 60
    path = render_word_in_sizes(word, sizes)
    print(f"Saved font size test on wallpaper to: {path}")

