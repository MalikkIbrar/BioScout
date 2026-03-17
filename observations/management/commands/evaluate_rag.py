"""
Management command to evaluate RAG retrieval accuracy.

Usage:
    python manage.py evaluate_rag
"""

from typing import Any

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Evaluate the RAG hybrid retriever against benchmark questions."""

    help = "Evaluate RAG retrieval accuracy against 10 benchmark questions."

    def handle(self, *args: Any, **options: Any) -> None:
        from observations.rag.evaluate import run_evaluation

        self.stdout.write("Running RAG evaluation (10 benchmark questions)...\n")

        report = run_evaluation(top_k=3)

        self.stdout.write("─" * 60)
        for item in report["per_question"]:
            status = "✅" if item["hit"] else "❌"
            self.stdout.write(f"{status} Q: {item['question']}")
            self.stdout.write(f"   Expected : {item['expected']}")
            self.stdout.write(f"   Retrieved: {item['retrieved']}")
            self.stdout.write(f"   Scores   : {item['scores']}\n")

        self.stdout.write("─" * 60)
        self.stdout.write(
            self.style.SUCCESS(
                f"Retrieval Accuracy : {report['correct']}/{report['total']} "
                f"({report['accuracy']*100:.1f}%)"
            )
        )
        self.stdout.write(
            f"Avg Retrieval Score: {report['average_retrieval_score']}"
        )
        contrib = report["method_contributions"]
        self.stdout.write(
            f"Method Contributions — BM25 only: {contrib['bm25_only']}  "
            f"Vector only: {contrib['vector_only']}  "
            f"Both: {contrib['both_methods']}"
        )
