"""
Hybrid Retriever combining BM25 keyword search and vector semantic search.

Uses Reciprocal Rank Fusion (RRF) to merge ranked results from both
retrieval methods into a single unified ranking.

Why hybrid?
- BM25 excels at exact keyword matches (species names, specific terms)
- Vector search excels at semantic similarity (concepts, paraphrases)
- RRF fusion consistently outperforms either method alone
"""

import logging
from typing import Any

from .bm25_search import SpeciesBM25
from .knowledge_base import get_all_documents
from .vector_store import SpeciesVectorStore

logger = logging.getLogger("bioscout")

# RRF constant — controls how much lower-ranked results are penalised
# k=60 is the standard value from the original RRF paper
RRF_K = 60


def _reciprocal_rank_fusion(
    ranked_lists: list[list[dict[str, Any]]],
    score_key_prefix: str = "",
) -> dict[str, float]:
    """
    Compute Reciprocal Rank Fusion scores across multiple ranked lists.

    RRF score for a document = sum(1 / (k + rank)) across all lists.
    Documents appearing in multiple lists get higher combined scores.

    Args:
        ranked_lists: List of ranked result lists. Each item must have 'species_name'.
        score_key_prefix: Unused, kept for API compatibility.

    Returns:
        Dict mapping species_name -> combined RRF score.
    """
    rrf_scores: dict[str, float] = {}

    for ranked_list in ranked_lists:
        for rank, doc in enumerate(ranked_list, start=1):
            name = doc.get("species_name", "")
            if name:
                rrf_scores[name] = rrf_scores.get(name, 0.0) + 1.0 / (RRF_K + rank)

    return rrf_scores


class HybridRetriever:
    """
    Hybrid retriever combining BM25 and vector search via RRF fusion.

    Auto-builds the index on first run if not already present.
    """

    def __init__(self) -> None:
        self._documents = get_all_documents()
        self._vector_store = SpeciesVectorStore()
        self._bm25 = SpeciesBM25.load(self._documents)
        self._ensure_index()

    def _ensure_index(self) -> None:
        """Build indexes automatically if vector store is empty."""
        try:
            stats = self._vector_store.get_stats()
            if stats["total_documents"] == 0:
                logger.info("Vector store empty — building RAG index automatically.")
                self._vector_store.index_documents(self._documents)
                self._bm25 = SpeciesBM25(self._documents)
                self._bm25.save()
                logger.info("RAG index built automatically (%d docs).", len(self._documents))
        except Exception as exc:
            logger.warning("Auto-index build failed (non-fatal): %s", exc)

    def hybrid_search(
        self, query: str, top_k: int = 3
    ) -> list[dict[str, Any]]:
        """
        Run hybrid BM25 + vector search and fuse results with RRF.

        Workflow:
          1. Run BM25 keyword search (top_k * 2 candidates)
          2. Run vector semantic search (top_k * 2 candidates)
          3. Apply Reciprocal Rank Fusion to merge rankings
          4. Deduplicate by species_name
          5. Enrich top_k results with full document data
          6. Return sorted by combined RRF score

        Args:
            query: Natural language query string.
            top_k: Number of final results to return.

        Returns:
            List of enriched document dicts with combined_score field.
        """
        candidates = top_k * 2

        # Step 1: BM25 search
        bm25_results = self._bm25.search_bm25(query, top_k=candidates)
        logger.debug("BM25 returned %d results for: %s", len(bm25_results), query)

        # Step 2: Vector search
        vector_results = self._vector_store.search_vector(query, top_k=candidates)
        logger.debug("Vector returned %d results for: %s", len(vector_results), query)

        # Step 3: RRF fusion
        rrf_scores = _reciprocal_rank_fusion([bm25_results, vector_results])

        # Step 4: Build a lookup of full document data
        doc_lookup: dict[str, dict[str, Any]] = {
            doc["species_name"]: doc for doc in self._documents
        }

        # Merge BM25 and vector individual scores for transparency
        bm25_score_map = {r["species_name"]: r.get("bm25_score", 0.0) for r in bm25_results}
        vector_score_map = {r["species_name"]: r.get("vector_score", 0.0) for r in vector_results}

        # Step 5: Build enriched results
        enriched: list[dict[str, Any]] = []
        for species_name, rrf_score in sorted(
            rrf_scores.items(), key=lambda x: x[1], reverse=True
        )[:top_k]:
            full_doc = doc_lookup.get(species_name, {})
            enriched.append(
                {
                    **full_doc,
                    "combined_score": round(rrf_score, 6),
                    "bm25_score": round(bm25_score_map.get(species_name, 0.0), 4),
                    "vector_score": round(vector_score_map.get(species_name, 0.0), 4),
                    "in_bm25": species_name in bm25_score_map,
                    "in_vector": species_name in vector_score_map,
                }
            )

        logger.info(
            "Hybrid search for '%s' returned %d results: %s",
            query,
            len(enriched),
            [r["species_name"] for r in enriched],
        )

        return enriched

    def format_context(self, docs: list[dict[str, Any]]) -> str:
        """
        Format retrieved documents as a clean context string for the LLM.

        Args:
            docs: List of enriched document dicts from hybrid_search.

        Returns:
            Formatted multi-section context string.
        """
        if not docs:
            return "No relevant species information found in the knowledge base."

        sections = []
        for i, doc in enumerate(docs, start=1):
            section = (
                f"[Source {i}: {doc.get('species_name', 'Unknown')} "
                f"({doc.get('scientific_name', '')})]\n"
                f"Category: {doc.get('category', 'N/A')}\n"
                f"Conservation Status: {doc.get('conservation_status', 'N/A')}\n"
                f"Habitat: {doc.get('habitat', 'N/A')}\n"
                f"Diet: {doc.get('diet', 'N/A')}\n"
                f"Found in Pakistan: {doc.get('found_in_pakistan', False)}\n"
                f"Description: {doc.get('description', 'N/A')}\n"
                f"Threats: {doc.get('threats', 'N/A')}\n"
                f"Fun Facts: {doc.get('fun_facts', 'N/A')}"
            )
            sections.append(section)

        return "\n\n---\n\n".join(sections)
