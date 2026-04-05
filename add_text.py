# create a function using python Pillow library that takes words stored in a list "vocab_today" and adds them to an image stored in "default_pic.webp"
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent


def _choose_font_for_width(draw, words, image_width, target_fraction=0.4):
    """
    Pick a single TrueType font (same size for all words) so that
    the AVERAGE word width is about target_fraction of the image width.
    """
    words = list(words) or ["Sample"]

    # Common macOS font locations (prefer broader, clean sans-serif faces)
    font_candidates = [
        "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Black.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ]

    font_path = None
    for path in font_candidates:
        try:
            ImageFont.truetype(path, size=20)
            font_path = path
            break
        except OSError:
            continue

    if font_path is None:
        # Fallback if somehow none of the system fonts work
        return ImageFont.load_default(), None

    best_font = None
    best_diff = float("inf")

    # Try a range of sizes and pick the one whose average width
    # is closest to target_fraction * image_width
    for size in range(20, 201, 4):
        font = ImageFont.truetype(font_path, size=size)

        widths = []
        for w in words:
            bbox = draw.textbbox((0, 0), w, font=font)
            widths.append(bbox[2] - bbox[0])

        avg_width = sum(widths) / len(widths)
        ratio = avg_width / image_width
        diff = abs(ratio - target_fraction)

        if diff < best_diff:
            best_diff = diff
            best_font = font

        if ratio >= target_fraction:
            # We've reached or exceeded the target fraction; good enough
            break

    return (best_font or ImageFont.load_default()), font_path


def _wrap_text(draw, text, font, max_width):
    """
    Wrap a single string into multiple lines so that each line's width
    does not exceed max_width. If there are no spaces, wraps by characters.
    """
    if not text:
        return []

    if " " in text:
        tokens = text.split(" ")
        sep = " "
    else:
        tokens = list(text)
        sep = ""

    lines = []
    current = ""

    for token in tokens:
        test = token if not current else current + sep + token
        bbox = draw.textbbox((0, 0), test, font=font)
        line_width = bbox[2] - bbox[0]

        if line_width <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = token

    if current:
        lines.append(current)

    return lines


def _pick_text_color(image, box=None):
    """
    Choose a solid text color (no outline) with strong contrast
    against the area where text will be drawn.

    If box is provided, it should be a (left, top, right, bottom) tuple
    defining the region to analyse; otherwise the whole image is used.
    """
    region = image.crop(box) if box is not None else image

    # Downscale for speed, then get average RGB in that region
    thumb = region.copy()
    thumb.thumbnail((64, 64))
    pixels = list(thumb.getdata())
    if not pixels:
        # safe default
        return (255, 255, 255, 255)

    r_avg = sum(p[0] for p in pixels) / len(pixels)
    g_avg = sum(p[1] for p in pixels) / len(pixels)
    b_avg = sum(p[2] for p in pixels) / len(pixels)

    # Perceived luminance (0 = black, 255 = white)
    luminance = 0.2126 * r_avg + 0.7152 * g_avg + 0.0722 * b_avg

    # Simple, robust choice: pure white on dark, pure black on light.
    # This maximizes contrast and avoids subtle palette mismatches.
    if luminance < 140:
        return (255, 255, 255, 255)  # bright text on dark-ish region
    else:
        return (0, 0, 0, 255)        # dark text on light-ish region


def _measure_total_height(
    draw,
    vocab_today_dict,
    main_font,
    translation_font,
    image_width,
    margin_x,
    margin_y,
):
    """
    Simulate layout to see how much vertical space is needed
    for all words with the given fonts.
    """
    max_text_width = image_width - 2 * margin_x
    y = margin_y

    total_entries = len(vocab_today_dict)
    words_done = 0
    last_fit_entries = total_entries

    for source_word, translation in vocab_today_dict.items():
        # main word lines
        main_lines = _wrap_text(draw, source_word, main_font, max_text_width)
        line_gap_main = int(getattr(main_font, "size", 1) * 0.2)

        for line in main_lines:
            bbox_main = draw.textbbox((0, 0), line, font=main_font)
            line_h = bbox_main[3] - bbox_main[1]
            y += line_h + line_gap_main

        # translation lines
        if translation:
            main_size = getattr(main_font, "size", 1)
            y += int(main_size * 0.1)
            trans_lines = _wrap_text(draw, translation, translation_font, max_text_width)
            line_gap_tr = int(getattr(translation_font, "size", 1) * 0.2)

            for line in trans_lines:
                bbox_tr = draw.textbbox((0, 0), line, font=translation_font)
                tr_h = bbox_tr[3] - bbox_tr[1]
                y += tr_h + line_gap_tr

        # gap before next pair
        main_size = getattr(main_font, "size", 1)
        y += int(main_size * 0.5)

    return y


def _count_entries_fit(
    draw,
    vocab_today_dict,
    main_font,
    translation_font,
    image_width,
    margin_x,
    margin_y,
    available_bottom,
):
    """
    Return how many (word, translation) entries from the top can fit
    vertically before exceeding available_bottom, using the same layout
    model as _measure_total_height.
    """
    max_text_width = image_width - 2 * margin_x
    y = margin_y
    count = 0

    for source_word, translation in vocab_today_dict.items():
        # main word lines
        main_lines = _wrap_text(draw, source_word, main_font, max_text_width)
        line_gap_main = int(getattr(main_font, "size", 1) * 0.2)

        for line in main_lines:
            bbox_main = draw.textbbox((0, 0), line, font=main_font)
            line_h = bbox_main[3] - bbox_main[1]
            if y + line_h > available_bottom:
                return count
            y += line_h + line_gap_main

        # translation lines
        if translation:
            main_size = getattr(main_font, "size", 1)
            y += int(main_size * 0.1)
            trans_lines = _wrap_text(draw, translation, translation_font, max_text_width)
            line_gap_tr = int(getattr(translation_font, "size", 1) * 0.2)

            for line in trans_lines:
                bbox_tr = draw.textbbox((0, 0), line, font=translation_font)
                tr_h = bbox_tr[3] - bbox_tr[1]
                if y + tr_h > available_bottom:
                    return count
                y += tr_h + line_gap_tr

        # gap before next pair
        main_size = getattr(main_font, "size", 1)
        if y + int(main_size * 0.5) > available_bottom:
            return count
        y += int(main_size * 0.5)

        count += 1

    return count


def add_vocab_to_image(
    vocab_today_dict,
    input_image_name="default_pic.webp",
    output_image_name="default_pic_with_text.webp",
):
    input_image_path = BASE_DIR / input_image_name
    output_image_path = BASE_DIR / output_image_name

    image = Image.open(input_image_path).convert("RGBA")
    draw = ImageDraw.Draw(image)

    image_width, image_height = image.size

    # Use only the source-language words (keys) to size the "ideal" main font
    main_words = list(vocab_today_dict.keys())
    main_font, font_path = _choose_font_for_width(
        draw, main_words, image_width, target_fraction=0.4
    )

    MIN_MAIN_SIZE = 76          # lower limit for the original full-size wallpaper
    target_fraction = 0.4

    # Treat images around iPhone wallpaper width as "full-size";
    # for smaller images, let the font scale down naturally.
    is_full_size = image_width >= 1000

    # Baseline font for most words
    # IMPORTANT: On full-size wallpapers we ALWAYS use the minimum readable
    # size (76) so that capacity estimation is stable and does not change
    # when you add/remove words.
    if is_full_size and font_path and hasattr(main_font, "size"):
        base_font = ImageFont.truetype(font_path, size=MIN_MAIN_SIZE)
    else:
        base_font = main_font

    # Position text with margins that scale with image size
    margin_x = max(int(image_width * 0.08), 16)
    margin_y = max(int(image_height * 0.08), 32)

    x, y = margin_x, margin_y
    max_text_width = image_width - 2 * margin_x

    # If this is a full-size wallpaper and we know the font face,
    # adapt the font size based on *both* width (40% rule) and the
    # total amount of text so it fits vertically, but never below 76.
    if is_full_size and font_path and hasattr(base_font, "size"):
        start_size = base_font.size
        chosen_main_font = base_font
        chosen_translation_font = ImageFont.truetype(
            font_path, size=int(start_size * 0.6)
        )

        size = start_size
        min_size = MIN_MAIN_SIZE
        available_bottom = image_height - margin_y
        too_many = False

        while size >= min_size:
            test_main = ImageFont.truetype(font_path, size=size)
            test_tr = ImageFont.truetype(font_path, size=int(size * 0.6))
            total_h = _measure_total_height(
                draw,
                vocab_today_dict,
                test_main,
                test_tr,
                image_width,
                margin_x,
                margin_y,
            )
            if total_h <= available_bottom:
                chosen_main_font = test_main
                chosen_translation_font = test_tr
                break
            size -= 2

        base_font = chosen_main_font
        # We will recompute per-word translation_font below, but this gives
        # us a good baseline for measuring and spacing.

    available_bottom = image_height - margin_y

    # Before drawing, for full-size wallpapers, estimate how many entries
    # fit vertically by *summing up* the heights of each word+translation
    # block using the final base font (fixed minimum size). If they don't
    # all fit, just report and return without drawing.
    if is_full_size and font_path and hasattr(base_font, "size"):
        est_main = ImageFont.truetype(font_path, size=base_font.size)
        est_tr = ImageFont.truetype(font_path, size=int(base_font.size * 0.6))
        height_used = margin_y
        fit_count = 0

        for src_word, trans in vocab_today_dict.items():
            # main word block
            main_lines = _wrap_text(draw, src_word, est_main, max_text_width)
            line_gap_main = int(est_main.size * 0.2)
            for line in main_lines:
                bbox = draw.textbbox((0, 0), line, font=est_main)
                line_h = bbox[3] - bbox[1]
                height_used += line_h + line_gap_main

            # translation block
            if trans:
                height_used += int(est_main.size * 0.1)
                trans_lines = _wrap_text(draw, trans, est_tr, max_text_width)
                line_gap_tr = int(est_tr.size * 0.2)
                for line in trans_lines:
                    bbox = draw.textbbox((0, 0), line, font=est_tr)
                    line_h = bbox[3] - bbox[1]
                    height_used += line_h + line_gap_tr

            # gap before next entry
            height_used += int(est_main.size * 0.5)

            if height_used <= available_bottom:
                fit_count += 1
            else:
                break

        total_entries = len(vocab_today_dict)
        if fit_count < total_entries:
            to_remove = total_entries - fit_count
            print(f"too many words: remove at least {to_remove}")
            # Do not draw anything or save an updated image
            return str(output_image_path)

    # Analyse only the band where text will actually sit for color choice
    text_region_box = (
        margin_x,
        margin_y,
        image_width - margin_y,
        min(image_height - margin_y, margin_y + int(image_height * 0.6)),
    )
    fill_color = _pick_text_color(image, box=text_region_box)

    content_bottom = y  # bottom-most pixel where we actually drew text

    for source_word, translation in vocab_today_dict.items():
        # Decide per-word main font size
        per_word_font = base_font
        per_word_font_path = font_path
        per_word_size = getattr(base_font, "size", MIN_MAIN_SIZE)

        if font_path and hasattr(base_font, "size") and base_font.size >= MIN_MAIN_SIZE:
            # Normal case: system behaves as before (single size from 40% estimate)
            pass
        elif font_path and hasattr(base_font, "size"):
            # Base font is at the lower limit; only shrink words that "need" it
            bbox_word = draw.textbbox((0, 0), source_word, font=base_font)
            word_width = bbox_word[2] - bbox_word[0]
            target_width = image_width * target_fraction

            if word_width > target_width:
                scale = target_width / max(word_width, 1)
                scaled_size = max(int(base_font.size * scale), 1)
                if scaled_size < base_font.size:
                    per_word_size = scaled_size
                    per_word_font = ImageFont.truetype(font_path, size=per_word_size)

        # Translation font for this word: smaller than its main word
        if per_word_font_path:
            translation_font = ImageFont.truetype(
                per_word_font_path, size=int(per_word_size * 0.6)
            )
        else:
            translation_font = per_word_font

        # --- main (German) word, possibly wrapped ---
        main_lines = _wrap_text(draw, source_word, per_word_font, max_text_width)
        line_gap_main = int(per_word_size * 0.2)

        for line in main_lines:
            bbox_main = draw.textbbox((0, 0), line, font=per_word_font)
            line_h = bbox_main[3] - bbox_main[1]

            draw.text((x, y), line, font=per_word_font, fill=fill_color)
            content_bottom = max(content_bottom, y + line_h)

            y += line_h + line_gap_main

        # --- translation below, smaller font (also wrapped) ---
        if translation:
            y += int(per_word_size * 0.1)  # small gap before translation
            trans_lines = _wrap_text(draw, translation, translation_font, max_text_width)
            line_gap_tr = int(translation_font.size * 0.2)

            for line in trans_lines:
                bbox_tr = draw.textbbox((0, 0), line, font=translation_font)
                tr_h = bbox_tr[3] - bbox_tr[1]

                draw.text(
                    (x, y),
                    line,
                    font=translation_font,
                    fill=fill_color,
                )
                content_bottom = max(content_bottom, y + tr_h)
                y += tr_h + line_gap_tr

        # Move down for next pair (spacing only, doesn't affect content_bottom)
        y += int(per_word_size * 0.5)

    # JPEG does not support alpha; convert if needed
    suffix = output_image_path.suffix.lower()
    final_image = image
    save_kwargs = {}
    if suffix in {".jpg", ".jpeg"}:
        if image.mode == "RGBA":
            final_image = image.convert("RGB")
        # use higher quality to keep text crisp
        save_kwargs.update({"quality": 95, "subsampling": 0, "optimize": True})

    final_image.save(output_image_path, **save_kwargs)
    return str(output_image_path)


if __name__ == "__main__":
    vocab_today = {
        "Apfffel": "apple",
        "Banane": "banana",
        "Zitrone": "lemon",
        "Orange": "orange",
        "Banana": "banana",
        "Cherry": "cherry",
        "Lemon": "lemon",
        "Orange": "orange",
        "Banana": "banana",
        "Cherry": "cherry",
        "Lemon": "lemon",
        "strawberry": "strawberry",
        "Brombeere": "blackberry",
        "Kiwi": "kiwi",
        "Nektarine": "nectarine",
        "Papayaaa": "papaya",
    
      
        
       
       
   
    
    }

    # Original default wallpaper
    add_vocab_to_image(vocab_today)

    # Additional iPhone wallpaper variants
    variants = [
        ("default_pic.webp", "default_pic_with_text.webp"),
        ("Iphone_wallpaper_2.jpeg", "Iphone_wallpaper_2_with_text.jpeg"),
        ("iphone_wallpaper_3.jpeg", "iphone_wallpaper_3_with_text.jpeg"),
        ("iphone_wallpaper_4.jpeg", "iphone_wallpaper_4_with_text.jpeg"),
        ("iphone_wallpaper_6.jpeg", "iphone_wallpaper_6_with_text.jpeg"),
    ]

    for input_name, output_name in variants:
        add_vocab_to_image(
            vocab_today,
            input_image_name=input_name,
            output_image_name=output_name,
        )