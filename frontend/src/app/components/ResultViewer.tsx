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
}

const FIELD_LABELS: Record<string, string> = {
  name: "Name",
  fatherName: "Father's Name",
  motherName: "Mother's Name",
  dateOfBirth: "Date of Birth",
  nidNumber: "NID Number",
  presentAddress: "Present Address",
  permanentAddress: "Permanent Address",
};

export default function ResultViewer({ data, onCopyJson }: ResultViewerProps) {
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-200">
        <h2 className="text-sm font-semibold text-gray-700">
          Extracted Information
        </h2>
        <button
          onClick={onCopyJson}
          className="text-xs text-blue-600 hover:text-blue-800 font-medium cursor-pointer"
        >
          Copy JSON
        </button>
      </div>

      <div className="divide-y divide-gray-100">
        {Object.entries(FIELD_LABELS).map(([key, label]) => {
          const value = data[key as keyof NIDData];
          return (
            <div key={key} className="flex px-4 py-3">
              <span className="text-sm font-medium text-gray-500 w-40 shrink-0">
                {label}
              </span>
              <span
                className={`text-sm ${
                  value ? "text-gray-900" : "text-gray-400 italic"
                }`}
              >
                {value || "Not detected"}
              </span>
            </div>
          );
        })}
      </div>

      <div className="px-4 py-3 bg-gray-50 border-t border-gray-200">
        <details>
          <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
            View Raw JSON
          </summary>
          <pre className="mt-2 text-xs text-gray-600 bg-white p-3 rounded border border-gray-200 overflow-x-auto">
            {JSON.stringify(data, null, 2)}
          </pre>
        </details>
      </div>
    </div>
  );
}
