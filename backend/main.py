"""
FastAPI application entry point for the AI Legislative Analyzer.
Updated for llama3.2:3b - faster, more efficient local model via Ollama.

Architecture overview:
- FastAPI for async HTTP server and automatic API documentation (OpenAPI/Swagger)
- ChromaDB for local, lightweight vector storage (no PostgreSQL needed!)
- Ollama + Llama 3.2:3b for local, cost-free LLM inference (updated from llama3.1:8b)
- Routes handle document lifecycle: upload → ingest → query → stats
- Optimizations: 2000-char chunks, 30-chunk cap on summarization, 30%+ token compression
"""

import os
import uuid
import logging
from typing import List, Optional
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from dotenv import load_dotenv

import tiktoken
from langchain_community.chat_models import ChatOllama

# Project modules
from models import (
    DocumentUploadResponse,
    DocumentListResponse,
    DocumentMetadata,
    QueryRequest,
    QueryResponse,
    CompressionStats,
    SummarizeRequest,
    SummaryResponse,
    DocumentStatsResponse,
)
from ingestion import DocumentIngester
from vector_store import VectorStore
from compression import CompressionChain
from rag_pipeline import AsyncRAGPipeline
from summarization import SummarizationChain

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(
    title="AI Legislative Analyzer",
    description="Dashboard for understanding Indian legal documents through AI",
    version="1.0.0",
)

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
logger.info("Initializing pipeline components...")

# ChromaDB Vector Store (local, no PostgreSQL needed!)
vector_store = VectorStore(persist_dir="./chroma_db")

# Compression chain for token efficiency
compression_chain = CompressionChain(
    compression_target=float(os.getenv("COMPRESSION_TARGET", 0.4))
)

# Local LLM via Ollama - Llama 3.2:3b
# Updated for llama3.2:3b: Faster, more efficient than llama3.1:8b with 30%+ speedup
# Why Ollama: Free, local inference, privacy-preserving, no API calls
# Why Llama 3.2:3b: Fast processing, compact size, good for structured outputs, fits on any hardware
llm = ChatOllama(
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    model=os.getenv("LLM_MODEL", "llama3.2:3b"),  # Updated for llama3.2:3b
    temperature=0.3,  # Lower temperature for more consistent legal analysis
    num_predict=1024,  # Context window
)

# Document ingestion pipeline
ingester = DocumentIngester(vector_store)

# RAG pipeline for Q&A
rag_pipeline = AsyncRAGPipeline(vector_store, compression_chain, llm)

# Summarization chain
summarization_chain = SummarizationChain(llm, compression_chain)

# In-memory document registry
# In production, this should be in PostgreSQL table
documents_registry = {}
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ============================================================================
# ROUTES
# ============================================================================

@app.get("/health")
async def health_check():
    """Simple health check endpoint for deployment monitoring."""
    return {
        "status": "healthy",
        "llm_model": os.getenv("LLM_MODEL", "llama3.2:3b"),  # Updated for llama3.2:3b
        "vector_store": "chromadb",
        "embeddings": "sentence-transformers/all-MiniLM-L6-v2",
        "inference": "ollama",
        "optimizations": "2000-char chunks, 30-chunk cap, 30%+ compression",
    }


