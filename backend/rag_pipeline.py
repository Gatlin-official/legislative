"""
RAG (Retrieval-Augmented Generation) pipeline: retrieve relevant context and generate answers.
Updated for llama3.2:3b - optimized for efficient token processing with reduced chunks.

Design rationale:
- RAG improves LLM accuracy by grounding responses in retrieved document content
- Compression happens BEFORE LLM call to minimize tokens/cost
- llama3.2:3b works efficiently with our optimized chunk size (2000 chars) and compression
- Streaming response allows users to see answers appearing in real-time
- Chain is modular: easy to swap retriever, compressor, or LLM backend
"""

import logging
import os
from typing import List, Dict, AsyncGenerator, Tuple
import tiktoken

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
from langchain_core.callbacks.base import BaseCallbackHandler

from vector_store import VectorStore
from compression import CompressionChain

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    Retrieval-Augmented Generation pipeline for Q&A on legal documents.
    Core flow: Question → Retrieve → Compress → Generate answer
    """
    
    def __init__(self, vector_store: VectorStore, compression_chain: CompressionChain, 
                 llm: BaseChatModel):
        """
        Initialize RAG pipeline.
        
        Args:
            vector_store: Initialized VectorStore for retrieval
            compression_chain: CompressionChain for token reduction
            llm: BaseChatModel instance (OpenAI, local, etc.) implementing LangChain interface
        """
        self.vector_store = vector_store
        self.compression_chain = compression_chain
        self.llm = llm  # Updated for llama3.2:3b - efficient token usage
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        logger.info("RAGPipeline initialized with llama3.2:3b optimizations")
    
    def query(self, doc_id: str, question: str, n_retrieve: int = 5) -> Dict:
        """
        Synchronous Q&A query: retrieve context, compress, generate answer, return stats.
        
        This is the main RAG workflow:
        1. Retrieve most relevant chunks via semantic search
        2. Compress retrieved context to reduce tokens
        3. Build prompt with compressed context + question
        4. Generate answer using LLM
        5. Return answer + compression statistics
        
        Args:
            doc_id: Document ID to query
            question: User's question about the document
            n_retrieve: Number of chunks to retrieve (default: 5)
        
        Returns:
            Dict with:
            - answer: Generated answer
            - compression_stats: Token efficiency metrics
            - retrieved_sources: Metadata of chunks used
        """
        try:
            logger.info(f"Starting RAG query for doc_id={doc_id}")
            
            # Step 1: Retrieve relevant chunks via semantic search
            retrieved_chunks = self.vector_store.query(
                doc_id=doc_id,
                query_text=question,
                n_results=n_retrieve
            )
            
            if not retrieved_chunks:
                logger.warning(f"No chunks retrieved for query in doc_id={doc_id}")
                return {
                    "answer": "I could not find relevant information in the document to answer your question.",
                    "compression_stats": {
                        "original_tokens": 0,
                        "compressed_tokens": 0,
                        "tokens_saved": 0,
                        "compression_ratio": 0,
                        "compression_percentage": 0,
                    },
                    "retrieved_sources": [],
                }
            
            # Step 2: Compress retrieved context
            compressed_context, compression_stats = self.compression_chain.compress_retrieved_context(
                retrieved_chunks
            )
            
            logger.info(f"Retrieved and compressed context: {compression_stats['compression_percentage']:.1f}% reduction")
            
            # Step 3: Build prompt with system context + retrieved documents + question
            prompt_messages = self._build_prompt(question, compressed_context)
            
            # Step 4: Generate answer using LLM
            answer = self.llm.invoke(prompt_messages).content
            
            # Step 5: Return results with source tracking
            source_metadata = [
                {
                    "source": chunk["metadata"].get("source"),
                    "similarity": chunk["similarity_score"],
                    "token_count": chunk["metadata"].get("token_count"),
                }
                for chunk in retrieved_chunks
            ]
            
            result = {
                "answer": answer,
                "compression_stats": compression_stats,
                "retrieved_sources": source_metadata,
            }
            
            logger.info(f"RAG query completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"RAG query failed: {e}", exc_info=True)
            raise
    
    def query_stream(self, doc_id: str, question: str, n_retrieve: int = 5) -> Tuple[AsyncGenerator, Dict]:
        """
        Streaming Q&A query: same as query() but returns answer as async generator.
        
        Allows frontend to display answer text as it's being generated (better UX).
        
        Returns:
            (async_generator_for_answer_text, dict_with_compression_stats_and_sources)
        """
        try:
            # Step 1: Retrieve and compress (same as sync query)
            retrieved_chunks = self.vector_store.query(
                doc_id=doc_id,
                query_text=question,
                n_results=n_retrieve
            )
            
            if not retrieved_chunks:
                async def empty_generator():
                    yield "I could not find relevant information in the document to answer your question."
                
                return empty_generator(), {
                    "compression_stats": {
                        "original_tokens": 0,
                        "compressed_tokens": 0,
                        "tokens_saved": 0,
                        "compression_ratio": 0,
                        "compression_percentage": 0,
                    },
                    "retrieved_sources": [],
                }
            
            # Compress context
            compressed_context, compression_stats = self.compression_chain.compress_retrieved_context(
                retrieved_chunks
            )
            
            # Build prompt
            prompt_messages = self._build_prompt(question, compressed_context)
            
            # Step 2: Generate response
            # Note: Simplified non-streaming version for compatibility
            async def answer_generator():
                """Async generator that yields the complete answer."""
                # Invoke LLM
                response = await self.llm.ainvoke(prompt_messages)
                
                # Yield the complete response (non-streaming for now)
                yield response.content if hasattr(response, 'content') else str(response)
            
            # Source metadata
            source_metadata = [
                {
                    "source": chunk["metadata"].get("source"),
                    "similarity": chunk["similarity_score"],
                    "token_count": chunk["metadata"].get("token_count"),
                }
                for chunk in retrieved_chunks
            ]
            
            return answer_generator(), {
                "compression_stats": compression_stats,
                "retrieved_sources": source_metadata,
            }
            
        except Exception as e:
            logger.error(f"Streaming RAG query failed: {e}", exc_info=True)
            raise
    
    def _build_prompt(self, question: str, compressed_context: str) -> List:
        """
        Build LangChain message list for RAG prompt.
        
        Format:
        - System message: role + behavior instructions
        - Context: compressed document chunks
        - User message: the question
        
        This structure guides LLM to use context for answers.
        """
        system_message = SystemMessage(
            content="""You are an expert legal analyst specializing in Indian legislative documents.
