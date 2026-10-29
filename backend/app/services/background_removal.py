import os
import tempfile
import logging

# Ensure model cache directory is writable in Serverless / Lambda environments (e.g. Vercel)
# In local development, respect user's ~/.u2net cache if it exists
if "U2NET_HOME" not in os.environ:
    user_u2net = os.path.expanduser("~/.u2net")
    if os.path.exists(user_u2net):
        os.environ["U2NET_HOME"] = user_u2net
    else:
        os.environ["U2NET_HOME"] = os.path.join(tempfile.gettempdir(), ".u2net")

import numpy as np
from PIL import Image
from scipy.ndimage import label, binary_dilation
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
        rembg.remove(dummy, session=session, only_mask=True)
        logger.info("Background removal model warmup complete.")
    except Exception as e:
        logger.warning(f"Model warmup warning: {e}")

def clean_alpha_specks(alpha_input, min_area_ratio: float = 0.003):
    """
    Removes tiny isolated floating alpha artifacts that don't belong to the product.
    Preserves all main connected components and their natural anti-aliased edge falloff.
    Accepts either a PIL RGBA Image or a 2D float/uint8 numpy alpha array.
    """
    is_image = isinstance(alpha_input, Image.Image)
    if is_image:
        alpha = np.array(alpha_input.split()[-1], dtype=np.float32)
    else:
        alpha = np.array(alpha_input, dtype=np.float32)

    # Core threshold to detect definite solid connected components
    core_mask = alpha > 40
    labeled, num_labels = label(core_mask, structure=np.ones((3, 3), dtype=int))
    
    if num_labels <= 1:
        if is_image:
            return alpha_input
        return alpha

    counts = np.bincount(labeled.ravel())
    areas = counts[1:]  # areas for labels 1 to num_labels
    if len(areas) == 0:
        if is_image:
            return alpha_input
        return alpha
    
    h, w = alpha.shape
    total_pixels = h * w
    min_pixels = int(total_pixels * min_area_ratio)

    max_area = np.max(areas)
    # Valid components are either reasonably large or at least 2% of the main subject
    valid_threshold = max(min_pixels, int(max_area * 0.02))

    small_labels = np.where(areas < valid_threshold)[0] + 1
    cleaned = alpha.copy()
    if len(small_labels) > 0:
        noise_mask = np.isin(labeled, small_labels)
        # Dilate noise mask slightly (5x5) so the soft anti-aliased halo around noise specks is wiped
        dilated_noise = binary_dilation(noise_mask, structure=np.ones((5, 5), dtype=bool))
        cleaned[dilated_noise] = 0.0

    if is_image:
        out = alpha_input.copy()
        out.putalpha(Image.fromarray(cleaned.astype(np.uint8)))
        return out

    return cleaned

def remove_background(
    image: Image.Image,
    inference_max_dimension: int = 1024,
    model_name: str = None
) -> Image.Image:
    """
    High-fidelity background removal:
    1. Retains the original full-resolution photo in memory (zero loss of texture/label detail).
    2. Runs neural network inference on an optimized working copy (1024px max dimension,
       matching the native 1024x1024 receptive field of isnet-general-use).
    3. Upscales the predicted alpha mask back to original native dimensions using
       high-precision bilinear interpolation for continuous sub-pixel edge smoothness.
    4. Applies continuous soft noise-floor suppression (no abrupt binary cutoffs) and removes
       disconnected background specks without harming the product's anti-aliased edge.
    5. Applies the pristine mask directly onto the original high-resolution photo.
    """
    if image.mode != "RGB":
        orig_rgb = image.convert("RGB")
    else:
        orig_rgb = image

    orig_w, orig_h = orig_rgb.size

    # Prepare working copy for neural network inference
    # Capped at inference_max_dimension (1024px) for optimal speed and receptive field
    if max(orig_w, orig_h) > inference_max_dimension:
        ratio = inference_max_dimension / max(orig_w, orig_h)
        proc_size = (max(1, int(round(orig_w * ratio))), max(1, int(round(orig_h * ratio))))
        proc_img = orig_rgb.resize(proc_size, Image.Resampling.BILINEAR)
    else:
        proc_img = orig_rgb

    session = get_or_load_session(model_name)
    
    # Run model to extract the raw grayscale alpha probability mask
    raw_mask = rembg.remove(
        proc_img,
        session=session,
        only_mask=True,
        post_process_mask=True
    )

    # Upscale alpha mask back to original native photo dimensions with bilinear filtering
    if raw_mask.size != (orig_w, orig_h):
        full_res_mask = raw_mask.resize((orig_w, orig_h), Image.Resampling.BILINEAR)
    else:
        full_res_mask = raw_mask

    alpha_arr = np.array(full_res_mask, dtype=np.float32)

    # Continuous soft noise-floor ramp:
    # Instead of harsh step `alpha < 35 = 0`, map [noise_floor, 255] smoothly to [0, 255]
    # This eliminates faint camera sensor background noise while preserving sub-pixel anti-aliasing
    noise_floor = 12.0
    alpha_arr = np.clip((alpha_arr - noise_floor) / (255.0 - noise_floor) * 255.0, 0.0, 255.0)

    # Remove isolated floating specks while protecting main product boundaries
    alpha_clean = clean_alpha_specks(alpha_arr)

    # Apply the mask directly to the original uncompressed photo
    final_fg = orig_rgb.convert("RGBA")
    final_fg.putalpha(Image.fromarray(alpha_clean.astype(np.uint8)))

    return final_fg
