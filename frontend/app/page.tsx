"use client";

import React, { useState } from "react";
import CameraView from "@/components/CameraView";
import ProcessingView from "@/components/ProcessingView";
import ResultView from "@/components/ResultView";
import { processProductPhoto, ProcessResult } from "@/lib/api";
import { AlertCircle, Camera, Sparkles } from "lucide-react";

type AppStep = "camera" | "processing" | "result";

export default function Home() {
  const [step, setStep] = useState<AppStep>("camera");
  const [originalUrl, setOriginalUrl] = useState<string | null>(null);
  const [processedResult, setProcessedResult] = useState<ProcessResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleCapture = async (blob: Blob, dataUrl: string) => {
    setOriginalUrl(dataUrl);
    setErrorMessage(null);
    setStep("processing");

    try {
      const result = await processProductPhoto(blob, "camera-photo.jpg");
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
      const result = await processProductPhoto(file, file.name);
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
          Self-hosted open-source RMBG • No permanent storage • Clean 1024×1024 studio output
        </p>
      </footer>
    </main>
  );
}
