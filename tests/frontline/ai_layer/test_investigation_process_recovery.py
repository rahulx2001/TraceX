"""Kill an actual worker during fake HTTP transport; preserve its reservation."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def test_process_death_during_transport_does_not_repeat_inference(tmp_path):
    environment = {**os.environ, "FRONTLINE_TEST_ISOLATION": "1", "FRONTLINE_AI_LAYER": "auto",
                   "FRONTLINE_DB_PATH": str(tmp_path/"ops.duckdb"), "DOMAIN_DB_PATH": str(tmp_path/"domains"),
                   "META_BUDGET_PATH": str(tmp_path/"budget.sqlite"), "META_CAP_PATH": str(tmp_path/"cap.json"),
                   "META_RESOURCE_PATH": str(tmp_path/"host"), "META_BACKEND": "meta", "META_MODEL_TEXT": "muse-spark-1.3",
                   "PROOF_STATE": str(tmp_path/"state.json"), "PROOF_WAITING": str(tmp_path/"waiting")}
    setup = """
import json, os, time
from pathlib import Path
from src.ai_layer import campaign_investigator as ci, safety_campaigns as sc, meta_client, config, budget
config.meta_enabled = lambda: True
config.active_api_key = lambda: 'fixture-key-never-sent'
meta_client.guard_url = lambda url: url
"""
    worker = setup + """
c = sc.demo_campaign('fixture', 'agent')
data = {'vehicle_id':'DEMO-CAR-003', 'revision':c['revision'], 'request_id':'interrupted-proof', 'text':'Knocking.'}
Path(os.environ['PROOF_STATE']).write_text(json.dumps({'campaign_id': c['campaign_id'], 'data':data}))
def blocked_transport(*args):
    Path(os.environ['PROOF_WAITING']).write_text(json.dumps(budget.status()))
    time.sleep(60)
    raise AssertionError('Parent should terminate fake transport')
meta_client.set_transport(blocked_transport)
ci.investigate(c['campaign_id'], data, 'fixture', 'agent')
"""
    child = subprocess.Popen([sys.executable, "-c", worker], env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic()+20
        marker = Path(environment["PROOF_WAITING"])
        while not marker.exists() and time.monotonic() < deadline and child.poll() is None:
            time.sleep(0.05)
        assert marker.exists(), f"Worker failed before fake transport: {child.poll()}"
        before = json.loads(marker.read_text())
        assert before["reserved_upper_bound_usd"] > 0
        child.kill()
        child.wait(timeout=5)
        restart = setup + """
state=json.loads(Path(os.environ['PROOF_STATE']).read_text())
def forbidden(*args): raise AssertionError('Restart must not call a provider')
meta_client.set_transport(forbidden)
recovered=ci.list_runs(state['campaign_id'])[0]
same=ci.investigate(state['campaign_id'], state['data'], 'fixture', 'agent')
assert recovered == same
print(json.dumps({'status':same['status'], 'retry':same['retry_requires_new_request'], 'operations':len(same['operations']), 'budget':budget.status()}))
"""
        result = subprocess.run([sys.executable, "-c", restart], env=environment, capture_output=True, text=True, timeout=20, check=True)
        actual = json.loads(result.stdout)
        assert actual["status"] == "interrupted" and actual["retry"] is True
        assert actual["operations"] == 1
        assert actual["budget"]["reserved_upper_bound_usd"] == before["reserved_upper_bound_usd"]
        assert actual["budget"]["live_successful_requests"] == 0
    finally:
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=5)
