import os
import logging
import numpy as np
from PIL import Image
import rembg
import cv2

logger = logging.getLogger("productshot.bg_removal")

# Configurable model choice (defaults to bria-rmbg, can also use u2netp for ultra-fast dev)
DEFAULT_MODEL = os.getenv("BG_MODEL", "bria-rmbg")

_session = None
_loaded_model_name = None

def get_or_load_session(model_name: str = None):
    """
    Loads and caches the open-source background removal model session.
    Loaded once at startup.
    """
    global _session, _loaded_model_name
    target_model = model_name or DEFAULT_MODEL
    
    if _session is None or _loaded_model_name != target_model:
        logger.info(f"Loading background removal model: {target_model}...")
        _session = rembg.new_session(target_model)
        _loaded_model_name = target_model
        logger.info(f"Model '{target_model}' loaded and ready.")
        
    return _session

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
    """
    if fg_image.mode != "RGBA":
        fg_image = fg_image.convert("RGBA")

    alpha = np.array(fg_image.split()[-1])
    mask = (alpha > 20).astype(np.uint8) * 255

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    
    if num_labels <= 1:
        return fg_image

    total_pixels = fg_image.width * fg_image.height
    min_pixels = int(total_pixels * min_area_ratio)

    # Find the largest connected component (excluding background at index 0)
    areas = stats[1:, cv2.CC_STAT_AREA]
    if len(areas) == 0:
        return fg_image
    
    max_area = np.max(areas)
    # Keep components that are either large enough or at least 5% of the largest component
    valid_threshold = max(min_pixels, int(max_area * 0.05))

    cleaned_alpha = alpha.copy()
    for i in range(1, num_labels):
        if stats[i, cv2.CC_STAT_AREA] < valid_threshold:
            cleaned_alpha[labels == i] = 0

    fg_image.putalpha(Image.fromarray(cleaned_alpha))
    return fg_image

def remove_background(image: Image.Image, max_dimension: int = 768) -> Image.Image:
    """
    Removes the background from an uploaded image using the local open-source model.
    Scales down excessively large input images before inference to keep processing fast.
    """
    # Normalize to RGB
    if image.mode != "RGB":
        image = image.convert("RGB")

    # Downscale overly huge input to preserve speed and avoid memory limits
    orig_w, orig_h = image.size
    if max(orig_w, orig_h) > max_dimension:
        ratio = max_dimension / max(orig_w, orig_h)
        new_size = (int(orig_w * ratio), int(orig_h * ratio))
        processing_img = image.resize(new_size, Image.Resampling.LANCZOS)
    else:
        processing_img = image

    session = get_or_load_session()
    
    # Run open-source foreground extraction
    fg_cutout = rembg.remove(
        processing_img,
        session=session,
        alpha_matting=False  # Keeps edges clean and avoids slow edge post-processing
    )

    # Clean small floating specks if any
    fg_clean = clean_alpha_specks(fg_cutout)
    return fg_clean
