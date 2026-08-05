# -*- coding: utf-8 -*-
"""
DASH AI Capture — Mobile-First Streamlit Edition
=================================================
Entry point.  Run:
    streamlit run app.py

Workflow:
    Open website → Camera → Level guidance → Frame pant →
    Capture → Quality checks → SAM 3 segmentation → Results
"""

import streamlit as st

# ── Page config must be the VERY FIRST Streamlit call ─────────────
st.set_page_config(
    page_title="DASH AI Capture",
    page_icon="👖",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Internal modules ───────────────────────────────────────────────
from components.camera   import render_camera_screen
from components.results  import render_results_screen
from components.processing import render_processing_screen
from utils.session       import init_session_state
from utils.styles        import inject_mobile_css

# ── Bootstrap ─────────────────────────────────────────────────────
inject_mobile_css()
init_session_state()

# ── Router ────────────────────────────────────────────────────────
screen = st.session_state.get("screen", "capture")

if screen == "capture":
    render_camera_screen()
elif screen == "processing":
    render_processing_screen()
elif screen == "results":
    render_results_screen()
else:
    st.session_state.screen = "capture"
    st.rerun()
