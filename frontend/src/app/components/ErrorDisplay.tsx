"use client";

interface ErrorDisplayProps {
  error?: {
    code: string;
    message: string;
  } | null;
  warnings?: string[];
}

export default function ErrorDisplay({ error, warnings }: ErrorDisplayProps) {
  if (!error && (!warnings || warnings.length === 0)) return null;

  return (
    <div className="space-y-3">
      {error && (
        <div
          id="error-display"
          className="border border-red-200 bg-red-50 rounded-lg px-4 py-3"
        >
          <div className="flex items-start gap-2">
            <svg
              className="h-5 w-5 text-red-500 shrink-0 mt-0.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <div>
              <p className="text-sm font-medium text-red-800">{error.message}</p>
              <p className="text-xs text-red-600 mt-1">Code: {error.code}</p>
            </div>
          </div>
        </div>
      )}

      {warnings && warnings.length > 0 && (
        <div
          id="warnings-display"
          className="border border-amber-200 bg-amber-50 rounded-lg px-4 py-3"
        >
          <div className="flex items-start gap-2">
            <svg
              className="h-5 w-5 text-amber-500 shrink-0 mt-0.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
              />
            </svg>
            <div>
              <p className="text-sm font-medium text-amber-800">Warnings</p>
              <ul className="mt-1 space-y-1">
                {warnings.map((w, i) => (
                  <li key={i} className="text-sm text-amber-700">
                    • {w}
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
