#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_store import validate_document


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    args = parser.parse_args()
    try:
        payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
        if isinstance(payload, dict) and payload.get("_meta", {}).get("marker") == "starline-git-submit-export":
            payload = payload.get("profile")
        validate_document(payload)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    print(json.dumps({"ok": True, "keys": sorted(payload)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
