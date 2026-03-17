"""
RAG evaluation module for BioScout.

Tests the hybrid retriever against 10 benchmark questions with known
expected species in the top-3 results. Calculates retrieval accuracy
and per-method contribution statistics.
"""

import logging
from typing import Any

logger = logging.getLogger("bioscout")

# Benchmark: (question, list of expected species names that should appear in top-3)
EVAL_QUESTIONS: list[tuple[str, list[str]]] = [
    ("What do snow leopards eat?", ["Snow Leopard"]),
    ("Which birds are common in Lahore?", ["House Sparrow", "Common Myna"]),
    ("Tell me about endangered mammals in Pakistan", ["Snow Leopard", "Pakistani Pangolin"]),
    ("What butterflies are found in Pakistan?", ["Common Jezebel Butterfly"]),
    ("Which reptiles are venomous in Pakistan?", ["Spectacled Cobra", "Russell's Viper"]),
    ("What trees are sacred in South Asia?", ["Peepal Tree", "Banyan Tree"]),
    ("Which animals live in Gilgit-Baltistan?", ["Snow Leopard", "Himalayan Marmot"]),
    ("Tell me about birds of prey in Pakistan", ["Black Kite", "Barn Owl"]),
    ("What insects are beneficial for agriculture?", ["Asian Honeybee"]),
    ("Which mammals are endangered in Pakistan?", ["Snow Leopard", "Pakistani Pangolin"]),
]


def run_evaluation(top_k: int = 3) -> dict[str, Any]:
    """
    Run the full RAG evaluation benchmark.

    For each test question, checks whether at least one expected species
    appears in the top_k retrieved results.

    Args:
        top_k: Number of results to retrieve per query.

    Returns:
        Dict with accuracy, per-question results, and method contribution stats.
    """
    from .hybrid_retriever import HybridRetriever

    retriever = HybridRetriever()

    results = []
    correct = 0
    total_bm25_only = 0
    total_vector_only = 0
    total_both = 0
    all_scores = []

    for question, expected_species in EVAL_QUESTIONS:
        retrieved = retriever.hybrid_search(question, top_k=top_k)
        retrieved_names = [r["species_name"] for r in retrieved]
        scores = [r.get("combined_score", 0.0) for r in retrieved]
        all_scores.extend(scores)

        # Check if any expected species is in results
        hit = any(exp in retrieved_names for exp in expected_species)
        if hit:
            correct += 1

        # Count method contributions
        for r in retrieved:
            in_bm25 = r.get("in_bm25", False)
            in_vector = r.get("in_vector", False)
            if in_bm25 and in_vector:
                total_both += 1
            elif in_bm25:
                total_bm25_only += 1
            elif in_vector:
                total_vector_only += 1

        results.append(
            {
                "question": question,
                "expected": expected_species,
                "retrieved": retrieved_names,
                "hit": hit,
                "scores": [round(s, 4) for s in scores],
            }
        )

    accuracy = correct / len(EVAL_QUESTIONS)
    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0.0

    return {
        "accuracy": round(accuracy, 3),
        "correct": correct,
        "total": len(EVAL_QUESTIONS),
        "average_retrieval_score": round(avg_score, 4),
        "method_contributions": {
            "bm25_only": total_bm25_only,
            "vector_only": total_vector_only,
            "both_methods": total_both,
        },
        "per_question": results,
    }
