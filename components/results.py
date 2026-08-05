# -*- coding: utf-8 -*-
"""
components/results.py
======================
Results screen — mobile layout:

  ✓ HEADER (success banner)
  ↓
  Original photo
  ↓
  Segmented pant (large)
  ↓
  Continue / Retake buttons
  ↓
  Download options (collapsible)
"""

from __future__ import annotations

import streamlit as st
from PIL import Image

from utils.image_utils import pil_to_bytes, make_zip
from utils.session     import reset_capture


def render_results_screen() -> None:
    """Display segmentation results in mobile-friendly vertical layout."""

    original:  Image.Image = st.session_state.captured_image
    mask_arr                = st.session_state.mask_arr
    segmented: Image.Image = st.session_state.segmented_image
    sam3_used: bool         = st.session_state.get("sam3_used", False)

    if original is None or segmented is None:
        st.error("Result data missing. Please retake.")
        reset_capture()
        st.rerun()
        return

    # ── Header ─────────────────────────────────────────────────────
    st.markdown("""
<div class="dash-header">
  <div class="dash-logo">DASH AI</div>
  <div class="dash-title">Pant Captured Successfully</div>
  <div class="dash-subtitle">Review your segmentation below</div>
</div>
""", unsafe_allow_html=True)

    # ── Success banner ─────────────────────────────────────────────
    engine = "SAM 3" if sam3_used else "Fallback (CPU)"
    st.markdown(f"""
<div class="result-success-banner">
  <div class="result-success-icon">✅</div>
  <div class="result-success-title">Pant captured successfully</div>
  <div class="result-success-sub">Segmentation engine: {engine}</div>
</div>
""", unsafe_allow_html=True)

    # ── Original image ─────────────────────────────────────────────
    st.markdown("""
<div class="result-image-section">
  <div class="result-image-label">Original Photo</div>
</div>
""", unsafe_allow_html=True)
    st.image(original, use_container_width=True)

    # ── Segmented pant (large) ─────────────────────────────────────
    st.markdown("""
<div class="result-image-section" style="padding-top:0;">
  <div class="result-image-label">Segmented Pant</div>
</div>
""", unsafe_allow_html=True)

    # Display segmented on white background for clarity
    bg = Image.new("RGB", segmented.size, (255, 255, 255))
    bg.paste(segmented, mask=segmented.split()[3] if segmented.mode == "RGBA" else None)
    st.image(bg, use_container_width=True)

    # ── Measurement pipeline (stub) ────────────────────────────────
    measurement = st.session_state.get("measurement")
    if measurement is not None:
        st.json(measurement)
    else:
        st.markdown("""
<div style="margin:0 16px 12px;padding:12px 16px;
            background:rgba(255,255,255,0.04);
            border:1px solid rgba(255,255,255,0.08);
            border-radius:12px;
            font-size:12px;color:rgba(255,255,255,0.4);text-align:center;">
  📏 Measurements coming soon — HRNet integration pending
</div>
""", unsafe_allow_html=True)

    # ── Action buttons ─────────────────────────────────────────────
    st.markdown('<div class="result-actions">', unsafe_allow_html=True)

    # Continue (primary)
    st.markdown('<div class="result-continue-btn">', unsafe_allow_html=True)
    if st.button("Continue →", key="continue_btn", use_container_width=True):
        # TODO: wire to next step (sizing recommendations etc.)
        st.info("Next step coming soon. For now, you can retake or download.")
    st.markdown('</div>', unsafe_allow_html=True)

    # Retake
    if st.button("← Retake Photo", key="retake_btn", use_container_width=True):
        reset_capture()
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Downloads (collapsed) ──────────────────────────────────────
    with st.expander("⬇ Download Results", expanded=False):
        col_orig, col_seg = st.columns(2)

        with col_orig:
            st.download_button(
                label="Original.jpg",
                data=pil_to_bytes(original.convert("RGB"), "JPEG"),
                file_name="Original.jpg",
                mime="image/jpeg",
                use_container_width=True,
            )

        with col_seg:
            st.download_button(
                label="Segmented.png",
                data=pil_to_bytes(segmented, "PNG"),
                file_name="Segmented.png",
                mime="image/png",
                use_container_width=True,
            )

        if mask_arr is not None:
            mask_pil = Image.fromarray(mask_arr)
            st.download_button(
                label="Mask.png",
                data=pil_to_bytes(mask_pil, "PNG"),
                file_name="Mask.png",
                mime="image/png",
                use_container_width=True,
            )

        st.download_button(
            label="📦 Download All (ZIP)",
            data=make_zip(original, mask_arr, segmented),
            file_name="dash_ai_capture.zip",
            mime="application/zip",
            use_container_width=True,
        )

    # ── Quality report (collapsed) ────────────────────────────────
    quality = st.session_state.get("quality")
    if quality:
        with st.expander("📊 Quality Report at Capture", expanded=False):
            data = {
                "Phone Level":  "✅" if quality.is_level   else "❌",
                "Pant Detected":"✅" if quality.is_pant    else "❌",
                "Fully Visible":"✅" if quality.is_visible else "❌",
                "Lighting":     "✅" if quality.is_lit     else "❌",
                "Sharpness":    "✅" if quality.is_sharp   else "❌",
                "Sharpness (Laplacian var)": quality.lap_var,
                "Mean Brightness": quality.brightness,
                "Pitch": f"{quality.pitch:+.1f}°",
                "Roll":  f"{quality.roll:+.1f}°",
            }
            for k, v in data.items():
                st.text(f"{k:<30} {v}")
