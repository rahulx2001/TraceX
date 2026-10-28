// [AI-LAYER] Hackathon demo path (#demo): the four key screens on one page.
// 1. Call in Hindi/Hinglish + photo  2. Case with evidence  3. Grounded brief
// 4. Safety-first early-warning board. Existing screens are untouched; every
// step links to its full page.
import { useEffect, useState } from "react";
import { aiGet, aiPostJson, aiStatus } from "../src/ai/aiApi.js";
import { SpeechLangSelect } from "../src/ai/CallAiExtras.jsx";
import EvidencePanel from "../src/ai/EvidencePanel.jsx";
import GroundedBriefPanel from "../src/ai/GroundedBriefPanel.jsx";
import MetaTag from "../src/ai/MetaTag.jsx";
import SafetyRiskBoard from "../src/ai/SafetyRiskBoard.jsx";

const LAST_SEED_KEY = "skewai.ai.lastDemoSeed";
const SAMPLE_HINGLISH = "Meri Honda CR-V 2019 ke brakes fail ho rahe hain, pedal neeche tak chala jata hai aur kal almost accident ho gaya.";

function readLastSeed() {
  try { return JSON.parse(window.localStorage.getItem(LAST_SEED_KEY) || "null"); } catch { return null; }
}

function Step({ n, title, children, link, linkLabel }) {
  return (
    <section className="card demo-step" style={{ padding: 14, marginBottom: 14 }} data-testid={`demo-step-${n}`}>
      <h2 style={{ marginTop: 0, display: "flex", gap: 10, alignItems: "baseline" }}>
        <span className="chip">{n}</span> {title}
        {link && <a href={link} className="muted small" style={{ marginLeft: "auto" }}>{linkLabel || "Open full screen"} →</a>}
      </h2>
      {children}
    </section>
  );
}

function NormalizeTry() {
  const [text, setText] = useState(SAMPLE_HINGLISH);
  const [out, setOut] = useState(null);
  const [busy, setBusy] = useState(false);
  async function run() {
    setBusy(true);
    try { setOut(await aiPostJson("/api/ai/language/normalize", { text })); }
    catch (e) { setOut({ error: e.message }); }
    finally { setBusy(false); }
  }
  return (
    <div style={{ marginTop: 8 }}>
      <textarea value={text} onChange={(e) => setText(e.target.value)} style={{ width: "100%", minHeight: 54 }}
        aria-label="Hindi or Hinglish complaint" />
      <button className="primary" onClick={run} disabled={busy || !text.trim()}>{busy ? "Normalising…" : "Detect + normalise to English"}</button>
      {out && !out.error && (
        <div className="small" style={{ marginTop: 6 }}>
          <span className="chip">detected: {out.lang}</span>{" "}
          <MetaTag mode={out.method === "meta_muse_spark" ? "enhanced" : "deterministic"} models={out.method === "meta_muse_spark" ? ["Muse Spark"] : []}
            fallbackReason={out.fallback_reason} />
          <div style={{ marginTop: 4 }}><strong>English:</strong> {out.normalized_en}</div>
          <div className="muted">Original kept alongside: {out.original}</div>
        </div>
      )}
      {out && out.error && <div className="muted small">Normalise failed ({out.error}).</div>}
    </div>
  );
}

