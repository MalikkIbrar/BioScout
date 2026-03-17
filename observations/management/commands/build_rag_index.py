"""
Management command to build the RAG vector and BM25 indexes.

Usage:
    python manage.py build_rag_index
"""

from typing import Any

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Build and persist the ChromaDB vector index and BM25 index."""

    help = "Build the RAG knowledge base indexes (ChromaDB vector + BM25)."

    def handle(self, *args: Any, **options: Any) -> None:
        from observations.rag.bm25_search import SpeciesBM25
        from observations.rag.knowledge_base import get_all_documents
        from observations.rag.vector_store import SpeciesVectorStore

        self.stdout.write("Loading knowledge base documents...")
        documents = get_all_documents()
        self.stdout.write(f"  Found {len(documents)} species documents.")

        # Build vector index
        self.stdout.write("\nBuilding ChromaDB vector index...")
        vs = SpeciesVectorStore()
        count = vs.index_documents(documents)
        self.stdout.write(f"  ✅ Indexed {count} documents into ChromaDB.")

        # Build and save BM25 index
        self.stdout.write("\nBuilding BM25 keyword index...")
        bm25 = SpeciesBM25(documents)
        bm25.save()
        self.stdout.write(f"  ✅ BM25 index built and saved ({len(documents)} docs).")

        stats = vs.get_stats()
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ RAG index built: {stats['total_documents']} documents indexed"
            )
        )
