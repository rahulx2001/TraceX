"""Issued supervisor credentials work as cookies without elevating another role."""
import time

from fastapi.testclient import TestClient


def test_exchange_preserves_verified_role_and_hides_token(reset_ops_db, monkeypatch):
    from src.api.main import app
    from src.api.rbac import issue_session

    monkeypatch.setenv("FRONTLINE_AUTH_REQUIRED", "1")
    monkeypatch.setenv("FRONTLINE_OPEN_MODE", "0")
    monkeypatch.setenv("SESSION_SECRET", "test-exchange-secret-at-least-32-characters")
    token = issue_session("judge", "supervisor", issuer_role="admin")["token"]
    with TestClient(app) as c:
        r = c.post("/api/frontline/auth/session/exchange", json={"token": token, "role": "admin"})
        assert r.status_code == 200
        assert r.json()["role"] == "supervisor"
        assert "token" not in r.json()
        assert "httponly" in r.headers["set-cookie"].lower()
        assert c.get("/api/frontline/auth/me").json()["role"] == "supervisor"
        assert c.post("/api/frontline/auth/session/exchange", json={"token": token + "tampered"}).status_code == 401
        assert c.post("/api/frontline/auth/session/exchange", json={"token": "operator-api-key"}).status_code == 401


def test_expired_exchange_cannot_authenticate(reset_ops_db, monkeypatch):
    from src.api.main import app
    from src.api.rbac import issue_session

    monkeypatch.setenv("SESSION_SECRET", "test-exchange-secret-at-least-32-characters")
    token = issue_session("judge", "agent")["token"]
    later = time.time() + 86400
    with TestClient(app) as c:
        with monkeypatch.context() as m:
            m.setattr("src.api.rbac.time.time", lambda: later)
            assert c.post("/api/frontline/auth/session/exchange", json={"token": token}).status_code == 401
