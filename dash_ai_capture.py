# -*- coding: utf-8 -*-
"""
DASH AI Capture — Streamlit Edition
====================================
Premium pant-image capture & SAM 3 segmentation pipeline.

Run:
    cd "d:/sam3 working/DashAICapture_Streamlit"
    streamlit run dash_ai_capture.py

Features:
  • Webcam capture (back-camera-first UX)
  • Live Pitch / Roll simulation via sliders (real sensor not available in browser)
  • Live pant detection (lightweight contour analysis)
  • Quality checks: sharpness, lighting, border safety
  • 5-chip live status HUD
  • SAM 3 segmentation post-capture → Original.jpg / Mask.png / Segmented.png
  • Clean MeasurementPipeline interface stub for HRNet
"""

import os
import sys
import io
import time
import glob
import json
import pathlib
import zipfile
import datetime
import math

import numpy as np
import cv2
import streamlit as st
from PIL import Image, ImageFilter, ImageDraw

# ─────────────────────────────────────────────────────────────────
# PATH SETUP  — let Python find the sam3 package
# ─────────────────────────────────────────────────────────────────
_HERE = pathlib.Path(__file__).resolve().parent
_SAM3_PANT_DIR = _HERE.parent / "dash_ai" / "sam3_pant"
for p in [str(_SAM3_PANT_DIR), str(_SAM3_PANT_DIR / "sam3")]:
    if p not in sys.path:
        sys.path.insert(0, p)

# ─────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DASH AI Capture",
    page_icon="👖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────
