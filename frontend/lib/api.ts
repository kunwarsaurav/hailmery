/**
 * API service for ProductShot backend
 */

export interface ProcessResult {
  blob: Blob;
  imageUrl: string;
  processingTimeMs?: number;
}

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");

function getEndpoint(path: string, queryString: string = ""): string {
  return `${API_BASE}${path}${queryString}`;
}

export async function processProductPhoto(
  photoBlob: Blob,
  fileName: string = "captured-product.jpg",
  model?: string,
  shadow: boolean = true,
  enhance: boolean = true
): Promise<ProcessResult> {
  const formData = new FormData();
  formData.append("file", photoBlob, fileName);

  const params = new URLSearchParams();
  if (model) params.set("model", model);
  if (shadow) params.set("shadow", "true");
  if (!enhance) params.set("enhance", "false");
  const queryString = params.toString() ? `?${params.toString()}` : "";

  const endpoint = getEndpoint("/api/process", queryString);

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      let errorMessage =
        "Couldn't process this image. Try taking another photo with the product clearly visible.";
      try {
        const errorData = await response.json();
        if (errorData?.detail) {
          errorMessage = errorData.detail;
        }
      } catch {
        // Keep generic message
      }
      throw new Error(errorMessage);
    }

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
    if (
      error.message &&
      !error.message.includes("fetch") &&
      !error.message.includes("network") &&
      !error.message.includes("Failed to fetch")
    ) {
      throw error;
    }
    throw new Error(
      error?.message ||
        "Could not connect to the ProductShot processing backend. Ensure the backend service is running."
    );
  }
}

export async function checkBackendHealth(): Promise<{ online: boolean; model?: string }> {
  try {
    const res = await fetch(getEndpoint("/api/health"), {
      method: "GET",
      signal: AbortSignal.timeout(3000),
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
