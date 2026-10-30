"""Read-only checks of a seeded current judge server; never calls a model."""
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request

REVIEW_KITS = ("original-300", "development", "fuel-complaints", "recalls", "study")


def check(base: str, key: str = "", auth_required: bool = True) -> dict:
    base = base.rstrip("/")
    def get(path, *, authenticated=True):
        headers = {"X-API-Key": key} if authenticated and key else {}
        try:
            with urllib.request.urlopen(urllib.request.Request(base + path, headers=headers), timeout=20) as response:
                return response.status, response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8", errors="replace")

    status, _ = get("/health", authenticated=False)
    assert status == 200, f"Health returned {status}"
    status, html = get("/ui/", authenticated=False)
    assert status == 200 and "<div id=\"root\">" in html, "Built dashboard is unavailable"
    if auth_required:
        status, _ = get("/api/safety-campaigns", authenticated=False)
        assert status == 401, f"Anonymous campaign read returned {status}; expected 401"
    status, body = get("/api/safety-campaigns")
    assert status == 200, f"Authenticated campaign list returned {status}"
    campaigns = json.loads(body)["campaigns"]
    prepared = [c for c in campaigns if c.get("synthetic_demo") and c.get("demo_version")]
    assert prepared, "Current prepared investigation campaign was not seeded"
    selected = prepared[0]
    path = "/api/safety-campaigns/" + selected["campaign_id"]
    status, body = get(path + "/packet")
    packet = json.loads(body)
    assert status == 200 and packet["synthetic_demo"] and "investigation_drafts" in packet
    verified = [v for v in packet["vehicles"] if v["match"] == "exact"]
    assert verified and all(v.get("installation_evidence") and v.get("trace_review") for v in verified), "Verified matches need inspectable installation records and reviews"
    assert all(v["trace_review"]["simulated"] for v in verified), "Prepared reviews must remain labelled simulated"
    assets = set()
    for kit in REVIEW_KITS:
        status, html = get("/api/safety-campaigns/review-kit/" + kit)
        assert status == 200 and "<html" in html.lower(), f"Review kit {kit} unavailable ({status})"
        assert "application/json" in html, f"Review kit {kit} has no prepared data"
        scripts = re.findall(r'<script[^>]+src="([^"]+)"', html)
        assert scripts, f"Review kit {kit} has no CSP-compatible client script"
        for script in scripts:
            assert script.startswith("/ui/review-scripts/"), f"Unexpected script path in {kit}"
            code, contents = get(script, authenticated=False)
            assert code == 200 and "<html" not in contents.lower(), f"Script {script} unavailable"
            assets.add(script)
    return {"ok": True, "scope": "read-only current setup and review-asset smoke", "model_calls": 0,
            "campaign_id": selected["campaign_id"], "demo_version": selected["demo_version"],
            "review_kits": list(REVIEW_KITS), "script_assets": sorted(assets),
            "authentication": "anonymous refused; key permitted" if auth_required else "open local mode"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--key-env", default="FRONTLINE_API_KEY", help="Name of the environment variable, never the key itself")
    parser.add_argument("--open", action="store_true", help="Validate intentionally open local server")
    args = parser.parse_args()
    print(json.dumps(check(args.base_url, os.environ.get(args.key_env, ""), not args.open), indent=2))


if __name__ == "__main__":
    main()
