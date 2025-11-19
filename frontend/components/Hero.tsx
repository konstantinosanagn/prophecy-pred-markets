"use client";

import React from "react";


export default function Hero() {
  return (
    <section className="relative overflow-hidden bg-white">
      {/* grid background */}
      <div className="pointer-events-none absolute inset-0 -z-10 bg-grid opacity-40" />

      {/* optional noise layer to make it feel less flat */}
      <div className="pointer-events-none absolute inset-0 -z-10 bg-noise opacity-20" />

      {/* content */}
      <div className="mx-auto max-w-6xl px-4 py-20">
        <div className="grid items-center gap-10 md:grid-cols-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-neutral-500">
              Web data, reimagined
            </p>
            <h1 className="mt-4 text-4xl font-semibold tracking-tight text-neutral-900 md:text-5xl">
              Turn the web into clean, structured data.
            </h1>
            <p className="mt-4 text-sm text-neutral-600 md:text-base">
              Crawl, clean, and search the web with one API — built for AI-native apps.
            </p>
            <div className="mt-6 flex flex-wrap items-center gap-3">
              <button className="rounded-full bg-orange-500 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-orange-600">
                Get API key
              </button>
              <button className="text-sm text-neutral-600 transition hover:text-neutral-900">
                View docs →
              </button>
            </div>
          </div>

          <div className="relative">
            <div className="rounded-2xl border border-neutral-200/80 bg-white/80 p-4 shadow-sm backdrop-blur-sm">
              {/* placeholder for code block / UI mock */}
              <div className="h-48 rounded-xl border border-dashed border-neutral-200/80" />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}


