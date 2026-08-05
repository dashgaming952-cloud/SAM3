# -*- coding: utf-8 -*-
"""
utils/styles.py
================
Injects mobile-first CSS that makes the Streamlit app
look like a native camera application on phones.
"""

import streamlit as st


def inject_mobile_css() -> None:
    st.markdown(
        """
<style>
/* ─── Google Font ─────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

/* ─── Global reset ────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [class*="css"] {
  font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
  -webkit-font-smoothing: antialiased;
}

/* ─── Hide ALL Streamlit chrome ───────────────────────────── */
#MainMenu { visibility: hidden !important; display: none !important; }
header[data-testid="stHeader"] { visibility: hidden !important; display: none !important; }
footer { visibility: hidden !important; display: none !important; }
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
[data-testid="stStatusWidget"] { display: none !important; }
.viewerBadge_container__r5tak { display: none !important; }
.reportview-container .main .block-container { padding-top: 0 !important; }
button[title="View fullscreen"] { display: none !important; }
[data-testid="manage-app-button"] { display: none !important; }

/* ─── Page canvas ─────────────────────────────────────────── */
.main {
  background: #0a0a0c !important;
  min-height: 100dvh;
}

.block-container {
  padding: 0 !important;
  max-width: 500px !important;
  margin: 0 auto !important;
  padding-bottom: env(safe-area-inset-bottom, 16px) !important;
}

/* ─── App wrapper ─────────────────────────────────────────── */
.dash-app {
  background: #0a0a0c;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  width: 100%;
  max-width: 500px;
  margin: 0 auto;
  position: relative;
  overflow-x: hidden;
}

/* ─── Header ──────────────────────────────────────────────── */
.dash-header {
  background: linear-gradient(135deg, #0f0f14 0%, #1a1a24 100%);
  padding: 14px 20px 10px;
  text-align: center;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  position: sticky;
  top: 0;
  z-index: 100;
}

.dash-logo {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 4px;
  color: rgba(255,255,255,0.5);
  text-transform: uppercase;
  margin-bottom: 2px;
}

.dash-title {
  font-size: 18px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: -0.3px;
}

.dash-subtitle {
  font-size: 12px;
  color: rgba(255,255,255,0.45);
  margin-top: 2px;
  font-weight: 400;
}

/* ─── Camera section ──────────────────────────────────────── */
.camera-section {
  position: relative;
  width: 100%;
  background: #000;
}

/* Streamlit camera_input styling */
[data-testid="stCameraInput"] {
  width: 100% !important;
  margin: 0 !important;
}

[data-testid="stCameraInput"] > div {
  border-radius: 0 !important;
  border: none !important;
  background: #000 !important;
  width: 100% !important;
  padding: 0 !important;
}

[data-testid="stCameraInput"] video {
  width: 100% !important;
  max-height: 60dvh !important;
  object-fit: cover !important;
  border-radius: 0 !important;
  display: block;
}

[data-testid="stCameraInput"] img {
  width: 100% !important;
  object-fit: contain !important;
  border-radius: 0 !important;
  display: block;
}

/* Hide the capture button label */
[data-testid="stCameraInput"] label {
  display: none !important;
}

/* Camera input inner capture button */
[data-testid="stCameraInput"] button {
  border-radius: 50% !important;
  width: 70px !important;
  height: 70px !important;
  background: rgba(255,255,255,0.95) !important;
  border: 4px solid rgba(255,255,255,0.4) !important;
  box-shadow: 0 4px 20px rgba(0,0,0,0.4) !important;
  margin: 12px auto !important;
  display: block !important;
  color: transparent !important;
  font-size: 0 !important;
}

[data-testid="stCameraInput"] button:hover {
  background: #fff !important;
  transform: scale(1.05) !important;
}

/* ─── Pant guide overlay canvas (HTML element) ────────────── */
.guide-wrap {
  position: relative;
  width: 100%;
  background: #000;
  overflow: hidden;
}

.pant-guide-svg {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  pointer-events: none;
  z-index: 10;
}

/* ─── Level bubble indicator ──────────────────────────────── */
.level-section {
  padding: 14px 16px 10px;
  background: #0f0f14;
  border-top: 1px solid rgba(255,255,255,0.06);
}

.level-row {
  display: flex;
  align-items: center;
  gap: 14px;
}

.bubble-level {
  flex-shrink: 0;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: rgba(255,255,255,0.05);
  border: 2px solid rgba(255,255,255,0.15);
  position: relative;
  overflow: hidden;
}

.bubble-inner {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #00e676;
  box-shadow: 0 0 8px rgba(0,230,118,0.8);
  position: absolute;
  transform: translate(-50%, -50%);
  transition: left 0.2s ease, top 0.2s ease;
}

.bubble-inner.warn { background: #ffab00; box-shadow: 0 0 8px rgba(255,171,0,0.8); }
.bubble-inner.bad  { background: #ff5252; box-shadow: 0 0 8px rgba(255,82,82,0.8); }

.bubble-crosshair {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  width: 100%; height: 100%;
}
.bubble-crosshair::before, .bubble-crosshair::after {
  content: '';
  position: absolute;
  background: rgba(255,255,255,0.2);
}
.bubble-crosshair::before {
  width: 1px; height: 100%;
  left: 50%; top: 0;
}
.bubble-crosshair::after {
  height: 1px; width: 100%;
  top: 50%; left: 0;
}

.level-info {
  flex: 1;
}

.level-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: rgba(255,255,255,0.35);
  margin-bottom: 4px;
}

.level-status {
  font-size: 15px;
  font-weight: 700;
  color: #fff;
}

.level-status.perfect { color: #00e676; }
.level-status.almost  { color: #ffab00; }
.level-status.bad     { color: #ff5252; }

.level-degrees {
  font-size: 11px;
  color: rgba(255,255,255,0.35);
  margin-top: 2px;
}

/* ─── Guidance banner ─────────────────────────────────────── */
.guidance-section {
  padding: 12px 16px;
  background: #0a0a0c;
}

.guidance-pill {
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 100px;
  padding: 10px 20px;
  text-align: center;
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
  transition: all 0.3s ease;
}

.guidance-pill.go {
  background: rgba(0,230,118,0.15);
  border-color: #00e676;
  color: #00e676;
}

/* ─── Status chips row ────────────────────────────────────── */
.status-section {
  padding: 10px 16px 12px;
  background: #0a0a0c;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 6px;
}

.status-chip {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px 4px;
  border-radius: 12px;
  border: 1px solid;
  transition: all 0.3s ease;
}

.status-chip.ok {
  background: rgba(0,230,118,0.1);
  border-color: rgba(0,230,118,0.4);
}

.status-chip.amber {
  background: rgba(255,171,0,0.1);
  border-color: rgba(255,171,0,0.4);
}

.status-chip.fail {
  background: rgba(255,255,255,0.04);
  border-color: rgba(255,255,255,0.12);
}

.status-icon {
  font-size: 14px;
  line-height: 1;
}

.status-label {
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.3px;
  text-align: center;
  color: rgba(255,255,255,0.55);
  line-height: 1.2;
}

.status-chip.ok   .status-label { color: #00e676; }
.status-chip.amber .status-label { color: #ffab00; }

/* ─── Capture button ──────────────────────────────────────── */
.capture-section {
  padding: 12px 16px;
  background: #0a0a0c;
}

/* Override Streamlit button inside capture section */
.capture-btn-wrap .stButton > button {
  width: 100% !important;
  height: 60px !important;
  border-radius: 30px !important;
  font-size: 16px !important;
  font-weight: 700 !important;
  letter-spacing: 0.3px !important;
  background: linear-gradient(135deg, #111 0%, #1a1a2e 100%) !important;
  color: #fff !important;
  border: 1.5px solid rgba(255,255,255,0.15) !important;
  transition: all 0.2s ease !important;
}

.capture-btn-wrap .stButton > button.capture-ready {
  background: linear-gradient(135deg, #00c853 0%, #00e676 100%) !important;
  border-color: #00e676 !important;
  color: #000 !important;
  box-shadow: 0 4px 20px rgba(0,230,118,0.35) !important;
}

/* ─── Instructions accordion ──────────────────────────────── */
.instructions-section {
  padding: 0 16px 20px;
  background: #0a0a0c;
}

.instructions-card {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 14px 16px;
}

.instructions-title {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: rgba(255,255,255,0.35);
  margin-bottom: 10px;
}

.instruction-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 8px;
  font-size: 13px;
  color: rgba(255,255,255,0.7);
  line-height: 1.4;
}

.instruction-item:last-child { margin-bottom: 0; }

.instruction-icon {
  font-size: 14px;
  flex-shrink: 0;
  margin-top: 1px;
}

/* ─── iOS permission button ───────────────────────────────── */
.ios-perm-section {
  padding: 10px 16px;
  background: #0a0a0c;
}

/* ─── Processing screen ───────────────────────────────────── */
.processing-screen {
  min-height: 100dvh;
  background: #0a0a0c;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 24px;
  text-align: center;
}

.processing-icon {
  font-size: 56px;
  margin-bottom: 24px;
  animation: pulse 1.6s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50%       { transform: scale(1.08); opacity: 0.75; }
}

.processing-title {
  font-size: 22px;
  font-weight: 800;
  color: #fff;
  margin-bottom: 8px;
}

.processing-sub {
  font-size: 14px;
  color: rgba(255,255,255,0.45);
  line-height: 1.5;
}

/* ─── Results screen ──────────────────────────────────────── */
.results-screen {
  background: #0a0a0c;
  min-height: 100dvh;
  padding-bottom: 40px;
}

.result-success-banner {
  background: linear-gradient(135deg, rgba(0,200,83,0.15) 0%, rgba(0,230,118,0.08) 100%);
  border-bottom: 1px solid rgba(0,230,118,0.2);
  padding: 20px 20px 16px;
  text-align: center;
}

.result-success-icon { font-size: 40px; margin-bottom: 8px; }

.result-success-title {
  font-size: 18px;
  font-weight: 800;
  color: #00e676;
  margin-bottom: 4px;
}

.result-success-sub {
  font-size: 13px;
  color: rgba(255,255,255,0.5);
}

.result-image-section {
  padding: 16px;
}

.result-image-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: rgba(255,255,255,0.35);
  margin-bottom: 8px;
}

.result-image-card {
  border-radius: 16px;
  overflow: hidden;
  background: #111;
  border: 1px solid rgba(255,255,255,0.08);
  margin-bottom: 14px;
}

.result-actions {
  padding: 0 16px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* Full-width buttons for results */
.result-actions .stButton > button,
.result-actions .stDownloadButton > button {
  width: 100% !important;
  height: 54px !important;
  border-radius: 27px !important;
  font-size: 15px !important;
  font-weight: 700 !important;
}

.result-actions .stButton > button {
  background: rgba(255,255,255,0.08) !important;
  color: #fff !important;
  border: 1px solid rgba(255,255,255,0.15) !important;
}

.result-continue-btn .stButton > button {
  background: linear-gradient(135deg, #00c853 0%, #00e676 100%) !important;
  color: #000 !important;
  border: none !important;
  box-shadow: 0 4px 20px rgba(0,230,118,0.3) !important;
  height: 60px !important;
  font-size: 16px !important;
  border-radius: 30px !important;
  width: 100% !important;
  font-weight: 800 !important;
}

.result-continue-btn .stButton > button:hover {
  box-shadow: 0 6px 28px rgba(0,230,118,0.45) !important;
  transform: translateY(-1px) !important;
}

/* ─── Streamlit image display ─────────────────────────────── */
[data-testid="stImage"] img {
  border-radius: 0 !important;
  display: block;
  width: 100% !important;
}

/* ─── Streamlit progress bar ──────────────────────────────── */
[data-testid="stProgressBar"] > div {
  background: rgba(255,255,255,0.08) !important;
  border-radius: 100px !important;
}

[data-testid="stProgressBar"] > div > div {
  background: linear-gradient(90deg, #00c853, #00e676) !important;
  border-radius: 100px !important;
}

/* ─── Expander (debug/advanced) ───────────────────────────── */
[data-testid="stExpander"] {
  border-radius: 12px !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
  background: rgba(255,255,255,0.03) !important;
  margin: 0 16px 12px !important;
}

[data-testid="stExpander"] > details > summary {
  font-size: 12px !important;
  color: rgba(255,255,255,0.45) !important;
}

/* ─── Warning / info boxes ────────────────────────────────── */
[data-testid="stAlert"] {
  border-radius: 12px !important;
  margin: 0 16px 12px !important;
}

/* ─── Responsive breakpoints ──────────────────────────────── */
@media (max-width: 480px) {
  .block-container { max-width: 100% !important; }
  .dash-title { font-size: 16px; }
  .status-label { font-size: 8px; }
}

@media (min-width: 501px) {
  /* Desktop: centre the phone-sized interface */
  .main { display: flex; justify-content: center; }
  .block-container {
    max-width: 500px !important;
    border-left: 1px solid rgba(255,255,255,0.06) !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
  }
}
</style>
        """,
        unsafe_allow_html=True,
    )
