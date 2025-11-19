"use client";

import React, { PropsWithChildren, useCallback, useEffect, useRef, useState } from "react";
import GridAndNoise from "./background/GridAndNoise";
import TopNav from "./background/TopNav";
import UrlInputBar from "./background/UrlInputBar";
import MarketSelection from "./background/MarketSelection";
import ConfigurationPanel, {
  AnalysisConfiguration,
  DEFAULT_CONFIG,
} from "./background/ConfigurationPanel";
import RecentSessions from "./background/RecentSessions";
import { RecentRun } from "./background/RecentMarketCard";
import { MarketSnapshotCard } from "../components/MarketSnapshotCard";
import { NewsCard } from "../components/NewsCard";
import SignalCard from "./background/SignalCard";
import ReportCard from "./background/ReportCard";
import EmptyPrompt from "./background/EmptyPrompt";
import { MarketSnapshotSkeleton } from "../components/skeletons/MarketSnapshotSkeleton";
import { NewsSkeleton } from "../components/skeletons/NewsSkeleton";
import { SignalSkeleton } from "../components/skeletons/SignalSkeleton";
import { ReportSkeleton } from "../components/skeletons/ReportSkeleton";
import { logger } from "../lib/logger";

export default function Background(_props: PropsWithChildren): React.JSX.Element {
  void _props; // Props are unused in this component
  const [isFocused, setIsFocused] = useState(false);
  const [url, setUrl] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [configuration, setConfiguration] = useState<AnalysisConfiguration>(DEFAULT_CONFIG);
  interface NewsArticle {
    title?: string;
    source?: string;
    url?: string;
    published_at?: string;
    snippet?: string;
    sentiment?: "bullish" | "bearish" | "neutral";
  }

  interface NewsContext {
    articles?: NewsArticle[];
    summary?: string;
    combined_summary?: string;
    tavily_queries?: string[];
    queries?: Array<{
      name?: string;
      query?: string;
      results?: NewsArticle[];
      answer?: string;
    }>;
  }

  interface AnalysisResults {
    market_snapshot?: {
      question?: string;
      url?: string;
      endDate?: string;
      end_date?: string;
      group_item_title?: string;
      groupItemTitle?: string;
      yes_price?: number;
      no_price?: number;
      volume?: string | number;
      volume24hr?: number;
      liquidity?: string | number;
      comment_count?: number;
      commentCount?: number;
      event_comment_count?: number;
      eventCommentCount?: number;
      series_comment_count?: number;
      seriesCommentCount?: number;
      best_bid?: number;
      bestBid?: number;
      best_ask?: number;
      bestAsk?: number;
      order_book?: { bids?: Array<{ price?: number; size?: number }>; asks?: Array<{ price?: number; size?: number }> };
      orderBook?: { bids?: Array<{ price?: number; size?: number }>; asks?: Array<{ price?: number; size?: number }> };
    };
    event_context?: {
      title?: string;
      url?: string;
      volume24hr?: number;
      commentCount?: number;
      seriesCommentCount?: number;
    };
    news_context?: NewsContext;
    signal?: {
      direction?: string;
      model_prob?: number;
      model_prob_abs?: number;
      confidence?: string;
      rationale?: string;
    };
    decision?: {
      action?: string;
      edge_pct?: number;
      toy_kelly_fraction?: number;
      notes?: string;
    };
    report?: string | { title?: string; markdown?: string } | Record<string, unknown>;
    market_options?: Array<{ slug?: string; question?: string; id?: string }>;
    requires_market_selection?: boolean;
  }

  const [results, setResults] = useState<AnalysisResults | null>(null);
  const [lastSortedMarketOptions, setLastSortedMarketOptions] = useState<
    { slug: string; question: string }[]
  >([]);
  const [selectedMarketSlug, setSelectedMarketSlug] = useState<string | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<{
    market?: string;
    news?: string;
    signal?: string;
    report?: string;
  } | null>(null);
  const pollingRef = useRef<boolean>(false);
  const runIdRef = useRef<string | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [recentSessionsRefreshTrigger, setRecentSessionsRefreshTrigger] = useState(0);

  const mapMarketOptions = useCallback(
    (
      options: Array<{ slug?: string; question?: string; id?: string; title?: string }> | undefined | null
    ) => {
      if (!Array.isArray(options)) {
        return [];
      }
      return options
        .map((option) => {
          const slug = option?.slug ?? option?.id;
          if (!slug) {
            return null;
          }
          return {
            slug: String(slug),
            question: option?.question || option?.title || String(slug),
          };
        })
        .filter(
          (
            option,
          ): option is {
            slug: string;
            question: string;
          } => Boolean(option)
        );
    },
    [],
  );

  // Handler to load a saved run from RecentSessions
  const handleRunSelect = useCallback(async (run: RecentRun) => {
    const runIdToLoad = run.run_id || run._id;
    if (!runIdToLoad) {
      logger.error("No run_id or _id in selected run:", run);
      return;
    }

    setSelectedRunId(String(runIdToLoad));
    setIsSubmitting(false);
    pollingRef.current = false;
    setRunId(null);
    runIdRef.current = null;

    try {
      const response = await fetch(`/api/run/${encodeURIComponent(runIdToLoad)}`);
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || errorData.error || "Failed to load saved run",
        );
      }

      const data = await response.json();
      const savedRun = data.run;

      if (!savedRun) {
        throw new Error("No run data in response");
      }

      // Map saved run to AnalysisResults format
      const mappedResults: AnalysisResults = {
        market_snapshot: savedRun.market_snapshot || {},
        event_context: savedRun.event_context || {},
        news_context: savedRun.news_context || {},
        signal: savedRun.signal || {},
        decision: savedRun.decision || {},
        report: savedRun.report || {},
        requires_market_selection: false,
      };

      // Set run status based on saved status
      const savedStatus = savedRun.status || {};
      setRunStatus({
        market: savedStatus.market === "done" ? "done" : "pending",
        news: savedStatus.news === "done" ? "done" : "pending",
        signal: savedStatus.signal === "done" ? "done" : "pending",
        report: savedStatus.report === "done" ? "done" : "pending",
      });

      setResults(mappedResults);
      setUrl(savedRun.polymarket_url || "");

      if (savedRun.market_snapshot?.slug) {
        setSelectedMarketSlug(savedRun.market_snapshot.slug);
      }
    } catch (error) {
      logger.error("Error loading saved run:", error);
      alert(error instanceof Error ? error.message : "Failed to load saved run");
    }
  }, []);

  const handleSubmit = async () => {
    // Prevent duplicate submissions
    if (!url.trim() || isSubmitting) {
      return;
    }
    
    // Stop any existing polling before starting a new submission
    pollingRef.current = false;
    setIsSubmitting(true);
    setResults(null);
    setRunStatus(null);
    setRunId(null);
    setSelectedRunId(null); // Clear selected run when starting new analysis
    runIdRef.current = null;
    pollingRef.current = false;
    
    try {
      const requestBody = {
        market_url: url.trim(),
        configuration: {
          use_tavily_prompt_agent: configuration.useTavilyPromptAgent,
          use_news_summary_agent: configuration.useNewsSummaryAgent,
          max_articles: configuration.maxArticles,
          max_articles_per_query: configuration.maxArticlesPerQuery,
          min_confidence: configuration.minConfidence,
          enable_sentiment_analysis: configuration.enableSentimentAnalysis,
        },
      };
      const response = await fetch("/api/analyze/start", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: "Unknown error" }));
        const errorMessage = errorData.detail || errorData.error || errorData.details || `HTTP error! status: ${response.status}`;
        throw new Error(errorMessage);
      }

      const data = await response.json();
      
      // Validate run_id exists - backend returns { "run_id": "run-..." }
      if (!data.run_id) {
        logger.error("No run_id in response:", data);
        throw new Error("Backend did not return run_id");
      }
      
      const newRunId = String(data.run_id).trim();
      if (!newRunId || newRunId === 'undefined' || newRunId === 'null') {
        logger.error("Invalid run_id:", newRunId);
        throw new Error("Invalid run_id received from backend");
      }
      
      // Set run_id to start polling - must use data.run_id (snake_case)
      // Set ref first for immediate access, then state for React updates
      runIdRef.current = newRunId;
      pollingRef.current = true;
      setRunId(newRunId);
      
      // Initialize with empty results to show skeletons
      setResults({
        market_snapshot: {},
        event_context: {},
        news_context: {},
        signal: {},
        decision: {},
        report: {},
      });
      setRunStatus({
        market: "pending",
        news: "pending",
        signal: "pending",
        report: "pending",
      });
    } catch (error) {
      logger.error("Error submitting URL:", error);
      const errorMessage = error instanceof Error ? error.message : "Failed to start analysis. Please try again.";
      // TODO: Replace with toast notification system
      // For now, using a more user-friendly approach than alert()
      if (typeof window !== 'undefined') {
        // In a production app, this would use a toast library like react-hot-toast
        // For MVP, we'll log and show a simple message
        window.alert(errorMessage);
      }
      setIsSubmitting(false);
    }
  };

  const handleSelectMarket = async (marketSlug: string) => {
    try {
      setIsSubmitting(true);
      setResults(null);
      setRunStatus(null);
      setRunId(null);
      setSelectedRunId(null); // Clear selected run when starting new analysis
      runIdRef.current = null;
      pollingRef.current = false;
      
      const body = {
        market_url: url.trim(),
        selected_market_slug: marketSlug,
        configuration: {
          use_tavily_prompt_agent: configuration.useTavilyPromptAgent,
          use_news_summary_agent: configuration.useNewsSummaryAgent,
          max_articles: configuration.maxArticles,
          max_articles_per_query: configuration.maxArticlesPerQuery,
          min_confidence: configuration.minConfidence,
          enable_sentiment_analysis: configuration.enableSentimentAnalysis,
        },
      };
      const response = await fetch("/api/analyze/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: "Unknown error" }));
        const errorMessage = errorData.detail || errorData.error || errorData.details || `HTTP error! status: ${response.status}`;
        throw new Error(errorMessage);
      }
      const data = await response.json();
      
      // Validate run_id exists
      if (!data.run_id) {
        logger.error("No run_id in response:", data);
        throw new Error("Server did not return a run_id");
      }
      
      const newRunId = String(data.run_id).trim();
      if (!newRunId || newRunId === 'undefined' || newRunId === 'null') {
        logger.error("Invalid run_id:", newRunId);
        throw new Error("Invalid run_id received from backend");
      }
      
      // Set run_id to start polling
      // Set ref first for immediate access, then state for React updates
      runIdRef.current = newRunId;
      pollingRef.current = true;
      setRunId(newRunId);
      
      // Initialize with empty results to show skeletons
      setResults({
        market_snapshot: {},
        event_context: {},
        news_context: {},
        signal: {},
        decision: {},
        report: {},
      });
      setRunStatus({
        market: "pending",
        news: "pending",
        signal: "pending",
        report: "pending",
      });
    } catch (e) {
      logger.error("Error selecting market:", e);
      const errorMessage = e instanceof Error ? e.message : "Failed to analyze selected market. Please try again.";
      // TODO: Replace with toast notification system
      if (typeof window !== 'undefined') {
        window.alert(errorMessage);
      }
      setIsSubmitting(false);
    }
  };

  const handleSortedOptionsChange = useCallback(
    (options: Array<{ slug?: string; question?: string; id?: string; title?: string }>) => {
      const mapped = mapMarketOptions(options);
      // Only update if the options have actually changed (prevent infinite loops)
      setLastSortedMarketOptions((prev) => {
        if (prev.length === mapped.length && 
            prev.every((p, i) => p.slug === mapped[i]?.slug && p.question === mapped[i]?.question)) {
          return prev; // No change, return previous to prevent re-render
        }
        return mapped;
      });
    },
    [mapMarketOptions],
  );
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSubmit();
    }
  };

  const humanizeClosesIn = (isoDate?: string) => {
    if (!isoDate) return "—";
    const end = new Date(isoDate).getTime();
    if (Number.isNaN(end)) return "—";
    const now = Date.now();
    const diffMs = Math.max(0, end - now);
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    if (diffDays >= 1) return `${diffDays} day${diffDays === 1 ? "" : "s"}`;
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    if (diffHours >= 1) return `${diffHours} hr${diffHours === 1 ? "" : "s"}`;
    const diffMins = Math.floor(diffMs / (1000 * 60));
    return `${diffMins} min`;
  };

  // Polling effect for phased analysis
  useEffect(() => {
    // Guard: don't poll if runId is falsy (null, undefined, empty string)
    // This prevents GET /api/run/undefined
    
    // Use ref as fallback if state hasn't updated yet (React state updates are async)
    const effectiveRunId = runId || runIdRef.current;
    
    // No run in progress yet – silently skip (expected on initial mount)
    if (!effectiveRunId) {
      return;
    }
    
    // If we have a value but it's not a string, skip
    if (typeof effectiveRunId !== "string") {
      return;
    }
    
    // Prevent multiple polling instances for the same runId
    if (!pollingRef.current) {
      return;
    }
    
    const trimmedRunId = effectiveRunId.trim();
    if (trimmedRunId === '' || trimmedRunId === 'undefined' || trimmedRunId === 'null') {
      return;
    }

    // Capture runId in a const to avoid closure issues
    const currentRunId = trimmedRunId;
    let cancelled = false;

    async function poll() {
      if (cancelled || !pollingRef.current) {
        return;
      }

      // Use the captured runId from the effect closure - double-check it's valid
      const runIdToUse = currentRunId;
      if (!runIdToUse || typeof runIdToUse !== 'string' || runIdToUse.trim() === '' || runIdToUse === 'undefined' || runIdToUse === 'null') {
        logger.error("runId is invalid in poll function!", runIdToUse);
        return;
      }

      try {
        const response = await fetch(`/api/run/${runIdToUse}`);
        if (!response.ok) {
          if (response.status === 404) {
            // Run not found yet, keep polling
            window.setTimeout(poll, 1500);
            return;
          }
          // For 500 errors, try to get more details and retry
          if (response.status === 500) {
            // Try to parse error details (for potential future use in logging)
            try {
              const errorData = await response.json();
              const _errorDetail = errorData.detail || errorData.error || "Internal server error";
              // Could log _errorDetail here if needed
            } catch {
              // Ignore JSON parse errors
            }
            // Retry after a longer delay for server errors
            window.setTimeout(poll, 3000);
            return;
          }
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        // Backend returns { run: { ... } } - must read data.run
        const run = data.run;

        if (!run) {
          // Run not found yet, keep polling
          if (!cancelled) {
            window.setTimeout(poll, 1500);
          }
          return;
        }

        if (!cancelled) {
          // Update status from run.status
          if (run.status) {
            setRunStatus(run.status);
          }

          // Update results as phases complete
          setResults((prevResults) => {
            if (!prevResults) {
              // Initialize with empty structure if needed
              return {
                market_snapshot: {},
                event_context: {},
                news_context: {},
                signal: {},
                decision: {},
                report: {},
              };
            }
            
            const updatedResults: AnalysisResults = { ...prevResults };
            
            if (run.status?.market === "done") {
              if (run.market_snapshot && Object.keys(run.market_snapshot).length > 0) {
                updatedResults.market_snapshot = run.market_snapshot;
              }
              if (run.event_context) {
                updatedResults.event_context = run.event_context;
              }
              if (run.market_options && Array.isArray(run.market_options) && run.market_options.length > 0) {
                updatedResults.market_options = run.market_options;
                // Only require market selection if market_snapshot is empty or missing
                if (!run.market_snapshot || Object.keys(run.market_snapshot).length === 0) {
                  updatedResults.requires_market_selection = true;
                } else {
                  updatedResults.requires_market_selection = false;
                }
              }
            }
            
            if (run.status?.news === "done" && run.news_context) {
              updatedResults.news_context = run.news_context;
            }
            
            if (run.status?.signal === "done" && run.signal) {
              updatedResults.signal = run.signal;
              updatedResults.decision = run.decision || updatedResults.decision;
            }
            
            if (run.status?.report === "done" && run.report) {
              updatedResults.report = run.report;
            }

            return updatedResults;
          });

          // Check if market selection is required
          const requiresMarketSelection =
            run.market_options &&
            Array.isArray(run.market_options) &&
            run.market_options.length > 0 &&
            (!run.market_snapshot || Object.keys(run.market_snapshot).length === 0);

          if (requiresMarketSelection) {
            // Set requires_market_selection in results state
            setResults((prevResults) => {
              if (!prevResults) return prevResults;
              return {
                ...prevResults,
                requires_market_selection: true,
                market_options: run.market_options,
              };
            });
            // Market selection required - stop polling and wait for user selection
            pollingRef.current = false;
            setIsSubmitting(false);
            return;
          }

          // Check if all phases are done or errored
          const status = run.status || {};
          const phases = Object.values(status);
          const allDoneOrError =
            phases.length > 0 &&
            phases.every((s) => s === "done" || s === "error");

          if (allDoneOrError) {
            pollingRef.current = false;
            setIsSubmitting(false);
            if (run.market_snapshot?.slug) {
              setSelectedMarketSlug(run.market_snapshot.slug);
            }
            // Refresh recent sessions when analysis completes
            setRecentSessionsRefreshTrigger((prev) => prev + 1);
          } else {
            // Schedule next poll
            window.setTimeout(poll, 1500);
          }
        }
      } catch (error) {
        logger.error("Error polling run status:", error);
        if (!cancelled && pollingRef.current) {
          // Log network errors during polling (don't show alert to avoid spam)
          if (error instanceof Error && error.message.includes("Network error")) {
            logger.warn("Network error while polling:", error.message);
          }
          // Retry after longer delay on error
          window.setTimeout(poll, 2500);
        }
      }
    }

    poll();

    return () => {
      cancelled = true;
    };
  }, [runId]);

  // Map backend news articles to NewsCard format
  const mapNewsArticles = useCallback((newsContext?: NewsContext) => {
    if (!newsContext?.articles || !Array.isArray(newsContext.articles) || newsContext.articles.length === 0) {
      return [];
    }

    return newsContext.articles.map((article) => ({
      title: article.title || "Untitled",
      source: article.source || "Unknown source",
      publishedAt: article.published_at || undefined,
      url: article.url || undefined,
      summary: article.snippet || undefined,
      sentiment: article.sentiment || "neutral", // Include sentiment from backend
    }));
  }, []);

  return (
    <section id="app-root" className="relative min-h-screen overflow-hidden bg-white text-neutral-900">
      {/* Soft grid + noise background, hero-style */}
      <GridAndNoise />

      {/* Tailwind CSS grid: 2 rows × 3 columns (2-8-2).
          - Row 1 (auto) has three cells; each gets top & bottom borders.
          - Row 2 (1fr) fills remaining height.
          - Columns have left/right borders so vertical lines span both rows. */}
      <div id="app-grid" className="grid min-h-screen w-full grid-rows-[auto,1fr] grid-cols-[minmax(0,2fr)_minmax(0,8fr)_minmax(0,2fr)]">
        {/* Row 1, Col 1 */}
        <div className="border-y border-l border-neutral-300 bg-white/90">
          <div className="h-10" />
        </div>

        {/* Row 1, Col 2 (navbar cell) */}
        <TopNav />

        {/* Row 1, Col 3 */}
        <div className="border-y border-r border-neutral-300 bg-white/90">
          <div className="h-10" />
        </div>

        {/* Row 2, Col 1 - Recent Sessions */}
        <RecentSessions
          onRunSelect={handleRunSelect}
          activeRunId={selectedRunId || runId}
          refreshTrigger={recentSessionsRefreshTrigger}
        />

        {/* Row 2, Col 2 */}
        <div className="border-x border-neutral-300 bg-white/90 flex flex-col">
          {/* Row 1: Input field in a grid */}
          <div id="input-row" className="grid grid-cols-[1fr_2fr_1fr] border-b border-neutral-300">
            <div className="p-4">{/* Cell 1 */}</div>
            <div className="p-4 border-x border-neutral-300" id="url-input-cell">
              <UrlInputBar
                url={url}
                isSubmitting={isSubmitting}
                isFocused={isFocused}
                onChange={setUrl}
                onSubmit={handleSubmit}
                onKeyDown={handleKeyDown}
                onFocusChange={setIsFocused}
              />
            </div>
            <div className="p-4">{/* Cell 3 */}</div>
          </div>

          {/* Row 2: Analysis results (or selection UI) */}
          <div className="p-4" id="results-pane">
            {results ? (
              <>
                {/* Show market selection if required, otherwise show analysis results */}
                {results.requires_market_selection && 
                 (!results.market_snapshot || Object.keys(results.market_snapshot).length === 0) &&
                 results.market_options && 
                 results.market_options.length > 0 ? (
                  <MarketSelection
                    options={results.market_options.filter((opt): opt is { slug: string; question?: string; id?: string } => !!opt.slug)}
                    eventContext={results.event_context}
                    isSubmitting={isSubmitting}
                    onSelect={handleSelectMarket}
                    onSortedOptionsChange={handleSortedOptionsChange}
                  />
                ) : (
                  <div>
                    {/* Market Snapshot - show skeleton if pending, card if done */}
                    {(() => {
                      const shouldShowMarketCard = runStatus?.market === "done" && results.market_snapshot && Object.keys(results.market_snapshot).length > 0;
                      const shouldShowMarketSkeleton = runStatus?.market === "pending" || runStatus?.market === undefined;
                      
                      if (shouldShowMarketCard && results.market_snapshot) {
                        return (
                      <div className="mb-6">
                      <MarketSnapshotCard
                    eventTitle={results.event_context?.title || results.market_snapshot.question || "Event"}
                    groupItemTitle={results.market_snapshot.group_item_title || results.market_snapshot.groupItemTitle}
                    polymarketUrl={results.market_snapshot.url || results.event_context?.url || url || "#"}
                    closesIn={humanizeClosesIn(results.market_snapshot.endDate || results.market_snapshot.end_date)}
                    endDate={results.market_snapshot.endDate || results.market_snapshot.end_date}
                    question={results.market_snapshot.question}
                    previousMarkets={
                      lastSortedMarketOptions.length > 0
                        ? lastSortedMarketOptions
                        : mapMarketOptions(results.market_options)
                    }
                    activeMarketSlug={selectedMarketSlug ?? undefined}
                    onMarketSelect={handleSelectMarket}
                    yesPrice={results.market_snapshot.yes_price ?? 0}
                    noPrice={results.market_snapshot.no_price ?? 0}
                    marketVolume={Number(results.market_snapshot.volume ?? 0)}
                    volume24h={results.market_snapshot.volume24hr || results.event_context?.volume24hr}
                    liquidity={Number(results.market_snapshot.liquidity ?? 0)}
                    commentCount={results.event_context?.commentCount ?? results.market_snapshot?.comment_count ?? results.market_snapshot?.commentCount}
                    eventCommentCount={
                      results.event_context?.commentCount ??
                      results.market_snapshot?.event_comment_count ??
                      results.market_snapshot?.eventCommentCount
                    }
                    seriesCommentCount={
                      results.event_context?.seriesCommentCount ??
                      results.market_snapshot?.series_comment_count ??
                      results.market_snapshot?.seriesCommentCount
                    }
                    bestBid={results.market_snapshot.best_bid ?? results.market_snapshot.bestBid}
                    bestAsk={results.market_snapshot.best_ask ?? results.market_snapshot.bestAsk}
                    bids={(results.market_snapshot.order_book?.bids || results.market_snapshot.orderBook?.bids || []).map((b: { price?: number; size?: number }) => ({
                      price: Number(b.price ?? 0),
                      size: Number(b.size ?? 0),
                    }))}
                    asks={(results.market_snapshot.order_book?.asks || results.market_snapshot.orderBook?.asks || []).map((a: { price?: number; size?: number }) => ({
                      price: Number(a.price ?? 0),
                      size: Number(a.size ?? 0),
                    }))}
                  />
                  </div>
                    );
                  } else if (shouldShowMarketSkeleton) {
                    return (
                      <div className="mb-6">
                        <MarketSnapshotSkeleton />
                      </div>
                    );
                  }
                  return null;
                })()}

                    {/* News - show skeleton if pending, card if done */}
                    {runStatus?.news === "done" && results.news_context && results.news_context.articles && results.news_context.articles.length > 0 ? (
                      <div className="mb-6">
                        <NewsCard
                          heading="Market News & Analysis"
                          highlights={mapNewsArticles(results.news_context)}
                          isLoading={false}
                          newsSummary={results.news_context.summary}
                          combinedSummary={results.news_context.combined_summary}
                          onItemClick={(item) => {
                            if (item.url) {
                              window.open(item.url, "_blank", "noopener,noreferrer");
                            }
                          }}
                        />
                      </div>
                    ) : runStatus?.news === "pending" || runStatus?.news === undefined ? (
                      <div className="mb-6">
                        <NewsSkeleton />
                      </div>
                    ) : null}

                    {/* Signal - show skeleton if pending, card if done */}
                    {runStatus?.signal === "done" && results.signal && Object.keys(results.signal).length > 0 ? (
                      <SignalCard signal={results.signal} />
                    ) : runStatus?.signal === "pending" || runStatus?.signal === undefined ? (
                      <SignalSkeleton />
                    ) : null}

                    {/* Report - show skeleton if pending, card if done */}
                    {runStatus?.report === "done" && results.report ? (
                      <ReportCard report={results.report} eventContext={results.event_context} />
                    ) : runStatus?.report === "pending" || runStatus?.report === undefined ? (
                      <ReportSkeleton />
                    ) : null}
                  </div>
                )}
              </>
            ) : (
              <EmptyPrompt />
            )}
          </div>
        </div>

        {/* Row 2, Col 3 - Configuration Panel */}
        <ConfigurationPanel
          config={configuration}
          onChange={setConfiguration}
          isSubmitting={isSubmitting}
        />
      </div>
    </section>
  );
}

