import { NextRequest, NextResponse } from "next/server";

const API_BACKEND = process.env.API_BACKEND_URL || "http://31.97.47.190:8001";

async function proxyRequest(req: NextRequest, { params }: { params: { path: string[] } }) {
  const path = params.path.join("/");
  const url = `${API_BACKEND}/api/${path}${req.nextUrl.search}`;

  const headers: Record<string, string> = {
    "Content-Type": req.headers.get("content-type") || "application/json",
  };

  const auth = req.headers.get("authorization");
  if (auth) headers["Authorization"] = auth;

  const fetchOptions: RequestInit = {
    method: req.method,
    headers,
  };

  if (req.method !== "GET" && req.method !== "HEAD") {
    fetchOptions.body = await req.text();
  }

  try {
    const response = await fetch(url, fetchOptions);
    const contentType = response.headers.get("content-type") || "";

    if (
      contentType.includes("application/pdf") ||
      contentType.includes("spreadsheetml") ||
      contentType.includes("octet-stream")
    ) {
      const buffer = await response.arrayBuffer();
      return new NextResponse(buffer, {
        status: response.status,
        headers: {
          "Content-Type": contentType,
          "Content-Disposition": response.headers.get("content-disposition") || "",
        },
      });
    }

    const data = await response.text();
    return new NextResponse(data, {
      status: response.status,
      headers: { "Content-Type": contentType },
    });
  } catch {
    return NextResponse.json({ detail: "Backend unavailable" }, { status: 502 });
  }
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PATCH = proxyRequest;
export const PUT = proxyRequest;
export const DELETE = proxyRequest;
