// SummaryView.tsx
// Displays the 3-section citizen-friendly summary of a document

import React, { useState, useEffect } from "react";
import { summarizeDocument } from "../api/client";
import { EfficiencyBadge } from "./EfficiencyBadge";

interface SummaryViewProps {
  docId: string;
  filename: string;
  onError: (error: string) => void;
}

interface Summary {
  what_does_it_do: string;
  who_is_affected: string;
  key_changes: string;
  compression_stats: {
    compression_percentage: number;
    tokens_saved: number;
    original_tokens: number;
    compressed_tokens?: number;
  };
  generation_time_seconds: number;
}

export const SummaryView: React.FC<SummaryViewProps> = ({
  docId,
  filename,
  onError,
}) => {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadSummary = async () => {
      try {
        setIsLoading(true);
        const result = await summarizeDocument(docId, "citizen");
        setSummary(result);
      } catch (error: any) {
        onError(error.message || "Failed to generate summary");
      } finally {
        setIsLoading(false);
      }
    };

    loadSummary();
  }, [docId]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent mb-4" />
          <p className="text-gray-600">Generating citizen-friendly summary...</p>
          <p className="text-sm text-gray-500 mt-2">This may take a moment</p>
        </div>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <p className="text-red-800">Failed to generate summary</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Document Header */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white px-6 py-4 rounded-lg">
        <h1 className="text-2xl font-bold mb-2">{filename}</h1>
        <p className="text-blue-100">
          Citizen-Friendly Summary | Generated in {summary.generation_time_seconds.toFixed(1)}s
        </p>
      </div>

      {/* Efficiency Stats */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-600 mb-2">Compression Efficiency</p>
            <EfficiencyBadge
              compression_percentage={summary.compression_stats.compression_percentage}
              tokens_saved={summary.compression_stats.tokens_saved}
              original_tokens={summary.compression_stats.original_tokens}
            />
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-600">Tokens Used</p>
            <p className="text-2xl font-bold text-blue-600">
              {summary.compression_stats.compressed_tokens ?? 
                (summary.compression_stats.original_tokens - summary.compression_stats.tokens_saved)}
            </p>
          </div>
        </div>
      </div>

      {/* Three-Section Summary */}
      <div className="grid gap-6">
        {/* What Does It Do */}
        <div className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-3 h-3 bg-blue-600 rounded-full" />
            <h2 className="text-xl font-bold text-gray-900">
              What This Bill Does
            </h2>
          </div>
          <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
            {summary.what_does_it_do}
          </p>
        </div>

        {/* Who Is Affected */}
        <div className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-3 h-3 bg-green-600 rounded-full" />
            <h2 className="text-xl font-bold text-gray-900">Who Is Affected</h2>
          </div>
          <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
            {summary.who_is_affected}
          </p>
        </div>

        {/* Key Changes */}
        <div className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-3 h-3 bg-amber-600 rounded-full" />
            <h2 className="text-xl font-bold text-gray-900">
              Key Changes from Existing Law
            </h2>
          </div>
          <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
            {summary.key_changes}
          </p>
        </div>
      </div>

      {/* Footer Note */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <p className="text-xs text-gray-600">
          💡 This summary is generated using AI and compressed to save tokens and time.
          For official or legal purposes, refer to the full document text.
        </p>
      </div>
    </div>
  );
};
