# -*- coding: utf-8 -*-
"""
components/camera.py
=====================
Mobile-first camera capture screen.

Layout (vertical stack, no columns):
  HEADER
  CAMERA  (Streamlit camera_input + SVG guide overlay)
  LEVEL INDICATOR  (bubble level from JS DeviceOrientation)
  GUIDANCE BANNER
  STATUS CHIPS
  CAPTURE BUTTON / INSTRUCTIONS

Phone level detection works via an injected <script> that reads
DeviceOrientationEvent and writes values into hidden Streamlit inputs
through a postMessage bridge.  Because Streamlit's Python layer cannot
subscribe to JS events in real-time, we read the last-known orientation
from session_state (updated via st.components.html query-param trick)
and fall back to 0° if unavailable.
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

from services.pant_detector  import detect_pant
from services.quality_checker import check_quality
from utils.image_utils        import draw_pant_guide_html
from utils.session            import go_processing


# ─────────────────────────────────────────────────────────────────
# JS ORIENTATION BRIDGE
# ─────────────────────────────────────────────────────────────────

_ORIENTATION_JS = """
<script>
(function() {
  // Only runs once
  if (window.__dashLevelInit) return;
  window.__dashLevelInit = true;

  var STORAGE_KEY = "dash_orientation";

  function writeOrientation(beta, gamma) {
    // beta  = pitch-like  (device tilt forward/back,  -180..180)
    // gamma = roll-like   (device tilt left/right,   -90..90)
    var payload = JSON.stringify({ beta: beta, gamma: gamma, ts: Date.now() });
    try { sessionStorage.setItem(STORAGE_KEY, payload); } catch(e) {}
    // Also post to parent iframe so Streamlit can receive it
    try { window.parent.postMessage({ type: "dash_orientation", beta: beta, gamma: gamma }, "*"); } catch(e) {}
  }

  function handleOrientation(e) {
    var beta  = e.beta  !== null ? e.beta  : 0;
    var gamma = e.gamma !== null ? e.gamma : 0;
    writeOrientation(beta, gamma);
    // Update bubble position in real-time without Python round-trip
    updateBubble(beta, gamma);
  }

  function updateBubble(beta, gamma) {
    var bubble = document.getElementById("dash-bubble");
    if (!bubble) return;
    // Clamp to ±20 for display
    var maxTilt = 20;
    var bx = Math.max(-maxTilt, Math.min(maxTilt, gamma)) / maxTilt; // left/right
    var by = Math.max(-maxTilt, Math.min(maxTilt, beta))  / maxTilt; // up/down
    // Map -1..1 to 20%..80% of parent circle
    var left = 50 + bx * 30;  // 20% .. 80%
    var top  = 50 + by * 30;
    bubble.style.left = left + "%";
    bubble.style.top  = top  + "%";
    // Colour
    var maxDeg = Math.max(Math.abs(beta), Math.abs(gamma));
    bubble.className = "bubble-inner" + (maxDeg <= 3 ? "" : maxDeg <= 5 ? " warn" : " bad");
  }

  // iOS requires explicit permission request
  function requestIOSPermission() {
    if (typeof DeviceOrientationEvent !== "undefined" &&
        typeof DeviceOrientationEvent.requestPermission === "function") {
      DeviceOrientationEvent.requestPermission().then(function(state) {
        if (state === "granted") {
          window.addEventListener("deviceorientation", handleOrientation, true);
        }
      }).catch(console.error);
    } else {
      window.addEventListener("deviceorientation", handleOrientation, true);
    }
  }

  // Expose for the button
  window.dashRequestOrientation = requestIOSPermission;

  // Auto-start on non-iOS
  if (typeof DeviceOrientationEvent === "undefined") {
    // Not available
  } else if (typeof DeviceOrientationEvent.requestPermission === "function") {
    // iOS — wait for button click
  } else {
    window.addEventListener("deviceorientation", handleOrientation, true);
  }

  // Restore last known values from sessionStorage on page reload
  try {
    var saved = sessionStorage.getItem(STORAGE_KEY);
    if (saved) {
      var d = JSON.parse(saved);
      if (Date.now() - d.ts < 5000) updateBubble(d.beta, d.gamma);
    }
  } catch(e) {}
})();
</script>
"""

_IOS_BUTTON_HTML = """
<button
  onclick="window.dashRequestOrientation && window.dashRequestOrientation()"
  style="
    display:block; width:100%; padding:12px 0;
    background:rgba(255,255,255,0.08);
    border:1px solid rgba(255,255,255,0.2);
    border-radius:100px;
    color:rgba(255,255,255,0.75);
    font-family:'Inter',system-ui,sans-serif;
    font-size:13px; font-weight:600;
    cursor:pointer; margin-bottom:4px;
  ">
  📡 Enable Level Guidance
