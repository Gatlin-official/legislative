// UploadArea.tsx
// Drag-and-drop upload component for documents

import React, { useState } from "react";
import { uploadDocument } from "../api/client";

interface UploadAreaProps {
  onUploadSuccess: (docId: string) => void;
  onUploadError: (error: string) => void;
}

export const UploadArea: React.FC<UploadAreaProps> = ({
  onUploadSuccess,
  onUploadError,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileUpload(e.target.files[0]);
    }
  };

  const handleFileUpload = async (file: File) => {
    // Validate file type
    const validTypes = [
      "application/pdf",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "text/plain",
    ];

    if (!validTypes.includes(file.type)) {
      onUploadError(
        "Invalid file type. Please upload PDF, DOCX, or TXT files."
      );
      return;
    }

    // Validate file size (limit to 50MB)
    const MAX_FILE_SIZE = 50 * 1024 * 1024;
    if (file.size > MAX_FILE_SIZE) {
      onUploadError("File too large. Maximum size is 50MB.");
      return;
    }

    setIsLoading(true);

    try {
      const result = await uploadDocument(file);
      onUploadSuccess(result.doc_id);
    } catch (error: any) {
      // Extract error message from various response formats
      let errorMessage = "Upload failed. Please try again.";
      
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.response?.statusText) {
        errorMessage = `Server error: ${error.response.statusText}`;
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      onUploadError(errorMessage);
      console.error("Upload error details:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleButtonClick = () => {
    const fileInput = document.getElementById("file-input") as HTMLInputElement;
    if (fileInput) {
      fileInput.click();
    }
  };

  return (
    <div
      className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
        isDragging
          ? "border-blue-500 bg-blue-50"
          : "border-gray-300 bg-gray-50 hover:bg-gray-100"
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="mb-4">
        <svg
          className="mx-auto h-12 w-12 text-gray-400"
          stroke="currentColor"
          fill="none"
          viewBox="0 0 48 48"
        >
          <path
            d="M28 8H12a4 4 0 00-4 4v20m32-12v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-12l-8.172-8.172a4 4 0 00-5.656 0L28 12m12 0H16m24 0v20"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>

      <p className="text-lg font-semibold text-gray-700 mb-2">
        Drag and drop your document here
      </p>
      <p className="text-sm text-gray-500 mb-4">
        or click to select from computer (PDF, DOCX, TXT)
      </p>

      <input
        type="file"
        accept=".pdf,.docx,.txt"
        onChange={handleFileChange}
        disabled={isLoading}
        className="hidden"
        id="file-input"
      />

      <label htmlFor="file-input">
        <button
          type="button"
          onClick={handleButtonClick}
          disabled={isLoading}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors cursor-pointer"
        >
          {isLoading ? "Uploading..." : "Select File"}
        </button>
      </label>
    </div>
  );
};
