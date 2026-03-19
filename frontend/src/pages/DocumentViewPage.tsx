// DocumentViewPage.tsx
// Main document view with split panel: summary on left, chat on right

import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { listDocuments } from "../api/client";
import { SummaryView } from "../components/SummaryView";
import { ChatInterface } from "../components/ChatInterface";

interface Document {
  doc_id: string;
  filename: string;
  upload_time: string;
  total_tokens: number;
  chunk_count: number;
  status: string;
}

export const DocumentViewPage: React.FC = () => {
  const { docId } = useParams<{ docId: string }>();
  const navigate = useNavigate();

  const [document, setDocument] = useState<Document | null>(null);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<"summary" | "chat">("summary");

  useEffect(() => {
    const loadDocument = async () => {
      try {
        const result = await listDocuments();
        const doc = result.documents.find((d: Document) => d.doc_id === docId);
        if (!doc) {
          setError("Document not found");
          return;
        }
        setDocument(doc);
      } catch (err: any) {
        setError(err.message || "Failed to load document");
      }
    };

    if (docId) {
      loadDocument();
    }
  }, [docId]);

  if (error) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-lg p-8 text-center max-w-md">
          <div className="text-red-600 text-4xl mb-4">⚠️</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Error</h1>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={() => navigate("/")}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  if (!document) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent mb-4" />
          <p className="text-gray-600">Loading document...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <div className="bg-white shadow-md">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <button
            onClick={() => navigate("/")}
            className="text-blue-600 hover:text-blue-800 flex items-center gap-2 font-semibold"
          >
            ← Back to Dashboard
          </button>
          <h1 className="text-2xl font-bold text-gray-900 text-center flex-1">
            {document.filename}
          </h1>
          <div className="w-24" /> {/* Spacer for balance */}
        </div>
      </div>

      {/* Main Content - Responsive Split View */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-200px)]">
          {/* Left Panel - Summary */}
          <div
            className={`lg:col-span-2 ${
              activeTab === "summary" ? "block" : "hidden lg:block"
            } overflow-auto bg-white rounded-lg shadow-md p-6`}
          >
            <SummaryView
              docId={document.doc_id}
              filename={document.filename}
              onError={setError}
            />
          </div>

          {/* Right Panel - Chat */}
          <div
            className={`lg:col-span-1 ${
              activeTab === "chat" ? "block" : "hidden lg:block"
            }`}
          >
            <ChatInterface docId={document.doc_id} onError={setError} />
          </div>
        </div>

        {/* Mobile Tab Switcher */}
        <div className="flex gap-4 mt-6 lg:hidden">
          <button
            onClick={() => setActiveTab("summary")}
            className={`flex-1 py-2 px-4 rounded-lg font-semibold transition-colors ${
              activeTab === "summary"
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-900 border border-gray-300"
            }`}
          >
            Summary
          </button>
          <button
            onClick={() => setActiveTab("chat")}
            className={`flex-1 py-2 px-4 rounded-lg font-semibold transition-colors ${
              activeTab === "chat"
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-900 border border-gray-300"
            }`}
          >
            Ask Questions
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="fixed bottom-4 right-4 bg-red-100 border-2 border-red-600 text-red-800 px-6 py-4 rounded-lg max-w-md">
          {error}
        </div>
      )}
    </div>
  );
};
