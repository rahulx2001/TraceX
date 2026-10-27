"""Dashboard reports must not hold up the live console WebSocket handshake."""

import asyncio
import threading

import httpx
import pytest
from fastapi import FastAPI

from src.api.routes import frontline, interactions, pipeline, platform56


@pytest.mark.parametrize(
    "path,module,function,is_async",
    [
        ("/api/frontline/wallboard", "src.frontline.wallboard", "build_wallboard", False),
        ("/api/frontline/metrics", "src.frontline.ops", "ops_metrics", False),
        ("/api/frontline/usage", "src.frontline.billing", "usage_dashboard", False),
        ("/api/frontline/copq/rank", "src.qubot.retrievers", "live_risk_by_dollar", False),
        ("/api/frontline/analytics/financial-impact", "src.frontline.analytics", "financial_impact", False),
        ("/api/frontline/insights/product-gap", "src.frontline.insights", "build_product_gap_board", False),
        ("/api/frontline/audits/export", "src.api.routes.frontline", "build_audit_export", True),
        ("/api/frontline/audits/export?format=csv", "src.api.export", "build_audit_export_csv", True),
    ],
)
async def test_console_connects_while_dashboard_report_is_busy(
    monkeypatch, path, module, function, is_async
):
    import importlib

    monkeypatch.setenv("FRONTLINE_OPEN_MODE", "1")
    monkeypatch.setenv("FRONTLINE_ENABLED", "1")
    monkeypatch.setattr(interactions, "fetch_agent_actions_since", lambda *args: [])
    started = threading.Event()
    release = threading.Event()

    def blocking_report(*args, **kwargs):
        started.set()
        release.wait(timeout=1)
        return {}

    async def blocking_async_report(*args, **kwargs):
        # The real async audit builder performs synchronous database/audit work.
        return blocking_report(*args, **kwargs)

    monkeypatch.setattr(
        importlib.import_module(module), function,
        blocking_async_report if is_async else blocking_report,
    )
    app = FastAPI()
    app.include_router(frontline.router)
    app.include_router(platform56.router)
    app.include_router(pipeline.router)
    app.add_api_websocket_route("/ws/console", interactions.console_ws)
    accepted = asyncio.Event()
    incoming = asyncio.Queue()

    async def send(message):
        if message["type"] == "websocket.accept":
            accepted.set()

    scope = {
        "type": "websocket", "asgi": {"version": "3.0"},
        "scheme": "ws", "path": "/ws/console", "raw_path": b"/ws/console",
        "query_string": b"", "headers": [], "subprotocols": [],
        "client": ("127.0.0.1", 1234), "server": ("127.0.0.1", 8000),
    }
    await incoming.put({"type": "websocket.connect"})
    ws_task = None
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        report = asyncio.create_task(client.get(path))
        try:
            assert await asyncio.to_thread(started.wait, 2), "report did not start"
            assert not report.done(), "report blocked the event loop until it finished"
            ws_task = asyncio.create_task(app(scope, incoming.get, send))
            await asyncio.wait_for(accepted.wait(), timeout=0.5)
            assert not report.done(), "console handshake waited for the report"
        finally:
            release.set()
            if ws_task:
                await incoming.put({"type": "websocket.disconnect", "code": 1000})
                await asyncio.wait_for(ws_task, timeout=2)
            response = await report
        assert response.status_code == 200
