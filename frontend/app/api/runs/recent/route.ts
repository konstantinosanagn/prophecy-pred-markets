import { NextRequest, NextResponse } from "next/server";

import { getBackendUrl, handleFetchError, parseErrorResponse } from "../../../../lib/api";
import { logger } from "../../../../lib/logger";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = searchParams.get("limit") || "20";

    const response = await fetch(
      `${getBackendUrl()}/api/runs/recent?limit=${encodeURIComponent(limit)}`,
      {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      },
    );

    if (!response.ok) {
      const errorData = await parseErrorResponse(response);
      return NextResponse.json(
        {
          error: `Backend error: ${response.status}`,
          detail:
            (errorData.detail as string) ||
            (errorData.error as string) ||
            (errorData.message as string) ||
            "Unknown error",
          details: errorData,
        },
        { status: response.status },
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    logger.error("Error proxying to backend:", error);
    return handleFetchError(error);
  }
}

