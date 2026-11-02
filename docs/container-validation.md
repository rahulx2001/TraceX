# Current container setup and verification

Use `Dockerfile.hackathon` and `docker-compose.hackathon.yml` for the current
Report → Investigate → Review → Evidence path. The generic `Dockerfile` is the
older pilot packaging and does not include the current campaign/review assets.

Set `FRONTLINE_API_KEY` and a **different** `SESSION_SECRET` to separate random
values of at least 32 characters in your private environment or local `.env`.
Preserve the values across restarts. Do not commit them. Then run:

```bash
docker compose -f docker-compose.hackathon.yml up --build
```

Open `http://127.0.0.1:8000/ui/`. Use **Have an operator API key?** for operator
entry. Container administrators can issue a named supervisor session locally:

```bash
docker compose -f docker-compose.hackathon.yml exec tracex python -c \
  "from src.api.rbac import issue_session; print(issue_session('local-supervisor', 'supervisor', issuer_role='admin')['token'])"
```

Treat that output as a credential. Use **Have a supervisor session?** at
`/ui/#signin` to exchange it for an HttpOnly cookie. The API key alone does not
grant supervisor review authority. The supervisor name above is a local setup
identity, not evidence that an independent reviewer participated.

The named `/app/data` volume preserves the campaign, original turns, review
history and local trust identity. First startup applies additive migrations,
seeds the labelled fictional records and creates a unique Ed25519 key with
owner-only file permissions. Restart preserves that key and existing records.
This key serves the preexisting contact evidence-locker mechanism; the campaign
packet is still explicitly **unsigned**.

Automatic local trust initialization never replaces a configured, revoked or
broken trust store. Production/staging/hardened deployments require explicitly
provisioned trust. The trust-root requirement remains enabled. An older seed
volume is refused with a version message; preserve it and choose a new volume
explicitly instead of deleting its history.

## Reproduce the checks without inference

The following runner creates its own disposable container, exposes it only on
loopback, mounts no host data and disables model calls. It does not read `.env`
or pass provider keys to the container. The source and verification-file hashes
are saved alongside the actual result and logs. Node and Playwright are needed
only for the browser portion; the Python runner uses the standard library.

```bash
TRACEX_REVISION=$(git rev-parse HEAD)
docker build --pull --no-cache \
  --label "org.opencontainers.image.revision=$TRACEX_REVISION" \
  -f Dockerfile.hackathon -t tracex-readiness:local .
npm --prefix dashboard ci
cd dashboard
npx playwright install chromium
cd ..
python3 -m scripts.docker_readiness --image tracex-readiness:local \
  --expected-revision "$TRACEX_REVISION" --compose --browser \
  --output /tmp/tracex-container-check.json
```

With installed Chrome, use `PLAYWRIGHT_CHANNEL=chrome` for the final command.
For a non-default Docker daemon, pass `--context NAME` to the runner and the
same context to the Docker build. Compose uses a unique project and volume;
the runner deletes only its own test resources. Omit `--compose` for a bare
`docker run` check without a volume. Both paths exclude the local `.env`.

The browser checks rendered credential entry, invalid-key refusal, visible
403 refusal when an operator tries to create a campaign, supervisor
session exchange and a typed report containing a denial and model-year
correction. It verifies original stored turns, reviewed source/vehicle handoff,
linked correction revision, supervisor acceptance and downloaded evidence.
API checks cover the current seed, anonymous refusal, five review pages and
their scripts. Restart checks preserve campaign and trust identity. No host
audio/video enters the image.

The [container workflow](../.github/workflows/container-readiness.yml) builds
without a developer cache and executes this path on every readiness-branch
commit. [Recorded execution](../reports/hackathon/container_validation/README.md)
separates successful checks from retained failed attempts. This validates
fictional text/software behavior, not real speech, independent human review,
hosted access or vehicle outcomes.
