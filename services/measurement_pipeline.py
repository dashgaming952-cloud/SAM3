# -*- coding: utf-8 -*-
"""
services/measurement_pipeline.py
==================================
Interface stub for the future HRNet landmark-based measurement pipeline.

Usage (future):
    from services.measurement_pipeline import run_measurement_pipeline
    result = run_measurement_pipeline(original, segmented, mask)

The function currently returns None — no fake measurements are generated.
Replace the body of _hrnet_pipeline() when HRNet weights are connected.
"""

from __future__ import annotations
from typing import Optional
import numpy as np
from PIL import Image


def run_measurement_pipeline(
    original_image: Image.Image,
    segmented_image: Image.Image,
    mask: np.ndarray,
) -> Optional[dict]:
    """
    Entry point for the complete measurement pipeline.

    Future pipeline:
        SAM 3 output
        ↓
        HRNet landmark detection
        ↓
        Waist-reference pixel scaling
        ↓
        Pant measurements

    Parameters
    ----------
    original_image  : PIL RGB — full original photograph
    segmented_image : PIL RGBA — background-removed pant
    mask            : np.ndarray H×W uint8 — binary mask (0/255)

    Returns
    -------
    dict with measurements, or None if not yet implemented.
    """
    return _hrnet_pipeline(original_image, segmented_image, mask)


def _hrnet_pipeline(original, segmented, mask) -> Optional[dict]:
    """
    STUB — HRNet not yet connected.
    Return None until real weights are integrated.

    DO NOT return fake measurements here.
    """
    # TODO: Load HRNet model, run landmark detection, compute measurements.
    return None
