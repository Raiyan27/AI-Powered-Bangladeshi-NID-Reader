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
  bloodGroup: string | null;
}

interface ResultViewerProps {
  data: NIDData;
  onCopyJson: () => void;
  copied?: boolean;
}

// Core fields list
const CORE_FIELDS: { key: keyof NIDData; label: string; icon: string }[] = [
  { key: "name", label: "Full Name", icon: "👤" },
  { key: "fatherName", label: "Father's Name", icon: "👨" },
  { key: "motherName", label: "Mother's Name", icon: "👩" },
  { key: "spouseName", label: "Spouse's Name", icon: "💍" },
  { key: "dateOfBirth", label: "Date of Birth", icon: "🎂" },
  { key: "nidNumber", label: "NID Number", icon: "🪪" },
  { key: "bloodGroup", label: "Blood Group", icon: "🩸" },
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
  const hasSpouse = Boolean(data.spouseName && String(data.spouseName).trim());
  const hasBloodGroup = Boolean(data.bloodGroup && String(data.bloodGroup).trim());

  // Dynamic field counting logic:
  // Baseline mandatory count is 6 (Name, Father, Mother, DOB, NID Number, Address).
  // Optional fields (spouseName, bloodGroup) dynamically increment totalCount only when present.
  let totalCount = 6;
  if (hasSpouse) totalCount += 1;
  if (hasBloodGroup) totalCount += 1;

  let detectedCount = 0;
  if (data.name && String(data.name).trim()) detectedCount += 1;
  if (data.fatherName && String(data.fatherName).trim()) detectedCount += 1;
  if (data.motherName && String(data.motherName).trim()) detectedCount += 1;
  if (data.dateOfBirth && String(data.dateOfBirth).trim()) detectedCount += 1;
  if (data.nidNumber && String(data.nidNumber).trim()) detectedCount += 1;
  if (data.address || data.presentAddress || data.permanentAddress) detectedCount += 1;
  if (hasSpouse) detectedCount += 1;
  if (hasBloodGroup) detectedCount += 1;

  // Determine if smart-card dual addresses exist
  const hasPresentOrPermanent = data.presentAddress || data.permanentAddress;

  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden shadow-sm bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 bg-gray-50 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500" />
          <h2 className="text-sm font-semibold text-gray-800">Extracted Information</h2>
          <span className="text-xs text-gray-500 font-medium">
            ({detectedCount}/{totalCount} fields)
          </span>
        </div>
        <button
          id="copy-json-button"
          onClick={onCopyJson}
          className={`text-xs font-medium cursor-pointer transition-colors px-2.5 py-1 rounded-md border ${
            copied
              ? "text-green-700 bg-green-50 border-green-200 font-semibold"
              : "text-blue-600 bg-white border-gray-200 hover:bg-blue-50 hover:border-blue-200"
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
          // Skip optional fields when not present
          if ((key === "spouseName" || key === "bloodGroup") && !value) return null;
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
          /* Standard card / single address */
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
