// ChatInterface.tsx
// Interactive Q&A component for asking questions about documents

import React, { useState, useRef, useEffect } from "react";
import { queryDocument } from "../api/client";
import { EfficiencyBadge } from "./EfficiencyBadge";

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  tokens_saved?: number;
  compression_percentage?: number;
}

interface ChatInterfaceProps {
  docId: string;
  onError: (error: string) => void;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  docId,
  onError,
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [lastStats, setLastStats] = useState<any>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!input.trim()) return;

    // Add user message to chat
    const userMessage: Message = {
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await queryDocument(docId, input);

      const assistantMessage: Message = {
        role: "assistant",
        content: response.answer,
        timestamp: new Date(),
        tokens_saved: response.compression_stats.tokens_saved,
        compression_percentage:
          response.compression_stats.compression_percentage,
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setLastStats(response.compression_stats);
    } catch (error: any) {
      onError(error.message || "Failed to get response");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg border border-gray-200">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-8">
            <p className="text-lg font-semibold mb-2">Ask a Question</p>
            <p className="text-sm">
              Start by asking about what a section means or how it affects you
            </p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-900"
              }`}
            >
              <p className="text-sm mb-2 whitespace-pre-wrap">{msg.content}</p>
              {msg.role === "assistant" && msg.compression_percentage && (
                <div className="mt-2">
                  <EfficiencyBadge
                    compression_percentage={msg.compression_percentage}
                    tokens_saved={msg.tokens_saved ?? 0}
                    original_tokens={
                      msg.tokens_saved ? msg.tokens_saved / (msg.compression_percentage / 100) : 0
                    }
                  />
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-200 text-gray-900 px-4 py-2 rounded-lg">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-gray-600 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-gray-600 rounded-full animate-bounce delay-100" />
                <div className="w-2 h-2 bg-gray-600 rounded-full animate-bounce delay-200" />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 p-4 bg-gray-50">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && handleSendMessage()}
            disabled={isLoading}
            placeholder="Ask a question about this document..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleSendMessage}
            disabled={isLoading || !input.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
          >
            Send
          </button>
        </div>

        {lastStats && (
          <div className="mt-3 text-xs text-gray-600">
            Last query compression: {lastStats.compression_percentage.toFixed(1)}%
            ({lastStats.tokens_saved} tokens saved)
          </div>
        )}
      </div>
    </div>
  );
};
