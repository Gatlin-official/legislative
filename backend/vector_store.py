"""
Vector store module using ChromaDB for local vector storage.
Simple, lightweight, no external database needed!

ChromaDB Benefits:
- Runs entirely locally in Python process
- No PostgreSQL required
- Automatic embedding generation
- Built-in similarity search
- Perfect for development and production
"""

import os
import logging
from typing import List, Dict
import chromadb
from langchain_community.embeddings import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)


class VectorStore:
    """Manages ChromaDB for embeddings and semantic search."""
    
    def __init__(self, persist_dir: str = "./chroma_db"):
        """
        Initialize ChromaDB client with persistent storage.
        
        Args:
            persist_dir: Directory where ChromaDB stores data (default: ./chroma_db)
        """
        self.persist_dir = persist_dir
        
        # Create persist directory if it doesn't exist
        os.makedirs(persist_dir, exist_ok=True)
        
        # Initialize ChromaDB with persistent storage
        self.client = chromadb.PersistentClient(path=persist_dir)
        
        # Initialize HuggingFace embeddings
        # all-MiniLM-L6-v2: 384-dimensional embeddings, lightweight, fast
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
        )
        
        logger.info(f"VectorStore initialized with ChromaDB at {persist_dir}")
    
    def add_chunks(self, doc_id: str, chunks: List[str], metadata: List[Dict]) -> int:
        """
        Add text chunks and embeddings to ChromaDB.
        
        Args:
            doc_id: Document ID
            chunks: List of text chunks
            metadata: List of metadata dicts (one per chunk)
        
        Returns:
            Number of chunks added
        """
        try:
            # Generate embeddings for all chunks
            embeddings_list = self.embeddings.embed_documents(chunks)
            
            # Get or create collection for this document
            collection = self.client.get_or_create_collection(
                name=f"doc_{doc_id}",
                metadata={"doc_id": doc_id}
            )
            
            # Prepare IDs for each chunk
            ids = [f"{doc_id}_chunk_{idx}" for idx in range(len(chunks))]
            
            # Add to ChromaDB
            collection.add(
                ids=ids,
                embeddings=embeddings_list,
                documents=chunks,
                metadatas=metadata
            )
            
            logger.info(f"Added {len(chunks)} chunks to ChromaDB for doc_id={doc_id}")
            return len(chunks)
            
        except Exception as e:
            logger.error(f"Failed to add chunks: {e}", exc_info=True)
            raise
    
    def query(self, doc_id: str, query_text: str, n_results: int = 5) -> List[Dict]:
        """
        Semantic search for relevant chunks using ChromaDB similarity.
        
        Args:
            doc_id: Document ID to search within
            query_text: User's question or search query
            n_results: Number of top chunks to retrieve (default: top-5)
        
        Returns:
            List of dicts with keys: text, metadata, similarity_score
        """
        try:
            # Get the collection for this document
            collection_name = f"doc_{doc_id}"
            
            try:
                collection = self.client.get_collection(name=collection_name)
            except ValueError:
                # Collection doesn't exist
                logger.warning(f"Collection {collection_name} not found")
                return []
            
            # Query ChromaDB with semantic search
            results = collection.query(
                query_texts=[query_text],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results: Convert distance to similarity (1 - distance)
            retrieved_chunks = []
            
            if results and results['documents'] and len(results['documents']) > 0:
                for doc, meta, distance in zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                ):
                    # ChromaDB returns cosine distance, convert to similarity
                    similarity = 1 - distance
                    retrieved_chunks.append({
                        "text": doc,
                        "metadata": meta,
                        "similarity_score": float(similarity),
                    })
            
            logger.info(f"Retrieved {len(retrieved_chunks)} chunks for query in doc_id={doc_id}")
            return retrieved_chunks
            
        except Exception as e:
            logger.error(f"Query failed: {e}", exc_info=True)
            return []
    
    def delete_document(self, doc_id: str) -> int:
        """
        Delete all chunks for a document (cleanup operation).
        
        Args:
            doc_id: Document ID to delete
        
        Returns:
            Number of chunks deleted
        """
        try:
            collection_name = f"doc_{doc_id}"
            
            try:
                collection = self.client.get_collection(name=collection_name)
                # Get count before deletion
                count = collection.count()
                # Delete collection
                self.client.delete_collection(name=collection_name)
                logger.info(f"Deleted {count} chunks for doc_id={doc_id}")
                return count
            except ValueError:
                logger.warning(f"Collection {collection_name} not found")
                return 0
                
        except Exception as e:
            logger.error(f"Failed to delete document: {e}", exc_info=True)
            raise
    
    def get_document_stats(self, doc_id: str) -> Dict:
        """Get statistics about a document's chunks."""
        try:
            collection_name = f"doc_{doc_id}"
            try:
                collection = self.client.get_collection(name=collection_name)
                return {
                    "doc_id": doc_id,
                    "chunk_count": collection.count(),
                    "collection_name": collection_name,
                }
            except ValueError:
                return {
                    "doc_id": doc_id,
                    "chunk_count": 0,
                    "error": "Collection not found"
                }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}", exc_info=True)
            return {"error": str(e)}
