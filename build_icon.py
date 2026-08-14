"""Generate Dead Letter's Windows application icon using Pillow."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path("DeadLetter.ico")
SIZE = 256
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
seal = (111, 44, 49, 255); seal_edge = (166, 74, 80, 255)
d.ellipse((157, 157, 231, 231), fill=seal, outline=seal_edge, width=5)
font = None
for candidate in ("C:/Windows/Fonts/georgiab.ttf", "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/segoeuib.ttf"):
    try:
        font = ImageFont.truetype(candidate, 30); break
    except OSError:
        pass
if font is None: font = ImageFont.load_default()
text = "DL"; bbox = d.textbbox((0, 0), text, font=font); tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
d.text((194 - tw/2, 194 - th/2 - 2), text, font=font, fill=(239, 221, 192, 255))
img.save(OUT, format="ICO", sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
print(f"Wrote {OUT}")
