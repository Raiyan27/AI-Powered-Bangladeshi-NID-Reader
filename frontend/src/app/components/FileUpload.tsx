"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface FileUploadProps {
  id: string;
  label: string;
  onFileSelect: (file: File | null) => void;
  accept?: string;
  initialFile?: File | null;
}

export default function FileUpload({
  id,
  label,
  onFileSelect,
  accept = ".jpg,.jpeg,.png",
  initialFile,
}: FileUploadProps) {
  const [preview, setPreview] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string>("");
  const [dragOver, setDragOver] = useState(false);
  const [inputMode, setInputMode] = useState<"upload" | "camera">("upload");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Reset when parent clears the file
  useEffect(() => {
    if (!initialFile) {
      setPreview(null);
      setFileName("");
      if (fileInputRef.current) fileInputRef.current.value = "";
      if (cameraInputRef.current) cameraInputRef.current.value = "";
      stopCamera();
    }
  }, [initialFile]);

  // Clean up camera on unmount
  useEffect(() => {
    return () => stopCamera();
  }, []);

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setCameraActive(false);
  };

  const handleFile = useCallback(
    (file: File | null) => {
      if (!file) {
        setPreview(null);
        setFileName("");
        onFileSelect(null);
        return;
      }

      const validTypes = ["image/jpeg", "image/jpg", "image/png"];
      if (!validTypes.includes(file.type)) {
        alert("Please upload a JPG, JPEG, or PNG image.");
        return;
      }

      setFileName(file.name);
      onFileSelect(file);

      const reader = new FileReader();
      reader.onload = (e) => setPreview(e.target?.result as string);
      reader.readAsDataURL(file);
    },
    [onFileSelect]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0] || null;
      handleFile(file);
    },
    [handleFile]
  );

  const handleRemove = () => {
    setPreview(null);
    setFileName("");
    onFileSelect(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
    stopCamera();
  };

  // --- Camera helpers ---

  const startCamera = async () => {
    setCameraError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCameraActive(true);
    } catch {
      setCameraError(
        "Camera access denied or not available. Please allow camera access or use file upload."
      );
    }
  };

  const capturePhoto = () => {
    if (!videoRef.current) return;
    const video = videoRef.current;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0);
    canvas.toBlob(
      (blob) => {
        if (!blob) return;
        const captured = new File([blob], `${id}-capture.jpg`, { type: "image/jpeg" });
        stopCamera();
        handleFile(captured);
      },
      "image/jpeg",
      0.92
    );
  };

  const switchMode = (mode: "upload" | "camera") => {
    stopCamera();
    setInputMode(mode);
    setCameraError(null);
    if (mode === "camera") {
      // brief delay so the video element mounts
      setTimeout(() => startCamera(), 50);
    }
  };

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-2">
        <label htmlFor={id} className="block text-sm font-medium text-gray-700">
          {label}
        </label>

        {/* Upload / Camera toggle */}
        <div className="flex items-center gap-1 bg-gray-100 rounded-md p-0.5 text-xs">
          <button
            type="button"
            onClick={() => switchMode("upload")}
            title="Upload from device"
            className={`flex items-center gap-1 px-2 py-1 rounded transition-all cursor-pointer ${
              inputMode === "upload"
                ? "bg-white text-gray-800 shadow-sm font-medium"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {/* Upload icon */}
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            Upload
          </button>
          <button
            type="button"
            onClick={() => switchMode("camera")}
            title="Use camera"
            className={`flex items-center gap-1 px-2 py-1 rounded transition-all cursor-pointer ${
              inputMode === "camera"
                ? "bg-white text-gray-800 shadow-sm font-medium"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {/* Camera icon */}
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Camera
          </button>
        </div>
      </div>

      {/* Preview */}
      {preview ? (
        <div className="relative border border-gray-200 rounded-lg overflow-hidden bg-gray-50">
          <img
            src={preview}
            alt={`Preview of ${label}`}
            className="w-full h-44 object-contain p-2"
          />
          <div className="flex items-center justify-between px-3 py-2 bg-white border-t border-gray-200">
            <span className="text-xs text-gray-500 truncate max-w-[160px]">{fileName}</span>
            <button
              type="button"
              onClick={handleRemove}
              className="text-xs text-red-500 hover:text-red-700 font-medium cursor-pointer"
            >
              Remove
            </button>
          </div>
        </div>

      ) : inputMode === "camera" ? (
        /* Camera viewfinder */
        <div className="border-2 border-dashed border-blue-300 rounded-lg overflow-hidden bg-black relative">
          {cameraError ? (
            <div className="flex flex-col items-center justify-center h-44 px-4 text-center gap-2">
              <svg className="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M12 9v2m0 4h.01M21 12c0 4.97-4.03 9-9 9s-9-4.03-9-9 4.03-9 9-9 9 4.03 9 9z" />
              </svg>
              <p className="text-xs text-red-400">{cameraError}</p>
              <button
                type="button"
                onClick={() => switchMode("upload")}
                className="text-xs text-blue-600 underline cursor-pointer"
              >
                Switch to file upload
              </button>
            </div>
          ) : cameraActive ? (
            <div className="relative">
              <video
                ref={videoRef}
                className="w-full h-44 object-cover"
                playsInline
                muted
              />
              {/* Capture button overlay */}
              <div className="absolute bottom-2 left-0 right-0 flex justify-center">
                <button
                  type="button"
                  id={`${id}-capture`}
                  onClick={capturePhoto}
                  className="w-12 h-12 rounded-full bg-white border-4 border-blue-500 shadow-lg flex items-center justify-center cursor-pointer hover:scale-105 transition-transform active:scale-95"
                  title="Capture photo"
                >
                  <div className="w-8 h-8 rounded-full bg-blue-500" />
                </button>
              </div>
            </div>
          ) : (
            /* Starting camera spinner */
            <div className="flex flex-col items-center justify-center h-44 gap-2">
              <svg className="animate-spin w-6 h-6 text-blue-400" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <p className="text-xs text-gray-400">Starting camera…</p>
            </div>
          )}
        </div>

      ) : (
        /* File upload drop zone */
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
            dragOver
              ? "border-blue-400 bg-blue-50"
              : "border-gray-300 hover:border-blue-400 hover:bg-gray-50"
          }`}
        >
          <svg className="mx-auto h-8 w-8 text-gray-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <p className="text-sm text-gray-600">
            Drag &amp; drop or{" "}
            <span className="text-blue-600 font-medium">browse</span>
          </p>
          <p className="text-xs text-gray-400 mt-1">JPG, JPEG, or PNG</p>
        </div>
      )}

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        id={id}
        type="file"
        accept={accept}
        onChange={(e) => handleFile(e.target.files?.[0] || null)}
        className="hidden"
      />
    </div>
  );
}
