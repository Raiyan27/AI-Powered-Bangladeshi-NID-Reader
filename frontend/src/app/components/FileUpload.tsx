"use client";

import { useCallback, useRef, useState } from "react";

interface FileUploadProps {
  id: string;
  label: string;
  onFileSelect: (file: File | null) => void;
  accept?: string;
}

export default function FileUpload({
  id,
  label,
  onFileSelect,
  accept = ".jpg,.jpeg,.png",
}: FileUploadProps) {
  const [preview, setPreview] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string>("");
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

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
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className="w-full">
      <label
        htmlFor={id}
        className="block text-sm font-medium text-gray-700 mb-2"
      >
        {label}
      </label>

      {preview ? (
        <div className="relative border border-gray-200 rounded-lg overflow-hidden bg-gray-50">
          <img
            src={preview}
            alt={`Preview of ${label}`}
            className="w-full h-48 object-contain p-2"
          />
          <div className="flex items-center justify-between px-3 py-2 bg-gray-50 border-t border-gray-200">
            <span className="text-sm text-gray-600 truncate max-w-[200px]">
              {fileName}
            </span>
            <button
              type="button"
              onClick={handleRemove}
              className="text-sm text-red-500 hover:text-red-700 font-medium cursor-pointer"
            >
              Remove
            </button>
          </div>
        </div>
      ) : (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            dragOver
              ? "border-blue-400 bg-blue-50"
              : "border-gray-300 hover:border-blue-400 hover:bg-gray-50"
          }`}
        >
          <svg
            className="mx-auto h-10 w-10 text-gray-400 mb-3"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          <p className="text-sm text-gray-600">
            Drag & drop or{" "}
            <span className="text-blue-600 font-medium">browse</span>
          </p>
          <p className="text-xs text-gray-400 mt-1">JPG, JPEG, or PNG</p>
        </div>
      )}

      <input
        ref={inputRef}
        id={id}
        type="file"
        accept={accept}
        onChange={(e) => handleFile(e.target.files?.[0] || null)}
        className="hidden"
      />
    </div>
  );
}
