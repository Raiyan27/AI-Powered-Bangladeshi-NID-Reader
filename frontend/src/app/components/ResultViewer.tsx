"use client";

interface NIDData {
  name: string | null;
  fatherName: string | null;
  motherName: string | null;
  dateOfBirth: string | null;
  nidNumber: string | null;
  presentAddress: string | null;
  permanentAddress: string | null;
}

interface ResultViewerProps {
  data: NIDData;
  onCopyJson: () => void;
  copied?: boolean;
}

const FIELD_LABELS: { key: keyof NIDData; label: string; icon: string }[] = [
  { key: "name", label: "Full Name", icon: "👤" },
  { key: "fatherName", label: "Father's Name", icon: "👨" },
  { key: "motherName", label: "Mother's Name", icon: "👩" },
  { key: "dateOfBirth", label: "Date of Birth", icon: "🎂" },
  { key: "nidNumber", label: "NID Number", icon: "🪪" },
  { key: "presentAddress", label: "Present Address", icon: "📍" },
  { key: "permanentAddress", label: "Permanent Address", icon: "🏠" },
];

export default function ResultViewer({
  data,
  onCopyJson,
  copied = false,
}: ResultViewerProps) {
  const detectedCount = Object.values(data).filter(Boolean).length;
  const totalCount = FIELD_LABELS.length;

  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden shadow-sm bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 bg-gray-50 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500" />
          <h2 className="text-sm font-semibold text-gray-800">
            Extracted Information
          </h2>
          <span className="text-xs text-gray-400">
            ({detectedCount}/{totalCount} fields)
          </span>
        </div>
        <button
          id="copy-json-button"
          onClick={onCopyJson}
          className={`text-xs font-medium cursor-pointer transition-colors px-2 py-1 rounded ${
            copied
              ? "text-green-600 bg-green-50"
              : "text-blue-600 hover:text-blue-800 hover:bg-blue-50"
          }`}
        >
          {copied ? "✓ Copied!" : "Copy JSON"}
        </button>
      </div>

      {/* Fields */}
      <div className="divide-y divide-gray-100">
        {FIELD_LABELS.map(({ key, label, icon }) => {
          const value = data[key];
          return (
            <div key={key} className="flex items-start gap-3 px-5 py-3.5">
              <span className="text-base mt-0.5 shrink-0">{icon}</span>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-gray-500 mb-0.5">
                  {label}
                </p>
                <p
                  className={`text-sm break-words ${
                    value ? "text-gray-900 font-medium" : "text-gray-400 italic"
                  }`}
                >
                  {value || "Not detected"}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Raw JSON */}
      <div className="px-5 py-4 bg-gray-50 border-t border-gray-200">
        <details>
          <summary className="text-xs font-medium text-gray-500 cursor-pointer hover:text-gray-700 select-none">
            View Raw JSON
          </summary>
          <pre
            id="raw-json-output"
            className="mt-3 text-xs text-gray-700 bg-white p-4 rounded-lg border border-gray-200 overflow-x-auto leading-relaxed"
          >
            {JSON.stringify(data, null, 2)}
          </pre>
        </details>
      </div>
    </div>
  );
}
