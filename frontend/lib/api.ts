/**
 * Shared API utilities for Next.js API routes.
 */

import { NextResponse } from "next/server";

/**
 * Get the backend URL from environment variables or default to localhost.
 */
export function getBackendUrl(): string {
  return process.env.BACKEND_URL || "http://localhost:8000";
}


/**
 * Handle fetch errors and return appropriate NextResponse.
 */
export function handleFetchError(error: unknown): NextResponse {
  const errorMessage = error instanceof Error ? error.message : String(error);
  return NextResponse.json(
    { 
      error: "Failed to connect to backend", 
      detail: errorMessage 
    },
    { status: 500 }
  );
}

/**
 * Parse error response from backend.
 * Attempts to extract error details from various response formats.
 */
export async function parseErrorResponse(response: Response): Promise<Record<string, unknown>> {
  try {
    return (await response.json()) as Record<string, unknown>;
  } catch {
    const errorText = await response.text();
    return { 
      detail: errorText || `Backend error: ${response.status}` 
    };
  }
}

