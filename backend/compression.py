"""
Token compression layer: reduces LLM input by removing boilerplate and dense semantic extraction.
Updated for llama3.2:3b - aggressive token reduction targeting 30%+ savings.

Design rationale - WHY this is critical:
- Legislative documents have extensive boilerplate: definitions, citations, legal formatting
- Example: "hereinafter referred to as", repetitive "Section X subsection Y" patterns
- By removing ~30-40% of tokens before LLM call, we reduce:
  * API costs (proportional to tokens)
  * Latency (smaller prompt → faster processing with llama3.2:3b)
  * LLM context pollution (noise reduction improves quality)
- Compression stats exposing actual token savings validates efficiency claims to users

The compression strategy is aggressive for llama3.2:3b:
1. Strip common boilerplate patterns (regex-based)
2. Remove redundant legal citations and cross-references
3. Collapse numbered/lettered lists
4. Remove excessive "As provided in" and "According to" phrases
5. ALWAYS measure before/after with tiktoken for transparency
"""

import re
import logging
import tiktoken
from typing import Tuple, Dict, List

logger = logging.getLogger(__name__)


class TextCompressor:
    """Compresses legal document text by removing boilerplate and non-essential content."""
    
    def __init__(self, compression_target: float = 0.4):
        """
        Initialize compressor.
        
        Args:
            compression_target: Target compression ratio (0.4 = 40% reduction target)
                This is a goal, not guaranteed - depends on document content
        """
        self.compression_target = compression_target
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # Updated for llama3.2:3b - Aggressive boilerplate patterns (targeting 30%+ reduction)
        # These patterns are ordered by frequency/impact in Indian legislative documents
        self.boilerplate_patterns = [
            # HIGHEST IMPACT: Legal definition padding
            r"([\w\s]+),\s*hereinafter\s+referred\s+to\s+as\s+['\"]?(\w+)['\"]?",  # "X, hereinafter referred to as Y"
            r",\s*whether\s+or\s+not\s+[^\n]+",  # ", whether or not..."
            r",\s*as\s+the\s+case\s+may\s+be",  # ", as the case may be"
            r",\s*without\s+prejudice\s+to\s+[^\n]+",  # ", without prejudice to..."
            r",\s*notwithstanding\s+anything\s+contained\s+in\s+[^\n]+",  # ", notwithstanding anything..."
            
            # Redundant "Section X" references in cross-citations
            r"\(subject\s+to\s+(?:the\s+)?(?:provisions\s+of\s+)?sections?\s+[\d\w,\s\-and]+\)",
            r"in\s+accordance\s+with\s+(?:the\s+)?(?:provisions\s+of\s+)?[^\n\.]+",
            r"as\s+per\s+(?:the\s+)?(?:provisions\s+of\s+)?[^\n\.]+",
            
            # Numbered/lettered citations that repeat information
            r"\(\s*\d+\s*\)",  # (1), (2), etc.
            r"\(\s*[a-z]\s*\)",  # (a), (b), (c), etc.
            r"\(\s*[ivx]+\s*\)",  # (i), (ii), (iii), etc.
            
            # Repetitive "Section X" only when followed by another section reference
            r"Section\s+\d+\s+and\s+Section\s+",  # Compress "Section 5 and Section 6" to section references only
            r"Clause\s+\d+\s+(?=Clause|Section|Article)",
            
            # Empty brackets and parentheses
            r"\(\s*\)",
            r"\[\s*\]",
            
            # Repeated structure words at line start
            r"^\s*(?:Clause|Section|Article|Provision)\s*:?\s*",
            
            # "This Act" / "This section" when already in context
            r"\bthis\s+(?:Act|Section|Clause|Article)\b",
            
            # Excessive preparation phrases
            r"\bprovided\s+that\b",
            r"\bwhere(?:by|in|under|upon|to|fore)?\b",
            r"\bthereupon\b",
            r"\bthereof\b",
            
            # Multiple consecutive "Whereas" (preamble padding)
            r"(?:Whereas\s+[^\n]*\n){2,}",
            
            # Multiple spaces, tabs, and newlines
            r"\n\s*\n+",
            r"[ \t]{2,}",
            
            # Excessive indentation
            r"^\s{4,}",
        ]
        
        logger.info(f"TextCompressor initialized with AGGRESSIVE compression target {compression_target} for llama3.2:3b")
    
    def compress(self, text: str) -> Tuple[str, Dict]:
        """
        Compress text using aggressive pattern-based boilerplate removal.
        Updated for llama3.2:3b to target 30%+ token reduction.
        
        Returns:
            (compressed_text, compression_stats_dict)
        """
        original_tokens = len(self.tokenizer.encode(text))
        
        compressed_text = text
        
        # Apply aggressive pattern removal iteratively for maximum compression
        # Multiple passes catch cascading patterns (e.g., removing X creates opportunity to remove Y)
        for pass_num in range(2):  # Two passes for aggressive compression
            # Apply all boilerplate patterns
            for pattern in self.boilerplate_patterns:
                try:
                    compressed_text = re.sub(pattern, " ", compressed_text, flags=re.IGNORECASE | re.MULTILINE)
                except Exception as e:
                    logger.warning(f"Pattern failed: {pattern}, error: {e}")
        
        # Apply targeted compression methods
        compressed_text = self._remove_definitions_padding(compressed_text)
        compressed_text = self._remove_section_headers(compressed_text)
        compressed_text = self._remove_repeated_preamble(compressed_text)
        compressed_text = self._remove_redundant_phrases(compressed_text)
        compressed_text = self._normalize_whitespace(compressed_text)
        
        # Count tokens after compression
        compressed_tokens = len(self.tokenizer.encode(compressed_text))
        
        # Calculate statistics
        tokens_saved = original_tokens - compressed_tokens
        compression_ratio = compressed_tokens / original_tokens if original_tokens > 0 else 0
        compression_percentage = (1 - compression_ratio) * 100
        
        stats = {
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "tokens_saved": tokens_saved,
            "compression_ratio": compression_ratio,
            "compression_percentage": compression_percentage,
            "target_met": compression_percentage >= (self.compression_target * 100),
        }
        
        logger.info(
            f"Compression complete (llama3.2:3b optimized): {original_tokens} → {compressed_tokens} tokens "
            f"({compression_percentage:.1f}% reduction)"
        )
        
        return compressed_text, stats
    
    def compress_chunks(self, chunks: List[str]) -> Tuple[List[str], Dict]:
        """
        Compress multiple chunks with aggregate statistics.
        
        Args:
            chunks: List of text chunks to compress
        
        Returns:
            (compressed_chunks_list, aggregate_stats_dict)
        """
        compressed_chunks = []
        all_original_tokens = 0
        all_compressed_tokens = 0
        
        for chunk in chunks:
            compressed_chunk, _ = self.compress(chunk)
            compressed_chunks.append(compressed_chunk)
            
            all_original_tokens += len(self.tokenizer.encode(chunk))
            all_compressed_tokens += len(self.tokenizer.encode(compressed_chunk))
        
        aggregate_stats = {
            "original_tokens": all_original_tokens,
            "compressed_tokens": all_compressed_tokens,
            "tokens_saved": all_original_tokens - all_compressed_tokens,
            "compression_ratio": all_compressed_tokens / all_original_tokens if all_original_tokens > 0 else 0,
            "compression_percentage": ((1 - (all_compressed_tokens / all_original_tokens)) * 100 
                                      if all_original_tokens > 0 else 0),
            "chunk_count": len(chunks),
        }
        
        return compressed_chunks, aggregate_stats
    
    def _remove_definitions_padding(self, text: str) -> str:
        """
        Remove padding around definitions.
        Example: "Minister, hereinafter referred to as the 'Minister'" → "Minister"
        """
        # Replace "X, hereinafter referred to as 'Y'" with just "X"
        text = re.sub(
            r"(\w+),\s*hereinafter\s+referred\s+to\s+as\s+['\"]?(?:\w+)['\"]?",
            r"\1",
            text,
            flags=re.IGNORECASE
        )
        return text
    
    def _remove_section_headers(self, text: str) -> str:
        """
        Simplify section number formatting that repeats information.
        "Section 5, subsection (i), clause (a):" → Keep minimal
        """
        # Simplify but preserve section references for context
        text = re.sub(
            r"(Section|Article|Clause|Sub-[Ss]ection)\s+[\d\w]+\s*[.,]?\s*(?=\(|\d|[A-Z])",
            lambda m: m.group(1).lower() + " ",
            text
        )
        return text
    
    def _remove_repeated_preamble(self, text: str) -> str:
        """
        Remove multiple consecutive "Whereas" clauses (common in preambles).
        These are often decorative in legislative preambles.
        Strategy: Keep first and last "Whereas" for context, collapse middle ones.
        """
        # Split on Whereas
        parts = re.split(r"(Whereas[^\n]*\n)", text)
        
        whereas_count = sum(1 for p in parts if p.startswith("Whereas"))
        
        # If excessive whereas clauses (>5), compress them
        if whereas_count > 5:
            # Keep structure but remove excessive padding
            text = re.sub(
                r"Whereas\s+[^\n]*\n\s*Whereas",
                "Whereas",
                text,
                flags=re.MULTILINE
            )
        
        return text
    
    def _remove_redundant_phrases(self, text: str) -> str:
        """
        Remove redundant legal phrases that add padding without semantic value.
        Updated for llama3.2:3b - aggressive phrase removal.
        """
        # Common padding phrases in legal documents
        redundant_phrases = [
            r"\bprovided\s+that\b",
            r"\bwhereby\b",
            r"\bwherein\b",
            r"\bwhereof\b",
            r"\bwhereto\b",
            r"\btherefrom\b",
            r"\bthereupon\b",
            r"\bthereat\b",
            r"\bthereunto\b",
            r"\bwherever\s+applicable\b",
            r"\bas\s+may\s+be\s+necessary\b",
            r"\bfrom\s+time\s+to\s+time\b",
            r"\bfrom\s+and\s+after\b",
            r"\ball\s+(?:and\s+)?sundry\b",
        ]
        
        for phrase in redundant_phrases:
            text = re.sub(phrase, " ", text, flags=re.IGNORECASE)
        
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """
        Remove excessive whitespace while preserving paragraph structure.
        Updated for llama3.2:3b - aggressive whitespace normalization.
        """
        # Remove lines with only whitespace
        text = re.sub(r"^[ \t]*\n", "", text, flags=re.MULTILINE)
        
        # Collapse multiple blank lines into single blank line
        text = re.sub(r"\n\n\n+", "\n\n", text)
        
        # Remove excessive leading spaces (indentation)
        text = re.sub(r"^\s{4,}", "", text, flags=re.MULTILINE)
        
        # Remove trailing spaces on lines
        text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
        
        # Collapse multiple spaces to single space within lines
        text = re.sub(r" {2,}", " ", text)
        
        return text
    
    def get_efficiency_score(self, compression_percentage: float) -> Dict:
        """
        Convert compression percentage to UI-friendly efficiency score (0-100).
        Updated for llama3.2:3b - targeting 30%+ as "good".
        
        Returns:
            Dict with:
            - score: 0-100
            - level: "red" (poor), "yellow" (okay), "green" (good)
            - message: Human-readable explanation
        """
        if compression_percentage >= 30:  # Updated for llama3.2:3b target
            level = "green"
            message = "Excellent compression (llama3.2:3b optimized)"
        elif compression_percentage >= 15:
            level = "yellow"
            message = "Good compression"
        else:
            level = "red"
            message = "Limited boilerplate to remove"
        
        # Normalize score to 0-100
        score = min(100, int(compression_percentage))
        
        return {
            "score": score,
            "level": level,
            "message": message,
            "percentage": compression_percentage,
        }


