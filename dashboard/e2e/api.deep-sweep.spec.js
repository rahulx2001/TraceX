/**
 * Deep OpenAPI GET sweep + mutation edge cases (aggressive).
 */
import { test, expect } from "@playwright/test";

const BASE = process.env.BASE_URL || "http://127.0.0.1:8000";
const KEY =
  process.env.E2E_API_KEY ||
  process.env.FRONTLINE_API_KEY ||
  "live-harden-key-32-chars-min!!";

const H = { "X-API-Key": KEY };

test.describe("Deep OpenAPI GET sweep", () => {
  test("production-like docs/openapi not anonymously open (or openapi sweep)", async ({
    request,
  }) => {
    const openapi = await request.get(`${BASE}/openapi.json`);
    const docs = await request.get(`${BASE}/docs`);
    // Hardened servers disable docs (404); open/local keep 200.
    if (openapi.status() === 404 || docs.status() === 404) {
      expect([404, 401, 403]).toContain(openapi.status());
      expect([404, 401, 403]).toContain(docs.status());
      return;
    }
    expect(openapi.status()).toBe(200);
    const spec = await openapi.json();
    const paths = Object.entries(spec.paths || {});
    const failures = [];
    for (const [path, methods] of paths) {
      if (!methods.get) continue;
      if (path.includes("{")) continue;
      if (path === "/docs" || path === "/redoc" || path === "/openapi.json") continue;
      // /audits/export runs the groundedness auditor for every interaction in
      // the window and is covered by its own test with a realistic timeout.
      if (path === "/api/frontline/audits/export") continue;
      // Optional integrations legitimately answer 503 when unconfigured:
      // Google OIDC without GOOGLE_CLIENT_ID is exercised separately.
      if (path === "/api/frontline/auth/oidc/start") continue;
      const res = await request.get(`${BASE}${path}`, { headers: H });
      if (res.status() >= 500) {
        failures.push(`GET ${path} → ${res.status()} ${(await res.text()).slice(0, 160)}`);
      }
    }
    expect(failures, failures.join("\n")).toEqual([]);
  });

  test("optional OIDC start fails closed when unconfigured", async ({ request }) => {
    const r = await request.get(`${BASE}/api/frontline/auth/oidc/start`, {
      maxRedirects: 0,
    });
    if (r.status() === 503) {
      const body = await r.json();
      expect(JSON.stringify(body).toLowerCase()).toContain("google");
      return;
    }
    // When OIDC is configured, /start is a redirect or a 200 login rendezvous.
    expect([200, 302, 307]).toContain(r.status());
  });

  test("audit export returns a verified 200 document", async ({ request }) => {
    // The auditor verifies every action in every returned interaction, so this
    // endpoint is intentionally slower than the read-only sweep above.
    const r = await request.get(`${BASE}/api/frontline/audits/export?limit=5`, {
      headers: H,
      timeout: 120_000,
    });
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(body.count).toBeGreaterThanOrEqual(0);
    expect(body.manifest?.sha256).toMatch(/^[a-f0-9]{64}$/);
    for (const row of body.interactions || []) {
      expect(row.audit?.overall_verdict).toBeTruthy();
    }
  });

  test("core /api GETs without auth are 401 (not 500)", async ({ request }) => {
    const sample = [
      "/api/frontline/cases",
      "/api/packs",
      "/api/interactions",
      "/api/frontline/metrics",
      "/api/v3/learning/proposals",
    ];
    for (const path of sample) {
      const res = await request.get(`${BASE}${path}`);
      expect(res.status(), path).not.toBe(500);
      expect([401, 403]).toContain(res.status());
    }
  });
});

