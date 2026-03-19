import axios from "axios";

// Configure API base URL - using Vite's import.meta.env instead of process.env
// Default to http://localhost:8000 if VITE_API_URL is not set
const API_BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Document management
export const uploadDocument = async (file: File) => {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const listDocuments = async () => {
  const response = await api.get("/documents");
  return response.data;
};

export const getDocumentStats = async (docId: string) => {
  const response = await api.get(`/stats/${docId}`);
  return response.data;
};

// Q&A and RAG
export const queryDocument = async (docId: string, question: string) => {
  const response = await api.post(`/ask/${docId}`, {
    doc_id: docId,
    question: question,
  });
  return response.data;
};

export const queryDocumentStream = async (
  docId: string,
  question: string,
  onChunk: (chunk: string) => void
) => {
  const eventSource = new EventSource(
    `${API_BASE_URL}/ask/${docId}/stream?question=${encodeURIComponent(question)}`
  );

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.chunk) {
        onChunk(data.chunk);
      }
    } catch (e) {
      console.error("Error parsing stream data:", e);
    }
  };

  eventSource.onerror = () => {
    eventSource.close();
  };

  return eventSource;
};

// Summarization
export const summarizeDocument = async (docId: string, style?: string) => {
  const response = await api.post(`/summarize/${docId}`, {
    doc_id: docId,
    style: style || "citizen",
  });
  return response.data;
};

// Health check
export const healthCheck = async () => {
  const response = await api.get("/health");
  return response.data;
};

export default api;
