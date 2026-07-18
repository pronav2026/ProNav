#!/usr/bin/env python3
"""Compose topology ablation comparison figure from individual trajectory screenshots.
Usage: python3 compose_figure.py
Output: imgs/topo_ablation.pdf (relative to project root)
"""
from PIL import Image, ImageChops, ImageColor, ImageDraw, ImageFont
import os
import re

# Paths
script_dir = os.path.dirname(os.path.abspath(__file__))
proj_root = os.path.dirname(os.path.dirname(script_dir))  # up to mypaper/
img_dir = script_dir
out_path = os.path.join(proj_root, "imgs", "topo_ablation.pdf")

a_files = [
    "A_baseline_timeout_step01_t5.0s.png",
    "A_baseline_timeout_step02_t15.0s.png",
    "A_baseline_timeout_step03_t24.9s.png",
    "A_baseline_timeout_step04_t34.9s.png",
    "A_baseline_timeout_LAST2_t49.5s.png",
]
b_files = sorted([f for f in os.listdir(img_dir) if f.startswith("B_")])

PAPER_RED = "#9B3D35"
PAPER_GREEN = "#2F6F4E"
INK = "#1F1F1F"
MUTED = "#666666"
BORDER = "#CFCFCF"
LIGHT_RULE = "#D9D9D9"
PANEL_BG = "#FAFAFA"
BG = "white"
TRAJECTORY_BLUE = (0, 92, 175)
TEMPORAL = "#8A8A8A"

def rotate_and_trim(path, angle=49, padding=6):
    """Rotate on a white background, then remove the large white outer margins."""
    im = Image.open(path).convert("RGBA").rotate(angle, expand=True)
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    im = Image.alpha_composite(bg, im).convert("RGB")

    diff = ImageChops.difference(im, Image.new("RGB", im.size, "white"))
    bbox = diff.getbbox()
    if bbox is None:
        return im

    left, top, right, bottom = bbox
    left = max(left - padding, 0)
    top = max(top - padding, 0)
    right = min(right + padding, im.width)
    bottom = min(bottom + padding, im.height)
    return im.crop((left, top, right, bottom))


def enhance_trajectory_colors(im):
    """Increase path contrast by recoloring saturated green trajectory pixels."""
    im = im.convert("RGB")
    pix = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b = pix[x, y]
            is_bright_green_path = g > 150 and r < 90 and b < 120 and g - max(r, b) > 70
            if is_bright_green_path:
                pix[x, y] = TRAJECTORY_BLUE
    return im


try:
    font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 21)
    font_badge = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    font_outcome = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 15)
    font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 13)
except Exception:
    font_title = font_badge = font_outcome = font_small = ImageFont.load_default()


def step_from_filename(filename):
    match = re.search(r"_t([0-9.]+)s", filename)
    return f"step {round(float(match.group(1)) * 10):d}" if match else ""


def fit_image(im, max_w, max_h):
    scale = min(max_w / im.width, max_h / im.height)
    size = (round(im.width * scale), round(im.height * scale))
    return im.resize(size, Image.LANCZOS)


