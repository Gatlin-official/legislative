"""
Information Density Evaluation Engine for Legislative Documents.

This module calculates how efficiently a document communicates key information
relative to the tokens consumed. It extracts facts, measures preservation rates,
and provides quality grades for competitive benchmarking.

Key Metric: Information Density = Facts Preserved / Tokens Consumed
Higher density = more value per token (the goal for competition)
"""

import re
import logging
import tiktoken
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from models import ExtractedFact, InformationDensityMetrics, DensityComparisonResponse, EnergyMetrics

logger = logging.getLogger(__name__)


class FactExtractor:
    """Extracts structured facts from legislative documents."""
    
    def __init__(self):
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # Regex patterns for fact extraction (ordered by importance)
        self.fact_patterns = {
            "amount": {
                "pattern": r"(?:₹|rupees?|Rs\.?|rs\.?)\s*([\d,]+(?:\.\d+)?)\s*(?:crore|lakh|thousand|lacs|million)?",
                "importance": 0.95,
                "description": "Monetary amounts, budgets, penalties, benefits"
            },
            "percentage": {
                "pattern": r"(\d+(?:\.\d+)?)\s*%",
                "importance": 0.90,
                "description": "Percentage changes, rates, thresholds"
            },
            "age_threshold": {
                "pattern": r"(?:age|year)s?\s+(?:of\s+)?(?:at\s+)?(?:least|minimum|above|over|greater|exceeding|>=|>)\s*(\d+)",
                "importance": 0.95,
                "description": "Age eligibility requirements"
            },
            "date": {
                "pattern": r"(?:on|from|by|since|before|after|from)\s+(?:\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}|January|February|March|April|May|June|July|August|September|October|November|December)",
                "importance": 0.85,
                "description": "Dates, timelines, effective dates, deadlines"
            },
            "condition": {
                "pattern": r"(?:if|provided that|subject to|only if|unless|where|when)\s+([^\.!?]*?)(?:\.|,|;|!|\?)",
                "importance": 0.90,
                "description": "Conditions, prerequisites, qualifications"
            },
            "penalty": {
                "pattern": r"(?:penalty|fine|punishment|liable|imprisonment|duration|maximum)\s+(?:of\s+)?(?:₹|Rs\.?|rupees?|rs\.?|upto?|up to|maximum)?\s*([\d,]+[a-z]*)",
                "importance": 0.95,
                "description": "Legal penalties, fines, punishments"
            },
            "entity": {
                "pattern": r"(?:ministry|department|authority|organization|board|commission|secretary|director|officer)\s+(?:of\s+)?([A-Za-z\s]+?)(?:\.|,|;|)|(?:Government|State|Union|Central)",
                "importance": 0.80,
                "description": "Organizations, government bodies, responsible entities"
            },
            "action": {
                "pattern": r"(?:shall|must|required to|entitled to|authorized to|prohibited from|restricted|forbidden)\s+([^\.]*?)(?:\.|,|;)",
                "importance": 0.85,
                "description": "Required actions, permissions, prohibitions"
            },
            "benefit": {
                "pattern": r"(?:benefit|allowance|grant|subsidy|rebate|exemption|waiver)\s+(?:of|:)?\s*([^\.]*?)(?:\.|,|;)",
                "importance": 0.90,
                "description": "Benefits provided to eligible persons"
            },
        }
    
    def extract_facts(self, text: str) -> List[ExtractedFact]:
        """
        Extract structured facts from legislative text.
        
        Returns:
            List of ExtractedFact objects with importance scores
        """
        facts: List[ExtractedFact] = []
        seen_facts = set()  # Avoid duplicates
        
        for fact_type, pattern_config in self.fact_patterns.items():
            try:
                matches = re.finditer(
                    pattern_config["pattern"],
                    text,
                    re.IGNORECASE | re.MULTILINE
                )
                
                for match in matches:
                    fact_text = match.group(0).strip()
                    
                    # Skip if already extracted
                    if fact_text.lower() in seen_facts:
                        continue
                    
                    seen_facts.add(fact_text.lower())
                    
                    # Get surrounding context (100 chars before/after)
                    start = max(0, match.start() - 100)
                    end = min(len(text), match.end() + 100)
                    source_context = text[start:end].strip()
                    
                    fact = ExtractedFact(
                        fact=fact_text,
                        fact_type=fact_type,
                        source_text=source_context,
                        importance_score=pattern_config["importance"]
                    )
                    facts.append(fact)
                    
            except re.error as e:
                logger.warning(f"Regex error in pattern {fact_type}: {e}")
                continue
        
        logger.info(f"Extracted {len(facts)} facts from text")
        return facts
    
    def filter_facts_in_text(self, text: str, facts: List[ExtractedFact]) -> List[ExtractedFact]:
        """
        Filter facts to keep only those present in the given text.
        Used to check fact preservation after compression.
        """
        preserved = []
        
        for fact in facts:
            # Check if fact (or close variation) appears in text
            fact_lower = fact.fact.lower()
            text_lower = text.lower()
            
            # Look for exact match
            if fact_lower in text_lower:
                preserved.append(fact)
            # Look for partial match (key parts of the fact)
            elif self._partial_fact_match(fact_lower, text_lower):
                preserved.append(fact)
        
        return preserved
    
    def _partial_fact_match(self, fact: str, text: str) -> bool:
        """Check if key parts of fact appear in text."""
        # Extract numbers and keywords
        numbers = re.findall(r'\d+(?:\.\d+)?', fact)
        keywords = re.findall(r'\b[a-z]{4,}\b', fact)
        
        if not numbers and not keywords:
            return False
        
        # At least one number or 2+ keywords must match
        number_match = any(str(num) in text for num in numbers)
        keyword_matches = sum(1 for kw in keywords if kw in text)
        
        return number_match or keyword_matches >= 2


