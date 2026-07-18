"use client";

import { useState } from "react";
import FileUpload from "./components/FileUpload";
import ResultViewer from "./components/ResultViewer";
import ErrorDisplay from "./components/ErrorDisplay";

interface NIDData {
  name: string | null;
  fatherName: string | null;
  motherName: string | null;
  dateOfBirth: string | null;
  nidNumber: string | null;
  presentAddress: string | null;
  permanentAddress: string | null;
}

interface ApiError {
  code: string;
  message: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [uploadMode, setUploadMode] = useState<"single" | "dual">("dual");
  const [frontFile, setFrontFile] = useState<File | null>(null);
  const [backFile, setBackFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<NIDData | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [error, setError] = useState<ApiError | null>(null);
  const [copied, setCopied] = useState(false);

  const handleExtract = async () => {
    setError(null);
    setResult(null);
    setWarnings([]);

    if (!frontFile) {
      setError({
        code: "MISSING_FRONT_IMAGE",
        message:
          uploadMode === "single"
            ? "Please upload the NID card image containing both sides."
            : "Please upload the front side of the NID card.",
      });
      return;
    }

    if (uploadMode === "dual" && !backFile) {
      setError({
        code: "MISSING_BACK_IMAGE",
        message: "Please upload the back side of the NID card.",
      });
      return;
    }

    setLoading(true);

    try {
      const formData = new FormData();
      formData.append("front", frontFile);
      if (uploadMode === "dual" && backFile) {
        formData.append("back", backFile);
      }

      const response = await fetch(`${API_URL}/extract`, {
        method: "POST",
        body: formData,
      });

      let data;
      try {
        data = await response.json();
      } catch {
        if (response.status >= 500) {
          setError({
            code: "INTERNAL_ERROR",
            message: `An internal server error occurred (Status ${response.status}). Please try again later.`,
          });
        } else {
          setError({
            code: "UNKNOWN_ERROR",
            message: `An unexpected error occurred (Status ${response.status}).`,
          });
        }
        return;
      }

      if (response.ok && data.success) {
        setResult(data.data);
        setWarnings(data.warnings || []);
      } else {
        setError(data.error || {
          code: "UNKNOWN_ERROR",
          message: data.message || "An error occurred during extraction.",
        });
      }
    } catch {
      setError({
        code: "NETWORK_ERROR",
        message:
          "Failed to connect to the server. Please ensure the backend is running.",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCopyJson = () => {
    if (result) {
      navigator.clipboard.writeText(JSON.stringify(result, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleReset = () => {
    setResult(null);
    setWarnings([]);
    setError(null);
    setFrontFile(null);
    setBackFile(null);
  };

  const canExtract =
    !loading &&
    !!frontFile &&
    (uploadMode === "single" || !!backFile);

  return (
    <main className="flex-1 flex items-start justify-center px-4 py-10">
      <div className="w-full max-w-2xl space-y-6">
        {/* Header */}
        <div className="text-center space-y-1">
          <div className="inline-flex items-center gap-2 text-blue-600 text-sm font-medium mb-2">
            <span className="w-2 h-2 rounded-full bg-blue-500 inline-block" />
            AI-Powered Document Extraction
          </div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
            Bangladesh NID Extractor
          </h1>
          <p className="text-gray-500 text-sm max-w-md mx-auto">
            Upload your NID card to extract structured information. Supports
            single combined scan images or separate front/back photos.
          </p>
        </div>

        {/* Upload Section */}
        <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-5 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700">
              Upload NID Card Images
            </h2>
            {(frontFile || backFile) && (
              <button
                id="reset-button"
                onClick={handleReset}
                className="text-xs text-gray-400 hover:text-gray-600 cursor-pointer transition-colors"
              >
                Reset all
              </button>
            )}
          </div>

          {/* Toggle Tabs */}
          <div className="flex bg-gray-100 p-1 rounded-lg">
            <button
              type="button"
              onClick={() => {
                setUploadMode("dual");
                handleReset();
              }}
              className={`flex-1 py-2 text-xs font-semibold rounded-md transition-all cursor-pointer ${
                uploadMode === "dual"
                  ? "bg-white text-gray-800 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              Two Images (Front & Back)
            </button>
            <button
              type="button"
              onClick={() => {
                setUploadMode("single");
                handleReset();
              }}
              className={`flex-1 py-2 text-xs font-semibold rounded-md transition-all cursor-pointer ${
                uploadMode === "single"
                  ? "bg-white text-gray-800 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              Single Image (Front & Back combined)
            </button>
          </div>

          {uploadMode === "dual" ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FileUpload
                id="front-upload"
                label="Front Side"
                onFileSelect={setFrontFile}
                initialFile={frontFile}
              />
              <FileUpload
                id="back-upload"
                label="Back Side"
                onFileSelect={setBackFile}
                initialFile={backFile}
              />
            </div>
          ) : (
            <div className="w-full">
              <FileUpload
                id="combined-upload"
                label="Combined Scan / Photocopy Image"
                onFileSelect={setFrontFile}
                initialFile={frontFile}
              />
            </div>
          )}

          <button
            id="extract-button"
            onClick={handleExtract}
            disabled={!canExtract}
            className={`w-full py-3 px-4 rounded-lg text-sm font-medium transition-all duration-150 ${
              canExtract
                ? "bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800 cursor-pointer shadow-sm"
                : "bg-gray-100 text-gray-400 cursor-not-allowed"
            }`}
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <svg
                  className="animate-spin h-4 w-4"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
                Extracting information…
              </span>
            ) : (
              "Extract Information"
            )}
          </button>
        </div>


        {/* How it works */}
        {!result && !error && !loading && (
          <div className="border border-gray-100 rounded-xl p-5 bg-gray-50">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
              How it works
            </p>
            <div className="grid grid-cols-3 gap-3">
              {[
                {
                  step: "1",
                  title: "Image Preprocessing",
                  desc: "OpenCV deskews, denoises, and enhances contrast",
                },
                {
                  step: "2",
                  title: "Vision AI Analysis",
                  desc: "LLM reads Bengali + English text directly from the image",
                },
                {
                  step: "3",
                  title: "Normalisation",
                  desc: "Dates, NID digits, and names are cleaned and validated",
                },
              ].map(({ step, title, desc }) => (
                <div key={step} className="space-y-1">
                  <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-600 text-xs font-bold flex items-center justify-center">
                    {step}
                  </div>
                  <p className="text-xs font-medium text-gray-700">{title}</p>
                  <p className="text-xs text-gray-500">{desc}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Error / Warnings */}
        <ErrorDisplay error={error} warnings={warnings} />

        {/* Results */}
        {result && (
          <ResultViewer
            data={result}
            onCopyJson={handleCopyJson}
            copied={copied}
          />
        )}

        {/* Footer */}
        <p className="text-center text-xs text-gray-400 pb-4">
          Images are processed server-side and never stored. NID data is not logged.
        </p>
      </div>
    </main>
  );
}
