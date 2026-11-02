"""Run a disposable, authenticated image through current readiness checks.

Uses a previously built, revision-labelled image. No host data mounts, provider
keys, model calls or public ports. Only the container created here is removed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import time
import urllib.request

from scripts.submission_smoke import check

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True)
    parser.add_argument('--expected-revision', required=True)
    parser.add_argument('--context')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--browser', action='store_true', help='Run the current report/correction browser check too')
    parser.add_argument('--compose', action='store_true', help='Use the documented Compose service with an isolated project/volume')
    args = parser.parse_args()
    docker = ['docker'] + (['--context', args.context] if args.context else [])
    def run(*command, **kwargs):
        return subprocess.check_output([*docker, *command], text=True, **kwargs).strip()
    image = json.loads(run('image', 'inspect', args.image))[0]
    actual = image.get('Config', {}).get('Labels', {}).get('org.opencontainers.image.revision')
    if actual != args.expected_revision:
        raise ValueError('Image revision label differs from the intended source commit')
    # Never inherit provider keys or the developer's live spend paths.
    env = {k: v for k, v in os.environ.items() if not k.startswith(('META_', 'FRONTLINE_', 'DOMAIN_'))}
    env.update(FRONTLINE_API_KEY=secrets.token_urlsafe(36), SESSION_SECRET=secrets.token_urlsafe(48),
               FRONTLINE_AUTH_REQUIRED='1', FRONTLINE_OPEN_MODE='0', FRONTLINE_AI_LAYER='off',
               FRONTLINE_LLM_ENABLED='0', FRONTLINE_TEST_ISOLATION='1', MODEL_API_KEY='',
               BASETEN_API_KEY='', OPENAI_API_KEY='', CLAUDE_API_KEY='', DEEPGRAM_API_KEY='')
    name = 'tracex-readiness-' + secrets.token_hex(5)
    result = {'recorded_at': datetime.now(timezone.utc).isoformat(), 'status': 'failed',
              'source_commit': actual, 'image_id': image['Id'], 'architecture': image['Architecture'],
              'image_os': image['Os'], 'docker_server': run('version', '--format', '{{.Server.Version}}'),
              'scope': 'Disposable container integration checks on fictional seed/text data; no live inference or real audio.',
              'host_data_mounts': False, 'model_calls': 0, 'checks': []}
    result['startup'] = 'docker_compose' if args.compose else 'docker_run'
    result['verification_files'] = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (Path(__file__), ROOT/'scripts/submission_smoke.py',
                     ROOT/'dashboard/scripts/container-readiness.test.mjs', ROOT/'dashboard/scripts/report-handoff.test.mjs')}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    created = False
    compose = None
    private_config = None
    try:
        flags = [flag for key in ('FRONTLINE_API_KEY', 'SESSION_SECRET', 'FRONTLINE_AUTH_REQUIRED',
                 'FRONTLINE_OPEN_MODE', 'FRONTLINE_AI_LAYER', 'FRONTLINE_LLM_ENABLED', 'FRONTLINE_TEST_ISOLATION')
                 for flag in ('--env', key)]
        if args.compose:
            result['compose_version'] = run('compose', 'version', '--short')
            private_config = tempfile.TemporaryDirectory(prefix='tracex-compose-check-')
            override = Path(private_config.name)/'override.json'
            # No credentials enter the override. --env-file excludes local .env.
            override.write_text(json.dumps({'services': {'tracex': {
                'image': args.image, 'container_name': name,
                'environment': {'FRONTLINE_AI_LAYER': 'off', 'FRONTLINE_LLM_ENABLED': '0',
                                'FRONTLINE_TEST_ISOLATION': '1'}, 'restart': 'no'}}}))
            env['TRACEX_PUBLISH'] = '127.0.0.1::8000'
            compose = ['compose', '--env-file', '/dev/null', '-p', name,
                       '-f', str(ROOT/'docker-compose.hackathon.yml'), '-f', str(override)]
            created = True  # Clean up this unique project even if startup is partial.
            run(*compose, 'up', '-d', '--no-build', env=env)
        else:
            run('run', '-d', '--name', name, '-p', '127.0.0.1::8000', *flags, args.image, env=env)
            created = True
        def container_base():
            endpoint = run('port', name, '8000/tcp').splitlines()[0]
            if not endpoint.startswith('127.0.0.1:'):
                raise ValueError('Test container must be exposed only on loopback')
            return 'http://' + endpoint
        base = container_base()
        def ready():
            for _ in range(120):
                if run('inspect', '--format', '{{.State.Running}}', name) != 'true':
                    raise RuntimeError('Container exited before readiness; see retained container log')
                try:
                    with urllib.request.urlopen(base+'/health', timeout=1) as response:
                        if response.status == 200:
                            return
                except (OSError, TimeoutError):
                    pass
                time.sleep(1)
            raise RuntimeError('Container did not become healthy within the bounded startup wait')
        ready()
        first = check(base, env['FRONTLINE_API_KEY'], True)
        result['checks'].append({'name': 'current_seed_auth_and_five_review_pages', 'result': first})
        version = run('exec', name, 'python', '-c', "from pathlib import Path; print(Path('/app/data/.hackathon_seeded').read_text().strip())")
        assert version == '2026-10-30-sourced-investigation-v3'
        result['seed_version'] = version
        def trust_identity():
            return json.loads(run('exec', name, 'python', '-c', "from pathlib import Path; import hashlib,json; p=Path('/app/data/locker_keys'); print(json.dumps({'public_sha256':hashlib.sha256((p/'locker_ed25519.pub.pem').read_bytes()).hexdigest(),'private_mode':oct((p/'locker_ed25519.pem').stat().st_mode & 0o777),'migrations':sorted(f.name for f in Path('/app/migrations').glob('*.sql'))}))"))
        identity = trust_identity()
        assert identity['private_mode'] == '0o600'
        assert len(identity['migrations']) >= 3, 'Migration source files are missing from the image'
        result['checks'].append({'name': 'owner_only_local_trust_and_packaged_migrations', 'result': identity})
        files = json.loads(run('exec', name, 'python', '-c', "from pathlib import Path; import json; print(json.dumps([str(p) for p in Path('/app').rglob('*') if p.is_file() and p.suffix in {'.mp4','.webm','.wav','.aiff'}]))"))
        assert files == [], 'Local media must not enter the image'
        result['checks'].append({'name': 'no_local_media', 'files': files})
        if args.browser:
            token = run('exec', name, 'python', '-c', "from src.api.rbac import issue_session; print(issue_session('browser-test-supervisor', 'supervisor', issuer_role='admin')['token'])")
            with tempfile.TemporaryDirectory(prefix='tracex-container-browser-') as private:
                fixture = Path(private)/'fixture.json'
                fixture.write_text(json.dumps({'base': base, 'api_key': env['FRONTLINE_API_KEY'], 'supervisor_token': token, 'campaign_id': first['campaign_id']}))
                fixture.chmod(0o600)
                browser = subprocess.run(['node', 'scripts/container-readiness.test.mjs', str(fixture)], cwd=ROOT/'dashboard', env=env, capture_output=True, text=True)
                log = args.output.with_suffix('.browser.log')
                log.write_text(browser.stdout + browser.stderr)
                result['checks'].append({'name': 'rendered_entry_report_correction_revision_review_export', 'exit_code': browser.returncode, 'log': log.name})
                if browser.returncode:
                    raise RuntimeError('Container browser check failed; see retained browser log')
        run('restart', '--time', '15', name)
        # Docker can allocate a different ephemeral host port on restart.
        base = container_base()
        ready()
        second = check(base, env['FRONTLINE_API_KEY'], True)
        assert second['campaign_id'] == first['campaign_id'], 'Restart silently reseeded the campaign'
        assert trust_identity() == identity, 'Restart replaced the trust identity or migrations'
        result['checks'].append({'name': 'restart_preserves_current_campaign_and_review_pages', 'result': second})
        result['status'] = 'passed'
    except Exception as exc:
        result['error'] = str(exc)
        raise
    finally:
        if created:
            log = args.output.with_suffix('.container.log')
            log.write_text(run('logs', name, stderr=subprocess.STDOUT))
            result['container_log'] = {'path': log.name, 'sha256': hashlib.sha256(log.read_bytes()).hexdigest()}
            if compose:
                run(*compose, 'down', '--volumes', env=env)
            else:
                run('rm', '-f', name)
        if private_config:
            private_config.cleanup()
        result['elapsed_ms'] = round((time.monotonic()-started)*1000)
        args.output.write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
