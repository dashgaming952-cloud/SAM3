# DASH AI Capture

> **Mobile-first pant photograph capture & SAM 3 segmentation pipeline.**

## What it does

Open the web app on your phone, photograph your pants flat on the floor, and receive:
- A precise binary segmentation mask (SAM 3)
- A transparent-background pant cutout (PNG)
- A quality report for every captured image

Future: HRNet landmark detection → waist/hip/inseam measurements.

---

## Quick start (local)

```bash
cd "d:/sam3 working/DashAICapture_Streamlit"
pip install -r requirements.txt
streamlit run app.py
```

Open **http://localhost:8501** in your browser (or on a phone on the same network).

---

## Project structure

```
app.py                          ← Entry point / router

components/
    camera.py                   ← Camera screen (mobile UI)
    processing.py               ← SAM 3 processing screen
    results.py                  ← Results & download screen

services/
    pant_detector.py            ← Contour-based pant detector (fallback)
    quality_checker.py          ← Blur / lighting / level quality checks
    sam3_service.py             ← SAM 3 inference wrapper
    model_manager.py            ← Download / cache / load SAM 3 checkpoint
    measurement_pipeline.py     ← HRNet stub (returns None until connected)

utils/
    styles.py                   ← Mobile-first CSS injection
    session.py                  ← Session state helpers
    image_utils.py              ← Pant guide SVG, rotation, zip

.streamlit/
    config.toml                 ← Dark theme, headless server
    secrets.toml.template       ← Copy → secrets.toml, add SAM3_MODEL_URL

requirements.txt
.gitignore
README.md
```

---

## Phone level detection

The app injects a `<script>` via `st.components.html()` that subscribes to
[`DeviceOrientationEvent`](https://developer.mozilla.org/en-US/docs/Web/API/DeviceOrientationEvent).

| Value | Meaning |
|-------|---------|
| `beta`  | Forward/back tilt (pitch-like) |
| `gamma` | Left/right tilt (roll-like) |

The JS writes values to `sessionStorage` and moves the bubble indicator
in real-time via direct DOM manipulation (no Streamlit round-trip needed
for the visual update).

**iOS permission**: iOS 13+ requires a user gesture to grant orientation access.
An "Enable Level Guidance" button is rendered; tapping it calls
`DeviceOrientationEvent.requestPermission()`.

If the sensor is unavailable, the bubble stays centred and the level
indicator shows "Level sensor unavailable".

---

## SAM 3 checkpoint caching

```
Application starts
    ↓
model_manager.get_sam3_model()   ← @st.cache_resource
    ↓
Checkpoint exists at /tmp/dash_models/sam3.pt ?
    YES → load SAM 3 → cache
    NO  → download from SAM3_MODEL_URL (streaming, 4 MB chunks)
           → verify size → load SAM 3 → cache
```

The model is loaded **once per Streamlit Cloud instance** and reused for
all subsequent images.

---

## Configuring the external model URL

### Option A — Streamlit secrets (recommended for Streamlit Cloud)

1. Copy `.streamlit/secrets.toml.template` → `.streamlit/secrets.toml`
2. Set `SAM3_MODEL_URL`:

```toml
SAM3_MODEL_URL = "https://drive.google.com/file/d/YOUR_FILE_ID/view?usp=sharing"
```

3. In Streamlit Cloud → **App settings → Secrets** paste the same content.

### Option B — Environment variable

```bash
export SAM3_MODEL_URL="https://your-cdn.com/sam3.pt"
streamlit run app.py
```

**Google Drive links** are automatically converted to direct download URLs.
**Any HTTPS direct link** also works.

---

## Deploying to Streamlit Cloud

1. Push this folder to a GitHub repository.
   - **Do NOT commit** `models/`, `.pt` files, `secrets.toml`, or user captures.
   - Use the provided `.gitignore`.

2. Go to [share.streamlit.io](https://share.streamlit.io) → New app.

3. Set **Main file path** to `app.py`.

4. Under **Advanced → Secrets** add:

```toml
SAM3_MODEL_URL = "https://drive.google.com/file/d/YOUR_FILE_ID/view?usp=sharing"
```

5. Deploy. On first load, the checkpoint downloads from Drive (~3.45 GB).
   Subsequent loads reuse the cached model.

---

## Streamlit Cloud limitations

| Resource | Streamlit Cloud (free) | Notes |
|----------|----------------------|-------|
| RAM | ~1 GB | SAM 3 requires ~4–6 GB → **will fail gracefully** |
| Disk | ~5 GB | Sufficient for checkpoint storage |
| GPU | None | CPU-only → fallback segmentation used |

**Recommendation for production**: Move SAM 3 inference to an external GPU
backend (Modal, RunPod, or a GPU API endpoint). The service interface in
`services/sam3_service.py` is designed to support this — just replace
`_run_inference()` with an HTTP call to your GPU backend.

---

## Known limitations

- **Streamlit camera_input** does not natively support `facingMode: environment`.
  On mobile, the camera selector defaults to whatever the browser chooses.
  Users can manually switch to the back camera in the browser camera picker.
- The SVG pant guide cannot be overlaid **on top of** the live camera feed
  natively in Streamlit (no real canvas layer access). It is shown immediately
  below the camera as a reference guide.
- Phone orientation values from `DeviceOrientationEvent` cannot be written
  directly to `st.session_state` without a custom Streamlit component.
  The bubble level animates in real-time via JS, but the Python quality-check
  uses 0.0° as the pitch/roll until a custom component bridge is built.
- SAM 3 (3.45 GB) cannot run on Streamlit Cloud's free tier. The fallback
  Otsu segmentation works but is less accurate.

---

## HRNet integration (future)

```python
# services/measurement_pipeline.py
def run_measurement_pipeline(original, segmented, mask):
    # Replace _hrnet_pipeline() body with real HRNet inference
    return _hrnet_pipeline(original, segmented, mask)
```

The `run_measurement_pipeline()` function is called after every successful
segmentation. It currently returns `None`. Plug HRNet weights in and return
a dict of measurements.
