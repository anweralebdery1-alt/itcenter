import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


CANVAS_SIZE = 1000
OUTER_BORDER = 24
INNER_LINE_INSET = 39
PHOTO_BOX = (42, 42, 958, 868)
FOOTER_TOP = 870
FOOTER_TEXT = "مركز آي تي للتطوير والتدريب - النجف الاشرف -"
WATERMARK_TEXT = "ITcenterstore"
BLUE = (11, 78, 162)
INNER_BLUE = (88, 137, 198)
BRAND_OVERLAY_PATH = (
    Path(__file__).resolve().parent / "assets" / "product_brand_overlay.png"
)
MAX_OUTPUT_BYTES = 450 * 1024


def _flatten_to_rgb(image):
    image = ImageOps.exif_transpose(image)
    if image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    ):
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, "white")
        return Image.alpha_composite(background, rgba).convert("RGB")
    return image.convert("RGB")


def _add_brand_overlay(canvas):
    with Image.open(BRAND_OVERLAY_PATH) as overlay:
        overlay.load()
        if overlay.size != canvas.size:
            raise ValueError("Product brand overlay has an invalid size")
        return Image.alpha_composite(canvas, overlay.convert("RGBA"))


def _save_optimized_jpeg(image):
    last_buffer = None
    for quality in (84, 80, 76, 72):
        buffer = io.BytesIO()
        image.convert("RGB").save(
            buffer,
            format="JPEG",
            quality=quality,
            optimize=True,
            progressive=True,
            subsampling=2,
        )
        buffer.seek(0)
        last_buffer = buffer
        if buffer.getbuffer().nbytes <= MAX_OUTPUT_BYTES:
            return buffer
    return last_buffer


def prepare_product_image(field_file):
    """Create the branded, square product image used throughout the storefront."""
    field_file.seek(0)
    with Image.open(field_file) as source:
        source.load()
        source = _flatten_to_rgb(source)

    photo_width = PHOTO_BOX[2] - PHOTO_BOX[0]
    photo_height = PHOTO_BOX[3] - PHOTO_BOX[1]
    photo = ImageOps.fit(
        source,
        (photo_width, photo_height),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )

    canvas = Image.new(
        "RGBA",
        (CANVAS_SIZE, CANVAS_SIZE),
        (*BLUE, 255),
    )
    draw = ImageDraw.Draw(canvas)
    draw.rectangle(
        (
            OUTER_BORDER,
            OUTER_BORDER,
            CANVAS_SIZE - OUTER_BORDER - 1,
            CANVAS_SIZE - OUTER_BORDER - 1,
        ),
        fill="white",
    )
    draw.rectangle(
        (
            INNER_LINE_INSET,
            INNER_LINE_INSET,
            CANVAS_SIZE - INNER_LINE_INSET - 1,
            CANVAS_SIZE - INNER_LINE_INSET - 1,
        ),
        outline=INNER_BLUE,
        width=2,
    )
    canvas.paste(photo, PHOTO_BOX[:2])

    draw = ImageDraw.Draw(canvas)
    draw.line(
        (
            INNER_LINE_INSET,
            FOOTER_TOP,
            CANVAS_SIZE - INNER_LINE_INSET - 1,
            FOOTER_TOP,
        ),
        fill=BLUE,
        width=3,
    )
    canvas = _add_brand_overlay(canvas)

    return _save_optimized_jpeg(canvas), "jpg"
