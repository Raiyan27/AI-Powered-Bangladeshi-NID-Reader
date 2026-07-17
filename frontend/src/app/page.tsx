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
  const [frontFile, setFrontFile] = useState<File | null>(null);
  const [backFile, setBackFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<NIDData | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [error, setError] = useState<ApiError | null>(null);

  const handleExtract = async () => {
    setError(null);
    setResult(null);
    setWarnings([]);

    if (!frontFile) {
      setError({
        code: "MISSING_FRONT_IMAGE",
        message: "Please upload the front side of the NID card.",
      });
      return;
    }

    if (!backFile) {
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
      formData.append("back", backFile);

      const response = await fetch(`${API_URL}/extract`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (data.success) {
        setResult(data.data);
        setWarnings(data.warnings || []);
      } else {
        setError(data.error);
      }
    } catch (err) {
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
    }
  };

  return (
    <main className="flex-1 flex items-start justify-center px-4 py-12">
      <div className="w-full max-w-xl space-y-6">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">
            Bangladesh NID Extractor
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Upload front and back images of an NID card to extract information
          </p>
        </div>

        {/* Upload Section */}
        <div className="border border-gray-200 rounded-lg p-5 space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <FileUpload
              id="front-upload"
              label="Front Side"
              onFileSelect={setFrontFile}
            />
            <FileUpload
              id="back-upload"
              label="Back Side"
              onFileSelect={setBackFile}
            />
          </div>

          <button
            id="extract-button"
            onClick={handleExtract}
            disabled={loading || !frontFile || !backFile}
            className={`w-full py-2.5 px-4 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
              loading || !frontFile || !backFile
                ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                : "bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800"
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
                Extracting...
              </span>
            ) : (
              "Extract Information"
            )}
          </button>
        </div>

        {/* Error / Warnings */}
        <ErrorDisplay error={error} warnings={warnings} />

        {/* Results */}
        {result && (
          <ResultViewer data={result} onCopyJson={handleCopyJson} />
        )}
      </div>
    </main>
  );
}
