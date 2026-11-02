"""Record final software checks without writing through shared dependency symlinks.

Use --out with a new directory for a later run. Existing logs are never replaced.
The browser step retains all assertions, changing only Vite's config loader in
memory. No frozen script or shared node_modules file is edited.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
PY = ROOT / '.venv-hackathon/bin/python'
STEPS = ['replay', 'frozen_replay', 'dashboard_build', 'full_tests', 'eval_frontline',
         'dashboard_source', 'pipeline', 'compileall', 'browser']


def sha(path):
    return subprocess.check_output(['shasum', '-a', '256', str(path)], text=True).split()[0]


def run(step, out):
    out.mkdir(parents=True, exist_ok=True)
    log = out / 'logs' / (step + '.txt')
    log.parent.mkdir(exist_ok=True)
    if log.exists():
        raise FileExistsError(log)
    env = dict(os.environ, FRONTLINE_TEST_ISOLATION='1', PYTHONDONTWRITEBYTECODE='1',
               OPENAI_API_KEY='', ANTHROPIC_API_KEY='', BASETEN_API_KEY='', META_API_KEY='')
    cwd = ROOT
    stdin = None
    note = None
    commands = {
        'replay': [str(PY), '-B', '-m', 'scripts.synthetic_project_smoke', '--out', str(out / 'replay')],
        'frozen_replay': [str(PY), '-B', '-m', 'scripts.defect_verify'],
        'dashboard_build': ['npm', 'run', 'build', '--', '--configLoader', 'native'],
        'full_tests': ['make', 'test', '-o', 'dashboard-build'],
        'eval_frontline': ['make', 'eval-frontline'],
        'dashboard_source': [str(PY), '-B', '-m', 'scripts.ml_improvement_report', 'check'],
        'pipeline': [str(PY), '-B', '-m', 'scripts.verify_ml_pipeline', '--records', '76', '--out', str(out / 'pipeline.json')],
        'compileall': ['make', 'compileall'],
        'browser': ['node', '--input-type=module'],
    }
    if step == 'full_tests':
        built = json.loads((out / 'dashboard_build.json').read_text())
        if built['exit_code'] or not (ROOT / 'dashboard/dist/index.html').exists():
            raise ValueError('Successful native dashboard build required before make test')
        note = 'Uses the separately verified native-loader build; all make test Python setup and tests execute.'
    if step == 'dashboard_build':
        cwd = ROOT / 'dashboard'
        note = 'Native config loading avoids .vite-temp writes through shared node_modules.'
    if step == 'browser':
        cwd = ROOT / 'dashboard/scripts'
        source = (cwd / 'assert-signin-reachable.mjs').read_text()
        needle = 'await build({ root: dashboard,'
        if source.count(needle) != 1:
            raise ValueError('Browser harness changed; review adapter before execution')
        stdin = source.replace(needle, 'await build({ configLoader: "native", root: dashboard,')
        (out / 'browser_harness_native.mjs').write_text(stdin)
        env['ML_UI_ARTIFACT_DIR'] = str(out / 'browser_screenshots')
        note = ('Original browser harness and imported ML evidence assertions run via stdin from dashboard/scripts. '
                'Only build configLoader is changed to native in memory; this is not a bare node --test invocation.')
    with tempfile.TemporaryDirectory(prefix='rca-handover-pycache-') as cache:
        if step == 'compileall':
            env['PYTHONPYCACHEPREFIX'] = cache
        source_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        started = datetime.now(timezone.utc).isoformat()
        clock = time.monotonic()
        with log.open('x') as stream:
            result = subprocess.run(commands[step], cwd=cwd, env=env, input=stdin, text=True,
                                    stdout=stream, stderr=subprocess.STDOUT)
    body = log.read_text()
    record = dict(step=step, started_at=started, finished_at=datetime.now(timezone.utc).isoformat(),
                  duration_seconds=round(time.monotonic()-clock, 3), cwd=str(cwd.relative_to(ROOT)),
                  command=shlex.join(commands[step]), environment={key: env[key] for key in
                      ['FRONTLINE_TEST_ISOLATION', 'PYTHONDONTWRITEBYTECODE', 'OPENAI_API_KEY',
                       'ANTHROPIC_API_KEY', 'BASETEN_API_KEY', 'META_API_KEY']},
                  stdin_artifact='browser_harness_native.mjs' if stdin else None, note=note,
                  exit_code=result.returncode, log=str(log.relative_to(out)), log_sha256=sha(log),
                  observed_pytest_counts=re.findall(r'\b\d+ (?:passed|failed|skipped|xfailed|xpassed|errors?)\b', body),
                  code_commit=source_commit,
                  completion_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  runner_sha256=sha(Path(__file__)))
    if step == 'compileall':
        record['bytecode_destination'] = 'Disposable external PYTHONPYCACHEPREFIX; cleaned after command'
    (out / (step + '.json')).write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps(record, indent=2), flush=True)
    return result.returncode


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--step', choices=STEPS, action='append', required=True)
    parser.add_argument('--out', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    for step in args.step:
        code = run(step, args.out.resolve())
        if code:
            raise SystemExit(code)