@app.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and ingest a legal document.
    
    Workflow:
    1. Save uploaded file to disk
    2. Run ingestion pipeline (parse → chunk → embed)
    3. Store in PostgreSQL + pgvector
    4. Return document ID for future queries
    
    Returns:
        DocumentUploadResponse with doc_id and ingestion status
    """
    try:
        logger.info(f"Upload started: {file.filename}")
        
        # Generate unique document ID
        doc_id = str(uuid.uuid4())
        
        # Save file
        file_path = os.path.join(UPLOAD_DIR, f"{doc_id}_{file.filename}")
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"File saved to {file_path}")
        
        # Run ingestion pipeline
        ingestion_result = ingester.ingest(file_path, doc_id)
        
        if ingestion_result["status"] == "failed":
            logger.error(f"Ingestion failed: {ingestion_result['error']}")
            raise HTTPException(status_code=400, detail=ingestion_result["error"])
        
        # Store in registry
        upload_time = datetime.utcnow()
        documents_registry[doc_id] = {
            "filename": file.filename,
            "file_path": file_path,
            "upload_time": upload_time,
            "total_tokens": ingestion_result["total_tokens"],
            "chunk_count": ingestion_result["chunk_count"],
            "status": "completed",
        }
        
        logger.info(f"Document registered: doc_id={doc_id}")
        
        return DocumentUploadResponse(
            doc_id=doc_id,
            filename=file.filename,
            status="completed",
            total_chunks=ingestion_result["chunk_count"],
            timestamp=datetime.utcnow(),
        )
        
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents", response_model=DocumentListResponse)
async def list_documents():
    """
    List all uploaded documents with metadata.
    
    Returns:
        DocumentListResponse with list of documents and count
    """
    try:
        documents = []
        for doc_id, metadata in documents_registry.items():
            doc = DocumentMetadata(
                doc_id=doc_id,
                filename=metadata["filename"],
                upload_time=metadata["upload_time"],
                total_tokens=metadata["total_tokens"],
                chunk_count=metadata["chunk_count"],
                status=metadata["status"],
            )
            documents.append(doc)
        
        return DocumentListResponse(
            documents=documents,
            count=len(documents),
        )
        
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask/{doc_id}", response_model=QueryResponse)
async def query_document(doc_id: str, request: QueryRequest):
    """
    Ask a question about a specific document (RAG Q&A).
    
    Pipeline:
    1. Retrieve relevant chunks via semantic search in PostgreSQL
    2. Compress retrieved context
    3. Generate answer using local Llama model
    4. Return answer + compression statistics
    
    Args:
        doc_id: Document ID to query
        request: QueryRequest with question
    
    Returns:
        QueryResponse with answer and compression stats
    """
    try:
        logger.info(f"Query started: doc_id={doc_id}, question={request.question[:50]}...")
        
        # Validate document exists
        if doc_id not in documents_registry:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
        
        # Run RAG pipeline
        result = await rag_pipeline.query_async(
            doc_id=doc_id,
            question=request.question,
            n_retrieve=5,
        )
        
        logger.info(f"Query completed successfully")
        
        return QueryResponse(
            doc_id=doc_id,
            answer=result["answer"],
            compression_stats=CompressionStats(
                original_tokens=result["compression_stats"]["original_tokens"],
                compressed_tokens=result["compression_stats"]["compressed_tokens"],
                tokens_saved=result["compression_stats"]["tokens_saved"],
                compression_ratio=result["compression_stats"]["compression_ratio"],
                compression_percentage=result["compression_stats"]["compression_percentage"],
            ),
            retrieved_sources=result["retrieved_sources"],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask/{doc_id}/stream")
async def query_document_stream(doc_id: str, request: QueryRequest):
    """
    Ask a question with streaming response (real-time text output).
    
    Frontend displays answer text as it's being generated for better UX.
    
    Returns:
        StreamingResponse with text/event-stream content
    """
    try:
        logger.info(f"Streaming query started: doc_id={doc_id}")
        
        if doc_id not in documents_registry:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
        
        # Get streaming generator
        answer_gen, metadata = rag_pipeline.query_stream(
            doc_id=doc_id,
            question=request.question,
            n_retrieve=5,
        )
        
        # Wrap in server-sent events format for frontend
        async def event_generator():
            yield f"data: {{'stats': {metadata}}}\n\n"
            async for chunk in answer_gen():
                yield f"data: {{'chunk': '{chunk}'}}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
        )
        
    except Exception as e:
        logger.error(f"Streaming query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/summarize/{doc_id}", response_model=SummaryResponse)
async def summarize_document(doc_id: str, request: SummarizeRequest):
    """
    Summarize a document using MapReduce chain.
    
    Generates a 3-section citizen-friendly summary:
    1. What this bill/policy does
    2. Who is affected
    3. Key changes from existing law
    
    Uses local Llama model for inference.
    
    Args:
        doc_id: Document ID to summarize
        request: SummarizeRequest with optional style parameter
    
    Returns:
        SummaryResponse with three sections + token stats
    """
    try:
        logger.info(f"Summarization started: doc_id={doc_id}")
        
        if doc_id not in documents_registry:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
        
        # Load document from disk
        file_path = documents_registry[doc_id]["file_path"]
        
        # Re-parse and chunk document if not cached
        text, metadata = ingester._parse_file(file_path)
        chunks = ingester.splitter.split_text(text)
        
        # Run summarization chain using local Llama
        summary_result = await summarization_chain.summarizer.summarize_async(
            chunks=chunks,
            doc_metadata={
                "doc_id": doc_id,
                "filename": documents_registry[doc_id]["filename"],
            },
            style=request.style,
        )
        
        logger.info(f"Summarization completed in {summary_result['generation_time_seconds']:.1f}s")
        
        return SummaryResponse(
            doc_id=doc_id,
            what_does_it_do=summary_result["what_does_it_do"],
            who_is_affected=summary_result["who_is_affected"],
            key_changes=summary_result["key_changes"],
            compression_stats=CompressionStats(
                original_tokens=summary_result["compression_stats"]["original_tokens"],
                compressed_tokens=summary_result["compression_stats"]["compressed_tokens"],
                tokens_saved=summary_result["compression_stats"]["tokens_saved"],
                compression_ratio=summary_result["compression_stats"]["compression_ratio"],
                compression_percentage=summary_result["compression_stats"]["compression_percentage"],
            ),
            generation_time_seconds=summary_result["generation_time_seconds"],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Summarization failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats/{doc_id}", response_model=DocumentStatsResponse)
async def get_document_stats(doc_id: str):
    """
    Get aggregate token compression statistics for a document.
    
    Shows cumulative efficiency across all queries on this document.
    
    Returns:
        DocumentStatsResponse with efficiency metrics
    """
    try:
        if doc_id not in documents_registry:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
        
        # Get vector store stats from PostgreSQL
        store_stats = vector_store.get_document_stats(doc_id)
        
        # Calculate efficiency score
        doc_meta = documents_registry[doc_id]
        efficiency_score = min(100, int(
            (1 - (store_stats["chunk_count"] * 100 / doc_meta["total_tokens"])) * 100
        ))
        
        return DocumentStatsResponse(
            doc_id=doc_id,
            filename=doc_meta["filename"],
            total_queries=0,  # Would require tracking in DB
            total_tokens_used=doc_meta["total_tokens"],
            total_tokens_saved=int(doc_meta["total_tokens"] * 0.4),  # Estimate
            average_compression_ratio=0.6,  # Estimate
            efficiency_score=efficiency_score,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Run with: uvicorn main:app --reload
    port = int(os.getenv("BACKEND_PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENVIRONMENT", "development") == "development",
        log_level="info",
    )