</button>
"""

# ─────────────────────────────────────────────────────────────────
# BUBBLE LEVEL HTML (server-side initial render)
# ─────────────────────────────────────────────────────────────────

def _bubble_level_html(pitch: float, roll: float) -> str:
    """Return HTML for the bubble level indicator."""
    max_tilt = 20.0
    bx = max(-max_tilt, min(max_tilt, roll))  / max_tilt
    by = max(-max_tilt, min(max_tilt, pitch)) / max_tilt
    left = 50 + bx * 30
    top  = 50 + by * 30

    max_deg = max(abs(pitch), abs(roll))
    if max_deg <= 3.0:
        cat, bubble_cls, status_text = "perfect", "",      "✓ Perfect"
    elif max_deg <= 5.0:
        cat, bubble_cls, status_text = "almost",  " warn", "Almost there"
    else:
        cat, bubble_cls, status_text = "bad",     " bad",  "Level your phone"

    deg_text = f"Pitch {pitch:+.1f}° · Roll {roll:+.1f}°"

    return f"""
<div class="level-section">
  <div class="level-row">
    <div class="bubble-level">
      <div class="bubble-crosshair"></div>
      <div id="dash-bubble" class="bubble-inner{bubble_cls}"
           style="left:{left:.1f}%;top:{top:.1f}%;"></div>
    </div>
    <div class="level-info">
      <div class="level-label">PHONE LEVEL</div>
      <div class="level-status {cat}">{status_text}</div>
      <div class="level-degrees">{deg_text}</div>
    </div>
  </div>
</div>
"""


# ─────────────────────────────────────────────────────────────────
# STATUS CHIPS
# ─────────────────────────────────────────────────────────────────

def _status_chips_html(quality) -> str:
    """Render the 5-chip status row."""
    chips = [
        ("Phone Level",  quality.is_level,   "📐"),
        ("Pant",         quality.is_pant,     "👖"),
        ("Full Pant",    quality.is_visible,  "🔲"),
        ("Lighting",     quality.is_lit,      "💡"),
        ("Sharpness",    quality.is_sharp,    "🔍"),
    ]

    items = ""
    for label, ok, icon in chips:
        cls = "ok" if ok else "fail"
        items += f"""
<div class="status-chip {cls}">
  <span class="status-icon">{icon}</span>
  <span class="status-label">{label}</span>
</div>"""

    return f"""
<div class="status-section">
  <div class="status-grid">{items}</div>
</div>
"""


# ─────────────────────────────────────────────────────────────────
# GUIDANCE BANNER
# ─────────────────────────────────────────────────────────────────

def _guidance_html(text: str, all_ok: bool) -> str:
    cls = "guidance-pill go" if all_ok else "guidance-pill"
    return f"""
<div class="guidance-section">
  <div class="{cls}">{text}</div>
</div>
"""


# ─────────────────────────────────────────────────────────────────
# INSTRUCTIONS
# ─────────────────────────────────────────────────────────────────

_INSTRUCTIONS_HTML = """
<div class="instructions-section">
  <div class="instructions-card">
    <div class="instructions-title">How to photograph</div>
    <div class="instruction-item">
      <span class="instruction-icon">📐</span>
      <span>Lay the pant flat on a clean, light-coloured surface</span>
    </div>
    <div class="instruction-item">
      <span class="instruction-icon">⬆️</span>
      <span>Waist should be at the top of the frame</span>
    </div>
    <div class="instruction-item">
      <span class="instruction-icon">👖</span>
      <span>Entire pant visible — both legs fully inside frame</span>
    </div>
    <div class="instruction-item">
      <span class="instruction-icon">📱</span>
      <span>Hold phone parallel to the floor, directly above the pant</span>
    </div>
    <div class="instruction-item">
      <span class="instruction-icon">💡</span>
      <span>Good, even lighting — avoid harsh shadows</span>
    </div>
  </div>
</div>
"""


# ─────────────────────────────────────────────────────────────────
# MAIN RENDER FUNCTION
# ─────────────────────────────────────────────────────────────────

def render_camera_screen() -> None:
    """Render the complete mobile-first camera capture screen."""

    # ── Header ─────────────────────────────────────────────────────
    st.markdown("""
