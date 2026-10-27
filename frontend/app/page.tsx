"use client";

import React, { useState } from "react";
import CameraView from "@/components/CameraView";
import ProcessingView from "@/components/ProcessingView";
import ResultView from "@/components/ResultView";
import { processProductPhoto, ProcessResult } from "@/lib/api";
import { AlertCircle, Camera, Zap, Sparkles } from "lucide-react";

type AppStep = "camera" | "processing" | "result";
type SpeedMode = "studio" | "instant";

export default function Home() {
  const [step, setStep] = useState<AppStep>("camera");
  const [speedMode, setSpeedMode] = useState<SpeedMode>("studio");
  const [originalUrl, setOriginalUrl] = useState<string | null>(null);
  const [processedResult, setProcessedResult] = useState<ProcessResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const activeModelParam = speedMode === "instant" ? "u2netp" : "isnet-general-use";

  const handleCapture = async (blob: Blob, dataUrl: string) => {
    setOriginalUrl(dataUrl);
    setErrorMessage(null);
    setStep("processing");

    try {
      const result = await processProductPhoto(blob, "camera-photo.jpg", activeModelParam);
      setProcessedResult(result);
      setStep("result");
    } catch (err: any) {
      console.error("Processing failed:", err);
      setErrorMessage(
        err.message ||
          "Couldn't process this image. Try taking another photo with the product clearly visible."
      );
      setStep("camera");
    }
  };

  const handleUpload = async (file: File) => {
    // Generate preview URL for uploaded photo
    const previewUrl = URL.createObjectURL(file);
    setOriginalUrl(previewUrl);
    setErrorMessage(null);
    setStep("processing");

    try {
      const result = await processProductPhoto(file, file.name, activeModelParam);
      setProcessedResult(result);
      setStep("result");
    } catch (err: any) {
      console.error("Upload processing failed:", err);
      setErrorMessage(
        err.message ||
          "Couldn't process this image. Try taking another photo with the product clearly visible."
      );
      setStep("camera");
    }
  };

  const handleRetake = () => {
    setOriginalUrl(null);
    setProcessedResult(null);
    setErrorMessage(null);
    setStep("camera");
  };

  return (
    <main className="min-h-screen flex flex-col justify-between bg-white text-neutral-900 px-4 py-8 md:py-12">
      {/* Header */}
      <header className="w-full max-w-2xl mx-auto text-center mb-6">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-neutral-100 text-neutral-800 text-xs font-semibold tracking-wide uppercase mb-3 border border-neutral-200/60 shadow-sm">
          <Camera className="w-3.5 h-3.5" />
          <span>ProductShot AI</span>
        </div>
        <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-neutral-950">
          ProductShot
        </h1>
        <p className="text-neutral-500 text-sm md:text-base mt-2 max-w-md mx-auto">
          Turn a quick product photo into a clean product image.
        </p>

        {/* Speed / Quality Mode Switcher */}
        {step === "camera" && (
          <div className="inline-flex items-center gap-1 p-1 bg-neutral-100 rounded-full border border-neutral-200/80 mt-5 shadow-sm">
            <button
              type="button"
              onClick={() => setSpeedMode("studio")}
              className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                speedMode === "studio"
                  ? "bg-white text-neutral-950 shadow-sm"
                  : "text-neutral-500 hover:text-neutral-900"
              }`}
            >
              <Sparkles className="w-3.5 h-3.5 text-neutral-800" />
              Studio HD (~1.8s)
            </button>
            <button
              type="button"
              onClick={() => setSpeedMode("instant")}
              className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                speedMode === "instant"
                  ? "bg-white text-neutral-950 shadow-sm"
                  : "text-neutral-500 hover:text-neutral-900"
              }`}
            >
              <Zap className="w-3.5 h-3.5 text-amber-500" />
              Instant (~0.5s)
            </button>
          </div>
        )}
      </header>

      {/* Error Alert Banner */}
      {errorMessage && (
        <div className="w-full max-w-md mx-auto mb-6 p-4 rounded-2xl bg-red-50 border border-red-200/80 flex items-start gap-3 shadow-sm animate-in fade-in">
          <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-medium text-red-800">{errorMessage}</p>
          </div>
          <button
            type="button"
            onClick={() => setErrorMessage(null)}
            className="text-xs text-red-500 hover:text-red-700 font-semibold cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Interactive Stage */}
      <div className="flex-1 flex flex-col items-center justify-center w-full max-w-2xl mx-auto">
        {step === "camera" && (
          <CameraView onCapture={handleCapture} onUpload={handleUpload} />
        )}

        {step === "processing" && (
          <ProcessingView originalPreviewUrl={originalUrl} />
        )}

        {step === "result" && processedResult && (
          <ResultView
            originalUrl={originalUrl}
            processedUrl={processedResult.imageUrl}
            processingTimeMs={processedResult.processingTimeMs}
            onRetake={handleRetake}
          />
        )}
      </div>

      {/* Simple Footer */}
      <footer className="w-full max-w-2xl mx-auto text-center mt-8 pt-6 border-t border-neutral-100">
        <p className="text-xs text-neutral-400">
          Fast open-source background removal • No cloud storage • Pure studio product photography
        </p>
      </footer>
    </main>
  );
}
