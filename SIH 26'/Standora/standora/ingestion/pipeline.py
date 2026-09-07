"""
Main ingestion pipeline that orchestrates chunking, embedding, and structured loading.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
import os

from .chunker import chunk_all_supported_in_category, Chunk
from .embedder import Embedder
from .vector_store import VectorStore, build_vector_store
from .structured_store import StructuredStore, load_structured_store
from .categories import CATEGORY_MAP

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """End-to-end ingestion pipeline for Standora knowledge base."""

    def __init__(
        self,
        data_root: Path,
        index_dir: Path,
        embedder_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        chunk_max_words: int = 350,
        chunk_min_words: int = 50,
    ):
        """
        Initialize the pipeline.

        Args:
            data_root: Root directory containing category folders
            index_dir: Directory to save/load FAISS index and metadata
            embedder_model: Sentence-transformers model name
            chunk_max_words: Maximum words per chunk
            chunk_min_words: Minimum words per chunk
        """
        self.data_root = Path(data_root)
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)

        self.embedder = Embedder(embedder_model)
        self.chunk_max_words = chunk_max_words
        self.chunk_min_words = chunk_min_words

        self.vector_store: Optional[VectorStore] = None
        self.structured_store: Optional[StructuredStore] = None

    def run(self, force_rebuild: bool = False) -> Dict[str, Any]:
        """
        Run the full ingestion pipeline.

        Args:
            force_rebuild: If True, rebuild even if index exists

        Returns:
            Statistics about the ingestion
        """
        index_path = self.index_dir / "faiss.index"
        metadata_path = self.index_dir / "chunks.pkl"

        # Check if index already exists
        if not force_rebuild and index_path.exists() and metadata_path.exists():
            logger.info("Loading existing index...")
            self.vector_store = VectorStore.load(
                str(index_path), str(metadata_path), self.embedder.dimension
            )
            self.structured_store = load_structured_store(self.data_root)
            return self.get_stats()

        logger.info("Building new index...")

        # Load and chunk all markdown files
        all_chunks = self._load_and_chunk_all()
        logger.info(f"Created {len(all_chunks)} chunks from markdown files")

        # Build vector store
        self.vector_store = build_vector_store(
            all_chunks,
            self.embedder,
            str(index_path),
            str(metadata_path),
        )
        logger.info(f"Vector store built with {self.vector_store.index.ntotal} vectors")

        # Load structured data
        self.structured_store = load_structured_store(self.data_root)
        logger.info(f"Structured store loaded: {self.structured_store.get_stats()}")

        return self.get_stats()

    def _load_and_chunk_all(self) -> List[Chunk]:
        """Load and chunk all .md files in all category directories."""
        all_chunks = []

        for folder_name, internal_category in CATEGORY_MAP.items():
            category_dir = self.data_root / folder_name
            if not category_dir.is_dir():
                logger.warning(f"Category directory not found: {category_dir}")
                continue

            logger.info(f"Processing category: {folder_name} -> {internal_category}")
            chunks = chunk_all_supported_in_category(category_dir, internal_category)
            all_chunks.extend(chunks)

        return all_chunks

    def load_existing(self) -> None:
        """Load existing index and structured store."""
        index_path = self.index_dir / "faiss.index"
        metadata_path = self.index_dir / "chunks.pkl"

        if not index_path.exists() or not metadata_path.exists():
            raise FileNotFoundError("Index not found. Run pipeline first.")

        self.vector_store = VectorStore.load(
            str(index_path), str(metadata_path), self.embedder.dimension
        )
        self.structured_store = load_structured_store(self.data_root)

    def get_stats(self) -> Dict[str, Any]:
        """Get combined statistics."""
        stats = {}
        if self.vector_store:
            stats["vector_store"] = self.vector_store.get_stats()
        if self.structured_store:
            stats["structured_store"] = self.structured_store.get_stats()
        return stats


def run_ingestion(
    data_root: Optional[str] = None,
    index_dir: Optional[str] = None,
    force_rebuild: bool = False,
) -> IngestionPipeline:
    """
    Convenience function to run ingestion with configurable paths.
    Uses environment variables or defaults.

    Args:
        data_root: Path to standora_data folder (or STANDORA_DATA_ROOT env var)
        index_dir: Path to index folder (or STANDORA_INDEX_DIR env var)
        force_rebuild: Force rebuild even if index exists

    Returns:
        Configured IngestionPipeline instance
    """
    if data_root is None:
        data_root = os.environ.get("STANDORA_DATA_ROOT", "standora_data")
    if index_dir is None:
        index_dir = os.environ.get("STANDORA_INDEX_DIR", "index")

    pipeline = IngestionPipeline(
        data_root=Path(data_root),
        index_dir=Path(index_dir),
    )
    pipeline.run(force_rebuild=force_rebuild)
    return pipeline