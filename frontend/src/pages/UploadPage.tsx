// UploadPage.tsx
// Main upload and document dashboard page

import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { listDocuments } from "../api/client";
import { UploadArea } from "../components/UploadArea";

interface Document {
  doc_id: string;
  filename: string;
  upload_time: string;
  total_tokens: number;
  chunk_count: number;
  status: string;
}

export const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [uploadMessage, setUploadMessage] = useState("");
  const [uploadError, setUploadError] = useState("");

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      setIsLoading(true);
      const result = await listDocuments();
      setDocuments(result.documents || []);
    } catch (error: any) {
      console.error("Failed to load documents:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUploadSuccess = (docId: string) => {
    setUploadMessage("✓ Document uploaded and processed successfully!");
    setUploadError("");
    loadDocuments();

    // Redirect to document view after 2 seconds
    setTimeout(() => {
      navigate(`/document/${docId}`);
    }, 2000);
  };

  const handleUploadError = (error: string) => {
    setUploadError(error);
    setUploadMessage("");
  };

  const handleDocumentClick = (docId: string) => {
    navigate(`/document/${docId}`);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-700 to-blue-900 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-6 py-12">
          <h1 className="text-4xl font-bold mb-2">
            AI Legislative Analyzer
          </h1>
          <p className="text-blue-100 text-lg">
            Understand Indian laws and policies in simple language
          </p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-12">
        {/* Upload Section */}
        <div className="mb-12">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">
            Upload a Document
          </h2>

          <div className="bg-white rounded-lg shadow-lg p-8 mb-6">
            <UploadArea
              onUploadSuccess={handleUploadSuccess}
              onUploadError={handleUploadError}
            />
          </div>

          {uploadMessage && (
            <div className="bg-green-50 border-2 border-green-200 rounded-lg p-4 text-green-800 flex items-center justify-between">
              <span>✓ {uploadMessage}</span>
              <button
                onClick={() => setUploadMessage("")}
                className="text-green-600 hover:text-green-800 font-semibold"
              >
                ×
              </button>
            </div>
          )}

          {uploadError && (
            <div className="bg-red-50 border-2 border-red-200 rounded-lg p-4 text-red-800 flex items-center justify-between">
              <div>
                <p className="font-semibold">✗ Upload Error</p>
                <p className="text-sm mt-1">{uploadError}</p>
              </div>
              <button
                onClick={() => setUploadError("")}
                className="text-red-600 hover:text-red-800 font-semibold flex-shrink-0"
              >
                ×
              </button>
            </div>
          )}
        </div>

        {/* Documents List */}
        <div>
          <h2 className="text-2xl font-bold text-gray-900 mb-6">
            Your Documents
          </h2>

          {isLoading ? (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-blue-600 border-t-transparent" />
              <p className="text-gray-600 mt-4">Loading documents...</p>
            </div>
          ) : documents.length === 0 ? (
            <div className="bg-white rounded-lg shadow-md p-8 text-center">
              <p className="text-gray-600 text-lg">
                No documents uploaded yet. Upload your first legal document above!
              </p>
            </div>
          ) : (
            <div className="grid gap-4">
              {documents.map((doc) => (
                <div
                  key={doc.doc_id}
                  onClick={() => handleDocumentClick(doc.doc_id)}
                  className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow cursor-pointer border-l-4 border-blue-600"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-gray-900 mb-2">
                        {doc.filename}
                      </h3>
                      <div className="flex gap-4 text-sm text-gray-600">
                        <span>📊 {doc.chunk_count} chunks</span>
                        <span>🔤 {doc.total_tokens.toLocaleString()} tokens</span>
                        <span
                          className={`px-2 py-1 rounded-full text-xs font-semibold ${
                            doc.status === "completed"
                              ? "bg-green-100 text-green-800"
                              : "bg-yellow-100 text-yellow-800"
                          }`}
                        >
                          {doc.status}
                        </span>
                      </div>
                    </div>
                    <div className="text-gray-400">→</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
