"""Draws the husky "WOOF!" t-shirt print (own artwork) -> projects/skins/prints/husky_woof.png.
Used by the galaxy Roblox outfit: char_wear(name, "tank", print="skins/prints/husky_woof.png")."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parents[1] / "projects" / "skins" / "prints" / "husky_woof.png"
S = 512
DARK, MID, LIGHT, WHITE, INK = (88, 90, 96), (128, 130, 138), (226, 226, 222), (250, 250, 248), (24, 24, 28)


def main():
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # soft halo so the print reads on a white shirt
    halo = Image.new("L", (S, S), 0)
    ImageDraw.Draw(halo).ellipse((40, 30, 472, 500), fill=90)
    im.paste((205, 205, 210, 255), (0, 0), halo.filter(ImageFilter.GaussianBlur(14)))
    d.ellipse((58, 48, 454, 482), fill=WHITE)
    # ears
    for sx in (1, -1):
        cx = S / 2 + sx * 95
        d.polygon([(cx - sx * 70, 230), (cx + sx * 5, 70), (cx + sx * 70, 250)], fill=DARK, outline=INK)
        d.polygon([(cx - sx * 38, 222), (cx + sx * 4, 118), (cx + sx * 40, 232)], fill=LIGHT)
    # head: dark cap with a white mask
    d.ellipse((130, 170, 382, 430), fill=DARK, outline=INK, width=4)
    d.polygon([(256, 205), (190, 300), (160, 380), (256, 432), (352, 380), (322, 300)], fill=WHITE)
    d.ellipse((150, 300, 362, 436), fill=WHITE)
    d.ellipse((205, 248, 307, 300), fill=MID)  # forehead stripe
    d.polygon([(232, 250), (256, 205), (280, 250)], fill=MID)
    # eyes, nose, smile
    for x in (205, 307):
        d.ellipse((x - 20, 300, x + 20, 344), fill=INK)
        d.ellipse((x - 9, 308, x + 1, 320), fill=WHITE)
    d.ellipse((232, 362, 280, 396), fill=INK)
    d.ellipse((244, 368, 256, 376), fill=(110, 110, 116))
    d.arc((214, 378, 258, 418), 20, 160, fill=INK, width=5)
    d.arc((254, 378, 298, 418), 20, 160, fill=INK, width=5)
    # WOOF!
    try:
        f = ImageFont.truetype("arialbd.ttf", 44)
    except OSError:
        f = ImageFont.load_default()
    d.text((340, 458), "WOOF!", font=f, fill=WHITE, stroke_width=5, stroke_fill=(150, 150, 156), anchor="mm")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