// Hero moment: the SAME Hinglish words through the pack's English kill-switch
// lexicon, first as spoken, then after English normalisation (Muse Spark when a
// key is set). NOTE: the live deterministic pipeline also runs the no-key
// hindi_safety.py layer, which catches this demo sentence; this panel isolates
// the pack lexicon so the remaining gap is visible and labelled honestly.
function HeroContrast({ text }) {
  const [out, setOut] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  async function run() {
    setBusy(true); setErr("");
    try { setOut(await aiPostJson("/api/ai/demo/safety-contrast", { text })); }
    catch (e) { setErr(e.message); } finally { setBusy(false); }
  }
  if (err) return <div className="muted small">Safety contrast unavailable ({err}).</div>;
  if (!out) return <button type="button" className="ghost" onClick={run} disabled={busy}>{busy ? "Comparing…" : "Compare safety checks"}</button>;
  const hit = (t) => t
    ? <span className="chip sev-critical">kill-switch: "{t}" → Critical, "do not drive"</span>
    : <span className="chip">no kill-switch term matched</span>;
  return (
    <div className="row" style={{ gap: 12, marginTop: 10, flexWrap: "wrap" }} data-testid="hero-contrast">
      <div className="card" style={{ flex: "1 1 280px", padding: 10 }}>
        <div className="small"><strong>Pack lexicon only</strong> <MetaTag mode="deterministic" /></div>
        <div className="small muted" style={{ margin: "4px 0" }}>English kill-switch lexicon on the caller's own words ({out.lang}); not the full no-key pipeline</div>
        {hit(out.original_kill_switch)}
      </div>
      <div className="card" style={{ flex: "1 1 280px", padding: 10 }}>
        <div className="small"><strong>Meta AI enhanced</strong>{" "}
          <MetaTag mode={out.translated_by_meta ? "enhanced" : "deterministic"} models={out.translated_by_meta ? ["Muse Spark"] : []} fallbackReason={out.fallback_reason} />
        </div>
        {out.translated_by_meta ? (
          <>
            <div className="small" style={{ margin: "4px 0" }}><strong>English:</strong> {out.normalized_en}</div>
            {hit(out.normalized_kill_switch)}
          </>
        ) : (
          <div className="small muted" style={{ margin: "4px 0" }}>
            Not run: no Meta key. With a key, Muse Spark translates first and the SAME lexicon runs on the English
            (covered by a mocked-Meta test; not verified against the live API).
          </div>
        )}
      </div>
      <div className="muted small" style={{ flexBasis: "100%" }}>This panel isolates the pack lexicon. The live no-key pipeline also runs the deterministic <span className="mono">hindi_safety.py</span> layer, which catches this demo sentence and opens the seeded case at Critical (verified 2026-10-26). AI can add a safety flag, never remove one.</div>
    </div>
  );
}

function CaseSummary({ caseId }) {
  const [c, setC] = useState(null);
  useEffect(() => {
    if (!caseId) return;
    aiGet(`/api/frontline/cases/${encodeURIComponent(caseId)}`).then(setC).catch(() => setC(null));
  }, [caseId]);
  if (!caseId) return <div className="muted small">Seed the scenario (or run a call) to get a case.</div>;
  if (!c) return <div className="muted small mono">{caseId}</div>;
  const flags = c.safety_flags && typeof c.safety_flags === "object" ? Object.keys(c.safety_flags).filter((f) => c.safety_flags[f]) : [];
  return (
    <div className="kvs small">
      <span className="k">case</span><span className="v mono">{c.case_id || caseId}</span>
      <span className="k">summary</span><span className="v">{c.description_summary || "—"}</span>
      <span className="k">component</span><span className="v">{c.category || "—"}</span>
      <span className="k">severity</span><span className="v">{c.severity || "—"} · P{c.priority} ({c.severity_source || "rules"})</span>
      <span className="k">safety flags</span><span className="v">{flags.length ? flags.join(", ") : "none"}</span>
      <span className="k">known issue</span><span className="v mono">{c.advisory_match_id || "—"}</span>
      <span className="k">investigation</span><span className="v mono">{c.investigation_id || "—"}</span>
    </div>
  );
}

function LotGuardStep() {
  const [lot, setLot] = useState(null);
  const [done, setDone] = useState(false);
  useEffect(() => {
    aiGet("/api/ai/lotguard/latest")
      .then((d) => setLot(d.lotguard || null))
      .catch(() => setLot(null))
      .finally(() => setDone(true));
  }, []);
  if (!done) return null;
  if (!lot) return null;
  return (
    <Step n={5} title="LotGuard: one cracked part protects its whole lot"
      link={`#issue/${encodeURIComponent(lot.investigation_id)}`} linkLabel="Open the lot investigation">
      <p className="muted small" style={{ marginTop: 0 }}>
        A workshop-verified suspension crack traced to supplier lot <span className="mono">LOT-SYN-2023-03-A</span>.
        Check the lot card, run the simulated owner symptom check, approve as supervisor, and record workshop
        outcomes — all counts are computed from warehouse rows. Nothing here sends a real message.
      </p>
      <p className="small"><strong>{lot.title}</strong> · status {lot.status}</p>
    </Step>
  );
}