test.describe("Deep mutation edges", () => {
  test("usage ignores client tenant spoof", async ({ request }) => {
    const post = await request.post(`${BASE}/api/frontline/usage`, {
      headers: { ...H, "Content-Type": "application/json" },
      data: { metric: "e2e_contacts", quantity: 1, tenant_id: "spoofed_tenant_xyz" },
    });
    expect(post.status()).toBe(200);
    const body = await post.json();
    expect(body.tenant_id).not.toBe("spoofed_tenant_xyz");
  });

  test("case note author cannot be spoofed to CEO", async ({ request }) => {
    // Prefer automotive pack corpus if active pack's fixture is empty/wrong.
    let sim = await request.post(
      `${BASE}/api/frontline/simulate?count=2&speed=instant&pack_id=automotive_nhtsa`,
      { headers: H, timeout: 60_000 },
    );
    if (sim.status() !== 200) {
      sim = await request.post(`${BASE}/api/frontline/simulate?count=2&speed=instant`, {
        headers: H,
        timeout: 60_000,
      });
    }
    expect(sim.status()).toBe(200);
    const simBody = await sim.json();
    expect((simBody.completed || 0) + (simBody.cases_created || 0)).toBeGreaterThan(0);

    const list = await request.get(`${BASE}/api/frontline/cases?include_simulated=true&limit=5`, {
      headers: H,
    });
    expect(list.status()).toBe(200);
    const cases = (await list.json()).cases || [];
    expect(cases.length, "simulate should create cases").toBeGreaterThan(0);
    const cid = cases[0].case_id;
    // case:write belongs to supervisor/admin, not the service principal.
    const serviceNote = await request.post(`${BASE}/api/frontline/cases/${cid}/notes`, {
      headers: { ...H, "Content-Type": "application/json" },
      data: { body: "e2e note", author: "CEO" },
    });
    expect(serviceNote.status()).toBe(403);

    const mint = await request.post(`${BASE}/api/frontline/auth/session`, {
      headers: { ...H, "Content-Type": "application/json" },
      data: { subject: "e2e-note-admin", role: "admin" },
    });
    if (mint.status() === 403) {
      test.info().annotations.push({
        type: "note",
        description: "FRONTLINE_BOOTSTRAP_ADMIN not enabled — service-key denial verified only",
      });
      return;
    }
    expect(mint.status()).toBe(200);
    const token = (await mint.json()).token;
    const note = await request.post(`${BASE}/api/frontline/cases/${cid}/notes`, {
      headers: { ...H, "Content-Type": "application/json", "X-Frontline-Session": token },
      data: { body: "e2e note", author: "CEO" },
    });
    expect(note.status()).toBe(200);
    const j = await note.json();
    expect(j.author).not.toBe("CEO");
    expect(j.author).toMatch(/service|operator|e2e|admin/i);
  });

  test("subscriptions create validates channel", async ({ request }) => {
    const bad = await request.post(`${BASE}/api/frontline/subscriptions`, {
      headers: { ...H, "Content-Type": "application/json" },
      data: { channel: "carrier-pigeon", target: "x@y.z" },
    });
    expect([400, 422]).toContain(bad.status());
  });

  test("jobs enqueue unknown type rejected; run-next denied for service", async ({
    request,
  }) => {
    const enq = await request.post(`${BASE}/api/frontline/jobs`, {
      headers: { ...H, "Content-Type": "application/json" },
      data: { job_type: "e2e_unknown_type", payload: { a: 1 } },
    });
    expect(enq.status()).toBe(400);
    const run = await request.post(`${BASE}/api/frontline/jobs/run-next`, {
      headers: H,
    });
    expect(run.status()).toBe(403);
  });

  test("dsr delete with service key is 403", async ({ request }) => {
    const r = await request.delete(`${BASE}/api/frontline/dsr/e2e_missing`, {
      headers: H,
    });
    expect(r.status()).toBe(403);
  });

  test("wrong API key is 401 everywhere critical", async ({ request }) => {
    const bad = { "X-API-Key": "wrong-key-that-is-long-enough!!" };
    for (const path of ["/api/frontline/cases", "/api/packs", "/api/interactions"]) {
      const r = await request.get(`${BASE}${path}`, { headers: bad });
      expect(r.status(), path).toBe(401);
    }
  });
});
