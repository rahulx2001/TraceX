"""Real sockets verify analytics cannot block health/WS and SIGTERM drains."""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

import httpx
import websockets


def test_analytics_leaves_live_sockets_responsive_and_sigterm_exits(tmp_path):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    marker = tmp_path / "analytics-started"
    source = """
import os, time
from pathlib import Path
import uvicorn
from src.api.main import app
from src.frontline import analytics
from src.ops.drain import DRAIN
from scripts.seed_domains import build
from src.data.warehouse import init_ops_db
init_ops_db()
build('automotive_nhtsa', force=True)

def slow_forecast(**kwargs):
    Path(os.environ['SLOW_MARKER']).touch()
    time.sleep(2)
    return {'ok': True}
analytics.forecast_cluster_volume = slow_forecast
# Keep a call active so shutdown must reach its deadline rather than exit
# immediately. The drain hook records that SIGTERM began the drain.
DRAIN.register_active('held-call')
DRAIN.on_drain(lambda: Path(os.environ['DRAIN_MARKER']).touch())
uvicorn.run(app, host='127.0.0.1', port=int(os.environ['TEST_PORT']), log_level='info', timeout_graceful_shutdown=1)
"""
    env = {**os.environ, "TEST_PORT": str(port), "SLOW_MARKER": str(marker),
           "DRAIN_MARKER": str(tmp_path / "draining"), "FRONTLINE_DRAIN_TIMEOUT_S": "0.2",
           "FRONTLINE_DB_PATH": str(tmp_path / "ops.duckdb"), "DOMAIN_DB_PATH": str(tmp_path / "domains"),
           "FRONTLINE_ENABLED": "1", "FRONTLINE_AUTH_REQUIRED": "0", "FRONTLINE_OPEN_MODE": "1",
           "FRONTLINE_API_KEY": "", "PILOT_HARDENED": "0", "FRONTLINE_TEST_ISOLATION": "1"}
    log_path = tmp_path / "server.log"
    with log_path.open("w") as log:
        process = subprocess.Popen([sys.executable, "-c", source], env=env, stdout=log, stderr=log)
        base = f"http://127.0.0.1:{port}"
        try:
            with httpx.Client(timeout=5) as client:
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    try:
                        if client.get(base + "/health").status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(0.05)
                else:
                    raise AssertionError(log_path.read_text())
                with ThreadPoolExecutor(max_workers=1) as pool:
                    slow = pool.submit(client.get, base + "/api/frontline/analytics/forecast")
                    deadline = time.monotonic() + 5
                    while not marker.exists() and time.monotonic() < deadline:
                        time.sleep(0.01)
                    assert marker.exists(), log_path.read_text()
                    start = time.monotonic()
                    assert client.get(base + "/health").status_code == 200

                    async def connect_console():
                        async with websockets.connect(f"ws://127.0.0.1:{port}/ws/console", open_timeout=1):
                            pass

                    asyncio.run(connect_console())
                    assert time.monotonic() - start < 1.5
                    assert not slow.done(), "analytics finished before the concurrency probe"
                    assert slow.result().json() == {"ok": True}
            start = time.monotonic()
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=5)
            assert (tmp_path / "draining").exists()
            assert 0.15 <= time.monotonic() - start < 5
            assert "Application shutdown complete" in log_path.read_text()
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
