# -*- coding: utf-8 -*-
"""
utils/image_utils.py
=====================
Image manipulation helpers shared across the application.
"""

import io
import zipfile
import numpy as np
import cv2
from PIL import Image, ImageDraw


# ─── Conversion helpers ────────────────────────────────────────────

def pil_to_bytes(img: Image.Image, fmt: str = "PNG") -> bytes:
    """Return PIL image encoded as bytes."""
    buf = io.BytesIO()
    if fmt.upper() == "JPEG":
        img.convert("RGB").save(buf, format="JPEG", quality=95)
    else:
        img.save(buf, format="PNG")
    return buf.getvalue()


def make_zip(original: Image.Image, mask_arr: np.ndarray,
             segmented: Image.Image) -> bytes:
    """Bundle Original / Mask / Segmented into a ZIP archive."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("Original.jpg",   pil_to_bytes(original.convert("RGB"), "JPEG"))
        zf.writestr("Mask.png",       pil_to_bytes(Image.fromarray(mask_arr), "PNG"))
        zf.writestr("Segmented.png",  pil_to_bytes(segmented, "PNG"))
    return buf.getvalue()


# ─── Pant guide overlay ────────────────────────────────────────────

def draw_pant_guide_html(width_px: int = 360, height_px: int = 480) -> str:
    """
    Return an HTML string containing an SVG pant-shaped guide overlay.
    The SVG is absolutely positioned and pointer-events: none so it
    sits visually above the camera feed without intercepting touch events.

    This is rendered via st.markdown(unsafe_allow_html=True) directly
    over the camera widget.
    """
    w, h = width_px, height_px

    # Key points (normalised fractions of w/h)
    left_f   = 0.16
    right_f  = 0.84
    top_f    = 0.06
    bot_f    = 0.94
    crotch_f = 0.44   # vertical position of crotch relative to top→bot
    narrow_f = 0.12   # how much each side narrows toward crotch

    l  = w * left_f
    r  = w * right_f
    t  = h * top_f
    b  = h * bot_f
    cy = t + (b - t) * crotch_f
    cx = w * 0.5

    # Waistband corners (slightly inset from outer)
    wl = l + (r - l) * narrow_f
    wr = r - (r - l) * narrow_f

    # SVG path for pant silhouette
    path = (
        f"M {wl:.1f},{t:.1f} "
        f"L {wr:.1f},{t:.1f} "
        f"L {r:.1f},{b:.1f} "
        f"L {cx+20:.1f},{b:.1f} "
        f"L {cx:.1f},{cy:.1f} "
        f"L {cx-20:.1f},{b:.1f} "
        f"L {l:.1f},{b:.1f} "
        f"Z"
    )

    # Corner bracket marks (top-left, top-right)
    cl = 22  # bracket length
    corners_svg = (
        # Top-left
        f'<line x1="{l:.0f}" y1="{t:.0f}" x2="{l+cl:.0f}" y2="{t:.0f}" '
        f'stroke="rgba(255,255,255,0.9)" stroke-width="2.5" stroke-linecap="round"/>'
        f'<line x1="{l:.0f}" y1="{t:.0f}" x2="{l:.0f}" y2="{t+cl:.0f}" '
        f'stroke="rgba(255,255,255,0.9)" stroke-width="2.5" stroke-linecap="round"/>'
        # Top-right
        f'<line x1="{r:.0f}" y1="{t:.0f}" x2="{r-cl:.0f}" y2="{t:.0f}" '
        f'stroke="rgba(255,255,255,0.9)" stroke-width="2.5" stroke-linecap="round"/>'
        f'<line x1="{r:.0f}" y1="{t:.0f}" x2="{r:.0f}" y2="{t+cl:.0f}" '
        f'stroke="rgba(255,255,255,0.9)" stroke-width="2.5" stroke-linecap="round"/>'
        # Bottom-left
        f'<line x1="{l:.0f}" y1="{b:.0f}" x2="{l+cl:.0f}" y2="{b:.0f}" '
        f'stroke="rgba(255,255,255,0.9)" stroke-width="2.5" stroke-linecap="round"/>'
        f'<line x1="{l:.0f}" y1="{b:.0f}" x2="{l:.0f}" y2="{b-cl:.0f}" '
        f'stroke="rgba(255,255,255,0.9)" stroke-width="2.5" stroke-linecap="round"/>'
        # Bottom-right
        f'<line x1="{r:.0f}" y1="{b:.0f}" x2="{r-cl:.0f}" y2="{b:.0f}" '
        f'stroke="rgba(255,255,255,0.9)" stroke-width="2.5" stroke-linecap="round"/>'
        f'<line x1="{r:.0f}" y1="{b:.0f}" x2="{r:.0f}" y2="{b-cl:.0f}" '
        f'stroke="rgba(255,255,255,0.9)" stroke-width="2.5" stroke-linecap="round"/>'
    )

    # Label at top
    label_y = t - 8

    svg = f"""
