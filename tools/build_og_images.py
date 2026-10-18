#!/usr/bin/env python3
"""Regenerates the per-vendor social share images ({slug}-og.png) from
data/vendors.json, so each vendor's share image always shows the
current price instead of going stale. Run after updating vendors.json:

    python3 tools/build_og_images.py

Requires Pillow (install once with: pip3 install --break-system-packages Pillow).
Looks for a serif/sans/mono font in a few common locations on macOS and
Linux; if none are found, it falls back to Pillow's built-in font and
tells you the images will look plainer than usual."""
import json, datetime, pathlib, sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow is not installed. Run: pip3 install --break-system-packages Pillow")
    sys.exit(1)

root = pathlib.Path(__file__).resolve().parent.parent
vendors = json.load(open(root/'data/vendors.json', encoding='utf-8'))

BG = (19, 29, 26)
INK = (233, 230, 223)
INK_SOFT = (154, 154, 163)
ACCENT = (79, 168, 156)
RED = (209, 106, 81)
GREEN = (90, 157, 111)
LINE = (36, 50, 46)
BG_RAISED = (26, 38, 34)

def find_font(candidates, size):
    for path in candidates:
        if pathlib.Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

SERIF_BOLD_PATHS = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf',
    '/System/Library/Fonts/Supplemental/Georgia Bold.ttf',
    '/Library/Fonts/Georgia Bold.ttf',
]
SANS_PATHS = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    '/System/Library/Fonts/Supplemental/Arial.ttf',
    '/Library/Fonts/Arial.ttf',
]
MONO_PATHS = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
    '/System/Library/Fonts/Supplemental/Menlo.ttc',
    '/System/Library/Fonts/SFNSMono.ttf',
    '/Library/Fonts/Courier New.ttf',
]
MONO_BOLD_PATHS = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf',
    '/System/Library/Fonts/Supplemental/Menlo-Bold.ttc',
    '/Library/Fonts/Courier New Bold.ttf',
]

f_logo = find_font(MONO_BOLD_PATHS, 28)
f_title = find_font(SERIF_BOLD_PATHS, 58)
f_tag = find_font(SANS_PATHS, 24)
f_label = find_font(MONO_PATHS, 18)
f_price = find_font(SERIF_BOLD_PATHS, 30)
f_verified = find_font(MONO_PATHS, 16)

def wrap(d, text, font, max_w):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if d.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

def nice(dstr):
    return datetime.date.fromisoformat(dstr).strftime('%b %-d, %Y')

def build(v):
    W, H = 1200, 630
    img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)
    margin = 72
    max_w = W - margin * 2

    mark_cx, mark_cy, mark_r = margin + 16, margin + 14, 14
    d.polygon([(mark_cx, mark_cy - mark_r), (mark_cx + mark_r, mark_cy), (mark_cx - mark_r, mark_cy)], fill=RED)
    d.polygon([(mark_cx, mark_cy + mark_r), (mark_cx + mark_r, mark_cy + 1), (mark_cx - mark_r, mark_cy + 1)], fill=GREEN)
    d.text((mark_cx + mark_r + 14, mark_cy - 14), "QuietHike", font=f_logo, fill=ACCENT)

    ty = 150
    for ln in wrap(d, f'{v["name"]} price changes', f_title, max_w):
        d.text((margin, ty), ln, font=f_title, fill=INK)
        ty += 68

    ty += 6
    for ln in wrap(d, f'Tracking: {v["tracks"]}', f_tag, max_w):
        d.text((margin, ty), ln, font=f_tag, fill=INK_SOFT)
        ty += 34

    card_y = max(ty + 24, 380)
    card_h = H - card_y - 72
    d.rounded_rectangle([margin, card_y, W - margin, card_y + card_h], radius=8, outline=LINE, width=2, fill=BG_RAISED)
    pad = 28
    cy = card_y + 24
    d.text((margin + pad, cy), "CURRENT PRICE", font=f_label, fill=INK_SOFT)
    cy += 30
    for ln in wrap(d, v['current'], f_price, max_w - pad * 2):
        d.text((margin + pad, cy), ln, font=f_price, fill=INK)
        cy += 40
    d.text((margin + pad, card_y + card_h - 34), f'Last rechecked {nice(v["last_verified"])} · quiethike.com', font=f_verified, fill=INK_SOFT)

    return img

for v in vendors:
    img = build(v)
    out = root / f'{v["slug"]}-og.png'
    img.save(out)
    print('wrote', out.name)
print('done —', len(vendors), 'social share images regenerated')
