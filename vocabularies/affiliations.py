"""
Utility to generate vocabulary of all Dutch organizations and their Research Organization Registry (ROR) identifier.

It is generated from the ROR Data Dump (https://ror.readme.io/docs/data-dump) in JSON format.

Usage: python3 affiliations.py /tmp/v1.74-2025-11-24-ror-data/v1.74-2025-11-24-ror-data_schema_v2.json
"""
__copyright__ = 'Copyright 2025-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
import sys
from typing import Any, List, Optional


def _organization_location(item: dict[str, Any]) -> bool:
    """Return True if organization location is 'NL'."""
    return any((loc.get("geonames_details") or {}).get("country_code") == "NL"
               for loc in item.get("locations", []))


def _organization_type(item: dict[str, Any]) -> bool:
    """Return True if organization type is 'education' or 'facility'."""
    return any(t in ("education", "facility") for t in item.get("types", []))


def _organization_name(item: dict[str, Any]) -> Optional[str]:
    """Return the organization name or None."""
    for n in item.get("names", []):
        if "ror_display" in n.get("types", []):
            return n.get("value")
    return None


def extract(data: List[dict[str, Any]]) -> List[dict[str, str]]:
    """Filter Dutch organizations with allowed types and return list of organizations."""
    organizations = []
    for it in data:
        if _organization_location(it) and _organization_type(it):
            organizations.append({"value": it.get("id"), "label": _organization_name(it) or ""})
    return sorted(organizations, key=lambda x: x["label"].lower())


def main(path: str) -> None:
    """Load JSON file, extract matching items, print JSON array."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(json.dumps(extract(data), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 affiliations.py /tmp/v1.74-2025-11-24-ror-data/v1.74-2025-11-24-ror-data_schema_v2.json")
        sys.exit(1)
    main(sys.argv[1])
