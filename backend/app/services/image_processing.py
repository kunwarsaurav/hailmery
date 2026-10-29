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
    1. Adaptive dynamic range & exposure recovery:
       - Uses percentile-based histogram analysis (p95) rather than a blunt average luminance.
       - Anchors the black point with a quadratic toe curve so dark/black products never
         get washed out into milky gray.
       - Gently recovers underexposed midtones and highlights without blowing out white products.
    2. Subtle studio contrast boost (1.05x): Provides crisp commercial pop without crushing shadows.
    3. Natural color fidelity (1.04x): Prevents oversaturating vibrant colors while adding subtle freshness.
    4. Commercial clarity unsharp masking (threshold=8, radius=1.0, percent=70):
       Sharpens fine textures, logos, stitching, and product details while ignoring digital camera sensor noise.
    """
    if fg.mode != "RGBA":
        fg = fg.convert("RGBA")

    r, g, b, a = fg.split()
    alpha_arr = np.array(a)

    rgb = Image.merge("RGB", (r, g, b))

    mask = alpha_arr > 10
    if np.any(mask):
        arr = np.array(rgb, dtype=np.float32)
        vis = arr[mask]
        lum = 0.299 * vis[:, 0] + 0.587 * vis[:, 1] + 0.114 * vis[:, 2]
        p95 = np.percentile(lum, 95)

        # Lift underexposed indoor camera shots where highlights are compressed
        # But protect deep blacks using toe curve: norm + (scale - 1) * norm^1.3
        if 40.0 < p95 < 215.0:
            target_scale = min(1.22, 230.0 / max(p95, 100.0))
            norm = np.clip(arr / 255.0, 0.0, 1.0)
            lift = (target_scale - 1.0) * (norm ** 1.3)
            enhanced_arr = np.clip((norm + lift) * 255.0, 0.0, 255.0)
            rgb = Image.fromarray(enhanced_arr.astype(np.uint8))

    # Subtle studio contrast (crisp without crushing dark details)
    rgb = ImageEnhance.Contrast(rgb).enhance(1.05)

    # Natural color vibrance (preserves color accuracy for e-commerce)
    rgb = ImageEnhance.Color(rgb).enhance(1.04)

    # Noise-aware commercial clarity (threshold 8 ignores mobile ISO noise)
    rgb = rgb.filter(ImageFilter.UnsharpMask(radius=1.0, percent=70, threshold=8))

    r_n, g_n, b_n = rgb.split()
    return Image.merge("RGBA", (r_n, g_n, b_n, a))


def create_studio_ground_shadow(
    prod_alpha: Image.Image,
    canvas_size: int,
    pos_x: int,
    pos_y: int,
    new_w: int,
    new_h: int
) -> Image.Image:
    """
    Generates a realistic 3D studio tabletop shadow:
    1. Ambient Ground Shadow: A horizontally projected, flattened shadow puddle
       underneath the product base, simulating overhead softbox lighting.
    2. Contact Occlusion Shadow: A tight, dense, dark shadow right along the contact
       seam where the product physically touches the surface.
    Unlike flat silhouette drop shadows, this does NOT float around the upper body or sides.
    """
    shadow_layer = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    base_y = pos_y + new_h

    # 1. Soft Ambient Ground Shadow (flattened perspective puddle underneath base)
    amb_w = max(1, int(new_w * 1.06))
    amb_h = max(6, int(new_h * 0.18))
    flat_alpha = prod_alpha.resize((amb_w, amb_h), Image.Resampling.BILINEAR)
    amb_img = Image.new("RGBA", (amb_w, amb_h), (28, 30, 38, 0))
    amb_alpha_arr = (np.array(flat_alpha, dtype=np.float32) * 0.22).astype(np.uint8)
    amb_img.putalpha(Image.fromarray(amb_alpha_arr))

    amb_x = pos_x - (amb_w - new_w) // 2
    amb_y = base_y - int(amb_h * 0.40)
    shadow_layer.paste(amb_img, (amb_x, amb_y), amb_img)
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=max(8, int(canvas_size * 0.016))))

    # 2. Contact Occlusion Shadow (tight, dense, anchored right where product touches table)
    contact_w = new_w
    contact_h = max(4, int(new_h * 0.06))
    contact_flat = prod_alpha.resize((contact_w, contact_h), Image.Resampling.BILINEAR)
    contact_img = Image.new("RGBA", (contact_w, contact_h), (18, 20, 26, 0))
    contact_alpha_arr = (np.array(contact_flat, dtype=np.float32) * 0.48).astype(np.uint8)
    contact_img.putalpha(Image.fromarray(contact_alpha_arr))

    contact_layer = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    contact_y = base_y - int(contact_h * 0.50)
    contact_layer.paste(contact_img, (pos_x, contact_y), contact_img)
    contact_layer = contact_layer.filter(ImageFilter.GaussianBlur(radius=max(3, int(canvas_size * 0.005))))

    return Image.alpha_composite(shadow_layer, contact_layer)


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
    - If add_shadow=True, applies a realistic dual-layer studio ground shadow
      (ambient falloff + contact occlusion) anchored to the table plane.
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

    # 7. Grounded Studio Contact & Ambient Shadow
    if add_shadow:
        prod_alpha = product.split()[-1]
        shadow_layer = create_studio_ground_shadow(
            prod_alpha=prod_alpha,
            canvas_size=canvas_size,
            pos_x=pos_x,
            pos_y=pos_y,
            new_w=new_w,
            new_h=new_h
        )
        canvas = Image.alpha_composite(canvas, shadow_layer)

    # 8. Composite enhanced product onto canvas
    canvas.paste(product, (pos_x, pos_y), product)

    # Convert to standard RGB JPEG canvas
    return canvas.convert("RGB")

