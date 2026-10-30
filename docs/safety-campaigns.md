# Safety campaigns: build and demo guide

TraceX now connects a documented component finding to installed-part traceability, reviewed owner outreach, workshop inspection, exact-part repair, follow-up and supplier corrective action. Open **Safety campaigns** in the sidebar, from Command center, or from an investigation's **Start a safety campaign** link.

This is a working single-tenant pilot with a complete synthetic walkthrough. It is not a validated accident predictor. Real provider messaging, OEM record integrations, workshop booking integrations and regulatory submissions are not implemented by this module.

## Run

Use the project's installed Python environment and existing API startup command. Rebuild the dashboard:

```bash
cd dashboard
npm run build
cd ..
.venv/bin/python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765/ui/#safety-campaigns`. Restart an already-running API process after deploying the new Python files. No manual database migration is required: the two additive safety campaign tables initialise on first access. Existing pilot data is preserved.

For an isolated walkthrough, use a separate warehouse. This example disables external AI and does not load the repository's `.env`:

```bash
FRONTLINE_TEST_ISOLATION=1 \
FRONTLINE_DB_PATH=/tmp/tracex-safety-demo/frontline.duckdb \
DOMAIN_DB_PATH=/tmp/tracex-safety-demo/domains \
FRONTLINE_OPEN_MODE=1 FRONTLINE_AI_LAYER=off FRONTLINE_ENABLED=1 \
.venv/bin/python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8766
```

Open `http://127.0.0.1:8766/ui/#safety-campaigns`. An isolated warehouse without a domain pack may show the shell's existing unhealthy/unreachable health badge; safety campaign endpoints operate independently of the historical pack warehouse. Do not reset the normal pilot warehouse to fix that badge.

The normal server uses the existing server-side Meta configuration and budgets. **Suggest symptoms with Meta** is an explicit optional action; loading the campaign never makes a model call. A missing key, timeout, or ungrounded output falls back to manual review. The plain-JSON provider fallback retains the expected schema in the prompt and validates the response locally.

A live check on 2026-10-29 through the main app on port 8765 successfully extracted `clunk` and `steering_pull` from a fictional Hinglish report using `meta-models/muse-spark-open-1026`. The demo and evidence packet APIs also passed. See [`reports/hackathon/safety_campaign_smoke.json`](../reports/hackathon/safety_campaign_smoke.json). This single integration check does not establish diagnostic accuracy or accident reduction.

## Five-minute walkthrough

All identifiers below are fictional and belong only to the synthetic demo.

1. Open **Safety campaigns**. The configured judge setup now prepares the walkthrough automatically; **Load ready demo** also prepares or reopens it without resetting your changes.
2. The overview already contains 12 vehicles, 8 simulated notices, 8 owner replies, 5 inspections, 3 vehicles with confirmed crack findings, 2 verified repairs and 2 reviewed resolutions. Eight vehicle reviews remain open. These are fictional records, not measured real-world outcomes.
3. Use **Review unknown lot** to inspect vehicle 010. **Fill demo example** supplies synthetic installation references for a trace review; review and save it to turn the unknown link into a verified match. Scope changes require fresh outreach approval.
4. Use **Read owner reports** to see stored English and Hinglish replies. **Fill example owner update** prepares another synthetic report. Meta suggestions are optional, use the existing configured backend, and must be reviewed before saving.
5. Use **Continue a repair** to open vehicle 003, which already has a documented crack and recovery. Select **Record part replacement**, click **Fill demo example**, and save. Repeat for repair verification, symptom-free follow-up and reviewer resolution. The reviewed part and procedure are already available.
6. Use **View a resolved vehicle** for vehicle 001. Its inspection, part replacement, verification, follow-up and disposition are recorded. Adding a new symptom report reopens it while preserving the earlier evidence in the audit timeline.
7. Vehicle 002 shows why a verified repair is not the same as completed follow-up: its owner is still unreachable. Vehicle 006 has an overdue booking. Vehicle 007 has no contact consent and received no simulated notice. Vehicles 011–012 have documented different lots.
8. **Supplier & audit trail** opens the recorded containment action, responsible quality owner, due date and evidence. Download the complete packet. Closure remains gated on verified traceability, completed vehicle dispositions, supplier verification and the manufacturer's regulatory decision reference.

All remaining demo forms include **Fill demo example**. It only fills the fields; it does not approve or save the action. These helpers are absent from real campaigns. Do not resolve outstanding vehicles just to make the dashboard green.

To prepopulate an existing configured warehouse, stop its API process and run with the same environment:

```bash
.venv-hackathon/bin/python -m scripts.safety_campaign_seed
```

This command is idempotent, makes no provider calls, and preserves the other campaigns and historical pilot data. The existing `scripts/judge_setup.sh` now runs it even if the older fixture seed is already current.

