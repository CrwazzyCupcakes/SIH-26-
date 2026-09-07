"""
Markdown chunker that preserves heading/section structure for citation.
Target chunk size: 200-400 words.
"""

from dataclasses import dataclass
from typing import List, Optional
import re
from pathlib import Path

from pypdf import PdfReader

from .categories import normalize_category


@dataclass
class Chunk:
    """A document chunk with metadata for citation."""
    text: str
    source_file: str
    category: str  # Internal category name (e.g., electrical_appliances_electronics)
    section: str
    heading_path: List[str]
    chunk_index: int
    word_count: int

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "source_file": self.source_file,
            "category": self.category,
            "section": self.section,
            "heading_path": self.heading_path,
            "chunk_index": self.chunk_index,
            "word_count": self.word_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Chunk":
        return cls(**data)


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def split_by_headings(markdown: str) -> List[tuple]:
    """
    Split markdown by headings, returning list of (heading_path, section_text).
    heading_path is a list of headings from root to current level.
    """
    lines = markdown.split("\n")
    sections = []
    current_heading_path = []
    current_section_lines = []

    heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$")

    for line in lines:
        match = heading_pattern.match(line)
        if match:
            if current_section_lines:
                sections.append((list(current_heading_path), "\n".join(current_section_lines).strip()))
                current_section_lines = []

            level = len(match.group(1))
            heading_text = match.group(2).strip()

            current_heading_path = current_heading_path[:level-1]
            current_heading_path.append(heading_text)
        else:
            current_section_lines.append(line)

    if current_section_lines:
        sections.append((list(current_heading_path), "\n".join(current_section_lines).strip()))

    return sections


def chunk_section(section_text: str, heading_path: List[str], max_words: int = 350, overlap: int = 50) -> List[str]:
    """
    Chunk a section into pieces of ~max_words with overlap.
    Splits on paragraphs first, then sentences if needed.
    """
    if count_words(section_text) <= max_words:
        return [section_text] if section_text.strip() else []

    paragraphs = [p.strip() for p in section_text.split("\n\n") if p.strip()]
    chunks = []
    current_chunk = []
    current_word_count = 0

    for para in paragraphs:
        para_words = count_words(para)

        if current_word_count + para_words <= max_words:
            current_chunk.append(para)
            current_word_count += para_words
        else:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))

            if para_words > max_words:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                sent_chunk = []
                sent_count = 0
                for sent in sentences:
                    sent_words = count_words(sent)
                    if sent_count + sent_words <= max_words:
                        sent_chunk.append(sent)
                        sent_count += sent_words
                    else:
                        if sent_chunk:
                            chunks.append(" ".join(sent_chunk))
                        sent_chunk = [sent]
                        sent_count = sent_words
                if sent_chunk:
                    chunks.append(" ".join(sent_chunk))
                current_chunk = []
                current_word_count = 0
            else:
                current_chunk = [para]
                current_word_count = para_words

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    if overlap > 0 and len(chunks) > 1:
        overlapped = []
        for i, chunk in enumerate(chunks):
            if i == 0:
                overlapped.append(chunk)
            else:
                prev_words = chunks[i-1].split()
                overlap_text = " ".join(prev_words[-overlap:])
                overlapped.append(overlap_text + "\n\n" + chunk)
        return overlapped

    return chunks


def chunk_markdown(markdown: str, source_file: str, folder_category: str, max_words: int = 350, min_words: int = 50) -> List[Chunk]:
    """
    Chunk a markdown document preserving heading hierarchy.
    Uses normalized internal category name.
    Returns list of Chunk objects with metadata.
    """
    internal_category = normalize_category(folder_category)
    sections = split_by_headings(markdown)
    all_chunks = []
    chunk_index = 0

    for heading_path, section_text in sections:
        if not section_text.strip():
            continue

        section_chunks = chunk_section(section_text, heading_path, max_words=max_words)

        for chunk_text in section_chunks:
            wc = count_words(chunk_text)
            if wc < min_words:
                continue

            section_name = heading_path[-1] if heading_path else "Introduction"

            all_chunks.append(Chunk(
                text=chunk_text,
                source_file=source_file,
                category=internal_category,
                section=section_name,
                heading_path=heading_path,
                chunk_index=chunk_index,
                word_count=wc,
            ))
            chunk_index += 1

    return all_chunks


def load_and_chunk_file(filepath: str, folder_category: str) -> List[Chunk]:
    """Load a markdown file and chunk it."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    return chunk_markdown(content, source_file=filepath, folder_category=folder_category)


def load_and_chunk_pdf(filepath: str, folder_category: str) -> List[Chunk]:
    """Extract text from a PDF and chunk it with page-aware citations."""
    reader = PdfReader(filepath)
    pages = []
    for page_number, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(f"# Page {page_number}\n\n{text}")

    return chunk_markdown(
        "\n\n".join(pages),
        source_file=filepath,
        folder_category=folder_category,
    )


def chunk_all_supported_in_category(category_dir: Path, folder_category: str) -> List[Chunk]:
    """Chunk Markdown and text-based PDF files in a category directory."""
    all_chunks = []
    for md_file in category_dir.glob("*.md"):
        chunks = load_and_chunk_file(str(md_file), folder_category)
        all_chunks.extend(chunks)
    for pdf_file in category_dir.glob("*.pdf"):
        chunks = load_and_chunk_pdf(str(pdf_file), folder_category)
        all_chunks.extend(chunks)
    return all_chunks


def chunk_all_markdown_in_category(category_dir: Path, folder_category: str) -> List[Chunk]:
    """Backward-compatible Markdown-only wrapper."""
    all_chunks = []
    for md_file in category_dir.glob("*.md"):
        all_chunks.extend(load_and_chunk_file(str(md_file), folder_category))
    return all_chunks