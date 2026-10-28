"""Seed the LotGuard demo scenario.  [AI-LAYER]

    python -m scripts.lotguard_seed [--owners 24] [--no-contact]

Runs against the configured warehouses (judge setup points them at
data/hackathon/judge-v2/). Safe to re-run: records/cluster/investigation
are skipped when present; each run registers one more owner batch.
See src/ai_layer/lotguard.py. All seeded data is synthetic and labelled.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Seed the LotGuard demo scenario")
    p.add_argument("--pack", default="automotive_nhtsa")
    p.add_argument("--owners", type=int, default=24)
    p.add_argument("--no-contact", action="store_true")
    p.add_argument("--out", default=None, help="also write the result JSON to this file")
    args = p.parse_args(argv)
    from src.ai_layer.lotguard import seed_lotguard_scenario

    out = asyncio.run(seed_lotguard_scenario(pack_id=args.pack, owners=args.owners,
                                             with_contact=not args.no_contact))
    text = json.dumps(out, indent=2, default=str)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return 0 if out.get("investigation_id") else 1


if __name__ == "__main__":
    raise SystemExit(main())
