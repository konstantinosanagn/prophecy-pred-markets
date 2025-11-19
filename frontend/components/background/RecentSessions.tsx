"use client";

import React, { useEffect, useState, useRef } from "react";
import { RefreshCw, History } from "lucide-react";
import clsx from "clsx";
import RecentMarketCard, { RecentRun } from "./RecentMarketCard";

interface RecentSessionsProps {
  onRunSelect: (run: RecentRun) => void;
  activeRunId?: string;
  refreshTrigger?: number; // Increment this to trigger refresh
}

export default function RecentSessions({
  onRunSelect,
  activeRunId,
  refreshTrigger = 0,
}: RecentSessionsProps): React.JSX.Element {
  const [runs, setRuns] = useState<RecentRun[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const fetchRecentRuns = async () => {
    // Cancel any pending requests
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new AbortController for this request
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/runs/recent?limit=20", {
        signal: abortController.signal,
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || errorData.error || "Failed to fetch recent runs",
        );
      }
      const data = await response.json();
      // Only update state if request wasn't aborted
      if (!abortController.signal.aborted) {
        setRuns(data.runs || []);
      }
    } catch (err) {
      // Ignore abort errors
      if (err instanceof Error && err.name === "AbortError") {
        return;
      }
      // Only set error if request wasn't aborted
      if (!abortController.signal.aborted) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to load recent sessions";
        setError(errorMessage);
        console.error("Error fetching recent runs:", err);
      }
    } finally {
      // Only update loading state if request wasn't aborted
      if (!abortController.signal.aborted) {
        setIsLoading(false);
      }
    }
  };

  useEffect(() => {
    fetchRecentRuns();
    // Cleanup: abort request on unmount or when refreshTrigger changes
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [refreshTrigger]);

  return (
    <div
      id="recent-sessions"
      className="h-full flex flex-col bg-white/90 border-0"
    >
      {/* Header */}
      <div className="p-4 bg-white/90">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold text-neutral-800 flex items-center gap-2">
            <History className="w-5 h-5" />
            Recent Sessions
          </h2>
          <button
            onClick={fetchRecentRuns}
            disabled={isLoading}
            className="p-1.5 rounded-md hover:bg-neutral-200 transition-colors disabled:opacity-50"
            title="Refresh recent sessions"
          >
            <RefreshCw
              className={clsx("w-4 h-4 text-neutral-600", isLoading && "animate-spin")}
            />
          </button>
        </div>
        <p className="text-xs text-neutral-500">
          Click a card to view analysis
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 border-0">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="text-sm text-neutral-500">Loading...</div>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-8">
            <p className="text-sm text-red-600 mb-2">{error}</p>
            <button
              onClick={fetchRecentRuns}
              className="text-xs text-indigo-600 hover:text-indigo-700 underline"
            >
              Try again
            </button>
          </div>
        ) : runs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <History className="w-12 h-12 text-neutral-300 mb-3" />
            <p className="text-sm text-neutral-500 mb-1">No recent sessions</p>
            <p className="text-xs text-neutral-400">
              Run an analysis to see it here
            </p>
          </div>
        ) : (
          <div className="space-y-3 border-0">
            {runs.map((run) => {
              const runId = run.run_id || run._id;
              return (
                <RecentMarketCard
                  key={runId}
                  run={run}
                  onClick={onRunSelect}
                  isActive={activeRunId === runId}
                />
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