class CompressionChain:
    """
    Orchestrates compression for full RAG pipeline.
    Handles both document chunks and query contexts.
    """
    
    def __init__(self, compression_target: float = 0.4):
        """Initialize compression chain."""
        self.compressor = TextCompressor(compression_target=compression_target)
    
    def compress_retrieved_context(self, retrieved_chunks: List[Dict]) -> Tuple[str, Dict]:
        """
        Compress chunks retrieved from vector store for RAG context.
        
        Input format: List of dicts with "text" and "metadata" keys
        Returns: (compressed_context_string, compression_stats_dict)
        """
        chunk_texts = [chunk["text"] for chunk in retrieved_chunks]
        compressed_chunks, stats = self.compressor.compress_chunks(chunk_texts)
        
        # Reconstruct with metadata for traceability
        compressed_context = "\n\n---\n\n".join(
            f"[From: {chunk['metadata'].get('source', 'unknown')}]\n{compressed}"
            for chunk, compressed in zip(retrieved_chunks, compressed_chunks)
        )
        
        return compressed_context, stats
    
    def compress_for_summary(self, text: str) -> Tuple[str, Dict]:
        """
        Compress full document text before summarization.
        Goal: Reduce document to core content before feeding to summarize chain.
        """
        return self.compressor.compress(text)