If a freshly built frontend shows **Not Found**, the API process may still be running the previous Python code. Restart that process and verify `GET /api/safety-campaigns` returns successfully with the existing operator credentials. Rebuilding Vite alone does not reload Python routes. Wait for the old process to release its DuckDB lock before starting the replacement.

## Vehicle import

Use **CSV template** in Vehicle traceability. Exact header:

```csv
vehicle_id,owner_ref,model,supplier,part_number,lot_id,trace_status,source_ref,contact_consent,channel
DEMO-CAR-101,DEMO-OWNER-101,Fictional crossover,SYN-AXLEWORKS,SYN-CA-2301,SYN-LOT-A,verified,SYN-BUILD-101,yes,whatsapp
```

- `vehicle_id` is a fleet vehicle identifier or VIN reference; this import does not decode a VIN or prove a component lot from the VIN.
- `owner_ref` references the authorised owner registry. This module does not require contact addresses.
- `trace_status`: `verified`, `unverified`, or `unknown`. Verified means the importing/reviewing operator has supporting build or current service-installation evidence. TraceX cannot independently authenticate that external evidence.
- A verified supplier + part + lot match is exact; an unverified matching row is possible; incomplete/unverified mismatches remain unknown; a documented verified mismatch is outside this lot's scope. An urgent report from such a vehicle still creates a safety review.
- `source_ref` must reference a build, installation or service record. Model similarity is not a substitute.
- `contact_consent`: `yes` or `no`; channel: `whatsapp`, `sms`, `phone`, or `email`. These are simulated channels here.
- Up to 500 rows per import, 500 KB input, and 2,000 vehicles per campaign. Imports are atomic. Duplicate vehicle IDs are rejected; use trace review to correct existing rows.
- Scope imports and trace corrections invalidate outreach approval. Existing notice records remain historical evidence.

## Implemented boundaries

- **Authority:** reviewer decisions on non-demo campaigns require a signed supervisor session, even in local open mode. Synthetic campaigns allow labelled review rehearsal; client request data cannot turn a normal campaign into a synthetic one. Operators with contact-write permission can load and update synthetic campaigns. Real campaign writes retain case-write permission and signed-supervisor approval requirements.
- **Safety:** critical seed findings and urgent reports create sticky holds. Free-text hazard keywords can over-triage and are not a diagnosis. A no-symptoms majority does not reduce urgency. A conflicting negative inspection cannot remove an unresolved confirmed repair need.
- **Evidence lifecycle:** current state and append-only audit events commit in one transaction. Revision conflicts reject stale writes. Repeated request IDs deduplicate the same action and reject changed payloads. New symptom reports invalidate previous episode verification and preserve historical evidence.
- **Remedy:** the reviewed replacement part must match the recorded repair. The procedure and approval snapshot are retained with the repair. The model cannot invent or approve parts.
- **Impact:** verified lot matches, unknown traceability, unresolved vehicles, holds, overdue records, owner reports, inspected vehicles, vehicles ever found cracked, current repairs/verification, and reviewed resolutions. Yield is cracks among inspected vehicles, not population prevalence. No accident-prevention counter, lives-saved estimate, or recall exemption is inferred.
- **AI:** optional English/Hindi/Hinglish symptom suggestions through the existing Meta adapter. Common PII patterns are redacted before transmission; accepted suggestions must quote the complete redacted report verbatim. The local original is then attached for review. Operators explicitly select symptoms before saving. Grounded quotations establish source fidelity, not medical/mechanical truth. An AI output never approves outreach or clears a vehicle.
- **Integrations:** notices, referrals, recovery, inspections and workshop records are recorded in the pilot. There is no live delivery provider, no automatic workshop reservation, no background reminder worker and no automatic regulatory filing. The live contact/early-warning/grounded-brief tools remain accessible through existing investigations.
- **Storage:** `safety_campaigns` stores versioned current state; `safety_campaign_events` stores immutable application-level event history. This follows the existing single-worker DuckDB pilot; it is not a multi-tenant database or tamper-proof external evidence archive.

## Verification

```bash
.venv/bin/python -m pytest tests/frontline/ai_layer/test_safety_campaigns.py \
  tests/frontline/ai_layer/test_lotguard_verify.py \
  tests/frontline/ai_layer/test_lotguard_workshop.py \
  tests/frontline/ai_layer/test_lotguard_approval.py -q
cd dashboard
npm run build
npm run test:theme
npm run test:qa-labels
npm run test:analytics
```

Tests use isolated databases and stub the provider. They exercise the full repair path, close-out/reopening, consent exclusions, scope corrections, conflicting evidence, malformed input, stale/concurrent requests, idempotency, rollback on failed audit write, and role boundaries.

Before a real field pilot, connect authoritative current installation/ownership records, manufacturer safety procedures, a consent-aware delivery provider with verified receipts, authenticated owner intake, a workshop system, scheduled follow-ups and the manufacturer's jurisdiction-specific recall/reporting process. Evaluate detection and extraction on independently labelled data; do not claim the existing historical backtests demonstrate reduced accidents.
