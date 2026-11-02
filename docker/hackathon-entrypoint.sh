#!/bin/sh
# [AI-LAYER] TraceX Hackathon single-container entrypoint: seed the demo once, then
# hand over to the unchanged pilot entrypoint (migrations, bootstrap, uvicorn).
set -e
cd /app
export AI_DEMO_ENABLED="${AI_DEMO_ENABLED:-1}"
export AI_EVIDENCE_DIR="${AI_EVIDENCE_DIR:-/app/data/ai_evidence}"
SEED_VERSION="2026-10-30-sourced-investigation-v3"
if [ -f /app/data/.hackathon_seeded ] && [ "$(cat /app/data/.hackathon_seeded)" != "$SEED_VERSION" ]; then
  echo "ERROR: demo seed version mismatch; expected $SEED_VERSION. Preserve the old volume and use a new demo data volume." >&2
  exit 1
fi
if [ ! -f /app/data/.hackathon_seeded ]; then
  echo "→ Hackathon demo seed (first start only)…"
  python -m scripts.migrate --db ops
  FRONTLINE_SEED_DEMO=1 python -m scripts.container_bootstrap
  FRONTLINE_AI_LAYER=off FRONTLINE_LLM_ENABLED=0 python -m scripts.safety_campaign_seed
  printf '%s\n' "$SEED_VERSION" > /app/data/.hackathon_seeded
fi
# Idempotent and preserves later operator work. Additive demo-version updates
# stay explicit in campaign history; an old volume is never wiped.
FRONTLINE_AI_LAYER=off FRONTLINE_LLM_ENABLED=0 python -m scripts.safety_campaign_seed
echo "   AI layer mode: $(python -c 'from src.ai_layer.config import ai_mode; print(ai_mode())')"
echo "   Demo path: http://localhost:${API_PORT:-8000}/ui/#demo"
exec /entrypoint.sh
