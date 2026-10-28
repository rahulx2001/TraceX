#!/usr/bin/env bash
# [AI-LAYER] One-command judge setup for the TraceX hackathon demo.
#
#   ./scripts/judge_setup.sh            # install, seed the demo, serve on http://127.0.0.1:8000
#   META_API_KEY=... ./scripts/judge_setup.sh   # same, with the optional Meta AI layer on
#   ./scripts/judge_setup.sh --no-serve # install + seed only
#
# Everything lives in data/hackathon/judge-v2/ (never the pilot data/frontline.duckdb).
# Seeding always uses the deterministic path, with no model spend. Serving
# loads the configured Meta key from .env and photo upload still works; with it, Muse Spark / SAM 3.1 add
# Hindi normalisation, slot filling, grounded briefs and photo analysis.
set -euo pipefail
cd "$(dirname "$0")/.."

SERVE=1
API_PORT="${API_PORT:-8000}"
for a in "$@"; do [ "$a" = "--no-serve" ] && SERVE=0; done

PYBIN="${PYTHON:-}"
if [ -z "$PYBIN" ]; then
  for c in python3.12 python3; do command -v "$c" >/dev/null 2>&1 && { PYBIN="$c"; break; }; done
fi
[ -n "$PYBIN" ] || { echo "Python 3.12 is required" >&2; exit 1; }
"$PYBIN" -c 'import sys; assert sys.version_info[:2] == (3, 12), "Use Python 3.12 for the reproducible judge setup"'
if [ -x .venv-hackathon/bin/python ]; then
  .venv-hackathon/bin/python -c 'import sys; assert sys.version_info[:2] == (3, 12), ".venv-hackathon must use Python 3.12"'
fi
START_AI_LAYER="${FRONTLINE_AI_LAYER:-auto}"
export FRONTLINE_AI_LAYER=off FRONTLINE_LLM_ENABLED=0 FRONTLINE_OPEN_MODE=0


echo "→ [1/5] Python env (.venv-hackathon) + dependencies"
[ -x .venv-hackathon/bin/python ] || "$PYBIN" -m venv .venv-hackathon
.venv-hackathon/bin/python -m pip install -q --upgrade pip
.venv-hackathon/bin/python -m pip install -q -r requirements.txt -c requirements-lock.txt

echo "→ [2/5] Dashboard build"
command -v npm >/dev/null 2>&1 || { echo "npm is required. The dashboard build is part of judge setup." >&2; exit 1; }
(
  cd dashboard
  if [ -f package-lock.json ]; then
    npm ci --silent
  else
    npm install --silent
  fi
  npm run build --silent
)

export FRONTLINE_DB_PATH="$PWD/data/hackathon/judge-v2/frontline.duckdb"
export DOMAIN_DB_PATH="$PWD/data/hackathon/judge-v2/domains"
export AI_EVIDENCE_DIR="$PWD/data/hackathon/judge-v2/ai_evidence"
export FRONTLINE_ENABLED=1 AI_DEMO_ENABLED=1
mkdir -p "$DOMAIN_DB_PATH"
chmod 700 data/hackathon/judge-v2

SEED_VERSION="2026-10-28-event"
if [ -f data/hackathon/judge-v2/.seeded ] && [ "$(cat data/hackathon/judge-v2/.seeded)" != "$SEED_VERSION" ]; then
  echo "Demo seed version mismatch: this checkout expects '$SEED_VERSION', found '$(cat data/hackathon/judge-v2/.seeded)'." >&2
  echo "The old seed is not reused. Move data/hackathon/judge-v2 aside (or delete it) and rerun this script." >&2
  exit 1
fi
if [ ! -f data/hackathon/judge-v2/.seeded ]; then
  echo "→ [3/5] Demo warehouses (fixture corpus, data/hackathon/judge-v2/)"
  .venv-hackathon/bin/python -m scripts.seed_frontline_fixtures
  echo "→ [4/5] Simulated traffic (opens early-warning investigations) + seeded India scenario"
  .venv-hackathon/bin/python -m src.frontline.simulator --count "${SIM_COUNT:-15}" --speed instant
  .venv-hackathon/bin/python -m scripts.ai_demo_seed --out data/hackathon/judge-v2/india_seed.json >/dev/null
  printf '%s\n' "$SEED_VERSION" > data/hackathon/judge-v2/.seeded
else
  echo "→ [3-4/5] data/hackathon seed $SEED_VERSION is current"
fi

KEY_FILE=data/hackathon/judge-v2/operator_api_key
[ -f "$KEY_FILE" ] || .venv-hackathon/bin/python -c "import secrets; print(secrets.token_hex(24))" > "$KEY_FILE"
chmod 600 "$KEY_FILE"
export FRONTLINE_API_KEY="$(cat "$KEY_FILE")" FRONTLINE_AUTH_REQUIRED=1

SESSION_FILE=data/hackathon/judge-v2/session_secret
[ -f "$SESSION_FILE" ] || .venv-hackathon/bin/python -c "import secrets; print(secrets.token_hex(32))" > "$SESSION_FILE"
chmod 600 "$SESSION_FILE"
export SESSION_SECRET="$(cat "$SESSION_FILE")"

SUPERVISOR_FILE=data/hackathon/judge-v2/supervisor_token.json
SUPERVISOR_TOKEN="$(.venv-hackathon/bin/python - << 'PY'
import json, time
from pathlib import Path
from fastapi import HTTPException
from src.api.rbac import issue_session
path = Path("data/hackathon/judge-v2/supervisor_token.json")
data = {}
if path.is_file():
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        data = {}
from src.api.rbac import verify_session
try:
    claims = verify_session(data.get("token") or "")
    current = claims.get("role") == "supervisor" and claims["exp"] > time.time() + 86400
except (ValueError, TypeError, KeyError, HTTPException):
    current = False
if not current:
    minted = issue_session(subject="judge_supervisor", role="supervisor", issuer_role="admin", ttl_s=86400 * 7)
    data = {"token": minted["token"], "exp": minted["exp"], "role": minted["role"]}
    path.write_text(json.dumps(data))
    path.chmod(0o600)
print(data["token"])
PY
)"
export SUPERVISOR_TOKEN

export FRONTLINE_AI_LAYER="$START_AI_LAYER"

echo
echo "AI layer: $(.venv-hackathon/bin/python -c 'from src.config import load_repo_env; load_repo_env(); from src.ai_layer.config import ai_mode; print(ai_mode())')"
echo "Seeded India case: $(.venv-hackathon/bin/python -c "import json;d=json.load(open('data/hackathon/judge-v2/india_seed.json'));print(d['case_id'], d['severity'], d['investigation_id'])")"
echo "The operator API key is a service principal. It does not sign you in as a supervisor."
echo "Operator API key (local only, paste on the Sign in page → 'Have an operator API key?'):"
echo "   $FRONTLINE_API_KEY"
echo "Supervisor session token (for supervisor actions like raise review):"
echo "   $SUPERVISOR_TOKEN"
echo "   (Sign in → Have a supervisor session? → paste this session. It is stored as an HttpOnly cookie.)"
echo "Demo path: http://127.0.0.1:$API_PORT/ui/#demo"
[ "$SERVE" = "1" ] || exit 0
echo "→ [5/5] Serving on http://127.0.0.1:$API_PORT (Ctrl-C to stop)"
exec .venv-hackathon/bin/python -m uvicorn src.api.main:app --host 127.0.0.1 --port "$API_PORT"
