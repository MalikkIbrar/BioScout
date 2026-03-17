"""
BM25 keyword search index for BioScout species knowledge base.

BM25 (Best Match 25) is a probabilistic ranking function that excels at
exact keyword matching — ideal for species names, habitat terms, and
specific biological vocabulary.
"""

import logging
import pickle
import re
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

logger = logging.getLogger("bioscout")

INDEX_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "bm25_index.pkl"


def _tokenize(text: str) -> list[str]:
    """
    Tokenize text for BM25 indexing.

    Lowercases, removes punctuation, splits on whitespace,
    and filters out very short tokens.

    Args:
        text: Input string.

    Returns:
        List of lowercase tokens.
    """
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = text.split()
    return [t for t in tokens if len(t) > 1]


def _doc_to_text(doc: dict[str, Any]) -> str:
    """
    Build a rich text representation of a species document for BM25 indexing.

    Weights important fields by repeating them (title boosting).

    Args:
        doc: Species document dict.

    Returns:
        Combined text string.
    """
    # Repeat species name and category for higher weight
    name = doc.get("species_name", "")
    category = doc.get("category", "")
    parts = [
        name, name, name,          # triple weight for species name
        doc.get("scientific_name", ""),
        category, category,         # double weight for category
        doc.get("habitat", ""),
        doc.get("diet", ""),
        doc.get("geographical_range", ""),
        doc.get("behavior", ""),
        doc.get("conservation_status", ""),
        doc.get("description", ""),
        doc.get("fun_facts", ""),
        doc.get("threats", ""),
        doc.get("physical_description", ""),
    ]
    return " ".join(p for p in parts if p and p != "N/A")


class SpeciesBM25:
    """
    BM25 keyword search index over species knowledge documents.

    Supports persistence to disk so the index survives server restarts.
    """

    def __init__(self, documents: list[dict[str, Any]]) -> None:
        """
        Build BM25 index from a list of species documents.

        Args:
            documents: List of species document dicts from knowledge_base.py.
        """
        self._documents = documents
        corpus_texts = [_doc_to_text(doc) for doc in documents]
        tokenized_corpus = [_tokenize(text) for text in corpus_texts]
        self._bm25 = BM25Okapi(tokenized_corpus)
        logger.info("BM25 index built with %d documents.", len(documents))

    def search_bm25(
        self, query: str, top_k: int = 3
    ) -> list[dict[str, Any]]:
        """
        Keyword search using BM25 ranking.

        Args:
            query: Search query string.
            top_k: Number of top results to return.

        Returns:
            List of dicts with species_name, bm25_score (normalised 0-1), rank.
        """
        tokens = _tokenize(query)
        if not tokens:
            return []

        raw_scores = self._bm25.get_scores(tokens)

        # Normalise scores to 0-1 range
        max_score = max(raw_scores) if max(raw_scores) > 0 else 1.0
        normalised = [s / max_score for s in raw_scores]

        # Pair with documents and sort
        scored = sorted(
            enumerate(normalised), key=lambda x: x[1], reverse=True
        )

        results = []
        for rank, (idx, score) in enumerate(scored[:top_k]):
            doc = self._documents[idx]
            results.append(
                {
                    "species_name": doc.get("species_name", ""),
                    "scientific_name": doc.get("scientific_name", ""),
                    "category": doc.get("category", ""),
                    "conservation_status": doc.get("conservation_status", ""),
                    "habitat": doc.get("habitat", ""),
                    "description": doc.get("description", ""),
                    "diet": doc.get("diet", ""),
                    "threats": doc.get("threats", ""),
                    "fun_facts": doc.get("fun_facts", ""),
                    "found_in_pakistan": doc.get("found_in_pakistan", False),
                    "bm25_score": round(score, 4),
                    "rank": rank + 1,
                }
            )

        return results

    def save(self) -> None:
        """Persist the BM25 index and documents to disk."""
        INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(INDEX_PATH, "wb") as f:
            pickle.dump(
                {"documents": self._documents, "bm25": self._bm25}, f
            )
        logger.info("BM25 index saved to %s", INDEX_PATH)

    @classmethod
    def load(cls, documents: list[dict[str, Any]]) -> "SpeciesBM25":
        """
        Load BM25 index from disk if available, otherwise build fresh.

        Args:
            documents: Fallback documents if no saved index found.

        Returns:
            SpeciesBM25 instance.
        """
        if INDEX_PATH.exists():
            try:
                with open(INDEX_PATH, "rb") as f:
                    data = pickle.load(f)
                instance = cls.__new__(cls)
                instance._documents = data["documents"]
                instance._bm25 = data["bm25"]
                logger.info("BM25 index loaded from disk (%d docs).", len(instance._documents))
                return instance
            except Exception as exc:
                logger.warning("Failed to load BM25 index: %s. Rebuilding.", exc)

        return cls(documents)
