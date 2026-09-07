"""
Retriever module - clean function interface for RAG retrieval and structured lookups.
This is the main interface that will be wired into Flask API and Groq function-calling router.
"""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any

from .chunker import Chunk
from .embedder import Embedder
from .vector_store import VectorStore
from .structured_store import StructuredStore, Standard, Lab, FAQ, CRSEntry, load_structured_store
from .pipeline import IngestionPipeline
from .categories import CATEGORY_MAP, REVERSE_CATEGORY_MAP


class Retriever:
    """
    Main retrieval interface combining vector search and structured lookups.

    Usage:
        retriever = Retriever.load(index_dir, data_root)

        # RAG retrieval
        results = retriever.retrieve("What is IS 14543?", category="food", k=5)

        # Structured lookups (category uses folder names: electricals, food, toys, shared)
        standard = retriever.lookup_standard("IS 14543")
        labs = retriever.get_labs(category="toys")
        faqs = retriever.search_faqs("certification")
    """

    def __init__(
        self,
        vector_store: VectorStore,
        structured_store: StructuredStore,
        embedder: Embedder,
    ):
        self.vector_store = vector_store
        self.structured_store = structured_store
        self.embedder = embedder

    @classmethod
    def load(
        cls,
        index_dir: Path,
        data_root: Path,
        embedder_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ) -> "Retriever":
        """Load retriever from existing index."""
        index_path = Path(index_dir) / "faiss.index"
        metadata_path = Path(index_dir) / "chunks.pkl"

        embedder = Embedder(embedder_model)
        vector_store = VectorStore.load(str(index_path), str(metadata_path), embedder.dimension)
        structured_store = load_structured_store(data_root)

        return cls(vector_store, structured_store, embedder)

    def _resolve_category(self, category: Optional[str]) -> Optional[str]:
        """Convert folder category name to internal category name."""
        if category is None:
            return None
        return CATEGORY_MAP.get(category, category)

    def retrieve(
        self,
        query: str,
        category: Optional[str] = None,
        k: int = 5,
        score_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks for a query using vector similarity.

        Args:
            query: User query string
            category: Optional category filter (folder name: 'electricals', 'food', 'toys', 'shared')
            k: Number of results to return
            score_threshold: Minimum similarity score (0-1) to include result

        Returns:
            List of dicts with: text, source_file, category, section, heading_path, score
        """
        internal_category = self._resolve_category(category)
        query_embedding = self.embedder.embed_single(query)
        results = self.vector_store.search(query_embedding, k=k, category=internal_category)

        filtered = [
            {
                "text": r["chunk"].text,
                "source_file": r["chunk"].source_file,
                "category": REVERSE_CATEGORY_MAP.get(r["chunk"].category, r["chunk"].category),
                "section": r["chunk"].section,
                "heading_path": r["chunk"].heading_path,
                "score": r["score"],
                "chunk_index": r["chunk"].chunk_index,
            }
            for r in results
            if r["score"] >= score_threshold
        ]

        return filtered

    def retrieve_with_citations(
        self,
        query: str,
        category: Optional[str] = None,
        k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve chunks formatted for citation in answers.
        Includes formatted citation string.
        """
        results = self.retrieve(query, category, k)

        for r in results:
            citation_parts = []
            if r["heading_path"]:
                citation_parts.append(" > ".join(r["heading_path"]))
            citation_parts.append(f"Source: {Path(r['source_file']).name}")
            r["citation"] = " | ".join(citation_parts)

        return results

    # --- Structured lookups (accept folder category names) ---

    def lookup_standard(self, is_number: str, category: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Look up a standard by IS number."""
        internal_category = self._resolve_category(category)
        std = self.structured_store.lookup_standard(is_number, internal_category)
        return std.to_dict() if std else None

    def search_standards(self, keyword: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search standards by keyword in title or IS number."""
        internal_category = self._resolve_category(category)
        standards = self.structured_store.search_standards_by_keyword(keyword, internal_category)
        return [s.to_dict() for s in standards]

    def get_all_standards(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all standards, optionally filtered by category."""
        internal_category = self._resolve_category(category)
        return [s.to_dict() for s in self.structured_store.get_all_standards(internal_category)]

    def get_labs(self, category: Optional[str] = None, location: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get testing labs, optionally filtered by category and/or location."""
        internal_category = self._resolve_category(category)
        return [lab.to_dict() for lab in self.structured_store.get_labs(internal_category, location)]

    def lookup_lab(self, name: str, category: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Look up a lab by name (partial match)."""
        internal_category = self._resolve_category(category)
        lab = self.structured_store.lookup_lab(name, internal_category)
        return lab.to_dict() if lab else None

    def get_faqs(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get FAQs, optionally filtered by category."""
        internal_category = self._resolve_category(category)
        return [faq.to_dict() for faq in self.structured_store.get_faqs(internal_category)]

    def search_faqs(self, query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search FAQs by keyword."""
        internal_category = self._resolve_category(category)
        return [faq.to_dict() for faq in self.structured_store.search_faqs(query, internal_category)]

    def get_crs_table(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get CRS table entries."""
        internal_category = self._resolve_category(category)
        return [crs.to_dict() for crs in self.structured_store.get_crs_table(internal_category)]

    def search_crs(self, keyword: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search CRS table by product category or IS number."""
        internal_category = self._resolve_category(category)
        return [crs.to_dict() for crs in self.structured_store.search_crs(keyword, internal_category)]

    def get_stats(self) -> Dict[str, Any]:
        """Get combined statistics."""
        return {
            "vector_store": self.vector_store.get_stats(),
            "structured_store": self.structured_store.get_stats(),
        }


# Module-level convenience functions (for simple import style)
_default_retriever: Optional[Retriever] = None


def init_retriever(
    index_dir: Optional[str] = None,
    data_root: Optional[str] = None,
    embedder_model: str = "sentence-transformers/all-MiniLM-L6-v2",
) -> Retriever:
    """Initialize the default retriever instance."""
    global _default_retriever

    if index_dir is None:
        index_dir = os.environ.get("STANDORA_INDEX_DIR", "index")
    if data_root is None:
        data_root = os.environ.get("STANDORA_DATA_ROOT", "standora_data")

    index_path = Path(index_dir) / "faiss.index"
    metadata_path = Path(index_dir) / "chunks.pkl"
    if not index_path.exists() or not metadata_path.exists():
        pipeline = IngestionPipeline(
            data_root=Path(data_root),
            index_dir=Path(index_dir),
            embedder_model=embedder_model,
        )
        pipeline.run(force_rebuild=True)

    _default_retriever = Retriever.load(Path(index_dir), Path(data_root), embedder_model)
    return _default_retriever


def get_retriever() -> Retriever:
    """Get the default retriever instance (must be initialized first)."""
    if _default_retriever is None:
        raise RuntimeError("Retriever not initialized. Call init_retriever() first.")
    return _default_retriever


# Convenience functions that use the default retriever
def retrieve(query: str, category: Optional[str] = None, k: int = 5) -> List[Dict[str, Any]]:
    """Convenience function for vector retrieval."""
    return get_retriever().retrieve(query, category, k)


def retrieve_with_citations(query: str, category: Optional[str] = None, k: int = 5) -> List[Dict[str, Any]]:
    """Convenience function for vector retrieval with citation formatting."""
    return get_retriever().retrieve_with_citations(query, category, k)


def lookup_standard(is_number: str, category: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Convenience function for standard lookup."""
    return get_retriever().lookup_standard(is_number, category)


def search_standards(keyword: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Convenience function for standard search."""
    return get_retriever().search_standards(keyword, category)


def get_labs(category: Optional[str] = None, location: Optional[str] = None) -> List[Dict[str, Any]]:
    """Convenience function for lab lookup."""
    return get_retriever().get_labs(category, location)


def get_faqs(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Convenience function for FAQ lookup."""
    return get_retriever().get_faqs(category)


def search_faqs(query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Convenience function for FAQ search."""
    return get_retriever().search_faqs(query, category)


def get_crs_table(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Convenience function for CRS table."""
    return get_retriever().get_crs_table(category)


def search_crs(keyword: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Convenience function for CRS search."""
    return get_retriever().search_crs(keyword, category)