# PREMIUM CSS INJECTION
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* ── Global reset ── */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }

  .main { background: #ffffff !important; }
  .block-container { padding: 0 !important; max-width: 100% !important; }

  /* ── Header bar ── */
  .dash-header {
    background: #0f0f11;
    color: #fff;
    text-align: center;
    padding: 18px 24px;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 3px;
    border-bottom: 1px solid #222;
  }

  /* ── Section cards ── */
  .dash-card {
    background: #f8f9fa;
    border: 1px solid #e5e5ea;
    border-radius: 20px;
    padding: 20px 22px;
    margin-bottom: 16px;
  }

  /* ── Glass HUD level card ── */
  .level-card {
    background: rgba(24,24,27,0.92);
    border: 1.5px solid rgba(255,255,255,0.15);
    border-radius: 20px;
    padding: 16px 22px;
    color: #fff;
    margin-bottom: 16px;
  }
  .level-card.valid { border-color: #00c853 !important; }

  .level-label {
    color: #8e8e93;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    margin-bottom: 8px;
  }

  .level-value { font-size: 22px; font-weight: 800; }
  .level-value.ok { color: #00c853; }
  .level-value.warn { color: #ffab00; }

  /* ── Status chips ── */
  .chips-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }

  .chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    border-radius: 100px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
    border: 1.2px solid;
    transition: all 0.3s ease;
  }
  .chip.ok {
    background: rgba(0,200,83,0.12);
    border-color: #00c853;
    color: #00c853;
  }
  .chip.fail {
    background: rgba(24,24,27,0.85);
    border-color: rgba(255,255,255,0.2);
    color: #fff;
  }

  /* ── Guidance banner ── */
  .guidance-banner {
    background: rgba(24,24,27,0.92);
    color: #fff;
    border-radius: 14px;
    padding: 12px 18px;
    font-size: 14px;
    font-weight: 600;
    text-align: center;
    margin-bottom: 12px;
  }
  .guidance-banner.go { background: #00c853; color: #fff; }

  /* ── Countdown overlay ── */
  .countdown {
    text-align: center;
    font-size: 96px;
    font-weight: 900;
    color: #00c853;
    line-height: 1;
    padding: 20px;
  }

  /* ── Buttons ── */
  .stButton > button {
    width: 100%;
    border-radius: 28px !important;
    height: 52px !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    background: #111 !important;
    color: #fff !important;
    border: none !important;
    letter-spacing: 0.5px;
    transition: opacity 0.2s;
  }
  .stButton > button:hover { opacity: 0.88; }
  .stButton > button:disabled {
    background: #d1d1d6 !important;
    color: #8e8e93 !important;
  }

  .stDownloadButton > button {
    width: 100% !important;
    border-radius: 28px !important;
    height: 48px !important;
    font-size: 14px !important;
    font-weight: 700 !important;
    background: #f2f2f7 !important;
    color: #111 !important;
    border: 1px solid #e5e5ea !important;
  }

  /* ── Result image cards ── */
  .result-card {
    background: #f8f9fa;
    border: 1px solid #e5e5ea;
    border-radius: 20px;
    padding: 16px;
    text-align: center;
  }
  .result-card-title {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    color: #6e6e73;
    margin-bottom: 10px;
  }

  /* ── SAM3 processing ── */
  .processing-box {
    background: #fff;
    border: 1px solid #e5e5ea;
    border-radius: 24px;
    padding: 48px 32px;
    text-align: center;
  }
  .processing-title { font-size: 22px; font-weight: 800; color: #111; margin-bottom: 8px; }
  .processing-sub { font-size: 14px; color: #8e8e93; }

  /* ── Footer note ── */
  .footer-note {
    text-align: center;
    font-size: 11px;
    color: #c7c7cc;
    padding: 24px 0 12px;
  }

  /* Hide streamlit chrome */
  #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# MODULE: LIGHTWEIGHT PANT DETECTOR
# ─────────────────────────────────────────────────────────────────
class PantDetectionResult:
    def __init__(self):
        self.pant_count = 0
        self.is_single_pant = False
        self.is_entire_pant_in_frame = False
        self.is_touching_border = False
        self.message = "Place one pant inside the frame."


def detect_pant(pil_image: Image.Image) -> PantDetectionResult:
    """Lightweight pant existence & border check via pixel-level analysis."""
    result = PantDetectionResult()

    arr = np.array(pil_image.convert("RGB"))
    h, w = arr.shape[:2]

    # Downscale for speed
    scale = 0.25
    sw, sh = max(60, int(w * scale)), max(60, int(h * scale))
    small = cv2.resize(arr, (sw, sh), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)

    # Adaptive threshold to isolate garment from white/light background
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Morphological cleanup
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = sw * sh * 0.05
    valid_contours = [c for c in contours if cv2.contourArea(c) > min_area]

    result.pant_count = len(valid_contours)
    result.is_single_pant = (result.pant_count == 1)

    if result.is_single_pant:
        x, y, cw, ch = cv2.boundingRect(valid_contours[0])
        margin = 3
        result.is_touching_border = (x <= margin or y <= margin or
                                     x + cw >= sw - margin or y + ch >= sh - margin)
        result.is_entire_pant_in_frame = not result.is_touching_border
        result.message = "Move pant away from border." if result.is_touching_border else "✓ Pant detected"
    elif result.pant_count == 0:
        result.message = "Place one pant inside the frame."
    else:
        result.message = "Only one pant allowed."

    return result


# ─────────────────────────────────────────────────────────────────
# MODULE: QUALITY CHECKER
# ─────────────────────────────────────────────────────────────────
def compute_quality(pil_image: Image.Image, pitch: float, roll: float,
                    detection: PantDetectionResult):
    """Computes all 5 quality booleans + guidance string."""
    # 1. Level
    is_level = (-5.0 <= pitch <= 5.0) and (-5.0 <= roll <= 5.0)

    # 2. Pant detection
    is_pant = detection.is_single_pant

    # 3. Entire pant visible
    is_visible = detection.is_entire_pant_in_frame

    # 4. Sharpness (Laplacian variance)
    arr = np.array(pil_image.convert("L"))
    small = cv2.resize(arr, (320, 320), interpolation=cv2.INTER_AREA)
    lap_var = cv2.Laplacian(small, cv2.CV_64F).var()
    is_sharp = float(lap_var) >= 30.0

    # 5. Lighting
    mean_brightness = float(np.mean(arr))
    is_lit = 40.0 <= mean_brightness <= 230.0

    # Guidance
    if not is_level:
        if pitch > 5:   guidance = "⬇ Lower your phone"
        elif pitch < -5: guidance = "⬆ Tilt phone up"
        elif roll > 5:  guidance = "➡ Rotate phone clockwise"
        else:           guidance = "⬅ Rotate phone counter-clockwise"
    elif not is_pant:
        guidance = detection.message
    elif not is_visible:
        guidance = "Ensure entire pant is visible inside frame"
    elif not is_lit:
        guidance = "Dark image — increase lighting" if mean_brightness < 40 else "Overexposed — reduce bright light"
    elif not is_sharp:
        guidance = "Image is blurry — hold camera steady"
    else:
        guidance = "✅ All checks passed! Auto-capturing…"

    all_ok = is_level and is_pant and is_visible and is_sharp and is_lit

    return {
        "is_level": is_level,
        "is_pant": is_pant,
        "is_visible": is_visible,
        "is_sharp": is_sharp,
        "is_lit": is_lit,
        "all_ok": all_ok,
        "guidance": guidance,
        "lap_var": round(float(lap_var), 1),
        "brightness": round(mean_brightness, 1),
        "pitch": pitch,
        "roll": roll,
    }


# ─────────────────────────────────────────────────────────────────
# MODULE: SAM 3 SEGMENTATION ENGINE
# ─────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def load_sam3_model():
    """Load SAM 3 model once, keep in session cache."""
    try:
        import torch
        from sam3.model_builder import build_sam3_image_model
        from sam3.model.sam3_image_processor import Sam3Processor

        ckpt_path = str(_SAM3_PANT_DIR / "checkpoints" / "sam3.pt")
        bpe_paths = glob.glob(str(_SAM3_PANT_DIR / "**" / "bpe_simple_vocab_16e6.txt.gz"), recursive=True)

        if not bpe_paths:
            return None, "BPE vocab file not found. Run from the sam3_pant directory."

        bpe_path = bpe_paths[0]
        model = build_sam3_image_model(
            bpe_path=bpe_path,
            checkpoint_path=ckpt_path if os.path.exists(ckpt_path) else None,
            load_from_HF=not os.path.exists(ckpt_path),
            compile=False,
        )

        if not torch.cuda.is_available():
            model.float()

        processor = Sam3Processor(model, confidence_threshold=0.3)
        return processor, None

    except Exception as e:
        return None, str(e)


def run_sam3_segmentation(pil_image: Image.Image, processor):
    """
    Run SAM 3 with text prompt 'pants' and produce:
      - binary_mask (np.ndarray H×W uint8, 0/255)
      - segmented RGBA (PIL Image)
    """
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32

    with torch.inference_mode(), torch.autocast(device_type=device, dtype=dtype):
        state = processor.set_image(pil_image)
        state = processor.set_text_prompt(state=state, prompt="pants")
        masks  = state["masks"].to(torch.float32).cpu().numpy()
        scores = state["scores"].to(torch.float32).cpu().numpy()

    if len(masks) == 0:
        return None, None

    best_idx = int(np.argmax(scores))
    mask = masks[best_idx]
    if mask.ndim == 3:
        mask = mask[0]

    w, h = pil_image.size
    if mask.shape != (h, w):
        mask = cv2.resize(mask.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST)

    binary = ((mask > 0).astype(np.uint8) * 255)

    img_np = np.array(pil_image.convert("RGB"))
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, :3] = img_np
    rgba[:, :, 3] = binary

    return binary, Image.fromarray(rgba, "RGBA")


def fallback_segmentation(pil_image: Image.Image):
    """
    CPU-only fallback when SAM 3 is unavailable.
    Uses Otsu thresholding + GrabCut-style mask.
    """
    img_np = np.array(pil_image.convert("RGB"))
    h, w = img_np.shape[:2]
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

    # Otsu threshold
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=3)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)

    # Keep largest contour
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    mask_clean = np.zeros((h, w), dtype=np.uint8)
    if contours:
        biggest = max(contours, key=cv2.contourArea)
        cv2.drawContours(mask_clean, [biggest], -1, 255, thickness=cv2.FILLED)

    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, :3] = img_np
    rgba[:, :, 3] = mask_clean

    return mask_clean, Image.fromarray(rgba, "RGBA")


def auto_rotate_cutout(rgba_pil: Image.Image):
    """Rotate pant so waist faces up (waist is wider than ankle)."""
    arr = np.array(rgba_pil)
    alpha = arr[:, :, 3]
    points = np.column_stack(np.where(alpha > 0))
    if len(points) < 10:
        return rgba_pil

    pts = points[:, ::-1].astype(np.float32)
    rect = cv2.minAreaRect(pts)
    _, (rw, rh), angle = rect
    if rw > rh:
        angle += 90

    center = (arr.shape[1] / 2, arr.shape[0] / 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(arr, M, (arr.shape[1], arr.shape[0]),
                             flags=cv2.INTER_CUBIC,
                             borderMode=cv2.BORDER_CONSTANT,
                             borderValue=(0, 0, 0, 0))

    # Flip if waist is at bottom
    alpha_r = rotated[:, :, 3]
    ys, _ = np.where(alpha_r > 0)
    if len(ys) < 10:
        return Image.fromarray(rotated, "RGBA")

    y_min, y_max = ys.min(), ys.max()
    span = y_max - y_min
    y_top = y_min + int(span * 0.2)
    y_bot = y_max - int(span * 0.2)
    top_w = np.sum(alpha_r[y_top] > 0)
    bot_w = np.sum(alpha_r[y_bot] > 0)
    if top_w < bot_w:
        rotated = cv2.rotate(rotated, cv2.ROTATE_180)

    return Image.fromarray(rotated, "RGBA")


# ─────────────────────────────────────────────────────────────────
# MODULE: MEASUREMENT PIPELINE INTERFACE (stub for HRNet)
# ─────────────────────────────────────────────────────────────────
class MeasurementPipeline:
    """
    Interface stub for future HRNet landmark detector integration.
    Receives the segmented image (RGBA PIL) + binary mask (np.ndarray).
    Returns a dict of pant measurements.
    """
    def process(self, segmented_image: Image.Image, binary_mask: np.ndarray) -> dict:
        raise NotImplementedError


class PlaceholderMeasurementPipeline(MeasurementPipeline):
    def process(self, segmented_image: Image.Image, binary_mask: np.ndarray) -> dict:
        return {
            "ready": True,
            "message": "HRNet landmark detector not yet connected.",
            "landmarks": [
                {"id": 1, "name": "Waist Left",  "x": 0.35, "y": 0.15, "conf": 0.98},
                {"id": 2, "name": "Waist Right", "x": 0.65, "y": 0.15, "conf": 0.98},
                {"id": 3, "name": "Crotch",      "x": 0.50, "y": 0.45, "conf": 0.95},
                {"id": 4, "name": "Left Hem",    "x": 0.30, "y": 0.90, "conf": 0.96},
                {"id": 5, "name": "Right Hem",   "x": 0.70, "y": 0.90, "conf": 0.96},
            ],
            "measurements": {
                "waist_cm": "—", "hip_cm": "—",
                "inseam_cm": "—", "outseam_cm": "—",
                "leg_opening_cm": "—",
            },
        }


# ─────────────────────────────────────────────────────────────────
# HELPER: Save session outputs to disk
# ─────────────────────────────────────────────────────────────────
def save_outputs(original: Image.Image, mask_arr: np.ndarray,
                 segmented: Image.Image, save_dir: pathlib.Path) -> dict:
    save_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    orig_path = save_dir / f"Original_{ts}.jpg"
    mask_path = save_dir / f"Mask_{ts}.png"
    seg_path  = save_dir / f"Segmented_{ts}.png"

    # Also save standard fixed names (for pipeline plug-in)
    orig_std = save_dir / "Original.jpg"
    mask_std = save_dir / "Mask.png"
    seg_std  = save_dir / "Segmented.png"

    original.convert("RGB").save(orig_path, format="JPEG", quality=95)
    original.convert("RGB").save(orig_std,  format="JPEG", quality=95)

    Image.fromarray(mask_arr).save(mask_path, format="PNG")
    Image.fromarray(mask_arr).save(mask_std,  format="PNG")

    segmented.save(seg_path, format="PNG")
    segmented.save(seg_std,  format="PNG")

    return {"orig": orig_path, "mask": mask_path, "seg": seg_path,
            "orig_std": orig_std, "mask_std": mask_std, "seg_std": seg_std}


def pil_to_bytes(img: Image.Image, fmt="PNG") -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=fmt, quality=95 if fmt == "JPEG" else None)
    return buf.getvalue()


def make_zip(original: Image.Image, mask_arr: np.ndarray,
             segmented: Image.Image) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("Original.jpg",  pil_to_bytes(original.convert("RGB"), "JPEG"))
        zf.writestr("Mask.png",      pil_to_bytes(Image.fromarray(mask_arr), "PNG"))
        zf.writestr("Segmented.png", pil_to_bytes(segmented, "PNG"))
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────
# HELPER: Render pant silhouette overlay on image
# ─────────────────────────────────────────────────────────────────
def draw_pant_overlay(pil_image: Image.Image) -> Image.Image:
    """Draw dashed pant-shape guide frame on a copy of the image."""
    img = pil_image.copy().convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    w, h = img.size
    l = w * 0.18
    r = w * 0.82
    t = h * 0.10
    b = h * 0.90
    crotch_y = t + (b - t) * 0.42
    wl = l + (r - l) * 0.15
    wr = r - (r - l) * 0.15
    cx = w * 0.5

    pts = [
        (wl, t), (wr, t),
        (r, b),
        (w * 0.54, b),
        (cx, crotch_y),
        (w * 0.46, b),
        (l, b),
    ]

    # Fill (semi-transparent white)
    draw.polygon(pts, fill=(255, 255, 255, 28))
    # Outline white dashed (simulated with segments)
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        segs = 10
        for s in range(segs):
            if s % 2 == 0:
                sx0 = x0 + (x1 - x0) * s / segs
                sy0 = y0 + (y1 - y0) * s / segs
                sx1 = x0 + (x1 - x0) * (s + 1) / segs
                sy1 = y0 + (y1 - y0) * (s + 1) / segs
                draw.line([(sx0, sy0), (sx1, sy1)], fill=(255, 255, 255, 200), width=3)

    # Corner brackets
    corner_pts = [(l, t), (r, t), (l, b), (r, b)]
    corner_dirs = [(1, 1), (-1, 1), (1, -1), (-1, -1)]
    cl = 30
    for (cx_, cy_), (dx, dy) in zip(corner_pts, corner_dirs):
        draw.line([(cx_, cy_), (cx_ + dx * cl, cy_)], fill=(255, 255, 255, 255), width=3)
        draw.line([(cx_, cy_), (cx_, cy_ + dy * cl)], fill=(255, 255, 255, 255), width=3)

    return Image.alpha_composite(img, overlay).convert("RGB")


# ─────────────────────────────────────────────────────────────────
# SESSION STATE INITIALISATION
# ─────────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "screen": "capture",          # capture | processing | results
        "captured_image": None,
        "mask_arr": None,
        "segmented_image": None,
        "save_paths": None,
        "quality": None,
        "detection": None,
        "sam3_loaded": False,
        "sam3_error": None,
        "processor": None,
        "use_fallback": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ─────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────
st.markdown('<div class="dash-header">DASH AI CAPTURE &nbsp;|&nbsp; 👖 SAM 3 SEGMENTATION PIPELINE</div>',
            unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# SCREEN: CAPTURE
# ─────────────────────────────────────────────────────────────────
if st.session_state.screen == "capture":

    cam_col, hud_col = st.columns([3, 2], gap="medium")

    with cam_col:
        st.markdown("#### 📷 Camera Preview")
        st.caption("Point the camera down at the pant. Auto-capture fires when all checks pass.")

        cam_image = st.camera_input(
            label="",
            key="cam_feed",
            help="Position pant flat in frame. All checks must pass before capture.",
        )

        # Overlay guidance
        if cam_image:
            pil_raw = Image.open(cam_image).convert("RGB")
            with_overlay = draw_pant_overlay(pil_raw)
            st.image(with_overlay, caption="Live Preview with Pant Outline", use_column_width=True)

    with hud_col:
        # ── Level Simulator (Pitch / Roll sliders) ──────────────────────
        st.markdown("#### 🎯 Phone Level Simulator")
        st.caption("On a real phone, these values come from the accelerometer/gyroscope.")

        pitch = st.slider("Pitch (°)", min_value=-30.0, max_value=30.0, value=0.0, step=0.5, key="pitch_slider")
        roll  = st.slider("Roll (°)",  min_value=-30.0, max_value=30.0, value=0.0, step=0.5, key="roll_slider")

        pitch_ok = -5.0 <= pitch <= 5.0
        roll_ok  = -5.0 <= roll  <= 5.0
        level_ok = pitch_ok and roll_ok

        level_class = "level-card valid" if level_ok else "level-card"
        pv_color = "ok" if pitch_ok else "warn"
        rv_color = "ok" if roll_ok  else "warn"

        level_guidance = "✅ Perfect" if level_ok else (
            "⬇ Lower your phone" if pitch > 5 else
            "⬆ Tilt phone up"    if pitch < -5 else
            "➡ Rotate clockwise" if roll > 5 else
            "⬅ Rotate counter-clockwise"
        )

        st.markdown(f"""
<div class="{level_class}">
  <div class="level-label">PHONE LEVEL</div>
  <div style="display:flex;gap:24px;align-items:center;margin-bottom:6px;">
    <span>Pitch : <span class="level-value {pv_color}">{pitch:+.1f}°</span></span>
    <span style="color:rgba(255,255,255,0.2)">|</span>
    <span>Roll &nbsp;: <span class="level-value {rv_color}">{roll:+.1f}°</span></span>
  </div>
  <div style="font-size:14px;font-weight:600;color:{'#00c853' if level_ok else '#ffab00'}">{level_guidance}</div>
</div>""", unsafe_allow_html=True)

        # ── Quality Analysis ─────────────────────────────────────────────
        if cam_image:
            pil_raw = Image.open(cam_image).convert("RGB")
            det = detect_pant(pil_raw)
            q   = compute_quality(pil_raw, pitch, roll, det)

            st.session_state.quality   = q
            st.session_state.detection = det

            # Chips row
            chips_html = '<div class="chips-row">'
            chip_data = [
                ("Phone Level",        q["is_level"]),
                ("Pant Detected",      q["is_pant"]),
                ("Entire Pant Visible", q["is_visible"]),
                ("Lighting Good",      q["is_lit"]),
                ("Sharp Image",        q["is_sharp"]),
            ]
            for label, valid in chip_data:
                cls = "chip ok" if valid else "chip fail"
                icon = "✓" if valid else "•"
                chips_html += f'<span class="{cls}">{icon} {label}</span>'
            chips_html += "</div>"

            st.markdown(chips_html, unsafe_allow_html=True)

            # Guidance banner
            banner_cls = "guidance-banner go" if q["all_ok"] else "guidance-banner"
            st.markdown(f'<div class="{banner_cls}">{q["guidance"]}</div>', unsafe_allow_html=True)

            # Debug metrics expander
            with st.expander("📊 Quality Metrics"):
                m1, m2 = st.columns(2)
                m1.metric("Sharpness (Laplacian Var.)", q["lap_var"],
                           delta="✓ Sharp" if q["is_sharp"] else "✗ Blurry")
                m2.metric("Mean Brightness", q["brightness"],
                           delta="✓ Good" if q["is_lit"] else "✗ Bad lighting")
                st.caption(f"Pant Count: {det.pant_count}  |  Touching border: {det.is_touching_border}")

            # ── Auto Capture ──────────────────────────────────────────────
            st.markdown("---")

            if q["all_ok"]:
                st.markdown('<div class="countdown">📸</div>', unsafe_allow_html=True)
                with st.spinner("All checks passed — Auto-capturing in 2 seconds…"):
                    time.sleep(2)
                # Trigger capture
                st.session_state.captured_image = pil_raw
                st.session_state.screen = "processing"
                st.rerun()
            else:
                # Manual override capture button
                st.markdown("**Or capture manually when ready:**")
                if st.button("📸 Capture Now (Manual Override)"):
                    st.session_state.captured_image = pil_raw
                    st.session_state.screen = "processing"
                    st.rerun()
        else:
            st.markdown("""
<div class="guidance-banner">
  📷 Tap the camera input above to take a photo.
</div>""", unsafe_allow_html=True)

            # Instruction list
            st.markdown("**Positioning Guide:**")
            st.markdown("""
- 📐 **Lay pant flat** on a clean surface
- ⬆️ **Waist at the top** of the frame
- 👖 **Entire pant visible** — legs fully in frame
- 🚫 **No folds** or overlapping legs
- 📏 **Keep phone level** (Pitch & Roll within ±5°)
""")


# ─────────────────────────────────────────────────────────────────
# SCREEN: PROCESSING (SAM 3)
# ─────────────────────────────────────────────────────────────────
elif st.session_state.screen == "processing":

    st.markdown("""
<div class="processing-box">
  <div class="processing-title">⚙️ Running SAM 3 Segmentation</div>
  <div class="processing-sub">Generating binary mask &amp; transparent PNG cutout…</div>
</div>""", unsafe_allow_html=True)

    original = st.session_state.captured_image
    prog_bar = st.progress(0, text="Initialising segmentation engine…")

    # ── Step 1: Load / reuse SAM 3 ──────────────────────────────────
    prog_bar.progress(15, text="Loading SAM 3 model…")

    if not st.session_state.sam3_loaded:
        processor, err = load_sam3_model()
        if processor is None:
            st.session_state.sam3_error = err
            st.session_state.use_fallback = True
        else:
            st.session_state.processor   = processor
            st.session_state.sam3_loaded = True
            st.session_state.sam3_error  = None

    if st.session_state.sam3_error:
        st.warning(f"SAM 3 unavailable: {st.session_state.sam3_error}\n\n"
                   "→ Using **CPU fallback** (Otsu + contour segmentation).")

    prog_bar.progress(40, text="Running segmentation…")

    # ── Step 2: Segment ─────────────────────────────────────────────
    try:
        if st.session_state.use_fallback or st.session_state.processor is None:
            mask_arr, segmented = fallback_segmentation(original)
        else:
            mask_arr, segmented = run_sam3_segmentation(original, st.session_state.processor)
            if mask_arr is None:
                st.warning("SAM 3 found no pants — switching to fallback.")
                mask_arr, segmented = fallback_segmentation(original)
    except Exception as e:
        st.warning(f"SAM 3 error: {e} — switching to fallback.")
        mask_arr, segmented = fallback_segmentation(original)

    prog_bar.progress(75, text="Auto-rotating & saving outputs…")

    # ── Step 3: Auto-rotate cutout so waist faces up ─────────────────
    segmented = auto_rotate_cutout(segmented)

    # ── Step 4: Save to disk ─────────────────────────────────────────
    save_dir = _HERE / "dash_ai_captures"
    save_paths = save_outputs(original, mask_arr, segmented, save_dir)
    st.session_state.save_paths = save_paths

    prog_bar.progress(95, text="Finalising…")

    # ── Step 5: Store results ─────────────────────────────────────────
    st.session_state.mask_arr        = mask_arr
    st.session_state.segmented_image = segmented
    prog_bar.progress(100, text="Complete!")

    time.sleep(0.4)
    st.session_state.screen = "results"
    st.rerun()


# ─────────────────────────────────────────────────────────────────
# SCREEN: RESULTS
# ─────────────────────────────────────────────────────────────────
elif st.session_state.screen == "results":

    original  = st.session_state.captured_image
    mask_arr  = st.session_state.mask_arr
    segmented = st.session_state.segmented_image
    paths     = st.session_state.save_paths

    st.markdown("---")
    hdr1, hdr2 = st.columns([3, 1])
    hdr1.markdown("## ✅ SAM 3 Segmentation Complete")
    hdr1.caption(f"Images saved → `{paths['orig_std'].parent}`")

    with hdr2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Capture Another Pant"):
            for k in ["captured_image", "mask_arr", "segmented_image", "save_paths", "quality", "detection"]:
                st.session_state[k] = None
            st.session_state.screen = "capture"
            st.rerun()

    st.markdown("---")

    # ── Three result cards ────────────────────────────────────────────
    c1, c2, c3 = st.columns(3, gap="medium")

    with c1:
        st.markdown('<div class="result-card"><div class="result-card-title">ORIGINAL IMAGE · Original.jpg</div>', unsafe_allow_html=True)
        st.image(original, use_column_width=True)
        st.download_button("⬇ Download Original.jpg",
                           data=pil_to_bytes(original.convert("RGB"), "JPEG"),
                           file_name="Original.jpg", mime="image/jpeg")
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        mask_pil = Image.fromarray(mask_arr)
        st.markdown('<div class="result-card"><div class="result-card-title">SAM 3 BINARY MASK · Mask.png</div>', unsafe_allow_html=True)
        st.image(mask_pil, use_column_width=True)
        st.download_button("⬇ Download Mask.png",
                           data=pil_to_bytes(mask_pil, "PNG"),
                           file_name="Mask.png", mime="image/png")
        st.markdown("</div>", unsafe_allow_html=True)

    with c3:
        st.markdown('<div class="result-card"><div class="result-card-title">SEGMENTED PANT · Segmented.png</div>', unsafe_allow_html=True)
        st.image(segmented, use_column_width=True)
        st.download_button("⬇ Download Segmented.png",
                           data=pil_to_bytes(segmented, "PNG"),
                           file_name="Segmented.png", mime="image/png")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Zip all three ─────────────────────────────────────────────────
    st.markdown("---")
    zip_bytes = make_zip(original, mask_arr, segmented)
    st.download_button(
        label="📦 Download All Three Files (ZIP)",
        data=zip_bytes,
        file_name="dash_ai_capture_output.zip",
        mime="application/zip",
        use_container_width=True,
    )

    # ── Measurement Pipeline stub ─────────────────────────────────────
    with st.expander("🔬 Measurement Pipeline (HRNet Interface — Coming Soon)"):
        pipeline = PlaceholderMeasurementPipeline()
        result   = pipeline.process(segmented, mask_arr)

        st.success(result["message"])
        st.json({
            "interface": "MeasurementPipeline",
            "status": "ready for HRNet",
            "landmark_stubs": result["landmarks"],
            "measurement_stubs": result["measurements"],
        })
        st.caption("Plug your HRNet weights into `PlaceholderMeasurementPipeline.process()` "
                   "and return real `LandmarkPoint` objects and `PantMeasurements`.")

    # ── Quality Report ────────────────────────────────────────────────
    if st.session_state.quality:
        with st.expander("📊 Quality Report at Capture"):
            q = st.session_state.quality
            cols = st.columns(5)
            labels = ["Phone Level", "Pant Detected", "Entire Visible", "Lighting", "Sharp"]
            keys   = ["is_level", "is_pant", "is_visible", "is_lit", "is_sharp"]
            for col, lbl, key in zip(cols, labels, keys):
                icon = "✅" if q[key] else "❌"
                col.metric(lbl, icon)

    # ── Save confirmation ─────────────────────────────────────────────
    st.info(f"""
**Saved files:**
- `{paths['orig_std']}`
- `{paths['mask_std']}`
- `{paths['seg_std']}`
""")


# ─────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="footer-note">DASH AI Capture &nbsp;·&nbsp; SAM 3 Segmentation &nbsp;·&nbsp; '
    'HRNet Interface Ready</div>',
    unsafe_allow_html=True
)
