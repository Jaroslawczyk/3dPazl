"""Draws packaging/pazl.ico (a stylised house) with Pillow."""
from pathlib import Path

from PIL import Image, ImageDraw

S = 256
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle((8, 8, S - 8, S - 8), 48, fill=(32, 44, 64, 255))
d.polygon([(40, 124), (128, 44), (216, 124)], fill=(214, 92, 62, 255))
d.rectangle((62, 120, 194, 214), fill=(236, 226, 206, 255))
d.rectangle((110, 152, 146, 214), fill=(120, 78, 48, 255))
for x in (74, 160):
    d.rectangle((x, 140, x + 24, 166), fill=(120, 180, 230, 255))
img.save(Path(__file__).with_name("pazl.ico"), sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
