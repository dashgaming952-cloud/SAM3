# -*- coding: utf-8 -*-
"""
services/pant_detector.py
==========================
Lightweight pant detector using contour analysis (CPU only, no model weights).

This module defines the canonical detect_pant() interface.
When a real ML detector becomes available, replace _contour_detect()
while keeping the PantDetection return type identical.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List

import numpy as np
import cv2
from PIL import Image


@dataclass
class PantDetection:
    """Canonical detection result returned by detect_pant()."""
    detected:      bool   = False
    confidence:    float  = 0.0
    bbox:          Optional[List[int]] = field(default=None)   # [x1, y1, x2, y2] in original coords
    fully_visible: bool   = False
    message:       str    = ""
    # Internal flag so callers know this is a fallback
    is_fallback:   bool   = True


def detect_pant(pil_image: Image.Image) -> PantDetection:
    """
    Detect whether a pant is present and fully visible in the image.

    Currently uses contour-based analysis on a downscaled copy.
    Returns a PantDetection regardless of whether the detector
    is a real model or the current fallback.

    NOTE: is_fallback=True until ML weights are connected.
    """
    return _contour_detect(pil_image)


# ─── Fallback implementation (contour analysis) ────────────────────

def _contour_detect(pil_image: Image.Image) -> PantDetection:
    result = PantDetection(is_fallback=True)

    arr = np.array(pil_image.convert("RGB"))
    orig_h, orig_w = arr.shape[:2]

    # Downscale for speed
    scale = 0.25
    sw = max(60, int(orig_w * scale))
    sh = max(60, int(orig_h * scale))
    small = cv2.resize(arr, (sw, sh), interpolation=cv2.INTER_AREA)
    gray  = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)

    # Adaptive threshold (garment vs light background)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN,  kernel, iterations=1)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = sw * sh * 0.05
    valid = [c for c in contours if cv2.contourArea(c) > min_area]

    if len(valid) == 0:
        result.message = "Place pant inside the frame"
        return result

    if len(valid) > 1:
        result.message = "Multiple objects detected — only one pant please"
        return result

    # Single large contour found
    x, y, cw, ch = cv2.boundingRect(valid[0])
    area_ratio = (cw * ch) / (sw * sh)

    # Map bbox back to original coordinates
    scale_x = orig_w / sw
    scale_y = orig_h / sh
    x1 = int(x * scale_x)
    y1 = int(y * scale_y)
    x2 = int((x + cw) * scale_x)
    y2 = int((y + ch) * scale_y)

    result.detected   = True
    result.bbox       = [x1, y1, x2, y2]
    result.confidence = min(0.9, area_ratio * 2.5)  # synthetic confidence

    # Border check (3-pixel margin in downscaled space)
    margin = 3
    touching = (
        x <= margin or y <= margin or
        x + cw >= sw - margin or y + ch >= sh - margin
    )
    result.fully_visible = not touching

    if touching:
        result.message = "Move farther — pant is cropped at border"
    else:
        result.message = "Pant detected"

    return result
