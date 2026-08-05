# -*- coding: utf-8 -*-
"""
services/model_manager.py
==========================
Handles downloading, verifying, and loading the SAM 3 checkpoint
from an external URL (Google Drive or any direct HTTPS link).

Configuration (Streamlit secrets or environment variables):
  SAM3_MODEL_URL  — direct HTTPS URL or Google Drive share link
  SAM3_MODEL_SIZE — expected file size in bytes (optional, for verification)

Local cache directory:
  /tmp/dash_models/sam3.pt   (Streamlit Cloud)
  or ./models/sam3.pt        (local dev)

Usage:
  from services.model_manager import get_sam3_model
  processor, error = get_sam3_model()
"""

from __future__ import annotations
import os
import sys
import logging
import pathlib
import hashlib
from typing import Optional, Tuple

import streamlit as st

logger = logging.getLogger(__name__)

# ─── Paths ────────────────────────────────────────────────────────

def _model_dir() -> pathlib.Path:
    """
    Return a writable directory for the checkpoint.
    /tmp/dash_models on Streamlit Cloud; ./models locally.
    """
    candidate = pathlib.Path("/tmp/dash_models")
    try:
        candidate.mkdir(parents=True, exist_ok=True)
        (candidate / ".write_test").touch()
        (candidate / ".write_test").unlink()
        return candidate
    except OSError:
        local = pathlib.Path(__file__).resolve().parent.parent / "models"
        local.mkdir(parents=True, exist_ok=True)
        return local


def _checkpoint_path() -> pathlib.Path:
    # 1. Custom path from secrets or environment variable
    custom_path_str = None
    try:
        custom_path_str = st.secrets.get("SAM3_MODEL_PATH", "")
    except Exception:
        pass
    if not custom_path_str:
        custom_path_str = os.environ.get("SAM3_MODEL_PATH", "")
    
    if custom_path_str:
        custom_path = pathlib.Path(custom_path_str.strip())
        if custom_path.exists():
            return custom_path

    # 2. Check standard sibling location (dash_ai/sam3_pant/checkpoints/sam3.pt)
    # relative to DashAICapture_Streamlit root: ../dash_ai/sam3_pant/checkpoints/sam3.pt
    here = pathlib.Path(__file__).resolve().parent.parent
    sibling_path = here.parent / "dash_ai" / "sam3_pant" / "checkpoints" / "sam3.pt"
    if sibling_path.exists():
        return sibling_path

    # 3. Check local models folder
    local_path = here / "models" / "sam3.pt"
    if local_path.exists():
        return local_path

    # 4. Check tmp path
    tmp_path = pathlib.Path("/tmp/dash_models/sam3.pt")
    if tmp_path.exists():
        return tmp_path

    # Default fallback path for downloading
    return _model_dir() / "sam3.pt"


# ─── URL helpers ───────────────────────────────────────────────────

def _get_model_url() -> Optional[str]:
    """Read SAM3_MODEL_URL from Streamlit secrets or env var."""
    # 1. Streamlit secrets
    try:
        url = st.secrets.get("SAM3_MODEL_URL", "")
        if url:
            return url.strip()
    except Exception:
        pass
    # 2. Environment variable
    url = os.environ.get("SAM3_MODEL_URL", "").strip()
    return url or None


def _resolve_drive_url(url: str) -> str:
    """
    Convert a Google Drive share link into a direct download URL.

    Supported input formats:
      https://drive.google.com/file/d/<FILE_ID>/view?usp=sharing
      https://drive.google.com/open?id=<FILE_ID>
      https://drive.google.com/uc?id=<FILE_ID>   ← already direct
    """
    import re

    # Already a direct download URL
    if "drive.google.com/uc" in url or "export=download" in url:
        return url

    # Extract file ID
    match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
    if not match:
        match = re.search(r"id=([a-zA-Z0-9_-]+)", url)
    if match:
        file_id = match.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t"

    # Not a Drive URL — return as-is (may be any HTTPS link)
    return url


# ─── Download ─────────────────────────────────────────────────────

def download_model(progress_callback=None) -> Tuple[bool, str]:
    """
    Download the SAM 3 checkpoint if it doesn't already exist locally.

    Returns (success: bool, error_message: str).
    progress_callback(fraction: float, message: str) called during download.
    """
    import requests

    ckpt = _checkpoint_path()

    # Already present — skip download
    expected_bytes = _get_expected_size()
    if ckpt.exists():
        actual = ckpt.stat().st_size
        if expected_bytes and actual < expected_bytes * 0.99:
            logger.warning(
                "Checkpoint size mismatch (%d vs %d). Re-downloading.",
                actual, expected_bytes,
            )
            ckpt.unlink(missing_ok=True)
        else:
            logger.info("Checkpoint already present at %s (%d bytes)", ckpt, actual)
            return True, ""

    url = _get_model_url()
    if not url:
        return False, (
            "SAM3_MODEL_URL is not configured. "
            "Add it to .streamlit/secrets.toml or as an environment variable."
        )

    url = _resolve_drive_url(url)
    logger.info("Downloading SAM 3 checkpoint from %s → %s", url, ckpt)

    try:
        with requests.get(url, stream=True, timeout=30) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            chunk_size = 4 * 1024 * 1024  # 4 MB chunks

            with open(ckpt, "wb") as f:
                for chunk in resp.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total:
                            progress_callback(
                                downloaded / total,
                                f"Downloading SAM 3… {downloaded // (1024*1024)} / {total // (1024*1024)} MB"
                            )

        return True, ""

    except requests.exceptions.RequestException as e:
        ckpt.unlink(missing_ok=True)
        err = f"Download failed: {e}"
        logger.error(err)
        return False, err
    except Exception as e:
        ckpt.unlink(missing_ok=True)
        err = f"Unexpected download error: {e}"
        logger.error(err)
        return False, err


