"use client";

import React, { useEffect, useState } from "react";
import { Sparkles, Loader2 } from "lucide-react";

interface ProcessingViewProps {
  originalPreviewUrl: string | null;
}

export default function ProcessingView({ originalPreviewUrl }: ProcessingViewProps) {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setSeconds((s) => s + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="w-full max-w-md mx-auto flex flex-col items-center text-center py-6 px-4">
      {/* Studio Processing Card */}
      <div className="relative w-full aspect-square max-w-[420px] bg-neutral-50 rounded-3xl border border-neutral-200/80 shadow-xl overflow-hidden flex flex-col items-center justify-center p-6">
        {/* Subtle background glow effect */}
        <div className="absolute inset-0 bg-gradient-to-tr from-neutral-100/50 via-white to-neutral-100/30 pointer-events-none" />

        {/* Small Original Preview Thumbnail */}
        {originalPreviewUrl && (
          <div className="relative mb-6">
            <div className="w-28 h-28 rounded-2xl overflow-hidden shadow-md border-2 border-white ring-1 ring-neutral-200 bg-neutral-900">
              <img
                src={originalPreviewUrl}
                alt="Captured product preview"
                className="w-full h-full object-cover opacity-80"
              />
            </div>
            {/* Spinning Indicator Badge */}
            <div className="absolute -bottom-2 -right-2 p-2 bg-neutral-900 text-white rounded-full shadow-lg">
              <Loader2 className="w-4 h-4 animate-spin text-white" />
            </div>
          </div>
        )}

        {/* Title */}
        <h2 className="text-xl font-semibold tracking-tight text-neutral-900 mb-2">
          Creating your product image...
        </h2>

        {/* Dynamic Status Text */}
        <p className="text-sm text-neutral-500 max-w-xs animate-pulse">
          {seconds < 4
            ? "Detecting foreground product & removing background..."
            : seconds < 12
            ? "Extracting crisp silhouette & centering on studio canvas..."
            : "Adding subtle studio ground shadow..."}
        </p>

        {/* Minimal progress pulse bar */}
        <div className="w-48 h-1 bg-neutral-200 rounded-full mt-6 overflow-hidden">
          <div className="w-full h-full bg-neutral-900 animate-[shimmer_2s_infinite] origin-left" />
        </div>
      </div>

      <p className="text-xs text-neutral-400 mt-6 flex items-center gap-1.5">
        <Sparkles className="w-3.5 h-3.5 text-neutral-500" />
        Self-hosted open-source model • In-memory processing
      </p>
    </div>
  );
}
