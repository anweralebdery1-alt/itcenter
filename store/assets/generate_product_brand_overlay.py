from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont


ASSET_DIR = Path(__file__).resolve().parent
FONT_DIR = ASSET_DIR / "fonts"
OUTPUT_PATH = ASSET_DIR / "product_brand_overlay.png"
SIZE = 1000
BLUE = (11, 78, 162)
FOOTER_TEXT = "مركز آي تي للتطوير والتدريب - النجف الاشرف -"
WATERMARK_TEXT = "ITcenterstore"


def font_that_fits(path, text, max_width, start_size, minimum_size):
    for size in range(start_size, minimum_size - 1, -1):
        font = ImageFont.truetype(str(path), size=size)
        left, _top, right, _bottom = font.getbbox(text)
        if right - left <= max_width:
            return font
    return ImageFont.truetype(str(path), size=minimum_size)


def centered_position(draw, text, font, center_x, center_y):
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    return (
        center_x - (right - left) / 2 - left,
        center_y - (bottom - top) / 2 - top,
    )


def main():
    overlay = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 0))

    watermark_font = font_that_fits(
        FONT_DIR / "Amiri-Bold.ttf",
        WATERMARK_TEXT,
        max_width=760,
        start_size=126,
        minimum_size=92,
    )
    bbox = watermark_font.getbbox(WATERMARK_TEXT)
    watermark_layer = Image.new(
        "RGBA",
        (bbox[2] - bbox[0] + 90, bbox[3] - bbox[1] + 90),
        (255, 255, 255, 0),
    )
    watermark_draw = ImageDraw.Draw(watermark_layer)
    watermark_draw.text(
        (45 - bbox[0], 45 - bbox[1]),
        WATERMARK_TEXT,
        font=watermark_font,
        fill=(4, 38, 84, 150),
        stroke_width=2,
        stroke_fill=(255, 255, 255, 175),
    )
    watermark_layer = watermark_layer.rotate(
        27,
        expand=True,
        resample=Image.Resampling.BICUBIC,
    )
    overlay.alpha_composite(
        watermark_layer,
        (
            (SIZE - watermark_layer.width) // 2,
            (42 + 868 - watermark_layer.height) // 2,
        ),
    )

    footer_text = get_display(arabic_reshaper.reshape(FOOTER_TEXT))
    footer_font = font_that_fits(
        FONT_DIR / "Amiri-Regular.ttf",
        footer_text,
        max_width=850,
        start_size=34,
        minimum_size=24,
    )
    draw = ImageDraw.Draw(overlay)
    draw.text(
        centered_position(draw, footer_text, footer_font, SIZE / 2, 915),
        footer_text,
        font=footer_font,
        fill=(*BLUE, 255),
    )

    overlay.save(OUTPUT_PATH, format="PNG", optimize=True)
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
