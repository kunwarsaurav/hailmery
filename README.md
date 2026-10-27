# ProductShot 📸
> **AI Product Photo Web App (MVP)**  
> Turn a quick product photo into a clean, studio-staged product image with automated background removal, centering, and realistic soft shadows.

---

## 🌟 Overview

ProductShot is a fast, lightweight proof-of-concept web application designed to isolate physical products from real-world photos and place them on a clean, professional e-commerce studio background.

**Core Workflow:**
$$\text{Camera / Upload} \longrightarrow \text{Open-Source RMBG Model} \longrightarrow \text{Bounding Box Detection} \longrightarrow \text{Centering \& Scaling} \longrightarrow \text{Studio Soft Shadow} \longrightarrow \text{1024}\times\text{1024 Download}$$

### Key Features
- **Zero Cloud / Third-Party APIs**: Self-hosted open-source background removal (BRIA RMBG / U2-Net).
- **100% Product Fidelity**: Preserves original textures, colors, logos, and typography without generative hallucinations.
- **Native Camera Experience**: Direct `getUserMedia` camera feed with square framing guide and mobile camera switching (`facingMode: environment`).
- **Device Upload Fallback**: One-click photo upload for desktop computers or devices without camera access.
- **Realistic Studio Shadow**: Multi-layered image-processing shadow (contact shadow + ambient ground diffuse shadow).
- **High-Resolution Output**: Standard 1024×1024 e-commerce format (JPEG quality 95).
- **Privacy-First**: Operates strictly in-memory or ephemeral buffers with zero persistent image storage or tracking.

---

## 🏛️ Architecture

```
meryhail/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI server & /api/process endpoint
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── background_removal.py  # Open-source model session & speck cleanup
│   │       └── image_processing.py   # Centering, bounding box, & studio shadow
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   │   ├── globals.css                # Styling & keyframes
│   │   ├── layout.tsx                 # Root layout & SEO meta tags
│   │   └── page.tsx                   # Main orchestrator (Camera -> Processing -> Result)
│   ├── components/
│   │   ├── CameraView.tsx             # getUserMedia live feed + shutter + upload button
│   │   ├── ProcessingView.tsx         # Responsive loading state with photo thumbnail
│   │   └── ResultView.tsx             # 1024x1024 studio shot display, compare toggle & download
│   ├── lib/
│   │   └── api.ts                     # API client with direct & proxy fallback
│   ├── package.json
│   └── next.config.ts                 # Next.js config with API proxy rewrites
│
└── README.md
```

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python**: 3.10+
- **Node.js**: 18+ (Node 20+ recommended)
- **Git**

---

### 1. Backend Setup

Open a terminal in the root directory:

```bash
cd backend

# (Optional but recommended) Create a virtual environment:
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies:
pip install -r requirements.txt
```

#### Run the Backend Server:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- Health check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)
- Interactive API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

> **Note on Model Download**: On the first startup, `rembg` will automatically download the model weights (e.g., `bria-rmbg.onnx`) into your local cache directory (`~/.u2net/`). Subsequent runs initialize from the local cache.

---

### 2. Frontend Setup

Open a second terminal:

```bash
cd frontend

# Install npm dependencies:
npm install

# Run development server:
npm run dev
```

Visit **[http://localhost:3000](http://localhost:3000)** in your browser or mobile device.

---

## ⚙️ Configuration & Environment Variables

### Backend (`backend/.env` or system environment):
| Variable | Default | Description |
|---|---|---|
| `BG_MODEL` | `bria-rmbg` | Model to use. Options: `bria-rmbg` (highest product accuracy), `u2netp` (ultra-fast lightweight CPU model), or `u2net`. |
| `PORT` | `8000` | Port for the FastAPI server. |

### Frontend (`frontend/.env.local`):
| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000` | Direct backend URL for client-side API requests. |
| `BACKEND_URL` | `http://127.0.0.1:8000` | Target URL used by Next.js API proxy rewrites. |

---

## 🔬 Hardware & Performance

- **CPU Support**: Fully supported out-of-the-box using ONNX Runtime CPU execution provider.
- **GPU Acceleration**: If NVIDIA CUDA is detected, ONNX Runtime automatically leverages GPU hardware without configuration changes.
- **Memory**: Ephemeral in-memory byte streams (`io.BytesIO`). No images are saved to disk.

---

## 📜 Model Information & Licensing

- **BRIA RMBG**: Developed by BRIA AI. Trained on high-fidelity foreground/background segmentation datasets. Free for non-commercial and research use under the BRIA License.
- **U2-Net / U2-Netp**: Open-source general object segmentation models under the Apache 2.0 license.

---

## 🧪 Production Verification
The application has been verified end-to-end:
- **Sneaker Test**: Full background clutter (bookshelf, flooring, armchair, rug) cleanly stripped; sneaker centered with ground contact & diffuse studio shadow.
- **Perfume Bottle Test**: Glass transparency and fine typography ("AURÉLIE - EAU DE PARFUM") preserved with 100% fidelity.
