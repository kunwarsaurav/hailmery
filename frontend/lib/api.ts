/**
 * API service for ProductShot backend
 */

export interface ProcessResult {
  blob: Blob;
  imageUrl: string;
  processingTimeMs?: number;
}

const CANDIDATE_HOSTS = [
  process.env.NEXT_PUBLIC_API_URL,
  "http://127.0.0.1:8001",
  "http://127.0.0.1:8000",
  "http://localhost:8001",
  "http://localhost:8000",
].filter(Boolean) as string[];

export async function processProductPhoto(
  photoBlob: Blob,
  fileName: string = "captured-product.jpg"
): Promise<ProcessResult> {
  const formData = new FormData();
  formData.append("file", photoBlob, fileName);

  // Probe direct backend endpoints (8001, 8000) then local proxy
  const endpoints = [
    ...CANDIDATE_HOSTS.map((base) => `${base}/api/process`),
    "/api/process",
  ];

  let lastError: any = null;

  for (const endpoint of endpoints) {
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
      lastError = error;
      // If it was a non-network error (e.g. 400 validation error from backend), throw immediately
      if (
        error.message &&
        !error.message.includes("fetch") &&
        !error.message.includes("network") &&
        !error.message.includes("Failed to fetch")
      ) {
        throw error;
      }
    }
  }

  throw new Error(
    lastError?.message ||
      "Could not connect to the ProductShot processing backend. Ensure the backend server is running."
  );
}

export async function checkBackendHealth(): Promise<{ online: boolean; model?: string }> {
  for (const host of CANDIDATE_HOSTS) {
    try {
      const res = await fetch(`${host}/api/health`, {
        method: "GET",
        signal: AbortSignal.timeout(2000),
      });
      if (res.ok) {
        const data = await res.json();
        return { online: true, model: data.model };
      }
    } catch {
      // Continue to next host
    }
  }

  try {
    const resFallback = await fetch("/api/health", {
      method: "GET",
      signal: AbortSignal.timeout(2000),
    });
    if (resFallback.ok) {
      const data = await resFallback.json();
      return { online: true, model: data.model };
    }
  } catch {
    return { online: false };
  }

  return { online: false };
}