def rounded_rect(draw, xy, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def text_size(draw, text, font):
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def tint_color(color, amount=0.88):
    """Mix a color with white for low-contrast publication badges."""
    r, g, b = ImageColor.getrgb(color)
    return tuple(round(c + (255 - c) * amount) for c in (r, g, b))


def draw_badge(draw, x, y, text, fill, font, pad_x=6, pad_y=2, min_w=0, inverse=False):
    """Draw a restrained publication-style label with a thin rule."""
    tw, th = text_size(draw, text, font)
    w = max(tw + pad_x * 2, min_w)
    h = th + pad_y * 2 + 1
    if inverse:
        rounded_rect(draw, (x, y, x + w, y + h), 2, fill=tint_color(fill), outline=fill, width=1)
        draw.text((x + (w - tw) // 2, y + pad_y - 1), text, fill=fill, font=font)
    else:
        draw.rectangle((x, y, x + w, y + h), fill="white")
        draw.line((x, y + h, x + w, y + h), fill=fill, width=1)
        draw.text((x + (w - tw) // 2, y + pad_y - 1), text, fill=INK, font=font)
    return w, h


def draw_outcome_mark(draw, x, y, color, kind):
    if kind == "success":
        draw.line((x, y + 6, x + 5, y + 12, x + 15, y), fill=color, width=3, joint="curve")
    else:
        draw.line((x + 2, y + 2, x + 14, y + 14), fill=color, width=3)
        draw.line((x + 14, y + 2, x + 2, y + 14), fill=color, width=3)


def outcome_badge_size(draw, text, font):
    pad_x = 8
    icon_w = 16
    icon_gap = 5
    h = 28
    tw, th = text_size(draw, text, font)
    w = pad_x * 2 + icon_w + icon_gap + tw
    return w, h


def draw_outcome_badge(draw, x, y, text, color, font):
    """Draw final outcome as a light rounded label with a leading check/cross."""
    pad_x = 8
    icon_w = 16
    icon_gap = 5
    w, h = outcome_badge_size(draw, text, font)
    _, th = text_size(draw, text, font)

    rounded_rect(draw, (x, y, x + w, y + h), 6, fill=tint_color(color, 0.88))

    kind = "success" if text.lower() == "success" else "timeout"
    icon_y = y + (h - 16) // 2
    draw_outcome_mark(draw, x + pad_x, icon_y, color, kind)

    text_x = x + pad_x + icon_w + icon_gap
    text_y = y + (h - th) // 2 - 1
    draw.text((text_x, text_y), text, fill=color, font=font)
    return w, h


def draw_dashed_line(draw, x0, y, x1, fill=TEMPORAL, width=1, dash=5, gap=4):
    x = x0
    while x < x1:
        draw.line((x, y, min(x + dash, x1), y), fill=fill, width=width)
        x += dash + gap


def draw_snapshot(canvas, x, y, im, time_text, row_color, tile_w, outcome=None, shared_scale=None):
    draw = ImageDraw.Draw(canvas)
    tile_h = 258
    pad = 2

    # Flat panel with a light border; avoids dashboard-like rounded cards.
    draw.rectangle((x, y, x + tile_w, y + tile_h), fill=PANEL_BG, outline=BORDER, width=1)

    if shared_scale is None:
        fitted = fit_image(im, tile_w - pad * 2, tile_h - pad * 2 - 8)
    else:
        fitted = im.resize(
            (
                max(1, round(im.width * shared_scale)),
                max(1, round(im.height * shared_scale)),
            ),
            Image.LANCZOS,
        )

    ix = x + (tile_w - fitted.width) // 2
    iy = y + 10 + (tile_h - 10 - fitted.height) // 2
    canvas.paste(fitted, (ix, iy))

    # Step label uses plain text plus a thin underline.
    badge_w, _ = text_size(draw, time_text, font_badge)
    badge_w += 12
    draw_badge(
        draw,
        x + tile_w - badge_w - 7,
        y + 5,
        time_text,
        fill="#555555",
        font=font_badge,
        pad_x=6,
        pad_y=2,
        inverse=False,
    )

    if outcome:
        outcome_w, outcome_h = outcome_badge_size(draw, outcome, font_outcome)
        draw_outcome_badge(
            draw,
            x + (tile_w - outcome_w) // 2,
            y + tile_h - outcome_h - 7,
            outcome,
            row_color,
            font=font_outcome,
        )


a_imgs = [enhance_trajectory_colors(rotate_and_trim(os.path.join(img_dir, f))) for f in a_files]
b_imgs = [enhance_trajectory_colors(rotate_and_trim(os.path.join(img_dir, f))) for f in b_files]

tile_h = 258
cell_pad = 2
content_max_h = tile_h - 2 * cell_pad - 8
gap_x = 8
row_gap = 10
margin_x = 12
margin_y = 12
label_h = 34

# Determine each row's shared scale from its rightmost image, then set every
# cell width to the largest resulting image width across the whole figure.
image_rows = [a_imgs, b_imgs]
row_scales = [content_max_h / imgs[-1].height for imgs in image_rows]
scaled_widths = []
for imgs, row_scale in zip(image_rows, row_scales):
    for i, im in enumerate(imgs):
        column_scale = row_scale * (0.94 if i == 1 else 1.0)
        scaled_widths.append(round(im.width * column_scale))

tile_w = max(scaled_widths) + 2 * cell_pad

total_w = margin_x * 2 + tile_w * 5 + gap_x * 4
total_h = margin_y * 2 + (label_h + tile_h) * 2 + row_gap

canvas = Image.new("RGB", (total_w, total_h), BG)
draw = ImageDraw.Draw(canvas)

rows = [
    (a_imgs, a_files, "(a) No topology cost", "Timeout", PAPER_RED),
    (b_imgs, b_files, "(b) With topology cost", "Success", PAPER_GREEN),
]

for row_idx, (imgs, files, title, final_outcome, color) in enumerate(rows):
    row_block_h = label_h + tile_h
    row_y = margin_y + row_idx * (row_block_h + row_gap)
    draw.text((margin_x, row_y + 1), title, fill=INK, font=font_title)
    subtitle = "low-priority detours" if row_idx == 0 else "direct cross-room path"
    sw, _ = text_size(draw, subtitle, font_small)
    draw.text((total_w - margin_x - sw, row_y + 7), subtitle, fill=MUTED, font=font_small)
    draw.line(
        (margin_x, row_y + label_h - 5, total_w - margin_x, row_y + label_h - 5),
        fill=LIGHT_RULE,
        width=1,
    )

    tile_y = row_y + label_h
    row_scale = row_scales[row_idx]

    for i, im in enumerate(imgs):
        tile_x = margin_x + i * (tile_w + gap_x)
        outcome = final_outcome if i == len(imgs) - 1 else None
        column_scale = row_scale * (0.94 if i == 1 else 1.0)
        draw_snapshot(
            canvas,
            tile_x,
            tile_y,
            im,
            step_from_filename(files[i]),
            color,
            tile_w,
            outcome,
            shared_scale=column_scale,
        )

canvas.save(out_path, quality=95)
canvas.save(os.path.join(proj_root, "imgs", "topo_ablation.png"), quality=95)
print(f"Saved: {out_path}")
print(f"Canvas: {canvas.size[0]} x {canvas.size[1]}")
print("Rotated images trimmed, trajectories recolored, normalized into a compact image plate with step badges.")
