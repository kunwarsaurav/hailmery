import io
import time
import logging
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError

import app.services.background_removal as bg_service
from app.services.image_processing import composite_product_shot

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("productshot.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load open-source model once and warm it up
    logger.info("Initializing ProductShot backend...")
    bg_service.get_or_load_session()
    bg_service.warm_up_model()
    logger.info("ProductShot backend initialized and ready.")
    yield
    # Shutdown
    logger.info("ProductShot backend shutting down.")

app = FastAPI(
    title="ProductShot API",
    description="High-Speed AI Product Photo background-removal and studio staging API",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Processing-Time-Ms", "X-Model-Name"],
)

@app.get("/api/health")
async def health_check():
    return {
        "status": "online",
        "service": "ProductShot API",
        "model": bg_service.DEFAULT_MODEL,
        "canvas_size": "1024x1024"
    }

@app.post("/api/process")
async def process_image(
    file: UploadFile = File(...),
    model: Optional[str] = Query(None, description="Optional model override: isnet-general-use, u2netp, silueta, bria-rmbg")
):
    """
    Main image processing endpoint:
    1. Receives uploaded product photo
    2. Runs open-source background-removal model (optimized for ~1-2s speed)
    3. Finds product bounding box
    4. Centers and scales cleanly to canvas
    5. Casts subtle studio ground shadow
    6. Composites onto white background
    7. Returns processed 1024x1024 JPEG
    """
    start_time = time.time()
    
    # 1. Validate file presence
    if not file or not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No image file provided. Please capture or upload a product photo."
        )

    # 2. Read bytes in-memory (no permanent disk storage)
    try:
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty. Please capture or upload a valid photo."
            )
        
        # Max limit 25MB to prevent memory abuse
        if len(content) > 25 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="Image file size exceeds 25MB limit. Please upload a smaller image."
            )

        input_img = Image.open(io.BytesIO(content))
        # Handle EXIF orientation if present
        try:
            from PIL import ImageOps
            input_img = ImageOps.exif_transpose(input_img)
        except Exception:
            pass

    except (UnidentifiedImageError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Couldn't recognize this file as an image. Please upload a valid JPG, PNG, or WebP photo."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading image: {e}")
        raise HTTPException(
            status_code=400,
            detail="Failed to read the uploaded image. Please try again."
        )

    # 3. Process image through AI background removal and studio staging
    try:
        active_model = model or bg_service.DEFAULT_MODEL
        logger.info(f"Processing photo '{file.filename}' (dimensions: {input_img.size}) using model: {active_model}...")
        
        # Step A: Background removal using open-source model
        fg_cutout = bg_service.remove_background(input_img, model_name=active_model)
        
        # Step B: Center, scale, realistic studio shadow, white canvas
        final_product_shot = composite_product_shot(
            fg_image=fg_cutout,
            canvas_size=1024,
            target_coverage=0.76,
            bg_color=(255, 255, 255)
        )
        
        # Step C: Encode in-memory as high-quality JPEG
        out_buffer = io.BytesIO()
        final_product_shot.save(out_buffer, format="JPEG", quality=95, optimize=True)
        out_bytes = out_buffer.getvalue()
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Successfully processed '{file.filename}' in {elapsed_ms}ms. Output: {len(out_bytes)} bytes.")

        return Response(
            content=out_bytes,
            media_type="image/jpeg",
            headers={
                "X-Processing-Time-Ms": str(elapsed_ms),
                "X-Model-Name": active_model,
                "Content-Disposition": 'inline; filename="productshot.jpg"'
            }
        )

    except Exception as e:
        logger.error(f"Image processing pipeline failed: {e}", exc_info=True)
        # Friendly human-readable error message as required
        raise HTTPException(
            status_code=500,
            detail="Couldn't process this image. Try taking another photo with the product clearly visible and well-lit."
        )