export default function DemoMode({ hashQuery }) {
  const q = hashQuery || {};
  const [seed, setSeed] = useState(readLastSeed());
  const [status, setStatus] = useState(null);
  const [proof, setProof] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const caseId = q.case || (!proof?.recorded_at && proof?.case_id) || seed?.case_id || null;
  const invId = q.inv || seed?.investigation_id || null;

  useEffect(() => { aiStatus().then(setStatus); }, []);

  async function runMetaWorkflow() {
    setBusy(true); setErr("");
    try { setProof(await aiPostJson("/api/ai/demo/meta-workflow", {})); }
    catch (e) { setErr(e.message); } finally { setBusy(false); }
  }

  async function loadRecordedProof() {
    setBusy(true); setErr("");
    try {
      const record = await aiGet("/api/ai/demo/proof");
      const text = record.checks?.find((c) => c.feature === "text");
      if (!record.live_transport || !text?.ok || !text.result) throw new Error("No successful recorded text workflow available");
      setProof({ ...text.result, recorded_at: record.recorded_at, api_host: record.api_host });
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  }

  function downloadProof() {
    const blob = new Blob([JSON.stringify(proof, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url; link.download = "tracex-meta-proof.json"; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  async function runSeed() {
    setBusy(true); setErr("");
    try {
      const out = await aiPostJson("/api/ai/demo/seed", {});
      setSeed(out);
      try { window.localStorage.setItem(LAST_SEED_KEY, JSON.stringify(out)); } catch { /* ignore */ }
    } catch (e) {
      setErr(e.message === "403" ? "Demo seeding is off on this server. Run `python -m scripts.ai_demo_seed` or start with AI_DEMO_ENABLED=1." : `Seed failed (${e.message})`);
    } finally { setBusy(false); }
  }

  return (
    <div className="demo-mode" style={{ maxWidth: 1100 }}>
      <header style={{ marginBottom: 14 }}>
        <h1 style={{ marginBottom: 4 }}>Catch vehicle faults before they cause crashes</h1>
        <p className="muted" style={{ marginTop: 0 }}>
          TraceX is designed to record customer complaints (voice, Hindi or English, with photos), link them to
          NHTSA-shaped warehouse data, and flag safety defects early. This demo seed is synthetic; the transcript and
          generated photo are labelled SYNTHETIC. The status distinguishes configured models from verified live features.
        </p>
        <div className="row" style={{ gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          {status && <MetaTag mode={status.mode} models={status.mode === "enhanced" ? [status.models?.text, status.models?.segmentation].filter(Boolean) : []} />}
          {status && status.mode !== "enhanced" && <span className="muted small">No Meta key: deterministic rules run every step; photo upload still works.</span>}
          <button className="primary" onClick={runSeed} disabled={busy} data-testid="demo-seed">{busy ? "Running scenario…" : "Run seeded India scenario"}</button>
          {seed && <span className="muted small">Last seed: <span className="mono">{seed.interaction_id}</span> · {seed.label}</span>}
        </div>
        {err && <div className="banner banner-warn small" style={{ marginTop: 8 }}>{err}</div>}
      </header>

      <section className="card" style={{ padding: 14, marginBottom: 14 }}>
        <h2>Meta complaint intake</h2>
        <p className="muted small">A synthetic Hindi complaint through the real intake and audit ledger. Inspect the original text, accepted translation, and fallback status.</p>
        <button type="button" className="primary" disabled={busy || status?.mode !== "enhanced"}
          onClick={runMetaWorkflow}>Run Meta complaint</button>
        <button type="button" className="ghost" disabled={busy} onClick={loadRecordedProof}>View recorded live proof</button>
        {status && <p className="small">Recorded live features: {Object.entries(status.verified_features || {}).filter(([, ok]) => ok).map(([name]) => name).join(", ") || "none"}</p>}
        {proof && <div data-testid="meta-workflow-result">
          {proof.recorded_at && <p className="small muted">Recorded synthetic run · {proof.recorded_at} · {proof.api_host}</p>}
          <p>{proof.ok ? "Accepted Meta output; ledger verified" : "Workflow incomplete — review the translation and fallback"}</p>
          <p><strong>Original complaint:</strong> {proof.input}</p>
          <p><strong>Local normalization:</strong> {proof.deterministic?.language?.normalized_en || "—"}</p>
          <p><strong>Accepted English:</strong> {proof.accepted?.language?.normalized_en || "No translation accepted"}</p>
          <p className="small">Model: {proof.model_id} · Result: {proof.fallback_reason || proof.reason || "—"}</p>
          {proof.case_id && <p className="small">{proof.recorded_at ? "Recorded case ID" : "Case ready for review"}: <span className="mono">{proof.case_id}</span>{!proof.recorded_at && <> · <a href="#cases">Open case queue →</a></>}</p>}
          <p className="small">Audit event: <span className="mono">{proof.event_id || "—"}</span> · {proof.ledger?.ok ? `${proof.ledger.checked} ledger actions verified` : "Ledger verification unavailable"}</p>
          <details><summary className="small">View proposed and accepted facts</summary>
            <p className="small">Proposed English: {proof.proposal?.normalized_en || "No translation proposed"}</p>
            <ul className="small">
              {Object.entries(proof.accepted?.filled || {}).map(([slot, fact]) => <li key={slot}>{slot}: {fact.value} · accepted from {fact.source}</li>)}
              {Object.entries(proof.accepted?.pending_confirmation || {}).map(([slot, fact]) => <li key={slot}>{slot}: {fact.value} · caller confirmation required</li>)}
              {Object.entries(proof.accepted?.rejected || {}).map(([slot, reason]) => <li key={slot}>{slot}: rejected · {String(reason).replaceAll("_", " ")}</li>)}
            </ul>
            {!Object.keys(proof.accepted?.filled || {}).length && <p className="small muted">Vehicle facts remain those extracted from the original complaint by local rules.</p>}
            <button type="button" className="ghost" onClick={downloadProof}>Download proof and audit details</button>
          </details>
        </div>}
      </section>
      <Step n={1} title="A driver in Pune calls in Hinglish and sends a photo" link="#call" linkLabel="Open voice agent">
        <SpeechLangSelect />
        <NormalizeTry />
        <HeroContrast text={seed?.transcript?.find((t) => t.speaker === "customer")?.text || SAMPLE_HINGLISH} />
        {seed?.transcript && (
          <details style={{ marginTop: 8 }} open>
            <summary className="small">Seeded call transcript (synthetic, ran through the real pipeline)</summary>
            <ul className="small" style={{ paddingLeft: 18 }}>
              {seed.transcript.map((t, i) => (
                <li key={i} className={t.speaker === "agent" ? "muted" : ""}><strong>{t.speaker}:</strong> {t.text}</li>
              ))}
            </ul>
            {(seed.safety_flags || []).length > 0 && (
              <div className="chip sev-critical">Kill-switch fired: {seed.safety_flags.join(", ")} → Critical/P1 safety escalation and "do not drive" script</div>
            )}
          </details>
        )}
      </Step>

      <Step n={2} title="The case, with photo evidence (SAM 3.1 overlay when enabled)" link="#cases" linkLabel="Open case queue">
        <CaseSummary caseId={caseId} />
        {caseId && <EvidencePanel caseId={caseId} />}
      </Step>

      <Step n={3} title="Grounded investigation brief: every claim cites warehouse record IDs" link={invId ? `#issue/${encodeURIComponent(invId)}` : "#warning"} linkLabel="Open issue">
        {invId ? <GroundedBriefPanel investigationId={invId} /> : <div className="muted small">No investigation linked yet: pick one from the board below.</div>}
      </Step>

      <Step n={4} title="Early-warning board, safety-critical first" link="#warning" linkLabel="Open early warning">
        <SafetyRiskBoard />
      </Step>

      <LotGuardStep />
    </div>
  );
}
