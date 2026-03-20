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


# ============================================================================
# INFORMATION DENSITY METRICS (NEW)
# ============================================================================

class ExtractedFact(BaseModel):
    """A single fact extracted from the document."""
    fact: str = Field(..., description="The extracted fact (e.g., 'Eligible age: 18+')")
    fact_type: str = Field(..., description="Type: amount, threshold, date, entity, condition, penalty, etc.")
    source_text: str = Field(..., description="Original text where fact was found")
    importance_score: float = Field(..., description="0-1, how critical this fact is")
    

class InformationDensityMetrics(BaseModel):
    """Comprehensive Information Density measurement for compressed content."""
    doc_id: str
    key_facts_extracted: List[ExtractedFact] = Field(..., description="Facts identified in original")
    key_facts_preserved: List[ExtractedFact] = Field(..., description="Facts remaining after compression")
    facts_count_original: int = Field(..., description="Total facts in original document")
    facts_count_preserved: int = Field(..., description="Facts that survived compression")
    tokens_consumed: int = Field(..., description="Tokens in compressed output")
    
    # Core metric
    information_density: float = Field(..., description="facts_preserved / tokens_consumed (higher is better)")
    preservation_rate: float = Field(..., description="% of facts that survived (0-1)")
    
    # Quality grades
    density_grade: str = Field(..., description="A+, A, B, C, D based on density")
    preservation_grade: str = Field(..., description="A+, A, B, C, D based on fact preservation")
    overall_grade: str = Field(..., description="Combined quality grade")
    
    # Detailed breakdown
    facts_by_type: Dict[str, int] = Field(..., description="Count of each fact type preserved")
    critical_facts_preserved: int = Field(..., description="High-importance facts preserved")
    
    # Metadata
    compression_stats: CompressionStats
    generation_time_seconds: Optional[float] = None


class DensityEvaluationRequest(BaseModel):
    """Request to evaluate Information Density for a document."""
    doc_id: str
    include_details: bool = Field(default=True, description="Include fact-by-fact breakdown")


class DensityComparisonResponse(BaseModel):
    """Comparison of density before and after compression."""
    doc_id: str
    original_density: float = Field(..., description="Facts/tokens in original")
    compressed_density: float = Field(..., description="Facts/tokens in compressed")
    density_improvement: float = Field(..., description="% improvement in density")
    efficiency_rating: str = Field(..., description="Excellent/Good/Fair/Poor")
    recommendation: str = Field(..., description="Actionable feedback")


class EnergyMetrics(BaseModel):
    """Environmental and cost impact metrics."""
    tokens_saved: int
    joules_saved: float = Field(..., description="Energy saved in joules")
    co2_grams_saved: float = Field(..., description="Carbon emissions saved in grams")
    cost_saved_usd: float = Field(..., description="Cost saved in USD")
    carbon_equivalent: str = Field(..., description="Human-friendly comparison (e.g., 'equivalent to Xkm car drive')")
    energy_savings_human: str = Field(..., description="Human-readable energy savings")
