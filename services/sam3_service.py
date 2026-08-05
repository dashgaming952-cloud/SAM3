# -*- coding: utf-8 -*-
"""
services/sam3_service.py
=========================
SAM 3 segmentation wrapper.

The public API is:
    segment_pant(pil_image) -> (binary_mask | None, segmented_rgba | None, error | None)

If SAM 3 cannot run (e.g. Streamlit Cloud CPU limits) the function
returns (None, None, error_message) with NO crash.
The caller (processing screen) decides whether to use the fallback.
"""

from __future__ import annotations
import logging
from typing import Optional, Tuple

import numpy as np
import cv2
from PIL import Image

logger = logging.getLogger(__name__)


# ─── Public API ────────────────────────────────────────────────────

def segment_pant(
    pil_image: Image.Image,
) -> Tuple[Optional[np.ndarray], Optional[Image.Image], Optional[str]]:
    """
    Run SAM 3 segmentation with text prompt "pants".

    Returns
    -------
    binary_mask   : np.ndarray H×W uint8 (0 / 255), or None on error
    segmented_rgba: PIL RGBA image with background removed, or None on error
    error         : str description of error, or None on success
    """
    try:
        from services.model_manager import get_sam3_model
        processor, err = get_sam3_model()
        if processor is None:
            return None, None, err or "SAM 3 model not available."

        return _run_inference(pil_image, processor)

    except Exception as exc:
        logger.exception("SAM 3 inference error")
        return None, None, f"SAM 3 inference error: {exc}"


# ─── Internal inference ────────────────────────────────────────────

def _run_inference(pil_image, processor):
    """Low-level SAM 3 inference call."""
    try:
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype  = torch.bfloat16 if torch.cuda.is_available() else torch.float32

        with torch.inference_mode(), torch.autocast(device_type=device, dtype=dtype):
            state  = processor.set_image(pil_image)
            state  = processor.set_text_prompt(state=state, prompt="pants")
            masks  = state["masks"].to(torch.float32).cpu().numpy()
            scores = state["scores"].to(torch.float32).cpu().numpy()

        if len(masks) == 0:
            return None, None, "SAM 3 found no segmentation mask."

        best_idx = int(np.argmax(scores))
        mask = masks[best_idx]
        if mask.ndim == 3:
            mask = mask[0]

        # Ensure mask matches original image dimensions
        w, h = pil_image.size
        if mask.shape != (h, w):
            mask = cv2.resize(
                mask.astype(np.float32), (w, h), interpolation=cv2.INTER_NEAREST
            )

        binary = ((mask > 0).astype(np.uint8) * 255)

        img_np = np.array(pil_image.convert("RGB"))
        rgba   = np.zeros((h, w, 4), dtype=np.uint8)
        rgba[:, :, :3] = img_np
        rgba[:, :, 3]  = binary

        return binary, Image.fromarray(rgba, "RGBA"), None

    except Exception as exc:
        logger.exception("SAM 3 _run_inference error")
        return None, None, str(exc)


# ─── CPU Fallback segmentation ─────────────────────────────────────

def fallback_segmentation(
    pil_image: Image.Image,
) -> Tuple[np.ndarray, Image.Image]:
    """
    CPU-only fallback using Otsu threshold + largest contour.
    Used when SAM 3 is unavailable.
    Always returns a result (may be imperfect).
    """
    img_np = np.array(pil_image.convert("RGB"))
    h, w = img_np.shape[:2]
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=3)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN,  kernel, iterations=2)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    mask_clean = np.zeros((h, w), dtype=np.uint8)
    if contours:
        biggest = max(contours, key=cv2.contourArea)
        cv2.drawContours(mask_clean, [biggest], -1, 255, thickness=cv2.FILLED)

    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, :3] = img_np
    rgba[:, :, 3]  = mask_clean

    return mask_clean, Image.fromarray(rgba, "RGBA")
