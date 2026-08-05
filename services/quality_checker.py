# -*- coding: utf-8 -*-
"""
services/quality_checker.py
============================
Lightweight image quality checks performed BEFORE SAM 3 is invoked.

All checks run on CPU using numpy / OpenCV only.
"""

from __future__ import annotations
import numpy as np
import cv2
from PIL import Image
from dataclasses import dataclass


@dataclass
class QualityReport:
    # Individual flags
    is_level:   bool = False
    is_pant:    bool = False
    is_visible: bool = False
    is_sharp:   bool = False
    is_lit:     bool = False

    # Numeric values for display
    lap_var:    float = 0.0
    brightness: float = 0.0
    pitch:      float = 0.0
    roll:       float = 0.0

    # Single primary guidance string shown to user
    guidance: str = ""

    @property
    def all_ok(self) -> bool:
        return self.is_level and self.is_pant and self.is_visible and self.is_sharp and self.is_lit

    @property
    def level_category(self) -> str:
        """'perfect' | 'almost' | 'bad'"""
        max_tilt = max(abs(self.pitch), abs(self.roll))
        if max_tilt <= 3.0:
            return "perfect"
        if max_tilt <= 5.0:
            return "almost"
        return "bad"

    @property
    def level_label(self) -> str:
        cat = self.level_category
        if cat == "perfect": return "✓ Perfect"
        if cat == "almost":  return "Almost there"
        return "Level your phone"


def check_quality(
    pil_image: Image.Image,
    pitch: float,
    roll: float,
    pant_detected: bool,
    pant_fully_visible: bool,
) -> QualityReport:
    """
    Run all quality checks and return a QualityReport.

    Parameters
    ----------
    pil_image       : PIL RGB image
    pitch / roll    : device orientation in degrees (real or 0.0 if unavailable)
    pant_detected   : result from pant_detector
    pant_fully_visible : pant not touching image borders
    """
    report = QualityReport(pitch=pitch, roll=roll)

    # ── 1. Level ──────────────────────────────────────────────────
    report.is_level = (abs(pitch) <= 5.0) and (abs(roll) <= 5.0)

    # ── 2. Pant ───────────────────────────────────────────────────
    report.is_pant    = pant_detected
    report.is_visible = pant_fully_visible

    # ── 3. Sharpness (Laplacian variance) ─────────────────────────
    arr_gray = np.array(pil_image.convert("L"))
    small = cv2.resize(arr_gray, (320, 320), interpolation=cv2.INTER_AREA)
    lap_var = float(cv2.Laplacian(small, cv2.CV_64F).var())
    report.lap_var = round(lap_var, 1)
    report.is_sharp = lap_var >= 30.0

    # ── 4. Lighting ───────────────────────────────────────────────
    mean_brightness = float(np.mean(arr_gray))
    report.brightness = round(mean_brightness, 1)
    report.is_lit = 40.0 <= mean_brightness <= 230.0

    # ── 5. Image size sanity ──────────────────────────────────────
    w, h = pil_image.size
    if w < 200 or h < 200:
        report.is_sharp = False   # treat tiny images as failed

    # ── Primary guidance ──────────────────────────────────────────
    if not report.is_level:
        if pitch > 5:
            report.guidance = "Tilt phone backward"
        elif pitch < -5:
            report.guidance = "Tilt phone forward"
        elif roll > 5:
            report.guidance = "Move phone left"
        else:
            report.guidance = "Move phone right"
    elif not report.is_pant:
        report.guidance = "Position pant in frame"
    elif not report.is_visible:
        report.guidance = "Entire pant must be visible"
    elif not report.is_lit:
        if mean_brightness < 40:
            report.guidance = "Too dark — improve lighting"
        else:
            report.guidance = "Too bright — reduce light"
    elif not report.is_sharp:
        report.guidance = "Hold still — image blurry"
    else:
        report.guidance = "Perfect — take photo"

    return report
