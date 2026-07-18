"use client";

interface NIDData {
  name: string | null;
  fatherName: string | null;
  motherName: string | null;
  spouseName: string | null;
  dateOfBirth: string | null;
  nidNumber: string | null;
  address: string | null;
  presentAddress: string | null;
  permanentAddress: string | null;
}

interface ResultViewerProps {
  data: NIDData;
  onCopyJson: () => void;
  copied?: boolean;
}

// Core fields always shown
const CORE_FIELDS: { key: keyof NIDData; label: string; icon: string }[] = [
  { key: "name", label: "Full Name", icon: "👤" },
  { key: "fatherName", label: "Father's Name", icon: "👨" },
  { key: "motherName", label: "Mother's Name", icon: "👩" },
  { key: "spouseName", label: "Spouse's Name", icon: "💍" },
  { key: "dateOfBirth", label: "Date of Birth", icon: "🎂" },
  { key: "nidNumber", label: "NID Number", icon: "🪪" },
];

// Address fields — rendered with special logic
const ADDRESS_FIELDS: { key: keyof NIDData; label: string }[] = [
  { key: "address", label: "Address" },
  { key: "presentAddress", label: "Present Address" },
  { key: "permanentAddress", label: "Permanent Address" },
];

export default function ResultViewer({
  data,
  onCopyJson,
  copied = false,
}: ResultViewerProps) {
  // Count non-null, non-empty values across all fields
  const allValues = Object.values(data).filter(
    (v) => v !== null && v !== undefined && String(v).trim() !== ""
  );
  const detectedCount = allValues.length;
  const totalCount = CORE_FIELDS.length + 1; // +1 for address group

  // Determine which address fields to show
  const hasPresentOrPermanent = data.presentAddress || data.permanentAddress;

  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden shadow-sm bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 bg-gray-50 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500" />
          <h2 className="text-sm font-semibold text-gray-800">Extracted Information</h2>
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
        {/* Core fields */}
        {CORE_FIELDS.map(({ key, label, icon }) => {
          const value = data[key];
          // Skip optional fields that are null
          if ((key === "spouseName") && !value) return null;
          return (
            <div key={key} className="flex items-start gap-3 px-5 py-3.5">
              <span className="text-base mt-0.5 shrink-0">{icon}</span>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-gray-500 mb-0.5">{label}</p>
                <p className={`text-sm break-words ${value ? "text-gray-900 font-medium" : "text-gray-400 italic"}`}>
                  {value || "Not detected"}
                </p>
              </div>
            </div>
          );
        })}

        {/* Address block */}
        {hasPresentOrPermanent ? (
          /* Smart card: show present + permanent separately */
          <>
            {ADDRESS_FIELDS.filter((f) => f.key !== "address").map(({ key, label }) => {
              const value = data[key];
              return (
                <div key={key} className="flex items-start gap-3 px-5 py-3.5">
                  <span className="text-base mt-0.5 shrink-0">
                    {key === "presentAddress" ? "📍" : "🏠"}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-gray-500 mb-0.5">{label}</p>
                    <p className={`text-sm break-words ${value ? "text-gray-900 font-medium" : "text-gray-400 italic"}`}>
                      {value || "Not detected"}
                    </p>
                  </div>
                </div>
              );
            })}
          </>
        ) : (
          /* Old card / single address */
          <div className="flex items-start gap-3 px-5 py-3.5">
            <span className="text-base mt-0.5 shrink-0">📍</span>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-gray-500 mb-0.5">Address</p>
              <p className={`text-sm break-words ${data.address ? "text-gray-900 font-medium" : "text-gray-400 italic"}`}>
                {data.address || "Not detected"}
              </p>
            </div>
          </div>
        )}
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
