# -*- coding: utf-8 -*-
"""
components/processing.py
=========================
Processing screen shown while SAM 3 segmentation runs.
"""

from __future__ import annotations

import streamlit as st
from PIL import Image

from services.sam3_service        import segment_pant, fallback_segmentation
from services.measurement_pipeline import run_measurement_pipeline
from utils.image_utils             import auto_rotate_cutout
from utils.session                 import reset_capture


def render_processing_screen() -> None:
    """Run SAM 3 and transition to results screen."""

    original: Image.Image = st.session_state.captured_image
    if original is None:
        st.error("No captured image found. Please retake.")
        reset_capture()
        st.rerun()
        return

    # ── Header ─────────────────────────────────────────────────────
    st.markdown("""
<div class="dash-header">
  <div class="dash-logo">DASH AI</div>
  <div class="dash-title">Analysing Your Pants</div>
  <div class="dash-subtitle">SAM 3 segmentation in progress…</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div style="text-align:center;padding:32px 24px 16px;">
  <div style="font-size:56px;animation:pulse 1.6s ease-in-out infinite;">✂️</div>
</div>
<style>
@keyframes pulse {
  0%,100%{transform:scale(1);opacity:1}
  50%{transform:scale(1.08);opacity:0.75}
}
</style>
""", unsafe_allow_html=True)

    prog = st.progress(0, text="Preparing segmentation engine…")

    # ── Step 1: Try SAM 3 ─────────────────────────────────────────
    prog.progress(10, text="Loading SAM 3 model…")
    mask_arr, segmented, err = segment_pant(original)

    sam3_used = (err is None)

    if err:
        # Show developer-friendly warning but continue with fallback
        st.warning(
            f"**SAM 3 unavailable:** {err}\n\n"
            "→ Using CPU fallback segmentation (Otsu + contour). "
            "Results will be less precise."
        )
        prog.progress(40, text="Running fallback segmentation…")
        mask_arr, segmented = fallback_segmentation(original)
    else:
        prog.progress(60, text="Segmentation complete — processing mask…")

    if mask_arr is None or segmented is None:
        st.error("Segmentation failed. Please retake the photo.")
        if st.button("← Retake", use_container_width=True):
            reset_capture()
            st.rerun()
        return

    # ── Step 2: Auto-rotate so waist faces up ─────────────────────
    prog.progress(75, text="Orienting cutout…")
    segmented = auto_rotate_cutout(segmented)

    # ── Step 3: Run measurement pipeline (stub) ───────────────────
    prog.progress(88, text="Running measurement pipeline…")
    measurement_result = run_measurement_pipeline(original, segmented, mask_arr)
    # measurement_result is None until HRNet is connected

    prog.progress(100, text="Done!")

    # ── Store results ─────────────────────────────────────────────
    st.session_state.mask_arr        = mask_arr
    st.session_state.segmented_image = segmented
    st.session_state.sam3_used       = sam3_used
    st.session_state.measurement     = measurement_result
    st.session_state.screen          = "results"
    st.rerun()
