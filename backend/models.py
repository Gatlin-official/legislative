"""
Pydantic models for request/response validation across the API.
These schemas ensure type safety and API documentation (FastAPI auto-generates OpenAPI docs from these).
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


class DocumentUploadResponse(BaseModel):
    """Response after successfully uploading and ingesting a document."""
    doc_id: str = Field(..., description="Unique document identifier")
    filename: str
    status: str = Field(default="ingesting", description="Current processing status")
    total_chunks: int = Field(default=0, description="Number of chunks after splitting")
    timestamp: datetime


class DocumentMetadata(BaseModel):
    """Metadata for a document in the system."""
    doc_id: str
    filename: str
    upload_time: datetime
    total_tokens: int = Field(description="Total tokens in original document")
    chunk_count: int
    status: str = Field(description="completed, ingesting, failed")


class DocumentListResponse(BaseModel):
    """List of all documents with their metadata."""
    documents: List[DocumentMetadata]
    count: int


class CompressionStats(BaseModel):
    """Statistics about token compression for a single query/chunk."""
    original_tokens: int
    compressed_tokens: int
    tokens_saved: int
    compression_ratio: float = Field(description="Ratio of compressed/original tokens")
    compression_percentage: float = Field(description="% of tokens removed")


class QueryRequest(BaseModel):
    """User's question for RAG Q&A system."""
    doc_id: str
    question: str = Field(..., description="User's question about the document")


class QueryResponse(BaseModel):
    """Response from RAG pipeline including answer and compression stats."""
    answer: str
    compression_stats: CompressionStats
    retrieved_sources: List[Dict] = Field(description="Metadata of retrieved chunks")
    doc_id: str


class SummarizeRequest(BaseModel):
    """Request to summarize a document using MapReduce chain."""
    doc_id: str
    style: str = Field(default="citizen", description="Summary style: citizen, technical, executive")


class SummaryResponse(BaseModel):
    """Three-section summary of a legislative document."""
    doc_id: str
    what_does_it_do: str = Field(description="What this bill/policy does")
    who_is_affected: str = Field(description="Who it affects - population groups, sectors, etc.")
    key_changes: str = Field(description="Key changes from existing law")
    compression_stats: CompressionStats
    generation_time_seconds: float


class DocumentStatsResponse(BaseModel):
    """Aggregate token compression statistics for a document."""
    doc_id: str
    filename: str
    total_queries: int
    total_tokens_used: int
    total_tokens_saved: int
    average_compression_ratio: float
    efficiency_score: float = Field(description="0-100, green if > 70%")
