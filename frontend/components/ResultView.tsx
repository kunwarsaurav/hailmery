"use client";

import React, { useState } from "react";
import { Download, RotateCcw, Check, Eye, EyeOff, Sparkles } from "lucide-react";

interface ResultViewProps {
  originalUrl: string | null;
  processedUrl: string;
  processingTimeMs?: number;
  onRetake: () => void;
}

export default function ResultView({
  originalUrl,
  processedUrl,
  processingTimeMs,
  onRetake,
}: ResultViewProps) {
  const [showOriginal, setShowOriginal] = useState(false);
  const [downloaded, setDownloaded] = useState(false);

  const handleDownload = () => {
    const link = document.createElement("a");
    link.href = processedUrl;
    link.download = `productshot-${Date.now()}.jpg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setDownloaded(true);
    setTimeout(() => setDownloaded(false), 3000);
  };

  return (
    <div className="w-full max-w-xl mx-auto flex flex-col items-center">
      {/* Header */}
      <div className="text-center mb-5">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-neutral-100 rounded-full text-xs font-medium text-neutral-700 mb-2">
          <Sparkles className="w-3.5 h-3.5 text-neutral-800" />
          Studio Isolated & Balanced
          {processingTimeMs && <span>• {(processingTimeMs / 1000).toFixed(1)}s</span>}
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-neutral-900">
          Your Product Image
        </h2>
      </div>

      {/* Main Studio Image Container */}
      <div className="relative w-full aspect-square max-w-[480px] bg-white rounded-3xl overflow-hidden shadow-2xl border border-neutral-200/80 group">
        <img
          src={showOriginal && originalUrl ? originalUrl : processedUrl}
          alt={showOriginal ? "Original photo" : "Clean studio product photo"}
          className="w-full h-full object-contain p-2"
        />

        {/* View Mode Tag */}
        <div className="absolute top-4 left-4">
          <span className="px-3 py-1 bg-black/60 backdrop-blur-md text-white text-xs font-semibold rounded-full uppercase tracking-wider">
            {showOriginal ? "Original Photo" : "Studio Shot (1024×1024)"}
          </span>
        </div>

        {/* Quick Compare Toggle Button (if original photo exists) */}
        {originalUrl && (
          <button
            type="button"
            onClick={() => setShowOriginal(!showOriginal)}
            className="absolute top-4 right-4 inline-flex items-center gap-1.5 px-3 py-1.5 bg-black/60 hover:bg-black/80 backdrop-blur-md text-white text-xs font-medium rounded-full transition-all active:scale-95 shadow-sm"
          >
            {showOriginal ? (
              <>
                <EyeOff className="w-3.5 h-3.5" />
                Show Studio Shot
              </>
            ) : (
              <>
                <Eye className="w-3.5 h-3.5" />
                Compare Original
              </>
            )}
          </button>
        )}
      </div>

      {/* Action Buttons */}
      <div className="w-full max-w-[480px] mt-6 flex flex-col sm:flex-row items-center gap-3">
        {/* Primary Download Button */}
        <button
          type="button"
          onClick={handleDownload}
          className="w-full flex-1 inline-flex items-center justify-center gap-2 px-6 py-4 bg-neutral-900 hover:bg-black text-white font-semibold rounded-2xl transition-all shadow-lg hover:shadow-xl active:scale-98 cursor-pointer"
        >
          {downloaded ? (
            <>
              <Check className="w-5 h-5 text-emerald-400" />
              <span>Downloaded!</span>
            </>
          ) : (
            <>
              <Download className="w-5 h-5" />
              <span>Download Image</span>
            </>
          )}
        </button>

        {/* Secondary Retake Button */}
        <button
          type="button"
          onClick={onRetake}
          className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-4 bg-neutral-100 hover:bg-neutral-200 text-neutral-800 font-semibold rounded-2xl transition-all active:scale-98 cursor-pointer border border-neutral-200/80"
        >
          <RotateCcw className="w-5 h-5" />
          <span>Retake Photo</span>
        </button>
      </div>

      {/* Small Helper Tip */}
      <p className="text-xs text-neutral-400 mt-4 text-center">
        High-resolution 1024×1024 with subtle studio ground shadow. Ready for store, catalog, or marketplace.
      </p>
    </div>
  );
}
