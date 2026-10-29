import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from scipy.ndimage import distance_transform_edt

def decontaminate_edges(fg: Image.Image, solid_threshold: float = 210.0) -> Image.Image:
    """
    Suppresses edge color bleeding / fringing:
    When a product is photographed against a colored or dark background (e.g. wood,
    carpet, colored wall, or ambient shadows), boundary pixels contain optical bleed
    from that background. When placed onto pure white (#FFFFFF), this causes a dirty
    or dark halo ring.

    This function extrapolates clean foreground colors from the solid core (alpha >= 210)
    outward into the semi-transparent boundary pixels using an exact Euclidean distance transform,
    completely neutralizing background spill while preserving silky-smooth anti-aliased alpha.
    """
    if fg.mode != "RGBA":
        fg = fg.convert("RGBA")

    r, g, b, a = fg.split()
    alpha = np.array(a, dtype=np.float32)
    rgb = np.array(Image.merge("RGB", (r, g, b)), dtype=np.float32)

    solid_mask = alpha >= solid_threshold
    if not np.any(solid_mask):
        solid_mask = alpha > 80.0
    if not np.any(solid_mask):
        return fg

    # Find the nearest solid foreground pixel coordinates for each boundary pixel
    _, indices = distance_transform_edt(~solid_mask, return_indices=True)
    clean_rgb = rgb[indices[0], indices[1]]

    # Target the semi-transparent boundary pixels where background contamination resides
    transition_mask = (alpha > 0) & (alpha < solid_threshold)
    if not np.any(transition_mask):
        return fg

    # Smooth transition curve:
    # At solid core boundary (alpha ~ 210), blend is 0 (original product details 100% kept)
    # Towards outer edge (alpha < 60), blend smoothly ramps to 1.0 (pure clean foreground color)
    t = np.clip((solid_threshold - alpha[transition_mask]) / (solid_threshold - 60.0), 0.0, 1.0)
    blend = t * t * (3.0 - 2.0 * t)  # Smoothstep

    rgb[transition_mask] = (
        rgb[transition_mask] * (1.0 - blend[:, None]) + clean_rgb[transition_mask] * blend[:, None]
    )

    clean_img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    r_c, g_c, b_c = clean_img.split()
    return Image.merge("RGBA", (r_c, g_c, b_c, a))


def enhance_product_cutout(fg: Image.Image) -> Image.Image:
    """
    Studio photo enhancement:
    1. Adaptive gamma exposure correction (brightens underexposed camera shots without clipping highlights).
    2. Studio contrast boost (1.15x) for deep blacks and clean whites.
    3. Color vibrance boost (1.18x) to counteract flat indoor camera color casts.
    4. Commercial clarity unsharp masking to bring out fine textures, logos, and materials.
    """
    if fg.mode != "RGBA":
        fg = fg.convert("RGBA")

    r, g, b, a = fg.split()
    alpha_arr = np.array(a)

    # 1. Extract RGB channels (keep input alpha 'a' untouched to preserve smooth anti-aliasing)
    rgb = Image.merge("RGB", (r, g, b))

    # 2. Analyze visible product pixels only
    mask = alpha_arr > 10
    if np.any(mask):
        arr = np.array(rgb, dtype=np.float32)
        vis = arr[mask]
        mean_lum = 0.299 * vis[:, 0].mean() + 0.587 * vis[:, 1].mean() + 0.114 * vis[:, 2].mean()

        # Lift underexposed indoor camera shots with gentle gamma curve (preserves specular highlights)
        if mean_lum < 165:
            gamma = max(0.68, min(0.95, mean_lum / 175.0))
            arr = 255.0 * np.power(np.clip(arr / 255.0, 0.0, 1.0), gamma)
            rgb = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    # 3. Boost Contrast
    rgb = ImageEnhance.Contrast(rgb).enhance(1.15)

    # 4. Boost Color Vibrance
    rgb = ImageEnhance.Color(rgb).enhance(1.18)

    # 5. Apply Commercial Clarity Sharpening
    rgb = rgb.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=2))

    r_n, g_n, b_n = rgb.split()
    return Image.merge("RGBA", (r_n, g_n, b_n, a))


def composite_product_shot(
    fg_image: Image.Image,
    canvas_size: int = 1024,
    target_coverage: float = 0.78,
    bg_color: tuple = (255, 255, 255),
    add_shadow: bool = True,
    auto_enhance: bool = True,
    decontaminate: bool = True
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

    # 1. Find tight bounding box of visible product (threshold 10 preserves anti-aliased edge)
    alpha = np.array(fg_image.split()[-1])
    coords = np.argwhere(alpha > 10)
    if coords.size == 0:
        bbox = (0, 0, fg_image.width, fg_image.height)
    else:
        y0, x0 = coords.min(axis=0)
        y1, x1 = coords.max(axis=0) + 1
        # 2px safety padding to ensure the anti-aliased edge gradient is never clipped
        x0 = max(0, int(x0) - 2)
        y0 = max(0, int(y0) - 2)
        x1 = min(fg_image.width, int(x1) + 2)
        y1 = min(fg_image.height, int(y1) + 2)
        bbox = (x0, y0, x1, y1)

    cropped = fg_image.crop(bbox)
    p_w, p_h = cropped.size

    if p_w <= 0 or p_h <= 0:
        raise ValueError("Invalid product dimensions after cropping")

    # 2. Edge Color Decontamination (neutralizes background spill / fringing at the border)
    if decontaminate:
        cropped = decontaminate_edges(cropped)

    # 3. Studio Lighting, Color & Clarity Enhancement
    if auto_enhance:
        cropped = enhance_product_cutout(cropped)

    # 4. Scale product nicely to ~78% of canvas without cropping
    max_dim = int(canvas_size * target_coverage)
    scale = min(max_dim / p_w, max_dim / p_h)
    new_w = max(1, int(round(p_w * scale)))
    new_h = max(1, int(round(p_h * scale)))
    product = cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # 5. Clean Centered Framing
    pos_x = (canvas_size - new_w) // 2
    pos_y = (canvas_size - new_h) // 2

    # 6. Seamless Studio Canvas (Pure #FFFFFF)
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (*bg_color, 255))

    prod_alpha = product.split()[-1]

    # 7. Natural Ambient Contour Shadow
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

    # 8. Composite enhanced product onto canvas
    canvas.paste(product, (pos_x, pos_y), product)

    # Convert to standard RGB JPEG canvas
    return canvas.convert("RGB")