def _get_expected_size() -> Optional[int]:
    """Read SAM3_MODEL_SIZE from secrets or env (bytes, optional)."""
    try:
        val = st.secrets.get("SAM3_MODEL_SIZE", "")
        if val:
            return int(val)
    except Exception:
        pass
    val = os.environ.get("SAM3_MODEL_SIZE", "")
    return int(val) if val else None


def verify_checkpoint() -> Tuple[bool, str]:
    """
    Basic sanity check on the local checkpoint.
    Returns (ok, error_message).
    """
    ckpt = _checkpoint_path()
    if not ckpt.exists():
        return False, "Checkpoint file not found."
    size = ckpt.stat().st_size
    if size < 1_000_000:   # less than 1 MB is certainly wrong
        return False, f"Checkpoint appears corrupted (size: {size} bytes)."
    return True, ""


# ─── SAM 3 model loading ───────────────────────────────────────────

def _add_sam3_to_path() -> bool:
    """
    Try to add the local sam3 package to sys.path.
    Returns True if the sam3 module can be imported.
    """
    # Path relative to this file: ../../dash_ai/sam3_pant/
    here = pathlib.Path(__file__).resolve().parent.parent
    candidates = [
        here.parent / "dash_ai" / "sam3_pant",
        here.parent / "dash_ai" / "sam3_pant" / "sam3",
    ]
    for p in candidates:
        s = str(p)
        if p.exists() and s not in sys.path:
            sys.path.insert(0, s)

    try:
        import sam3  # noqa: F401
        return True
    except ImportError:
        return False


@st.cache_resource(show_spinner=False)
def get_sam3_model():
    """
    Load SAM 3 once and cache using @st.cache_resource.

    Returns (processor, error_message).
    If error_message is not None, processor is None.

    Call flow:
        1. Ensure checkpoint is present (download if needed).
        2. Add sam3 package to sys.path.
        3. Build model + processor.
        4. Return cached handle.
    """
    import glob

    # ── Step 1: Download if needed ─────────────────────────────────
    ok, err = download_model()
    if not ok:
        return None, err

    ok, err = verify_checkpoint()
    if not ok:
        return None, err

    ckpt = str(_checkpoint_path())

    # ── Step 2: Add sam3 to path ───────────────────────────────────
    if not _add_sam3_to_path():
        return None, (
            "sam3 Python package not found. "
            "Clone the SAM 3 repo alongside this project."
        )

    # ── Step 3: Import and build ───────────────────────────────────
    try:
        import torch
        from sam3.model_builder import build_sam3_image_model
        from sam3.model.sam3_image_processor import Sam3Processor

        # Locate BPE vocab
        sam3_root = pathlib.Path(__file__).resolve().parent.parent.parent / "dash_ai" / "sam3_pant"
        bpe_paths = glob.glob(str(sam3_root / "**" / "bpe_simple_vocab_16e6.txt.gz"), recursive=True)
        if not bpe_paths:
            # Try within the sam3 package itself
            import sam3 as _sam3_pkg
            pkg_root = pathlib.Path(_sam3_pkg.__file__).parent
            bpe_paths = glob.glob(str(pkg_root / "**" / "bpe_simple_vocab_16e6.txt.gz"), recursive=True)

        if not bpe_paths:
            return None, "BPE vocab file (bpe_simple_vocab_16e6.txt.gz) not found."

        bpe_path = bpe_paths[0]

        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("Loading SAM 3 on %s from %s", device, ckpt)

        model = build_sam3_image_model(
            bpe_path=bpe_path,
            checkpoint_path=ckpt,
            load_from_HF=False,
            compile=False,
        )

        if device == "cpu":
            model = model.float()

        processor = Sam3Processor(model, confidence_threshold=0.3)
        logger.info("SAM 3 loaded successfully.")
        return processor, None

    except MemoryError:
        return None, (
            "Insufficient memory to load SAM 3. "
            "Consider moving inference to an external GPU backend (Modal/RunPod)."
        )
    except Exception as exc:
        logger.exception("SAM 3 load error")
        return None, f"SAM 3 load error: {exc}"


def clear_cache() -> None:
    """Remove the local checkpoint to force a fresh download."""
    ckpt = _checkpoint_path()
    if ckpt.exists():
        ckpt.unlink()
        logger.info("Checkpoint removed from %s", ckpt)
