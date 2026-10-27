import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

def enhance_product_cutout(fg: Image.Image) -> Image.Image:
    """
    Studio photo enhancement:
    1. Defringes noisy semi-transparent background bleed (alpha < 35).
    2. Adaptive gamma exposure correction (brightens underexposed camera shots without clipping highlights).
    3. Studio contrast boost (1.15x) for deep blacks and clean whites.
    4. Color vibrance boost (1.18x) to counteract flat indoor camera color casts.
    5. Commercial clarity unsharp masking to bring out fine textures, logos, and materials.
    """
    if fg.mode != "RGBA":
        fg = fg.convert("RGBA")

    r, g, b, a = fg.split()
    alpha_arr = np.array(a)

    # 1. Defringe: Snap noisy boundary bleed to zero
    alpha_arr[alpha_arr < 35] = 0
    cleaned_alpha = Image.fromarray(alpha_arr)

    # 2. Extract RGB channels
    rgb = Image.merge("RGB", (r, g, b))

    # 3. Analyze visible product pixels only
    mask = alpha_arr > 35
    if np.any(mask):
        arr = np.array(rgb, dtype=np.float32)
        vis = arr[mask]
        mean_lum = 0.299 * vis[:, 0].mean() + 0.587 * vis[:, 1].mean() + 0.114 * vis[:, 2].mean()

        # Lift underexposed indoor camera shots with gentle gamma curve (preserves specular highlights)
        if mean_lum < 165:
            gamma = max(0.68, min(0.95, mean_lum / 175.0))
            arr = 255.0 * np.power(np.clip(arr / 255.0, 0.0, 1.0), gamma)
            rgb = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    # 4. Boost Contrast
    rgb = ImageEnhance.Contrast(rgb).enhance(1.15)

    # 5. Boost Color Vibrance
    rgb = ImageEnhance.Color(rgb).enhance(1.18)

    # 6. Apply Commercial Clarity Sharpening
    rgb = rgb.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=2))

    r_n, g_n, b_n = rgb.split()
    return Image.merge("RGBA", (r_n, g_n, b_n, cleaned_alpha))


def composite_product_shot(
    fg_image: Image.Image,
    canvas_size: int = 1024,
    target_coverage: float = 0.78,
    bg_color: tuple = (255, 255, 255),
    add_shadow: bool = True,
    auto_enhance: bool = True
) -> Image.Image:
    """
    Universal e-commerce product staging that works on ANY product:
    phones, keys, shoes, apparel, electronics, bottles, cosmetics, jewelry.

    - Places product on 100% pure studio white canvas (#FFFFFF).
    - If add_shadow=True, applies a natural ambient contour drop shadow derived
      directly from the product's actual silhouette (no artificial floor smudges).
    - If add_shadow=False, produces a pristine 100% pure flat white Amazon catalog cutout.
    """
    if fg_image.mode != "RGBA":
        fg_image = fg_image.convert("RGBA")

    # 1. Studio Lighting, Color & Clarity Enhancement
    if auto_enhance:
        fg_image = enhance_product_cutout(fg_image)

    # 2. Defringe & Find tight bounding box of visible product
    alpha = np.array(fg_image.split()[-1])
    coords = np.argwhere(alpha > 35)
    if coords.size == 0:
        bbox = (0, 0, fg_image.width, fg_image.height)
    else:
        y0, x0 = coords.min(axis=0)
        y1, x1 = coords.max(axis=0) + 1
        bbox = (int(x0), int(y0), int(x1), int(y1))

    cropped = fg_image.crop(bbox)
    p_w, p_h = cropped.size

    if p_w <= 0 or p_h <= 0:
        raise ValueError("Invalid product dimensions after cropping")

    # 3. Scale product nicely to ~78% of canvas without cropping
    max_dim = int(canvas_size * target_coverage)
    scale = min(max_dim / p_w, max_dim / p_h)
    new_w = max(1, int(round(p_w * scale)))
    new_h = max(1, int(round(p_h * scale)))
    product = cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # 4. Clean Centered Framing
    pos_x = (canvas_size - new_w) // 2
    pos_y = (canvas_size - new_h) // 2

    # 5. Seamless Studio Canvas (Pure #FFFFFF)
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (*bg_color, 255))

    prod_alpha = product.split()[-1]

    # 6. Natural Ambient Contour Shadow
    if add_shadow:
        # Casts a soft, realistic ambient shadow hugging the EXACT product silhouette
        shadow_layer = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        shadow_img = Image.new("RGBA", (new_w, new_h), (35, 38, 45, 0))
        alpha_tint = (np.array(prod_alpha, dtype=np.float32) * 0.20).astype(np.uint8)
        shadow_img.putalpha(Image.fromarray(alpha_tint))

        # Gentle natural downward offset (simulates overhead studio softbox light)
        offset_y = pos_y + max(4, int(canvas_size * 0.012))
        shadow_layer.paste(shadow_img, (pos_x, offset_y), shadow_img)
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=15))

        canvas = Image.alpha_composite(canvas, shadow_layer)

    # 7. Composite enhanced product onto canvas
    canvas.paste(product, (pos_x, pos_y), product)

    # Convert to standard RGB JPEG canvas
    return canvas.convert("RGB")

