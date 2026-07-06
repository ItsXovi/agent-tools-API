#!/usr/bin/env python3
"""Create an API key for PDF Toolkit API."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.services.keys import TIER_LIMITS, create_api_key, init_db  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a PDF Toolkit API key")
    parser.add_argument("--label", default=None, help="Optional label for the key")
    parser.add_argument(
        "--tier",
        choices=sorted(TIER_LIMITS),
        default="free",
        help="Usage tier (default: free)",
    )
    args = parser.parse_args()

    init_db()
    raw_key, record = create_api_key(label=args.label, tier=args.tier)

    print("API key created.")
    print(f"  key_id: {record.id}")
    print(f"  tier:   {record.tier}")
    print(f"  limit:  {record.limit} conversions/month")
    if record.label:
        print(f"  label:  {record.label}")
    print()
    print("Save this key now — it will not be shown again:")
    print(raw_key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
