"""Generate Dead Letter's Windows application and updater icons using Pillow."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SIZE = 256


def font(size):
    for candidate in (
        "C:/Windows/Fonts/georgiab.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
    ):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


def save_main_icon():
    img = Image.new("RGBA", (SIZE, SIZE), (23, 23, 25, 255))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((14, 14, 242, 242), radius=28, fill=(34, 34, 38, 255), outline=(216, 170, 85, 255), width=8)
    d.rounded_rectangle((28, 28, 228, 228), radius=22, outline=(95, 75, 45, 255), width=3)
    line = (183, 178, 166, 255); body = (238, 233, 222, 255)
    d.line((55, 190, 160, 190), fill=line, width=8)
    d.line((76, 190, 76, 61), fill=line, width=8)
    d.line((72, 61, 161, 61), fill=line, width=8)
    d.line((160, 61, 160, 88), fill=line, width=6)
    d.ellipse((141, 86, 179, 124), outline=body, width=6)
    d.line((160, 124, 160, 165), fill=body, width=6)
    d.line((160, 137, 139, 153), fill=body, width=6)
    d.line((160, 137, 181, 153), fill=body, width=6)
    d.line((160, 165, 144, 188), fill=body, width=6)
    d.line((160, 165, 176, 188), fill=body, width=6)
    d.ellipse((157, 157, 231, 231), fill=(111, 44, 49, 255), outline=(166, 74, 80, 255), width=5)
    f = font(30); text = "DL"; bbox = d.textbbox((0, 0), text, font=f); tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    d.text((194 - tw/2, 194 - th/2 - 2), text, font=f, fill=(239, 221, 192, 255))
    img.save("DeadLetter.ico", format="ICO", sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])


def save_updater_icon():
    # Intentionally subdued and visually distinct from the actual game icon.
    img = Image.new("RGBA", (SIZE, SIZE), (29, 31, 35, 255))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((18, 18, 238, 238), radius=32, fill=(43, 46, 52, 255), outline=(102, 112, 126, 255), width=7)
    d.arc((54, 52, 202, 200), 205, 355, fill=(151, 163, 181, 255), width=14)
    d.arc((54, 52, 202, 200), 25, 175, fill=(151, 163, 181, 255), width=14)
    d.polygon([(194, 84), (215, 54), (218, 96)], fill=(151, 163, 181, 255))
    d.polygon([(62, 169), (41, 201), (39, 158)], fill=(151, 163, 181, 255))
    f = font(42); text = "UP"; bbox = d.textbbox((0, 0), text, font=f); tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    d.text((128 - tw/2, 126 - th/2 - 3), text, font=f, fill=(225, 228, 233, 255))
    img.save("DeadLetterUpdater.ico", format="ICO", sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])


save_main_icon()
save_updater_icon()
print("Wrote DeadLetter.ico and DeadLetterUpdater.ico")
