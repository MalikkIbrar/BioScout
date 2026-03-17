"""
ChromaDB vector store for BioScout species knowledge base.

Uses ChromaDB's built-in DefaultEmbeddingFunction (all-MiniLM-L6-v2 via onnxruntime)
— no torch or sentence-transformers required.
"""

import logging
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger("bioscout")

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "chroma_db"


class SpeciesVectorStore:
    """
    Persistent ChromaDB vector store for species knowledge documents.

    Uses the default embedding function (all-MiniLM-L6-v2 via onnxruntime)
    which runs locally with no external API calls.
    """

    def __init__(self) -> None:
        DB_PATH.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(DB_PATH))
        self._ef = embedding_functions.DefaultEmbeddingFunction()
        self._collection = self._client.get_or_create_collection(
            name="species_knowledge",
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"},
        )

    def _doc_to_text(self, doc: dict[str, Any]) -> str:
        """
        Combine key fields into a single searchable text string for embedding.

        Args:
            doc: Species document dict.

        Returns:
            Concatenated text string.
        """
        parts = [
            doc.get("species_name", ""),
            doc.get("scientific_name", ""),
            doc.get("category", ""),
            doc.get("habitat", ""),
            doc.get("diet", ""),
            doc.get("geographical_range", ""),
            doc.get("behavior", ""),
            doc.get("conservation_status", ""),
            doc.get("description", ""),
            doc.get("fun_facts", ""),
            doc.get("threats", ""),
        ]
        return " | ".join(p for p in parts if p and p != "N/A")

    def index_documents(self, documents: list[dict[str, Any]]) -> int:
        """
        Index all species documents into ChromaDB.

        Clears existing collection and re-indexes from scratch to ensure
        consistency when the knowledge base is updated.

        Args:
            documents: List of species document dicts.

        Returns:
            Number of documents indexed.
        """
        # Clear existing documents
        existing = self._collection.count()
        if existing > 0:
            all_ids = self._collection.get()["ids"]
            self._collection.delete(ids=all_ids)
            logger.info("Cleared %d existing documents from vector store.", existing)

        ids = []
        texts = []
        metadatas = []

        for doc in documents:
            doc_id = doc["species_name"].lower().replace(" ", "_")
            text = self._doc_to_text(doc)
            metadata = {
                "species_name": doc.get("species_name", ""),
                "scientific_name": doc.get("scientific_name", ""),
                "category": doc.get("category", ""),
                "conservation_status": doc.get("conservation_status", ""),
                "found_in_pakistan": str(doc.get("found_in_pakistan", False)),
                "habitat": doc.get("habitat", "")[:200],
            }
            ids.append(doc_id)
            texts.append(text)
            metadatas.append(metadata)

        # Batch upsert
        self._collection.upsert(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
        )

        logger.info("Indexed %d documents into vector store.", len(documents))
        return len(documents)

    def search_vector(
        self, query: str, top_k: int = 3
    ) -> list[dict[str, Any]]:
        """
        Semantic similarity search using cosine distance.

        Args:
            query: Natural language query string.
            top_k: Number of results to return.

        Returns:
            List of dicts with species_name, score, metadata.
        """
        if self._collection.count() == 0:
            logger.warning("Vector store is empty. Run build_rag_index first.")
            return []

        results = self._collection.query(
            query_texts=[query],
            n_results=min(top_k, self._collection.count()),
            include=["metadatas", "distances", "documents"],
        )

        output = []
        for i, meta in enumerate(results["metadatas"][0]):
            distance = results["distances"][0][i]
            # Convert cosine distance to similarity score (0-1)
            score = max(0.0, 1.0 - distance)
            output.append(
                {
                    "species_name": meta.get("species_name", ""),
                    "scientific_name": meta.get("scientific_name", ""),
                    "category": meta.get("category", ""),
                    "conservation_status": meta.get("conservation_status", ""),
                    "habitat": meta.get("habitat", ""),
                    "vector_score": round(score, 4),
                    "rank": i + 1,
                }
            )

        return output

    def get_stats(self) -> dict[str, Any]:
        """
        Return statistics about the vector store.

        Returns:
            Dict with total_documents count and db_path.
        """
        return {
            "total_documents": self._collection.count(),
            "db_path": str(DB_PATH),
        }
