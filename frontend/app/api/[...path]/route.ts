import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/**
 * Returns the base URL for the backend service.
 * In Vercel Services, BACKEND_URL is dynamically injected at runtime via service binding.
 */
function getBackendBaseUrl(): string {
  if (process.env.BACKEND_URL) {
    return process.env.BACKEND_URL.replace(/\/$/, "");
  }
  // Local development fallback
  return "http://127.0.0.1:8001";
}

async function forwardRequest(request: NextRequest) {
  const backendBase = getBackendBaseUrl();
  const targetUrl = new URL(request.nextUrl.pathname + request.nextUrl.search, backendBase);

  const headers = new Headers(request.headers);
  headers.delete("host");

  const method = request.method;
  let body: BodyInit | undefined = undefined;

  if (method !== "GET" && method !== "HEAD") {
    body = await request.arrayBuffer();
  }

  try {
    const response = await fetch(targetUrl, {
      method,
      headers,
      body,
    });

    const responseHeaders = new Headers(response.headers);
    return new NextResponse(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (error: any) {
    // If 8001 failed in local dev, try 8000 as a fallback
    if (!process.env.BACKEND_URL && backendBase.includes("8001")) {
      try {
        const fallbackUrl = new URL(
          request.nextUrl.pathname + request.nextUrl.search,
          "http://127.0.0.1:8000"
        );
        const fallbackRes = await fetch(fallbackUrl, { method, headers, body });
        return new NextResponse(fallbackRes.body, {
          status: fallbackRes.status,
          statusText: fallbackRes.statusText,
          headers: new Headers(fallbackRes.headers),
        });
      } catch {
        // Fall through
      }
    }

    return NextResponse.json(
      {
        detail: `Failed to connect to backend service at ${backendBase}: ${
          error?.message || error
        }`,
      },
      { status: 502 }
    );
  }
}

export async function GET(request: NextRequest) {
  return forwardRequest(request);
}

export async function POST(request: NextRequest) {
  return forwardRequest(request);
}

export async function PUT(request: NextRequest) {
  return forwardRequest(request);
}

export async function DELETE(request: NextRequest) {
  return forwardRequest(request);
}

export async function OPTIONS(request: NextRequest) {
  return forwardRequest(request);
}
