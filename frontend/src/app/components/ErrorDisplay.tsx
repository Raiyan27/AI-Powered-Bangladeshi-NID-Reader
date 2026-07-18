"use client";

interface ApiError {
  code: string;
  message: string;
}

interface ErrorDisplayProps {
  error: ApiError | null;
  warnings: string[];
}

const ERROR_CODE_LABELS: Record<string, string> = {
  MISSING_FRONT_IMAGE: "Missing Front Image",
  MISSING_BACK_IMAGE: "Missing Back Image",
  INVALID_IMAGE_FORMAT: "Invalid Image Format",
  LOW_IMAGE_QUALITY: "Low Image Quality",
  OCR_FAILED: "OCR Failed",
  AI_EXTRACTION_FAILED: "AI Extraction Failed",
  INVALID_DOCUMENT_TYPE: "Invalid Document Type",
  INVALID_FRONT_IMAGE: "Invalid Front Image",
  INVALID_BACK_IMAGE: "Invalid Back Image",
  NETWORK_ERROR: "Network Error",
  INTERNAL_ERROR: "Server Error",
  UNKNOWN_ERROR: "Unknown Error",
};

export default function ErrorDisplay({ error, warnings }: ErrorDisplayProps) {
  if (!error && warnings.length === 0) return null;

  return (
    <div className="space-y-3">
      {/* Hard error */}
      {error && (
        <div
          id="error-display"
          role="alert"
          className="border border-red-200 bg-red-50 rounded-xl px-5 py-4"
        >
          <div className="flex items-start gap-3">
            <span className="text-red-500 text-lg mt-0.5">⚠️</span>
            <div>
              <p className="text-sm font-semibold text-red-800">
                {ERROR_CODE_LABELS[error.code] || error.code}
              </p>
              <p className="text-sm text-red-700 mt-0.5">{error.message}</p>
              <p className="text-xs text-red-500 mt-1 font-mono">
                Code: {error.code}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Warnings (partial extraction) */}
      {warnings.length > 0 && (
        <div
          id="warnings-display"
          className="border border-amber-200 bg-amber-50 rounded-xl px-5 py-4"
        >
          <div className="flex items-start gap-3">
            <span className="text-amber-500 text-lg mt-0.5">ℹ️</span>
            <div className="flex-1">
              <p className="text-sm font-semibold text-amber-800 mb-1.5">
                Partial Extraction ({warnings.length} warning
                {warnings.length > 1 ? "s" : ""})
              </p>
              <ul className="space-y-1">
                {warnings.map((warning, i) => (
                  <li key={i} className="text-sm text-amber-700 flex gap-2">
                    <span className="text-amber-400 shrink-0">•</span>
                    {warning}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
