#!/usr/bin/env python3
"""
Demo script showing the ingestion pipeline and retrieval working end-to-end.
Uses relative paths / environment variables for portability.
"""

import sys
import os
from pathlib import Path

# Add standora to path
sys.path.insert(0, str(Path(__file__).parent / "standora"))

from standora.ingestion import IngestionPipeline, Retriever
from standora.ingestion.pipeline import run_ingestion


def get_project_root() -> Path:
    """Get project root from environment or relative to this file."""
    return Path(__file__).parent


def run_demo():
    """Run the full demo: ingest data, then test retrieval."""

    project_root = get_project_root()
    DATA_ROOT = project_root / "standora_data"
    INDEX_DIR = project_root / "index"

    print("=" * 60)
    print("Standora Ingestion Pipeline Demo")
    print("=" * 60)
    print(f"Data root: {DATA_ROOT}")
    print(f"Index dir: {INDEX_DIR}")

    # Step 1: Run ingestion
    print("\n[1/3] Running ingestion pipeline...")
    pipeline = run_ingestion(
        data_root=str(DATA_ROOT),
        index_dir=str(INDEX_DIR),
        force_rebuild=True,
    )

    stats = pipeline.get_stats()
    print(f"\nVector Store Stats:")
    vs = stats.get("vector_store", {})
    print(f"  Total chunks: {vs.get('total_chunks', 0)}")
    print(f"  Total vectors: {vs.get('total_vectors', 0)}")
    print(f"  Dimension: {vs.get('dimension', 0)}")
    print(f"  Categories: {vs.get('categories', {})}")

    print(f"\nStructured Store Stats:")
    ss = stats.get("structured_store", {})
    print(f"  Standards: {ss.get('standards', 0)}")
    print(f"  Labs: {ss.get('labs', 0)}")
    print(f"  FAQs: {ss.get('faqs', 0)}")
    print(f"  CRS Entries: {ss.get('crs_entries', 0)}")
    print(f"  Categories: {ss.get('categories', {})}")

    # Step 2: Initialize retriever
    print("\n[2/3] Initializing retriever...")
    retriever = Retriever.load(INDEX_DIR, DATA_ROOT)
    print("Retriever ready.")

    # Step 3: Test queries
    print("\n[3/3] Testing retrieval...")

    test_queries = [
        # Food category queries
        ("What is IS 14543?", "food"),
        ("BIS certification process for packaged water", "food"),
        ("Edible oil standards in India", "food"),
        ("FSSAI and BIS overlap for food", "food"),

        # Toys category queries
        ("What are the toy safety standards in India?", "toys"),
        ("BIS licensing process for toys", "toys"),
        ("IS 9873 parts for toy safety", "toys"),
        ("Do toys need mandatory certification?", "toys"),

        # Electricals category queries
        ("CRS registration for LED lamps", "electricals"),
        ("IS 16102 requirements", "electricals"),
        ("How to verify BIS certification for charger", "electricals"),

        # Shared / cross-category
        ("How to get BIS certification?", None),
        ("Testing labs for food products", None),
        ("Hallmarking process for gold", "shared"),
        ("Consumer complaint process", "shared"),
    ]

    for query, category in test_queries:
        print(f"\n--- Query: '{query}' ---")
        if category:
            print(f"    Category filter: {category}")

        # Vector retrieval
        results = retriever.retrieve_with_citations(query, category=category, k=3)
        print(f"  Vector results: {len(results)}")
        for i, r in enumerate(results, 1):
            print(f"    {i}. [{r['category']}] {r['section']} (score: {r['score']:.3f})")
            print(f"       Citation: {r['citation']}")
            print(f"       Preview: {r['text'][:150]}...")

        # Structured lookups demo
        if "standard" in query.lower() or "IS " in query:
            std_results = retriever.search_standards(query, category)
            if std_results:
                print(f"  Standard matches: {len(std_results)}")
                for s in std_results[:2]:
                    print(f"    - {s['is_number']}: {s['title']} ({s['scheme']})")

        if "lab" in query.lower():
            labs = retriever.get_labs(category=category)
            if labs:
                print(f"  Labs in {category or 'all'}: {len(labs)}")
                for lab in labs[:2]:
                    print(f"    - {lab['name']} ({lab['location']})")

    # Test direct structured lookups
    print("\n" + "=" * 60)
    print("Direct Structured Lookups")
    print("=" * 60)

    print("\n--- lookup_standard('IS 14543') ---")
    std = retriever.lookup_standard("IS 14543")
    if std:
        print(f"  {std['is_number']}: {std['title']}")
        print(f"  Mandatory: {std['mandatory']}, Scheme: {std['scheme']}")

    print("\n--- search_standards('water', category='food') ---")
    for s in retriever.search_standards("water", "food"):
        print(f"  {s['is_number']}: {s['title']}")

    print("\n--- search_standards('LED', category='electricals') ---")
    for s in retriever.search_standards("LED", "electricals"):
        print(f"  {s['is_number']}: {s['title']}")

    print("\n--- get_labs(category='food') ---")
    for lab in retriever.get_labs("food"):
        print(f"  {lab['name']} - {lab['location']} - {lab['scope']}")

    print("\n--- get_labs(category='electricals') ---")
    for lab in retriever.get_labs("electricals"):
        print(f"  {lab['name']} - {lab['location']} - {lab['scope']}")

    print("\n--- get_faqs(category='toys') ---")
    for faq in retriever.get_faqs("toys"):
        print(f"  Q: {faq['question']}")
        print(f"  A: {faq['answer'][:100]}...")

    print("\n--- get_crs_table(category='electricals') ---")
    for crs in retriever.get_crs_table("electricals"):
        print(f"  {crs['product_category']}: {crs['is_number']}")

    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()