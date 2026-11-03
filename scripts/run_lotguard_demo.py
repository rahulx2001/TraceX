"""Run the isolated canonical LotGuard walkthrough at http://127.0.0.1:8770/ui/.

Uses a dedicated warehouse and the configured AI services from the local
.env. Canonical seeding stays offline; --offline also disables providers
while serving. Build dashboard first: cd dashboard && npm run build.
"""
import argparse
import asyncio
import json
import os
import secrets
from contextlib import contextmanager
from pathlib import Path
import sys


PROVIDER_KEYS = (
    "META_API_KEY", "MODEL_API_KEY", "BASETEN_API_KEY", "OPENAI_API_KEY",
    "CLAUDE_API_KEY", "DEEPGRAM_API_KEY",
)


def configure_services(root: Path, *, offline: bool) -> None:
    if not offline:
        from dotenv import load_dotenv
        load_dotenv(root / ".env", override=False)
        os.environ.pop("FRONTLINE_TEST_ISOLATION", None)
        os.environ.update(FRONTLINE_AI_LAYER="auto", FRONTLINE_LLM_ENABLED="1",
                          FRONTLINE_DISABLE_INLINE_WORKER="0")
        os.environ.setdefault("META_TIMEOUT_S", "30")
        os.environ["DEEPGRAM_ENABLED"] = "1" if os.getenv("DEEPGRAM_API_KEY", "").strip() else "0"
    else:
        os.environ.update({key: "" for key in PROVIDER_KEYS})
        os.environ.update(FRONTLINE_TEST_ISOLATION="1", FRONTLINE_AI_LAYER="off",
                          FRONTLINE_LLM_ENABLED="0", DEEPGRAM_ENABLED="0",
                          FRONTLINE_DISABLE_INLINE_WORKER="1")


@contextmanager
def offline_seed():
    """Keep canonical cases reproducible without clearing serving credentials."""
    names = (*PROVIDER_KEYS, "FRONTLINE_AI_LAYER", "FRONTLINE_LLM_ENABLED",
             "DEEPGRAM_ENABLED", "FRONTLINE_TEST_ISOLATION")
    saved = {name: os.environ.get(name) for name in names}
    try:
        os.environ.update({key: "" for key in PROVIDER_KEYS})
        os.environ.update(FRONTLINE_AI_LAYER="off", FRONTLINE_LLM_ENABLED="0",
                          DEEPGRAM_ENABLED="0", FRONTLINE_TEST_ISOLATION="1")
        yield
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8770)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--seed-only", action="store_true")
    parser.add_argument("--offline", action="store_true", help="Disable AI providers and background jobs for an offline replay")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    configure_services(root, offline=args.offline or args.seed_only)
    state = (args.state or root / "data/hackathon/eps-b14").resolve()
    state.mkdir(parents=True, exist_ok=True)
    secret_file = state / "local-session-secret"
    if not secret_file.exists():
        secret_file.write_text(secrets.token_urlsafe(48))
        secret_file.chmod(0o600)
    os.environ.update(
        FRONTLINE_DB_PATH=str(state / "ops.duckdb"),
        DOMAIN_DB_PATH=str(state / "domains"), OIDC_LOCAL_PATH=str(state / "oidc.json"),
        FRONTLINE_OPEN_MODE="1", FRONTLINE_AUTH_REQUIRED="0", FRONTLINE_API_KEY="",
        SESSION_SECRET=secret_file.read_text().strip(),
        FRONTLINE_ENABLED="1", API_HOST="127.0.0.1", API_PORT=str(args.port),
        FRONTLINE_SLM_MODE="legacy", FRONTLINE_EMBEDDING_MODE="legacy",
        PILOT_HARDENED="0", SOC2_MODE="0", CONNECTOR_ENABLED="0", ALERT_WEBHOOK_URL="",
        AI_EVIDENCE_DIR=str(root / "data/evidence/eps-b14"),
        QUBOT_LOCKER_DIR=str(state / "lockers"))
    # Cookies are host-scoped, not port-scoped. Keep the pilot's unrelated
    # supervisor cookie out of this separate fictional application's session.
    from src.api import rbac
    rbac.SESSION_COOKIE_LEGACY = "lotguard_eps_demo_session"
    rbac.SESSION_COOKIE_HOST = "__Host-lotguard_eps_demo_session"
    from src.data.warehouse import init_ops_db
    from src.config import settings
    from src.frontline import connectors
    from scripts.seed_domains import build
    from src.ai_layer.eps_demo import seed_eps_demo, frozen_evaluation
    connectors.CONFIG_PATH = state / "connector-config.json"
    connectors.OUTBOX_DIR = state / "outbox"
    connectors.reset_connector_config_cache()
    connectors.set_connector_config(enabled=False, webhook_url="", shared_secret="")
    init_ops_db()
    if not settings.domain_db_path("automotive_nhtsa").exists():
        build("automotive_nhtsa")
    if not frozen_evaluation()["verified"]:
        raise RuntimeError("Frozen evaluation gate failed; refresh and review before recording")
    with offline_seed():
        fixture = asyncio.run(seed_eps_demo())
    fixture["url"] = f"http://127.0.0.1:{args.port}/ui/{fixture['case_url']}"
    (state / "scenario.json").write_text(json.dumps(fixture, indent=2))
    print(fixture["message"], flush=True)
    print(fixture["url"], flush=True)
    from src.ai_layer.config import ai_status
    service_status = ai_status()
    print("AI services:", service_status["mode"], "· narration:",
          "on" if service_status["narration"]["enabled"] else "off", "· server speech:",
          "on" if os.getenv("DEEPGRAM_ENABLED") == "1" else "browser speech (no Deepgram key)", flush=True)
    if not args.seed_only:
        import uvicorn
        from src.api.main import app
        uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning", access_log=False)


if __name__ == "__main__":
    main()