Your task is to explain complex legal and policy documents in simple, citizen-friendly language.

Guidelines:
1. Answer ONLY based on the provided document chunks
2. If information is not in the document, say "This is not covered in the provided document"
3. Avoid legal jargon where possible; explain terms in simple language
4. Structure answers clearly with bullet points for readability
5. If the question is ambiguous, ask for clarification rather than guessing

Remember: You are explaining laws to citizens, not lawyers. Prioritize clarity."""
        )
        
        context_message = HumanMessage(
            content=f"""Here are the relevant sections from the document:

{compressed_context}"""
        )
        
        question_message = HumanMessage(
            content=f"""Based on the above document sections, please answer this citizen's question:

{question}"""
        )
        
        return [system_message, context_message, question_message]
    
    def get_query_statistics(self, compression_stats: Dict) -> Dict:
        """
        Convert compression stats to metrics for UI display.
        
        Returns formatted stats for efficiency badge.
        """
        return {
            "tokens_used": compression_stats["compressed_tokens"],
            "tokens_saved": compression_stats["tokens_saved"],
            "efficiency_score": 100 - int(compression_stats["compression_ratio"] * 100),
            "savings_percentage": compression_stats["compression_percentage"],
        }


class AsyncRAGPipeline(RAGPipeline):
    """
    Async variant of RAGPipeline for non-blocking concurrent queries.
    Useful for FastAPI endpoints that need to handle multiple simultaneous requests.
    """
    
    async def query_async(self, doc_id: str, question: str, n_retrieve: int = 5) -> Dict:
        """
        Async version of query().
        Same logic, but non-blocking for concurrent request handling.
        """
        try:
            logger.info(f"Starting async RAG query for doc_id={doc_id}")
            
            # Retrieve chunks (typically fast, no I/O blocking needed)
            retrieved_chunks = self.vector_store.query(
                doc_id=doc_id,
                query_text=question,
                n_results=n_retrieve
            )
            
            if not retrieved_chunks:
                return {
                    "answer": "I could not find relevant information in the document to answer your question.",
                    "compression_stats": {
                        "original_tokens": 0,
                        "compressed_tokens": 0,
                        "tokens_saved": 0,
                        "compression_ratio": 0,
                        "compression_percentage": 0,
                    },
                    "retrieved_sources": [],
                }
            
            # Compress context
            compressed_context, compression_stats = self.compression_chain.compress_retrieved_context(
                retrieved_chunks
            )
            
            # Build prompt
            prompt_messages = self._build_prompt(question, compressed_context)
            
            # Async LLM call
            response = await self.llm.ainvoke(prompt_messages)
            answer = response.content
            
            # Source metadata
            source_metadata = [
                {
                    "source": chunk["metadata"].get("source"),
                    "similarity": chunk["similarity_score"],
                    "token_count": chunk["metadata"].get("token_count"),
                }
                for chunk in retrieved_chunks
            ]
            
            return {
                "answer": answer,
                "compression_stats": compression_stats,
                "retrieved_sources": source_metadata,
            }
            
        except Exception as e:
            logger.error(f"Async RAG query failed: {e}", exc_info=True)
            raise
