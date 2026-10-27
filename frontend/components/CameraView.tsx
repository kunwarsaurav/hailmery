"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import { Camera, Upload, RefreshCw, Sparkles } from "lucide-react";

interface CameraViewProps {
  onCapture: (blob: Blob, originalDataUrl: string) => void;
  onUpload: (file: File) => void;
}

export default function CameraView({ onCapture, onUpload }: CameraViewProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [mounted, setMounted] = useState(false);
  const [hasCamera, setHasCamera] = useState<boolean | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [facingMode, setFacingMode] = useState<"environment" | "user">("environment");
  const [isStartingCamera, setIsStartingCamera] = useState(true);

  useEffect(() => {
    setMounted(true);
  }, []);

  const startCamera = useCallback(async (mode: "environment" | "user") => {
    setIsStartingCamera(true);
    setCameraError(null);

    // Stop any existing stream
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    try {
      if (typeof navigator === "undefined" || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("Camera API is not supported in this browser.");
      }

      const constraints: MediaStreamConstraints = {
        video: {
          facingMode: { ideal: mode },
          width: { ideal: 1920 },
          height: { ideal: 1080 },
        },
        audio: false,
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      setHasCamera(true);
    } catch (err: any) {
      console.warn("Camera start failed:", err);
      setHasCamera(false);
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        setCameraError("Camera access was denied. You can allow camera permissions or upload a photo instead.");
      } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
        setCameraError("No camera found on this device. Please upload a product photo.");
      } else {
        setCameraError("Unable to access camera. Please upload a product photo instead.");
      }
    } finally {
      setIsStartingCamera(false);
    }
  }, []);

  useEffect(() => {
    if (mounted) {
      startCamera(facingMode);
    }

    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, [mounted, facingMode, startCamera]);

  const toggleCameraFacing = () => {
    setFacingMode((prev) => (prev === "environment" ? "user" : "environment"));
  };

  const capturePhoto = () => {
    const video = videoRef.current;
    if (!video || !video.videoWidth || !video.videoHeight) return;

    // Capture the video frame in square ratio matching the UI guide
    const canvas = document.createElement("canvas");
    const vWidth = video.videoWidth;
    const vHeight = video.videoHeight;

    const size = Math.min(vWidth, vHeight);
    const startX = (vWidth - size) / 2;
    const startY = (vHeight - size) / 2;

    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    if (facingMode === "user") {
      ctx.translate(size, 0);
      ctx.scale(-1, 1);
    }

    ctx.drawImage(video, startX, startY, size, size, 0, 0, size, size);

    const dataUrl = canvas.toDataURL("image/jpeg", 0.95);

    canvas.toBlob(
      (blob) => {
        if (blob) {
          onCapture(blob, dataUrl);
        }
      },
      "image/jpeg",
      0.95
    );
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onUpload(file);
    }
  };

  if (!mounted) {
    return (
      <div className="w-full max-w-xl mx-auto flex flex-col items-center">
        <div className="w-full aspect-square max-w-[480px] bg-neutral-100 rounded-3xl animate-pulse" />
      </div>
    );
  }

  return (
    <div className="w-full max-w-xl mx-auto flex flex-col items-center">
      {/* Hidden File Input Fallback */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        style={{ display: "none" }}
        className="hidden"
        onChange={handleFileChange}
      />

      {/* Main Camera Frame */}
      <div className="relative w-full aspect-square max-w-[480px] bg-neutral-900 rounded-3xl overflow-hidden shadow-2xl border border-neutral-800 flex items-center justify-center">
        {hasCamera === true ? (
          <>
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className={`w-full h-full object-cover ${facingMode === "user" ? "scale-x-[-1]" : ""}`}
            />

            {/* Subtle Square Framing Overlay */}
            <div className="absolute inset-8 pointer-events-none border border-white/25 rounded-2xl flex flex-col justify-between p-4">
              <div className="flex justify-between items-start">
                <div className="w-6 h-6 border-t-2 border-l-2 border-white/80 rounded-tl-lg" />
                <div className="w-6 h-6 border-t-2 border-r-2 border-white/80 rounded-tr-lg" />
              </div>
              <div className="text-center">
                <span className="text-xs font-medium tracking-wider uppercase px-3 py-1 bg-black/40 backdrop-blur-md rounded-full text-white/90">
                  Align Product in Frame
                </span>
              </div>
              <div className="flex justify-between items-end">
                <div className="w-6 h-6 border-b-2 border-l-2 border-white/80 rounded-bl-lg" />
                <div className="w-6 h-6 border-b-2 border-r-2 border-white/80 rounded-br-lg" />
              </div>
            </div>

            {/* Flip Camera Button (top-right) */}
            <button
              type="button"
              onClick={toggleCameraFacing}
              className="absolute top-4 right-4 p-2.5 bg-black/50 hover:bg-black/70 backdrop-blur-md text-white rounded-full transition-transform active:scale-90"
              title="Switch Camera"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </>
        ) : isStartingCamera ? (
          <div className="flex flex-col items-center justify-center text-neutral-400 gap-3 p-6 text-center">
            <div className="w-8 h-8 border-2 border-neutral-600 border-t-white rounded-full animate-spin" />
            <p className="text-sm">Starting camera preview...</p>
          </div>
        ) : (
          /* Fallback when camera is unavailable or denied */
          <div className="flex flex-col items-center justify-center text-center p-8 text-neutral-300 gap-4">
            <div className="w-14 h-14 rounded-2xl bg-neutral-800 flex items-center justify-center text-neutral-400 mb-1">
              <Camera className="w-7 h-7" />
            </div>
            <div>
              <h3 className="font-semibold text-white text-base">Camera Unavailable</h3>
              <p className="text-xs text-neutral-400 mt-1 max-w-xs">
                {cameraError || "You can upload a product image from your device directly."}
              </p>
            </div>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-white text-black text-sm font-semibold rounded-full hover:bg-neutral-100 transition-all shadow-md active:scale-95 cursor-pointer"
            >
              <Upload className="w-4 h-4" />
              Upload Product Photo
            </button>
          </div>
        )}
      </div>

      {/* Control Actions Bar */}
      <div className="w-full max-w-[480px] mt-6 flex items-center justify-between px-6">
        {/* Upload Fallback Button */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="flex flex-col items-center gap-1 text-neutral-500 hover:text-neutral-900 transition-colors p-2 cursor-pointer"
          title="Upload from device"
        >
          <div className="w-11 h-11 rounded-full bg-neutral-100 hover:bg-neutral-200 flex items-center justify-center transition-colors">
            <Upload className="w-5 h-5 text-neutral-700" />
          </div>
          <span className="text-xs font-medium">Upload</span>
        </button>

        {/* Circular Shutter Button */}
        <button
          type="button"
          disabled={!hasCamera}
          onClick={capturePhoto}
          className={`relative group w-20 h-20 rounded-full flex items-center justify-center transition-all ${
            hasCamera
              ? "active:scale-90 hover:scale-105 cursor-pointer"
              : "opacity-40 cursor-not-allowed"
          }`}
          title="Take Photo"
        >
          {/* Outer ring */}
          <div className="absolute inset-0 rounded-full border-4 border-neutral-900 group-hover:border-black transition-colors" />
          {/* Inner shutter button */}
          <div className="w-16 h-16 rounded-full bg-neutral-900 group-hover:bg-black transition-colors shadow-lg" />
        </button>

        {/* Framing / Tip Indicator */}
        <div className="flex flex-col items-center gap-1 text-neutral-400 p-2 opacity-80">
          <div className="w-11 h-11 rounded-full bg-neutral-50 flex items-center justify-center border border-neutral-200">
            <Sparkles className="w-4 h-4 text-neutral-500" />
          </div>
          <span className="text-xs font-medium">Auto Studio</span>
        </div>
      </div>
    </div>
  );
}
