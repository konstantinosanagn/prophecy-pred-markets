"use client";

import type { ReactNode } from "react";
import type { Signal } from "../../types/signal";
import SignalPill from "../analysis/SignalPill";
import ThemeToggle from "./ThemeToggle";
import FlamingOrb from "../ui/FlamingOrb";

type Props = {
  urlInput: ReactNode;
  signal?: Signal | null;
};

export default function TopBar({ urlInput, signal }: Props) {
  return (
    <header
      className="flex items-center gap-5 px-7 border-b border-line bg-topbar-bg backdrop-blur-glass"
      style={{ height: 60 }}
    >
      {/* Logo */}
      <div className="flex items-center gap-2.5" style={{ width: 232 }}>
        <span
          className="flex items-center justify-center overflow-hidden"
          style={{ width: 30, height: 30 }}
        >
          <FlamingOrb size={0.3} />
        </span>
        <span className="text-lg font-semibold text-ink" style={{ letterSpacing: "-0.02em" }}>
          prophecy
          <span className="text-accent">.</span>
        </span>
      </div>

      {/* URL input centered in the viewport (mirrors the 232px logo column on the right) */}
      <div className="flex-1 flex justify-center min-w-0">
        <div className="w-full" style={{ maxWidth: 560 }}>
          {urlInput}
        </div>
      </div>

      {/* Right cluster — fixed width matches the logo column so the URL input centers in the viewport */}
      <div
        className="flex items-center justify-end gap-3 flex-shrink-0"
        style={{ width: 232 }}
      >
        <SignalPill signal={signal ?? null} size="sm" />
        <ThemeToggle />
      </div>
    </header>
  );
}