class InformationDensityCalculator:
    """Calculates Information Density metrics for documents."""
    
    def __init__(self):
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.fact_extractor = FactExtractor()
    
    def calculate_density(
        self,
        doc_id: str,
        original_text: str,
        compressed_text: str,
        compression_stats: Dict
    ) -> InformationDensityMetrics:
        """
        Calculate comprehensive Information Density metrics.
        
        Args:
            doc_id: Document identifier
            original_text: Original uncompressed text
            compressed_text: Compressed text
            compression_stats: Token compression statistics
        
        Returns:
            InformationDensityMetrics with full evaluation
        """
        start_time = datetime.now()
        
        # Step 1: Extract facts from original
        original_facts = self.fact_extractor.extract_facts(original_text)
        logger.info(f"Extracted {len(original_facts)} facts from original document")
        
        # Step 2: Check which facts survived compression
        preserved_facts = self.fact_extractor.filter_facts_in_text(compressed_text, original_facts)
        logger.info(f"Preserved {len(preserved_facts)} of {len(original_facts)} facts after compression")
        
        # Step 3: Calculate core metrics
        facts_original = len(original_facts)
        facts_preserved = len(preserved_facts)
        tokens_consumed = compression_stats.get("compressed_tokens", 1)
        
        # Information Density = preserved facts per token
        information_density = facts_preserved / max(tokens_consumed, 1)
        
        # Preservation rate
        preservation_rate = facts_preserved / max(facts_original, 1)
        
        # Step 4: Grade calculations
        density_grade = self._grade_density(information_density)
        preservation_grade = self._grade_preservation(preservation_rate)
        overall_grade = self._combine_grades(density_grade, preservation_grade)
        
        # Step 5: Fact type breakdown
        facts_by_type = {}
        critical_facts_preserved = 0
        for fact in preserved_facts:
            fact_type = fact.fact_type
            facts_by_type[fact_type] = facts_by_type.get(fact_type, 0) + 1
            if fact.importance_score >= 0.90:
                critical_facts_preserved += 1
        
        # Step 6: Build response
        generation_time = (datetime.now() - start_time).total_seconds()
        
        metrics = InformationDensityMetrics(
            doc_id=doc_id,
            key_facts_extracted=original_facts,
            key_facts_preserved=preserved_facts,
            facts_count_original=facts_original,
            facts_count_preserved=facts_preserved,
            tokens_consumed=tokens_consumed,
            information_density=information_density,
            preservation_rate=preservation_rate,
            density_grade=density_grade,
            preservation_grade=preservation_grade,
            overall_grade=overall_grade,
            facts_by_type=facts_by_type,
            critical_facts_preserved=critical_facts_preserved,
            compression_stats=compression_stats,
            generation_time_seconds=generation_time,
        )
        
        logger.info(
            f"Density calculation complete: {information_density:.4f} facts/token, "
            f"{preservation_rate*100:.1f}% preservation, Grade: {overall_grade}"
        )
        
        return metrics
    
    def _grade_density(self, density: float) -> str:
        """Grade Information Density score."""
        if density > 0.020: return "A+"
        if density > 0.015: return "A"
        if density > 0.010: return "B"
        if density > 0.005: return "C"
        return "D"
    
    def _grade_preservation(self, preservation: float) -> str:
        """Grade fact preservation rate."""
        if preservation > 0.95: return "A+"
        if preservation > 0.90: return "A"
        if preservation > 0.80: return "B"
        if preservation > 0.70: return "C"
        return "D"
    
    def _combine_grades(self, density_grade: str, preservation_grade: str) -> str:
        """Combine two grades into overall grade."""
        # Convert to numeric
        grade_values = {"A+": 4, "A": 3, "B": 2, "C": 1, "D": 0}
        avg = (grade_values[density_grade] + grade_values[preservation_grade]) / 2
        
        if avg >= 3.5: return "A+"
        if avg >= 3: return "A"
        if avg >= 2: return "B"
        if avg >= 1: return "C"
        return "D"
    
    def compare_density(
        self,
        doc_id: str,
        original_text: str,
        compressed_text: str,
        original_tokens: int,
        compressed_tokens: int
    ) -> DensityComparisonResponse:
        """
        Compare Information Density before and after compression.
        
        Returns:
            Detailed comparison with improvement metrics
        """
        # Extract facts
        original_facts = self.fact_extractor.extract_facts(original_text)
        preserved_facts = self.fact_extractor.filter_facts_in_text(compressed_text, original_facts)
        
        # Calculate densities
        # For original: use all facts that exist / original tokens
        original_density = len(original_facts) / max(original_tokens, 1)
        
        # For compressed: use preserved facts / compressed tokens
        compressed_density = len(preserved_facts) / max(compressed_tokens, 1)
        
        # Calculate improvement
        if original_density > 0:
            improvement_percent = ((compressed_density - original_density) / original_density) * 100
        else:
            improvement_percent = 0
        
        # Determine efficiency rating
        if improvement_percent > 50:
            rating = "Excellent"
            recommendation = "Outstanding compression with fact preservation. This document is highly optimized."
        elif improvement_percent > 20:
            rating = "Good"
            recommendation = "Strong density improvement. Some minor information density gains possible."
        elif improvement_percent > 0:
            rating = "Fair"
            recommendation = "Modest density improvement. Consider more aggressive boilerplate removal."
        else:
            rating = "Poor"
            recommendation = "Compression may be removing important facts. Review compression strategy."
        
        return DensityComparisonResponse(
            doc_id=doc_id,
            original_density=original_density,
            compressed_density=compressed_density,
            density_improvement=improvement_percent,
            efficiency_rating=rating,
            recommendation=recommendation,
        )