<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg"
     style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:20;">
  <defs>
    <style>
      .guide-text {{
        font-family: 'Inter', system-ui, sans-serif;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1px;
        fill: rgba(255,255,255,0.75);
        text-anchor: middle;
        dominant-baseline: auto;
      }}
    </style>
  </defs>

  <!-- Pant silhouette fill -->
  <path d="{path}" fill="rgba(255,255,255,0.05)" />

  <!-- Pant silhouette stroke (dashed) -->
  <path d="{path}"
        fill="none"
        stroke="rgba(255,255,255,0.55)"
        stroke-width="1.8"
        stroke-dasharray="8 5"
        stroke-linecap="round" />

  <!-- Corner brackets -->
  {corners_svg}

  <!-- "WAIST" label -->
  <text class="guide-text" x="{cx:.0f}" y="{t - 10:.0f}">WAIST</text>

  <!-- Instruction text -->
  <rect x="{w*0.1:.0f}" y="{h*0.96:.0f}" width="{w*0.8:.0f}" height="22"
        rx="11" fill="rgba(0,0,0,0.55)" />
  <text class="guide-text" x="{cx:.0f}" y="{h*0.96+14:.0f}"
        fill="rgba(255,255,255,0.8)" font-size="10px" letter-spacing="0.5px">
    Place entire pant inside frame
  </text>
</svg>
"""
    return svg


# ─── Post-segmentation helpers ─────────────────────────────────────

def auto_rotate_cutout(rgba_pil: Image.Image) -> Image.Image:
    """
    Rotate pant PNG so the waist (wider end) faces up.
    Uses minAreaRect on non-transparent pixels.
    """
    arr = np.array(rgba_pil)
    alpha = arr[:, :, 3]
    points = np.column_stack(np.where(alpha > 0))
    if len(points) < 20:
        return rgba_pil

    pts = points[:, ::-1].astype(np.float32)
    rect = cv2.minAreaRect(pts)
    _, (rw, rh), angle = rect
    if rw > rh:
        angle += 90

    center = (arr.shape[1] / 2, arr.shape[0] / 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        arr, M, (arr.shape[1], arr.shape[0]),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0),
    )

    alpha_r = rotated[:, :, 3]
    ys, _ = np.where(alpha_r > 0)
    if len(ys) < 10:
        return Image.fromarray(rotated, "RGBA")

    y_min, y_max = ys.min(), ys.max()
    span = y_max - y_min
    y_top = y_min + int(span * 0.2)
    y_bot = y_max - int(span * 0.2)
    top_w = int(np.sum(alpha_r[y_top] > 0))
    bot_w = int(np.sum(alpha_r[y_bot] > 0))
    if top_w < bot_w:
        rotated = cv2.rotate(rotated, cv2.ROTATE_180)

    return Image.fromarray(rotated, "RGBA")