<div class="dash-header">
  <div class="dash-logo">DASH AI</div>
  <div class="dash-title">Photograph Your Pants</div>
  <div class="dash-subtitle">We'll find your perfect fit.</div>
</div>
""", unsafe_allow_html=True)

    # ── Inject JS orientation bridge (runs once) ───────────────────
    # We inject the script inside a tiny hidden HTML component
    components.html(_ORIENTATION_JS + _IOS_BUTTON_HTML, height=48, scrolling=False)

    # ── Camera input ───────────────────────────────────────────────
    # Wrap in a container div so our CSS targets it cleanly
    st.markdown('<div class="camera-section">', unsafe_allow_html=True)

    cam_image = st.camera_input(
        label="Take a photo of your pant",
        label_visibility="collapsed",
        key="dash_cam",
        help="Point at the pant and press the shutter button",
    )

    st.markdown('</div>', unsafe_allow_html=True)

    # ── SVG guide overlay ──────────────────────────────────────────
    # Shown below camera as a visual aid (cannot overlay camera
    # natively in Streamlit, but placed immediately after so user
    # sees it while setting up the shot)
    guide_svg = draw_pant_guide_html(360, 220)
    st.markdown(f"""
<div style="position:relative;width:100%;height:220px;background:#111;overflow:hidden;">
  {guide_svg}
  <div style="position:absolute;inset:0;display:flex;align-items:center;
              justify-content:center;color:rgba(255,255,255,0.2);
              font-size:12px;font-weight:600;letter-spacing:1px;">
    PANT GUIDE
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Phone level ────────────────────────────────────────────────
    pitch = st.session_state.get("pitch_deg", 0.0)
    roll  = st.session_state.get("roll_deg",  0.0)
    st.markdown(_bubble_level_html(pitch, roll), unsafe_allow_html=True)

    # ── Quality analysis (only if camera produced an image) ────────
    quality = None
    if cam_image is not None:
        pil_raw = Image.open(cam_image).convert("RGB")

        # Run detection + quality check
        detection = detect_pant(pil_raw)
        quality   = check_quality(
            pil_image          = pil_raw,
            pitch              = pitch,
            roll               = roll,
            pant_detected      = detection.detected,
            pant_fully_visible = detection.fully_visible,
        )

        # ── Guidance banner ────────────────────────────────────────
        st.markdown(_guidance_html(quality.guidance, quality.all_ok),
                    unsafe_allow_html=True)

        # ── Status chips ───────────────────────────────────────────
        st.markdown(_status_chips_html(quality), unsafe_allow_html=True)

        # ── Capture button ─────────────────────────────────────────
        st.markdown('<div class="capture-section"><div class="capture-btn-wrap">',
                    unsafe_allow_html=True)

        if quality.all_ok:
            btn_label = "✓ Capture — All Checks Passed"
        else:
            btn_label = "📸 Capture Anyway"

        if st.button(btn_label, key="capture_btn", use_container_width=True):
            go_processing(pil_raw)
            st.rerun()

        st.markdown('</div></div>', unsafe_allow_html=True)

        # Debug expander (collapsed by default)
        with st.expander("📊 Quality Details", expanded=False):
            st.caption(
                f"Sharpness (Laplacian var): {quality.lap_var}  |  "
                f"Brightness: {quality.brightness}  |  "
                f"Pitch: {pitch:+.1f}°  Roll: {roll:+.1f}°"
            )
            if detection.is_fallback:
                st.caption("⚠️ Pant detection: using contour fallback (no ML model loaded)")
            if detection.bbox:
                st.caption(f"Detected bbox: {detection.bbox}")

    else:
        # No image yet — show default guidance + instructions
        st.markdown(_guidance_html("Position pant flat in frame, then capture", False),
                    unsafe_allow_html=True)

        # Placeholder status chips (all grey)
        chips = [
            ("Phone Level",  False, "📐"),
            ("Pant",         False, "👖"),
            ("Full Pant",    False, "🔲"),
            ("Lighting",     False, "💡"),
            ("Sharpness",    False, "🔍"),
        ]
        items = "".join(
            f'<div class="status-chip fail">'
            f'<span class="status-icon">{icon}</span>'
            f'<span class="status-label">{label}</span></div>'
            for label, _, icon in chips
        )
        st.markdown(
            f'<div class="status-section"><div class="status-grid">{items}</div></div>',
            unsafe_allow_html=True,
        )

        # Instructions
        st.markdown(_INSTRUCTIONS_HTML, unsafe_allow_html=True)