class EnergyCalculator:
    """Calculates energy and environmental impact of token compression."""
    
    @staticmethod
    def calculate_energy_savings(
        tokens_saved: int,
        provider: str = "ollama",
        num_queries: int = 1
    ) -> EnergyMetrics:
        """
        Calculate real energy/carbon/cost savings from token compression.
        
        Args:
            tokens_saved: Number of tokens saved
            provider: LLM provider ('ollama' for local, 'openai' for cloud)
            num_queries: Number of queries (for aggregate metrics)
        
        Returns:
            EnergyMetrics with environmental and cost impact
        """
        # Energy consumption per token (Joules)
        # Local Ollama: ~0.0001J (very efficient, local GPU/CPU)
        # OpenAI GPT-4: ~0.001J (cloud, includes infrastructure)
        # OpenAI GPT-3.5: ~0.0003J (cloud, cheaper model)
        
        if provider.lower() == "ollama":
            joules_per_token = 0.0001
            co2_per_token = 0.00001  # ~0.01mg CO2 per token (local renewable energy likely)
            cost_per_token = 0.0  # Free with local inference
        elif provider.lower() == "openai-gpt4":
            joules_per_token = 0.001
            co2_per_token = 0.000008  # ~8mg CO2 per token
            cost_per_token = 0.00003  # ~$0.00003 per token for GPT-4
        elif provider.lower() == "openai-gpt3.5":
            joules_per_token = 0.0003
            co2_per_token = 0.0000024  # ~2.4mg CO2 per token
            cost_per_token = 0.000001  # ~$0.000001 per token for GPT-3.5
        else:
            # Default to OpenAI GPT-3.5
            joules_per_token = 0.0003
            co2_per_token = 0.0000024
            cost_per_token = 0.000001
        
        # Calculate totals
        total_tokens_saved = tokens_saved * num_queries
        joules_saved = total_tokens_saved * joules_per_token
        co2_saved = total_tokens_saved * co2_per_token
        cost_saved = total_tokens_saved * cost_per_token
        
        # Convert to human-friendly equivalents
        km_car_equivalent = co2_saved / 0.120  # 120g CO2 per km car
        kwh_equivalent = joules_saved / 3_600_000  # 1 kWh = 3.6M joules
        
        # Human-readable strings
        carbon_equivalent = f"Equivalent to {km_car_equivalent:.2f} km car drive"
        energy_savings_human = f"Saved {kwh_equivalent:.4f} kWh + ₹{cost_saved*80:.2f} + {co2_saved:.2f}g CO2"
        
        return EnergyMetrics(
            tokens_saved=total_tokens_saved,
            joules_saved=joules_saved,
            co2_grams_saved=co2_saved,
            cost_saved_usd=cost_saved,
            carbon_equivalent=carbon_equivalent,
            energy_savings_human=energy_savings_human,
        )


# ============================================================================
# BENCHMARK DATASETS (for testing)
# ============================================================================

BENCHMARK_BILLS = {
    "sample_bill_1": {
        "title": "Employment (Amendment) Bill 2024",
        "original_tokens": 8500,
        "expected_facts": [
            "Eligible age: 18+",
            "Benefit: ₹5000/month",
            "Penalty: ₹1 million first offense",
            "Applies to: All Indian citizens",
            "Effective: January 1, 2024",
            "Reporting: Quarterly",
        ]
    },
}
