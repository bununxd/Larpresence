"""
Generates the Larpresence logo: icon.ico, logo.png and tray_icon_b64.txt.
Black and white. Needs: pip install Pillow
Run from the project folder:  python tools/make_icon.py
"""
import base64
import io
import os

from PIL import Image, ImageDraw

S = 1024          # master size
K = 4             # supersampling factor (smooth edges)
W = S * K
BLACK = (10, 10, 10, 255)
WHITE = (255, 255, 255, 255)

u = W / 1024


def circle(d, cx, cy, r, fill):
    d.ellipse(((cx - r) * u, (cy - r) * u, (cx + r) * u, (cy + r) * u), fill=fill)


def build():
    img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # black rounded square
    d.rounded_rectangle((0, 0, W - 1, W - 1), radius=232 * u, fill=BLACK)

    # bold white "L"
    r = 70 * u
    d.rounded_rectangle((262 * u, 190 * u, 422 * u, 800 * u), radius=r, fill=WHITE)   # stem
    d.rounded_rectangle((262 * u, 640 * u, 720 * u, 800 * u), radius=r, fill=WHITE)   # foot

    # presence dot: black ring cut into the foot, white dot inside
    circle(d, 742, 742, 178, BLACK)
    circle(d, 742, 742, 124, WHITE)
    return img.resize((S, S), Image.LANCZOS)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    master = build()
    master.save(os.path.join(root, "logo.png"))
    master.save(os.path.join(root, "icon.ico"),
                sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)])
    buf = io.BytesIO()
    master.resize((64, 64), Image.LANCZOS).save(buf, "PNG")
    with open(os.path.join(here, "tray_icon_b64.txt"), "w") as f:
        f.write(base64.b64encode(buf.getvalue()).decode())
    print("created icon.ico, logo.png and tools/tray_icon_b64.txt")
