# -*- coding: utf-8 -*-
"""
utils/session.py
================
Session state initialisation and helpers.
"""

import streamlit as st


def init_session_state() -> None:
    """Initialise all session state keys with safe defaults."""
    defaults = {
        # Navigation
        "screen": "capture",           # capture | processing | results

        # Captured image (PIL.Image)
        "captured_image": None,

        # Segmentation outputs
        "mask_arr": None,              # np.ndarray H×W uint8
        "segmented_image": None,       # PIL RGBA

        # Quality snapshot at capture time
        "quality": None,               # dict from quality_checker

        # SAM 3 status
        "sam3_error": None,            # str or None

        # Phone orientation (populated by JS bridge)
        "orientation_available": None,  # True / False / None (unknown)
        "pitch_deg": 0.0,
        "roll_deg":  0.0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_capture() -> None:
    """Clear capture state, returning to camera screen."""
    for k in ["captured_image", "mask_arr", "segmented_image", "quality"]:
        st.session_state[k] = None
    st.session_state.screen = "capture"


def go_processing(image) -> None:
    """Transition to processing screen with the given PIL image."""
    st.session_state.captured_image = image
    st.session_state.screen = "processing"
