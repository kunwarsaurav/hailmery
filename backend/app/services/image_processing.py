import numpy as np
from PIL import Image, ImageFilter, ImageDraw

def composite_product_shot(
    fg_image: Image.Image,
    canvas_size: int = 1024,
    target_coverage: float = 0.76,
    bg_color: tuple = (255, 255, 255)
) -> Image.Image:
    """
    Takes an RGBA foreground image, crops to tight product bounding box,
    resizes to fit cleanly inside canvas, centers it, adds a soft realistic
    studio shadow underneath, and composites onto a clean white background.
    """
    if fg_image.mode != "RGBA":
        fg_image = fg_image.convert("RGBA")

    # 1. Determine bounding box of visible product (alpha threshold > 15)
    alpha = np.array(fg_image.split()[-1])
    coords = np.argwhere(alpha > 15)
    
    if coords.size == 0:
        # Fallback if no visible pixels detected
        bbox = (0, 0, fg_image.width, fg_image.height)
    else:
        y0, x0 = coords.min(axis=0)
        y1, x1 = coords.max(axis=0) + 1
        bbox = (int(x0), int(y0), int(x1), int(y1))

    # Crop tightly to product bounds
    product_cropped = fg_image.crop(bbox)
    p_w, p_h = product_cropped.size

    if p_w <= 0 or p_h <= 0:
        raise ValueError("Invalid product dimensions after cropping")

    # 2. Scale product so it occupies a sensible percentage of the canvas without cropping
    max_dim = int(canvas_size * target_coverage)
    scale = min(max_dim / p_w, max_dim / p_h)
    new_w = max(1, int(round(p_w * scale)))
    new_h = max(1, int(round(p_h * scale)))
    product_scaled = product_cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # 3. Placement on canvas (slightly lifted ~2% to balance ground shadow)
    ground_offset = int(canvas_size * 0.02)
    pos_x = (canvas_size - new_w) // 2
    pos_y = ((canvas_size - new_h) // 2) - ground_offset

    # Product bottom coordinate on canvas
    bottom_y = pos_y + new_h

    # 4. Generate Realistic Studio Shadow
    # A) Soft ambient ground shadow (flattened projection of product silhouette)
    shadow_canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    
    # Flatten the product silhouette vertically to simulate light from above-front
    shadow_h = max(12, int(new_h * 0.16))
    shadow_w = int(new_w * 1.04)
    
    prod_alpha = product_scaled.split()[-1]
    shadow_shape = prod_alpha.resize((shadow_w, shadow_h), Image.Resampling.BILINEAR)
    
    # Create soft dark neutral shadow with subtle opacity (max ~20%)
    diffuse_shadow = Image.new("RGBA", (shadow_w, shadow_h), (35, 35, 40, 0))
    diffuse_alpha_arr = np.array(shadow_shape, dtype=np.float32) * 0.20
    diffuse_shadow.putalpha(Image.fromarray(diffuse_alpha_arr.astype(np.uint8)))
    
    diff_x = (canvas_size - shadow_w) // 2
    diff_y = bottom_y - int(shadow_h * 0.35)
    shadow_canvas.paste(diffuse_shadow, (diff_x, diff_y), diffuse_shadow)
    shadow_canvas = shadow_canvas.filter(ImageFilter.GaussianBlur(radius=16))

    # B) Contact shadow (subtle sliver right at contact plane so product rests on ground)
    contact_canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    contact_w = int(new_w * 0.70)
    contact_h = max(6, int(new_h * 0.035))
    contact_x = (canvas_size - contact_w) // 2
    contact_y = bottom_y - int(contact_h * 0.55)
    
    draw = ImageDraw.Draw(contact_canvas)
    draw.ellipse(
        [contact_x, contact_y, contact_x + contact_w, contact_y + contact_h],
        fill=(25, 25, 30, 75)
    )
    contact_canvas = contact_canvas.filter(ImageFilter.GaussianBlur(radius=5))

    # 5. Composite: Canvas -> Ambient Shadow -> Contact Shadow -> Product
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (*bg_color, 255))
    canvas = Image.alpha_composite(canvas, shadow_canvas)
    canvas = Image.alpha_composite(canvas, contact_canvas)
    canvas.paste(product_scaled, (pos_x, pos_y), product_scaled)

    # Convert to RGB (pure JPEG / PNG format for final export)
    return canvas.convert("RGB")
