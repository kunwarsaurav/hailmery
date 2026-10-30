/**
 * API service for ProductShot backend
 * NEXT_PUBLIC_API_URL should be set to the Railway backend URL, e.g.:
 *   https://productshot-backend.up.railway.app
 */

export interface ProcessResult {
  blob: Blob;
  imageUrl: string;
  processingTimeMs?: number;
}

// Railway backend URL — set via NEXT_PUBLIC_API_URL env var in Vercel project settings
const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");

function getEndpoint(path: string, queryString: string = ""): string {
  return `${API_BASE}${path}${queryString}`;
}

export async function processProductPhoto(
  photoBlob: Blob,
  fileName: string = "captured-product.jpg"
): Promise<ProcessResult> {
  const formData = new FormData();
  formData.append("file", photoBlob, fileName);

  const endpoint = getEndpoint("/api/process");

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      let errorMessage = `Processing failed (HTTP ${response.status}).`;
      try {
        const text = await response.text();
        try {
          const errorData = JSON.parse(text);
          if (errorData?.detail) {
            errorMessage = errorData.detail;
          }
        } catch {
          if (text && text.length < 200) {
            errorMessage = text;
          }
        }
      } catch {
        // Fallback
      }
      throw new Error(errorMessage);
    }

    const contentType = response.headers.get("content-type") || "";

    // 1. JSON Base64 response
    if (contentType.includes("application/json")) {
      const data = await response.json();
      const imageUrl = data.image?.startsWith("data:")
        ? data.image
        : `data:image/jpeg;base64,${data.image}`;

      let resultBlob: Blob;
      try {
        const blobRes = await fetch(imageUrl);
        resultBlob = await blobRes.blob();
      } catch {
        resultBlob = new Blob([], { type: "image/jpeg" });
      }

      return {
        blob: resultBlob,
        imageUrl,
        processingTimeMs: data.processing_time_ms,
      };
    }

    // 2. Binary JPEG response
    const timingHeader = response.headers.get("X-Processing-Time-Ms");
    const processingTimeMs = timingHeader
      ? parseInt(timingHeader, 10)
      : undefined;

    const resultBlob = await response.blob();
    const imageUrl = URL.createObjectURL(resultBlob);

    return {
      blob: resultBlob,
      imageUrl,
      processingTimeMs,
    };
  } catch (error: any) {
    throw new Error(
      error?.message ||
        "Could not connect to the ProductShot processing server. Please try again."
    );
  }
}

export async function checkBackendHealth(): Promise<{ online: boolean; model?: string }> {
  try {
    const res = await fetch(getEndpoint("/api/health"), {
      method: "GET",
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      const data = await res.json();
      return { online: true, model: data.model };
    }
  } catch {
    return { online: false };
  }

  return { online: false };
}
