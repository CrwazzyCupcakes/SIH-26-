"""
Category name mappings - shared constants to avoid circular imports.
"""

# Category mapping: folder name -> JSON internal category name
CATEGORY_MAP = {
    "electricals": "electrical_appliances_electronics",
    "food": "packaged_food_products",
    "toys": "toys",
    "shared": "shared",
}

REVERSE_CATEGORY_MAP = {v: k for k, v in CATEGORY_MAP.items()}


def normalize_category(folder_name: str) -> str:
    """Convert folder name to internal category name."""
    return CATEGORY_MAP.get(folder_name, folder_name)


def denormalize_category(internal_name: str) -> str:
    """Convert internal category name to folder name."""
    return REVERSE_CATEGORY_MAP.get(internal_name, internal_name)