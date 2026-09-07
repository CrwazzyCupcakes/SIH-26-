"""
FAISS vector store for document retrieval with metadata.
"""

import json
import pickle
from pathlib import Path
from typing import List, Optional, Dict, Any
import numpy as np
import faiss

from .chunker import Chunk
from .embedder import Embedder


class VectorStore:
    """FAISS-based vector store with metadata persistence."""

    def __init__(self, dimension: int, index_path: Optional[str] = None, metadata_path: Optional[str] = None):
        """
        Initialize vector store.

        Args:
            dimension: Embedding dimension
            index_path: Path to load/save FAISS index
            metadata_path: Path to load/save chunk metadata
        """
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)  # Inner product = cosine similarity (since normalized)
        self.chunks: List[Chunk] = []
        self.index_path = index_path
        self.metadata_path = metadata_path

    def add_chunks(self, chunks: List[Chunk], embeddings: np.ndarray) -> None:
        """Add chunks and their embeddings to the store."""
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks must match number of embeddings")

        self.index.add(embeddings)
        self.chunks.extend(chunks)

    def search(self, query_embedding: np.ndarray, k: int = 5, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for similar chunks.

        Args:
            query_embedding: Query vector (1, dimension) or (dimension,)
            k: Number of results to return
            category: Optional category filter (internal category name)

        Returns:
            List of dicts with chunk data and similarity score
        """
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)

        # Search more than k to allow for category filtering
        search_k = min(k * 3, self.index.ntotal) if category else k
        if search_k == 0:
            return []

        scores, indices = self.index.search(query_embedding, search_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            chunk = self.chunks[idx]
            if category and chunk.category != category:
                continue
            results.append({
                "chunk": chunk,
                "score": float(score),
                "index": int(idx),
            })
            if len(results) >= k:
                break

        return results

    def save(self, index_path: Optional[str] = None, metadata_path: Optional[str] = None) -> None:
        """Save index and metadata to disk."""
        index_path = index_path or self.index_path
        metadata_path = metadata_path or self.metadata_path

        if not index_path or not metadata_path:
            raise ValueError("Paths must be provided either at init or at save time")

        Path(index_path).parent.mkdir(parents=True, exist_ok=True)
        Path(metadata_path).parent.mkdir(parents=True, exist_ok=True)

        faiss.write_index(self.index, index_path)

        with open(metadata_path, "wb") as f:
            pickle.dump([c.to_dict() for c in self.chunks], f)

    @classmethod
    def load(cls, index_path: str, metadata_path: str, dimension: int) -> "VectorStore":
        """Load vector store from disk."""
        index = faiss.read_index(index_path)
        with open(metadata_path, "rb") as f:
            chunk_dicts = pickle.load(f)

        store = cls(dimension=dimension, index_path=index_path, metadata_path=metadata_path)
        store.index = index
        store.chunks = [Chunk.from_dict(d) for d in chunk_dicts]
        return store

    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        categories = {}
        for chunk in self.chunks:
            categories[chunk.category] = categories.get(chunk.category, 0) + 1
        return {
            "total_chunks": len(self.chunks),
            "total_vectors": self.index.ntotal,
            "dimension": self.dimension,
            "categories": categories,
        }


def build_vector_store(
    chunks: List[Chunk],
    embedder: Embedder,
    index_path: str,
    metadata_path: str,
    batch_size: int = 32,
) -> VectorStore:
    """
    Convenience function to build a vector store from chunks.
    """
    texts = [c.text for c in chunks]
    embeddings = embedder.embed(texts, batch_size=batch_size)

    store = VectorStore(dimension=embedder.dimension)
    store.add_chunks(chunks, embeddings)
    store.save(index_path, metadata_path)
    return store