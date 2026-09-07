"""
Standora Ingestion Pipeline

Modular components for:
- Document chunking (preserving heading/section structure)
- Embedding generation with sentence-transformers
- FAISS vector index management
- Structured data loading (standards, labs, FAQs, CRS table)
- Retrieval and lookup interfaces
"""

from .chunker import chunk_markdown, Chunk
from .embedder import Embedder
from .vector_store import VectorStore
from .structured_store import StructuredStore
from .pipeline import IngestionPipeline
from .retriever import (
    Retriever,
    init_retriever,
    get_retriever,
    retrieve,
    retrieve_with_citations,
    lookup_standard,
    search_standards,
    get_labs,
    get_faqs,
    search_faqs,
    get_crs_table,
    search_crs,
)
from .categories import CATEGORY_MAP, REVERSE_CATEGORY_MAP, normalize_category, denormalize_category

__all__ = [
    "chunk_markdown",
    "Chunk",
    "Embedder",
    "VectorStore",
    "StructuredStore",
    "IngestionPipeline",
    "Retriever",
    "init_retriever",
    "get_retriever",
    "retrieve",
    "retrieve_with_citations",
    "lookup_standard",
    "search_standards",
    "get_labs",
    "get_faqs",
    "search_faqs",
    "get_crs_table",
    "search_crs",
    "CATEGORY_MAP",
    "REVERSE_CATEGORY_MAP",
    "normalize_category",
    "denormalize_category",
]