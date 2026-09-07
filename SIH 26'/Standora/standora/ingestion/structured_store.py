"""
Structured data store for standards, labs, FAQs, CRS table, etc.
These are loaded as-is for exact-match/structured lookup, NOT embedded.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict, field


@dataclass
class Standard:
    """Indian Standard metadata."""
    is_number: str
    title: str
    year: str
    mandatory: Any  # Can be bool or string
    scheme: str
    source_url: str
    notes: str
    category: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Lab:
    """Testing laboratory metadata."""
    name: str
    location: str
    scope: str
    contact: str
    category: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FAQ:
    """FAQ entry with citation."""
    question: str
    answer: str
    citation: str
    category: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CRSEntry:
    """CRS product table entry."""
    product_category: str
    is_number: str
    notification_reference: str
    category: str

    def to_dict(self) -> dict:
        return asdict(self)


class StructuredStore:
    """In-memory structured data store with lookup methods."""

    def __init__(self):
        self.standards: List[Standard] = []
        self.labs: List[Lab] = []
        self.faqs: List[FAQ] = []
        self.crs_table: List[CRSEntry] = []

        self._standards_by_category: Dict[str, List[Standard]] = {}
        self._labs_by_category: Dict[str, List[Lab]] = {}
        self._faqs_by_category: Dict[str, List[FAQ]] = {}
        self._crs_by_category: Dict[str, List[CRSEntry]] = {}

    def load_category(self, category_dir: Path, folder_category: str) -> None:
        """Load all structured JSON files from a category directory."""
        internal_category = folder_category  # Already normalized by caller
        self._load_standards(category_dir, internal_category)
        self._load_labs(category_dir, internal_category)
        self._load_faqs(category_dir, internal_category)
        self._load_crs_table(category_dir, internal_category)
        self._rebuild_indices()

    def _load_standards(self, category_dir: Path, internal_category: str) -> None:
        standards_file = category_dir / "standards.json"
        if not standards_file.exists():
            return
        with open(standards_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Trust the JSON's internal category field
        for s in data.get("standards", []):
            self.standards.append(Standard(category=internal_category, **s))

    def _load_labs(self, category_dir: Path, internal_category: str) -> None:
        labs_file = category_dir / "labs.json"
        if not labs_file.exists():
            return
        with open(labs_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        for lab in data.get("labs", []):
            self.labs.append(Lab(category=internal_category, **lab))

    def _load_faqs(self, category_dir: Path, internal_category: str) -> None:
        faqs_file = category_dir / "faqs.json"
        if not faqs_file.exists():
            return
        with open(faqs_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        for faq in data.get("faqs", []):
            self.faqs.append(FAQ(category=internal_category, **faq))

    def _load_crs_table(self, category_dir: Path, internal_category: str) -> None:
        crs_file = category_dir / "crs_table.json"
        if not crs_file.exists():
            return
        with open(crs_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        for entry in data.get("sample_rows", []):
            self.crs_table.append(CRSEntry(category=internal_category, **entry))

    def _rebuild_indices(self) -> None:
        self._standards_by_category = {}
        self._labs_by_category = {}
        self._faqs_by_category = {}
        self._crs_by_category = {}

        for s in self.standards:
            self._standards_by_category.setdefault(s.category, []).append(s)
        for lab in self.labs:
            self._labs_by_category.setdefault(lab.category, []).append(lab)
        for faq in self.faqs:
            self._faqs_by_category.setdefault(faq.category, []).append(faq)
        for crs in self.crs_table:
            self._crs_by_category.setdefault(crs.category, []).append(crs)

    # --- Standards ---

    def lookup_standard(self, is_number: str, category: Optional[str] = None) -> Optional[Standard]:
        """Look up a standard by IS number (exact or partial match)."""
        search_category = self._standards_by_category.get(category, []) if category else self.standards
        for std in search_category:
            if is_number.lower() in std.is_number.lower():
                return std
        return None

    def search_standards_by_keyword(self, keyword: str, category: Optional[str] = None) -> List[Standard]:
        """Find standards matching a keyword in title or IS number."""
        search_category = self._standards_by_category.get(category, []) if category else self.standards
        keyword_lower = keyword.lower()
        return [
            s for s in search_category
            if keyword_lower in s.title.lower() or keyword_lower in s.is_number.lower()
        ]

    def get_all_standards(self, category: Optional[str] = None) -> List[Standard]:
        """Get all standards, optionally filtered by category."""
        if category:
            return self._standards_by_category.get(category, [])
        return self.standards

    # --- Labs ---

    def lookup_lab(self, name: str, category: Optional[str] = None) -> Optional[Lab]:
        """Look up a lab by name (partial match)."""
        search_category = self._labs_by_category.get(category, []) if category else self.labs
        name_lower = name.lower()
        for lab in search_category:
            if name_lower in lab.name.lower():
                return lab
        return None

    def get_labs(self, category: Optional[str] = None, location: Optional[str] = None) -> List[Lab]:
        """Get labs, optionally filtered by category and/or location."""
        search_category = self._labs_by_category.get(category, []) if category else self.labs
        if location:
            location_lower = location.lower()
            return [lab for lab in search_category if location_lower in lab.location.lower()]
        return search_category

    # --- FAQs ---

    def get_faqs(self, category: Optional[str] = None) -> List[FAQ]:
        """Get FAQs, optionally filtered by category."""
        if category:
            return self._faqs_by_category.get(category, [])
        return self.faqs

    def search_faqs(self, query: str, category: Optional[str] = None) -> List[FAQ]:
        """Search FAQs by keyword in question or answer."""
        search_category = self._faqs_by_category.get(category, []) if category else self.faqs
        query_lower = query.lower()
        return [
            faq for faq in search_category
            if query_lower in faq.question.lower() or query_lower in faq.answer.lower()
        ]

    # --- CRS Table ---

    def get_crs_table(self, category: Optional[str] = None) -> List[CRSEntry]:
        """Get CRS table entries, optionally filtered by category."""
        if category:
            return self._crs_by_category.get(category, [])
        return self.crs_table

    def search_crs(self, keyword: str, category: Optional[str] = None) -> List[CRSEntry]:
        """Search CRS table by product category or IS number."""
        search_category = self._crs_by_category.get(category, []) if category else self.crs_table
        keyword_lower = keyword.lower()
        return [
            crs for crs in search_category
            if keyword_lower in crs.product_category.lower() or keyword_lower in crs.is_number.lower()
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        all_categories = set(
            list(self._standards_by_category.keys()) +
            list(self._labs_by_category.keys()) +
            list(self._faqs_by_category.keys()) +
            list(self._crs_by_category.keys())
        )
        return {
            "standards": len(self.standards),
            "labs": len(self.labs),
            "faqs": len(self.faqs),
            "crs_entries": len(self.crs_table),
            "categories": {
                cat: {
                    "standards": len(self._standards_by_category.get(cat, [])),
                    "labs": len(self._labs_by_category.get(cat, [])),
                    "faqs": len(self._faqs_by_category.get(cat, [])),
                    "crs_entries": len(self._crs_by_category.get(cat, [])),
                }
                for cat in all_categories
            },
        }


def load_structured_store(data_root: Path) -> StructuredStore:
    """Load structured data from all category directories under data_root."""
    from .categories import CATEGORY_MAP

    store = StructuredStore()
    for folder_name, internal_category in CATEGORY_MAP.items():
        category_dir = data_root / folder_name
        if category_dir.is_dir():
            store.load_category(category_dir, internal_category)
    return store