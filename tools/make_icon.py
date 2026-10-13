"""Draws the TickTray icon from scratch with Pillow and exports .ico (16-256), PNGs and a preview sheet.

Usage:  venv/Scripts/python tools/make_icon.py <output_folder> [name]
Concept: a thick progress ring (about 75% of the time left) around a check mark ("Tick").
"""
import math
import os
import sys

from PIL import Image, ImageDraw

S = 1024
MARGIN = 40
RADIUS = 230
COLORS = {
    'top': (99, 102, 241),      # indigo
    'bottom': (139, 61, 214),   # violet
    'light': (255, 255, 255, 255),
    'track': (255, 255, 255, 70),
    'amber': (251, 191, 36, 255),
}
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
PREVIEW_SIZES = [16, 24, 32, 48, 256]
RING_R, RING_W = 330, 86
PROGRESS = 0.75


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def background():
    grad = Image.new('RGB', (S, S))
    gd = ImageDraw.Draw(grad)
    for y in range(S):
        gd.line([(0, y), (S, y)], fill=lerp(COLORS['top'], COLORS['bottom'], y / (S - 1)))
    mask = Image.new('L', (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([MARGIN, MARGIN, S - MARGIN, S - MARGIN], radius=RADIUS, fill=255)
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    img.paste(grad, (0, 0), mask)
    highlight = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(highlight).ellipse([-200, -620, S + 200, 420], fill=(255, 255, 255, 34))
    return Image.alpha_composite(img, Image.composite(highlight, Image.new('RGBA', (S, S)), mask))


def point_on_ring(angle_deg):
    a = math.radians(angle_deg)
    return S / 2 + RING_R * math.cos(a), S / 2 + RING_R * math.sin(a)


def cap(d, p, r, fill):
    d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=fill)


def draw_symbol(img):
    cx = cy = S / 2
    box = [cx - RING_R, cy - RING_R, cx + RING_R, cy + RING_R]
    track = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(track).ellipse(box, outline=COLORS['track'], width=RING_W)
    img.alpha_composite(track)

    d = ImageDraw.Draw(img)
    start = -90
    end = start + 360 * PROGRESS
    d.arc(box, start, end, fill=COLORS['light'], width=RING_W)
    cap(d, point_on_ring(start), RING_W / 2, COLORS['light'])
    cap(d, point_on_ring(end), RING_W / 2, COLORS['amber'])

    pts = [(cx - 135, cy + 8), (cx - 28, cy + 118), (cx + 150, cy - 105)]
    w = 78
    d.line(pts, fill=COLORS['light'], width=w, joint='curve')
    for p in (pts[0], pts[2]):
        cap(d, p, w / 2, COLORS['light'])


def preview_sheet(img):
    pad, gap = 24, 28
    width = pad * 2 + sum(PREVIEW_SIZES) + gap * (len(PREVIEW_SIZES) - 1)
    height = pad * 2 + max(PREVIEW_SIZES) * 2 + gap
    sheet = Image.new('RGBA', (width, height), (255, 255, 255, 255))
    ImageDraw.Draw(sheet).rectangle([0, height // 2, width, height], fill=(32, 34, 38, 255))
    for top in (pad, pad + max(PREVIEW_SIZES) + gap):
        x = pad
        for size in PREVIEW_SIZES:
            small = img.resize((size, size), Image.LANCZOS)
            sheet.alpha_composite(small, (x, top + (max(PREVIEW_SIZES) - size) // 2))
            x += size + gap
    return sheet


def main(out_dir, name='TickTray'):
    os.makedirs(out_dir, exist_ok=True)
    img = background()
    draw_symbol(img)
    img.save(os.path.join(out_dir, f'{name}-1024.png'))
    img.resize((256, 256), Image.LANCZOS).save(os.path.join(out_dir, f'{name}-256.png'))
    img.save(os.path.join(out_dir, f'{name}.ico'), sizes=[(s, s) for s in ICO_SIZES])
    preview_sheet(img).save(os.path.join(out_dir, f'{name}-preview.png'))
    print('written to', out_dir)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'TickTray')
