"""Isolated real API for the rendered sign-in regression test. No external calls."""
import argparse
import csv
import io
import json
import os
from pathlib import Path
import secrets
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True)
    parser.add_argument("--dist", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--mode", choices=("auth", "open"), required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root))
    state = Path(args.state)
    state.mkdir(parents=True, exist_ok=True)
    key = secrets.token_urlsafe(32)
    os.environ.update(
        FRONTLINE_TEST_ISOLATION="1", FRONTLINE_DB_PATH=str(state / "ops.duckdb"),
        DOMAIN_DB_PATH=str(state / "domains"), OIDC_LOCAL_PATH=str(state / "oidc.json"),
        QUBOT_LOCKER_DIR=str(state / "lockers"),
        FRONTLINE_OPEN_MODE="1" if args.mode == "open" else "0",
        FRONTLINE_AUTH_REQUIRED="0" if args.mode == "open" else "1",
        FRONTLINE_API_KEY="" if args.mode == "open" else key,
        SESSION_SECRET=secrets.token_urlsafe(48), FRONTLINE_SERVICE_IS_ADMIN="0",
        FRONTLINE_AI_LAYER="off", FRONTLINE_LLM_ENABLED="0", FRONTLINE_ENABLED="1",
        FRONTLINE_SLM_MODE="legacy", FRONTLINE_EMBEDDING_MODE="legacy",
        FRONTLINE_DISABLE_INLINE_WORKER="1", PILOT_HARDENED="0", SOC2_MODE="0",
        META_API_KEY="", MODEL_API_KEY="", BASETEN_API_KEY="", OPENAI_API_KEY="", CLAUDE_API_KEY="",
        DEEPGRAM_API_KEY="", META_BUDGET_PATH=str(state / "budget.sqlite"),
        META_CAP_PATH=str(state / "calls.json"), META_RESOURCE_PATH=str(state / "host"),
    )
    from src.ai_layer import safety_campaigns as sc, campaign_investigator as ci
    from src.api.rbac import issue_session
    from src.data.warehouse import init_ops_db
    from scripts.seed_domains import build
    init_ops_db()
    build("automotive_nhtsa")
    # Fictional fixture with real-campaign permission enforcement, confined to
    # this temporary warehouse. It supplies no human or model evaluation data.
    campaign = sc.create_campaign({
        "title": "Browser authentication fixture (fictional)", "supplier": "TEST-SUPPLIER",
        "part_number": "TEST-PART", "lot_id": "TEST-LOT", "component_name": "Control arm",
        "seed_evidence": "Fictional fixture for verifying access, not mechanical evidence.",
    }, "test-fixture", "supervisor")
    row = dict(vehicle_id="AUTH-FIXTURE-001", owner_ref="TEST-OWNER", model="Fictional test vehicle",
               supplier="TEST-SUPPLIER", part_number="TEST-PART", lot_id="TEST-LOT",
               trace_status="unverified", source_ref="AUTH-TEST-RECORD", contact_consent="no", channel="phone")
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=sc.CSV_COLUMNS)
    writer.writeheader()
    writer.writerow(row)
    campaign = sc.apply_action(campaign["campaign_id"], "import", {"csv": buffer.getvalue()},
                               "test-fixture", "supervisor", campaign["revision"], "auth-import")
    run = ci.investigate(campaign["campaign_id"], {"vehicle_id": row["vehicle_id"],
                         "revision": campaign["revision"], "request_id": "auth-draft",
                         "text": "Fictional report: steering pulls left. No fire occurred."}, "test-fixture", "supervisor")
    fixture = {"campaign_id": campaign["campaign_id"], "run_id": run["run_id"], "api_key": key}
    if args.mode == "auth":
        fixture["supervisor_token"] = issue_session("browser-test-supervisor", "supervisor", issuer_role="admin")["token"]
    path = state / "fixture.json"
    path.write_text(json.dumps(fixture))
    path.chmod(0o600)
    from src.api.main import app, _StreamedStaticFiles
    import uvicorn
    app.router.routes[:] = [r for r in app.router.routes if getattr(r, "path", None) != "/ui"]
    app.mount("/ui", _StreamedStaticFiles(directory=args.dist, html=True), name="dashboard")
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning", access_log=False)


if __name__ == "__main__":
    main()
