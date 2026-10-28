import os
import tempfile
import logging

# Ensure model cache directory is writable in Serverless / Lambda environments (e.g. Vercel)
# Lambda root filesystem is read-only; only /tmp is writable
if "U2NET_HOME" not in os.environ:
    os.environ["U2NET_HOME"] = os.path.join(tempfile.gettempdir(), ".u2net")

import numpy as np
from PIL import Image
from scipy.ndimage import label
import rembg
import onnxruntime as ort

logger = logging.getLogger("productshot.bg_removal")

# High-performance, razor-sharp model (1.8s on CPU vs 34s for bria-rmbg)
# Configurable via BG_MODEL: 'isnet-general-use', 'u2netp' (0.3s ultra-fast), 'silueta' (1.7s), or 'bria-rmbg'
DEFAULT_MODEL = os.getenv("BG_MODEL", "isnet-general-use")

_sessions = {}

def create_optimized_session(model_name: str):
    """Creates a rembg session with multi-threaded CPU execution and graph optimizations."""
    opts = ort.SessionOptions()
    # Use available CPU cores for intra-op parallelism
    opts.intra_op_num_threads = min(8, os.cpu_count() or 4)
    opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    
    return rembg.new_session(model_name, session_options=opts)

def get_or_load_session(model_name: str = None):
    """
    Loads and caches the open-source background removal model session.
    Loaded once and reused across all requests.
    """
    global _sessions
    target_model = model_name or DEFAULT_MODEL
    
    if target_model not in _sessions:
        logger.info(f"Loading optimized background removal model: {target_model}...")
        _sessions[target_model] = create_optimized_session(target_model)
        logger.info(f"Model '{target_model}' loaded and ready for high-speed inference.")
        
    return _sessions[target_model]

def warm_up_model():
    """Warms up the model with a tiny synthetic image so first user request is instant."""
    try:
        session = get_or_load_session()
        dummy = Image.new("RGB", (64, 64), color=(255, 255, 255))
        rembg.remove(dummy, session=session)
        logger.info("Background removal model warmup complete.")
    except Exception as e:
        logger.warning(f"Model warmup warning: {e}")

def clean_alpha_specks(fg_image: Image.Image, min_area_ratio: float = 0.005) -> Image.Image:
    """
    Removes tiny isolated floating alpha artifacts that don't belong to the product.
    Preserves all main connected components.
    Uses pure scipy.ndimage (avoids heavy opencv dependency).
    """
    if fg_image.mode != "RGBA":
        fg_image = fg_image.convert("RGBA")

    alpha = np.array(fg_image.split()[-1])
    # Zero out low-alpha boundary noise (table reflections, lens glare)
    alpha[alpha < 35] = 0
    mask = alpha > 35

    # 8-connectivity labeling using a 3x3 structuring element
    labeled, num_labels = label(mask, structure=np.ones((3, 3), dtype=int))
    
    if num_labels <= 1:
        fg_image.putalpha(Image.fromarray(alpha))
        return fg_image

    counts = np.bincount(labeled.ravel())
    areas = counts[1:]  # areas for labels 1 to num_labels
    if len(areas) == 0:
        fg_image.putalpha(Image.fromarray(alpha))
        return fg_image
    
    total_pixels = fg_image.width * fg_image.height
    min_pixels = int(total_pixels * min_area_ratio)

    max_area = np.max(areas)
    valid_threshold = max(min_pixels, int(max_area * 0.04))

    small_labels = np.where(areas < valid_threshold)[0] + 1
    if len(small_labels) > 0:
        remove_mask = np.isin(labeled, small_labels)
        alpha[remove_mask] = 0

    fg_image.putalpha(Image.fromarray(alpha))
    return fg_image

def remove_background(image: Image.Image, max_dimension: int = 768, model_name: str = None) -> Image.Image:
    """
    Removes the background using the local open-source model.
    Optimizes input image dimension to 768px for sub-2-second inference speed.
    """
    if image.mode != "RGB":
        image = image.convert("RGB")

    # Downscale overly huge input to preserve sub-2-second speed
    orig_w, orig_h = image.size
    if max(orig_w, orig_h) > max_dimension:
        ratio = max_dimension / max(orig_w, orig_h)
        new_size = (int(orig_w * ratio), int(orig_h * ratio))
        processing_img = image.resize(new_size, Image.Resampling.LANCZOS)
    else:
        processing_img = image

    session = get_or_load_session(model_name)
    
    # Run open-source foreground extraction with post-processing mask enabled
    fg_cutout = rembg.remove(
        processing_img,
        session=session,
        alpha_matting=False,
        post_process_mask=True
    )

    # Clean small floating specks and zero out boundary bleed
    fg_clean = clean_alpha_specks(fg_cutout)
    return fg_clean
