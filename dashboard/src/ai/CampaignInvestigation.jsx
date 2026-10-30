import { useEffect, useRef, useState } from "react";
import { apiHeaders } from "../apiAuth.js";

async function request(path, body) {
  const r = await fetch(path, { credentials: "same-origin", headers: apiHeaders(body ? { "Content-Type": "application/json" } : {}),
    ...(body ? { method: "POST", body: JSON.stringify(body) } : {}) });
  const data = await r.json();
  if (!r.ok) throw new Error(typeof data.detail === "string" ? data.detail : `Request failed (${r.status})`);
  return data;
}

function SourceRecord({ source, onOpen }) {
  const provenance = source.provenance || {};
  const retrieval = source.retrieval || {};
  return <article className="sc-source-record">
    <strong>{source.source_id} · {source.kind?.replaceAll("_", " ")}</strong>
    {(source.turns || []).length ? <ol className="sc-source-turns">{source.turns.map(turn => <li key={turn.turn_id}>
      <p>{turn.text}</p><small>{turn.speaker} · {turn.at || turn.timestamp || "Time unavailable"} · {turn.turn_id}</small>
    </li>)}</ol> : <p className="sc-source-text">{source.text}</p>}
    <p className="sc-muted small">{provenance.actor || provenance.author || provenance.by || ""}{provenance.at ? ` · ${provenance.at}` : ""}</p>
    {(retrieval.omitted_older_records > 0 || retrieval.omitted_characters > 0) && <p className="sc-mode-note">This lookup omitted {retrieval.omitted_older_records ? `${retrieval.omitted_older_records} older report(s)` : `${retrieval.omitted_characters} characters`}. Not retrieved does not mean no evidence exists.</p>}
    <details><summary>Source identity and hash</summary><pre>{JSON.stringify(provenance, null, 2)}</pre><code>{source.sha256}</code></details>
    {onOpen && provenance.url && <button type="button" className="ghost" onClick={() => onOpen(provenance.url, source.full_sha256 || source.sha256)}>Open original record</button>}
  </article>;
}

function InterpretationReview({ kind, index, value = {}, disabled, change }) {
  return <div className="sc-claim-review"><label className="sc-field"><span>Review {kind} {index + 1}</span><select aria-label={`Review ${kind} ${index + 1}`} value={value.decision || ""} disabled={disabled} onChange={e => change({ decision: e.target.value })}>
    <option value="">Not yet reviewed</option><option value="accept">Accept as written</option><option value="correct">Correct interpretation</option><option value="reject">Reject unsupported claim</option></select></label>
    {["correct", "reject"].includes(value.decision) && <label className="sc-field"><span>{value.decision === "reject" ? "Rejection reason" : "Correction"} for {kind} {index + 1}</span><textarea rows={2} maxLength={1000} disabled={disabled} value={value.correction || ""} onChange={e => change({ ...value, correction: e.target.value })} /></label>}
  </div>;
}

export default function CampaignInvestigation({ campaign, initialVehicleId = "", interactionId = "", replyId = "", initialAssistanceMode = "full_investigation", onOpenStep }) {
  const [vehicleId, setVehicleId] = useState(initialVehicleId || (interactionId ? "" : campaign.vehicles.find(v => v.replies.length && !v.resolution)?.vehicle_id || campaign.vehicles[0]?.vehicle_id || ""));
  const [text, setText] = useState("");
  const [sourcePreview, setSourcePreview] = useState(null);
  const [sourceBusy, setSourceBusy] = useState(false);
  const [sourceReviewed, setSourceReviewed] = useState(false);
  const [vehicleConfirmed, setVehicleConfirmed] = useState(false);
  const [originalRecord, setOriginalRecord] = useState(null);
  const [sourceChanged, setSourceChanged] = useState(false);
  const [corrections, setCorrections] = useState({});
  const [observationCorrections, setObservationCorrections] = useState({});
  const [assistanceMode, setAssistanceMode] = useState(initialAssistanceMode);
  const [recordPage, setRecordPage] = useState(null);
  const sourceGeneration = useRef(0), followupRef = useRef(null), snapshotRef = useRef(null);
  const [runs, setRuns] = useState([]);
  const [selected, setSelected] = useState(null);
  const [followup, setFollowup] = useState("");
  const [busy, setBusy] = useState(false);
  const [activeRequestId, setActiveRequestId] = useState(null);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [decision, setDecision] = useState("needs_correction");
  const [attest, setAttest] = useState(false);
  const lock = useRef(false), pending = useRef(null), alive = useRef(true);
  const base = `/api/safety-campaigns/${campaign.campaign_id}/investigations`;
  const vehicle = campaign.vehicles.find(v => v.vehicle_id === vehicleId);
  useEffect(() => { alive.current = true; request(base).then(d => { if (alive.current) setRuns(d.runs); }).catch(e => { if (alive.current) setError(e.message); });
    return () => { alive.current = false; }; }, [base]);
  useEffect(() => {
    if (interactionId) loadSource(`/api/safety-campaigns/report-sources/interactions/${encodeURIComponent(interactionId)}`);
    else if (replyId && initialVehicleId) loadSource(`/api/safety-campaigns/${encodeURIComponent(campaign.campaign_id)}/report-sources/replies/${encodeURIComponent(initialVehicleId)}/${encodeURIComponent(replyId)}`);
    else { sourceGeneration.current++; setSourcePreview(null); setSourceBusy(false); }
    return () => { sourceGeneration.current++; };
  }, [interactionId, replyId, initialVehicleId, campaign.campaign_id]);
  useEffect(() => {
    if (initialVehicleId && campaign.vehicles.some(v => v.vehicle_id === initialVehicleId)) changeVehicle(initialVehicleId);
  }, [initialVehicleId]);
  useEffect(() => { setAssistanceMode(initialAssistanceMode); }, [initialAssistanceMode]);
  async function loadSource(url) {
    const generation = ++sourceGeneration.current;
    setSourceBusy(true); setError(""); setSourcePreview(null); setSourceReviewed(false); setVehicleConfirmed(false); setText("");
    try {
      const result = await request(url);
      if (alive.current && generation === sourceGeneration.current) setSourcePreview(result);
    } catch (e) { if (alive.current && generation === sourceGeneration.current) setError(e.message); }
    finally { if (alive.current && generation === sourceGeneration.current) setSourceBusy(false); }
  }
  function changeVehicle(id) {
    setVehicleId(id); setSelected(null); setVehicleConfirmed(false); setRecordPage(null);
    if (sourcePreview?.source_ref.kind === "campaign_reply") { sourceGeneration.current++; setSourcePreview(null); setSourceReviewed(false); setText(""); }
  }
  function useManual(value = "") {
    sourceGeneration.current++; setSourceBusy(false); setSourcePreview(null); setSourceReviewed(false); setVehicleConfirmed(false); setText(value);
  }
  async function openOriginal(url, expectedHash) {
    if (typeof url !== "string" || !url.startsWith("/api/safety-campaigns/")) return;
    setError("");
    try { const result = await request(url); if (alive.current) { const original = result.source || result; setOriginalRecord(original); if (expectedHash && original.sha256 !== expectedHash) setSourceChanged(true); } }
    catch (e) { if (alive.current) setError(e.message); }
  }
  function citation(ev) {
    const source = (selected?.sources || selected?.report_sources || []).find(s => s.source_id === ev.source_id);
    const provenance = ev.provenance || source?.provenance;
    const turn = ev.source_turn || ev;
    return <details key={ev.sentence_id}><summary>Source {ev.sentence_id}</summary><blockquote>{ev.quote}</blockquote>
      {turn.turn_id && <p className="sc-muted small">Stored turn {turn.turn_id} · {turn.speaker} · {turn.at}</p>}
      {provenance?.url && <button type="button" className="ghost" onClick={() => openOriginal(provenance.url, source?.full_sha256 || source?.sha256)}>Open original record</button>}
    </details>;
  }
  async function browseRecords(kind, offset = 0) {
    setError("");
    try { const result = await request(`/api/safety-campaigns/${encodeURIComponent(campaign.campaign_id)}/vehicles/${encodeURIComponent(vehicleId)}/records/${kind}?offset=${offset}&limit=5`); if (alive.current) setRecordPage(result); }
    catch (e) { if (alive.current) setError(e.message); }
  }
  async function refreshRuns() {
    try { const result = await request(base); if (alive.current) { setRuns(result.runs); if (selected) setSelected(result.runs.find(r => r.run_id === selected.run_id) || selected); } }
    catch (e) { if (alive.current) setError(e.message); }
  }
  useEffect(() => {
    if (!activeRequestId) return;
    let stopped = false, timer;
    async function poll() {
      try {
        const result = await request(base);
        if (stopped || !alive.current) return;
        setRuns(result.runs);
        const active = result.runs.find(item => item.request_id === activeRequestId);
        if (active) setSelected(active);
      } catch { /* The POST or manual refresh reports connection errors. */ }
      if (!stopped) timer = window.setTimeout(poll, 1200);
    }
    timer = window.setTimeout(poll, 800);
    return () => { stopped = true; window.clearTimeout(timer); };
  }, [base, activeRequestId]);
  const stale = selected && selected.snapshot_revision !== campaign.revision;
  function choose(run) { setSelected(run); setVehicleId(run.vehicle_id); setVehicleConfirmed(false); setNote(""); setAttest(false); setFollowup(""); setCorrections({}); setObservationCorrections({}); setOriginalRecord(null); setSourceChanged(false); setDecision("needs_correction"); }
  async function run(parent = null) {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError("");
    const body = { vehicle_id: parent ? parent.vehicle_id : vehicleId, revision: campaign.revision,
      assistance_mode: parent?.assistance_mode || assistanceMode,
      parent_run_id: parent?.run_id || null,
      ...(parent ? (followup.trim() ? { text: followup } : {}) : sourcePreview ? {
        source_ref: sourcePreview.source_ref, source_reviewed: sourceReviewed, vehicle_association_confirmed: vehicleConfirmed,
      } : { text }) };
    if (!parent && sourcePreview && (!sourceReviewed || !vehicleConfirmed)) { lock.current = false; setBusy(false); return; }
    const signature = JSON.stringify(body);
    if (pending.current?.signature !== signature) pending.current = { signature, id: crypto.randomUUID() };
    setActiveRequestId(pending.current.id);
    try {
      const result = await request(base, { ...body, request_id: pending.current.id });
      if (!alive.current) return;
      setRuns(items => [...items.filter(r => r.run_id !== result.run_id), result]); choose(result); pending.current = null;
    } catch (e) { if (alive.current) setError(e.message); }
    finally { lock.current = false; if (alive.current) { setBusy(false); setActiveRequestId(null); } }
  }
  async function review(e) {
    e.preventDefault(); if (lock.current) return;
    lock.current = true; setBusy(true); setError("");
    try {
      const result = await request(`${base}/${selected.run_id}/review`, { note, decision, attestation: attest,
        corrections: Object.entries(corrections).filter(([, value]) => value.decision).map(([index, value]) => ({ claim_index: Number(index), ...value })),
        observation_corrections: Object.entries(observationCorrections).filter(([, value]) => value.decision).map(([index, value]) => ({ observation_index: Number(index), ...value })) });
      if (alive.current) { setSelected(result); setRuns(items => items.map(r => r.run_id === result.run_id ? result : r)); }
    } catch (e) { if (alive.current) setError(e.message); }
    finally { lock.current = false; if (alive.current) setBusy(false); }
  }
  async function openReview(id) {
    const tab = window.open("", "_blank");
    try {
      const response = await fetch(`/api/safety-campaigns/review-kit/${id}`, { credentials: "same-origin", headers: apiHeaders() });
      if (!response.ok) throw new Error(`Review document unavailable (${response.status})`);
      const html = (await response.text()).replaceAll('src="/ui/review-scripts/', `src="${window.location.origin}/ui/review-scripts/`);
      const url = URL.createObjectURL(new Blob([html], { type: "text/html" }));
      if (tab) { tab.opener = null; tab.location.href = url; } else window.open(url, "_blank", "noopener");
      window.setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (e) { tab?.close(); setError(e.message); }
  }
  function advance() {
    const step = selected?.brief?.next_step;
    if (step === "ask_followup" && followupRef.current) { followupRef.current.focus(); followupRef.current.scrollIntoView({ block: "center" }); }
    else if (step === "review_trace") onOpenStep(selected.vehicle_id, "trace");
    else if (["review_inspection", "review_repair"].includes(step)) onOpenStep(selected.vehicle_id, "workshop", step === "review_repair" ? "verify_repair" : "inspection");
    else if (snapshotRef.current) { snapshotRef.current.open = true; snapshotRef.current.querySelector("summary")?.focus(); snapshotRef.current.scrollIntoView({ block: "center" }); }
  }
  const canRun = !!vehicleId && !busy && !sourceBusy && (sourcePreview ? sourceReviewed && vehicleConfirmed : !!text.trim());
  async function prepareNewRequest() {
    const prior = selected;
    const source = prior?.report_sources?.[0];
    pending.current = null; setSelected(null);
    if (source?.provenance?.url) await loadSource(source.provenance.url);
    else useManual(source?.text || "");
    if (prior?.vehicle_id) setVehicleId(prior.vehicle_id);
  }
  const hasCorrections = !!selected?.review?.corrections?.length || !!selected?.review?.observation_corrections?.length || selected?.review?.decision === "needs_correction";
  const stageLabels = { reading_report: "Reading report", checking_records: "Checking records", drafting: "Drafting", ready_for_review: "Ready for review", failed: "Failed", interrupted: "Interrupted" };
  const choices = [...Object.values(corrections), ...Object.values(observationCorrections)];
  const hasClaimChanges = choices.some(value => ["correct", "reject"].includes(value.decision));
  const invalidCorrection = choices.some(value => ["correct", "reject"].includes(value.decision) && !value.correction?.trim());
  const allInterpretationsReviewed = (selected?.brief?.claims || []).every((_, i) => corrections[i]?.decision === "accept") && (selected?.extraction?.observations || []).every((_, i) => observationCorrections[i]?.decision === "accept");
  function changeInterpretation(kind, index, value) { (kind === "claim" ? setCorrections : setObservationCorrections)(items => ({ ...items, [index]: value })); if (["correct", "reject"].includes(value.decision)) setDecision("needs_correction"); }
  return <section className="sc-panel sc-full" data-testid="campaign-investigation">
    <div className="sc-section-head"><div><h2>Investigate with Meta</h2><p className="sc-muted">Turn an owner report into cited observations, read-only evidence lookups and a reviewed next step.</p></div><span className="sc-tag">Engineer review required</span></div>
    {error && <p role="alert" className="banner banner-error">{error}</p>}
    <div className="sc-fields">
      <label className="sc-field"><span>Investigation vehicle</span><select aria-label="Investigation vehicle" value={vehicleId} disabled={busy || sourceBusy} onChange={e => changeVehicle(e.target.value)}>
        <option value="">Select the vehicle for this report…</option>
        {campaign.vehicles.map(v => <option key={v.vehicle_id} value={v.vehicle_id}>{v.vehicle_id} · {v.model} · {v.match}</option>)}</select></label>
    </div>
    {interactionId && <p className="sc-mode-note">Report handoff · stored interaction {interactionId}. Confirm the source and its vehicle below. Opening this page makes no model call.</p>}
    {sourceBusy && <p role="status">Loading the original report…</p>}
    {interactionId && !sourceBusy && !sourcePreview && <button type="button" disabled={busy} onClick={() => loadSource(`/api/safety-campaigns/report-sources/interactions/${encodeURIComponent(interactionId)}`)}>Retry loading original report</button>}
    {sourcePreview ? <div className="sc-inset" data-testid="report-source-preview"><h3>Review the stored report</h3>
      <SourceRecord source={sourcePreview.source} />
      <p className="sc-muted small">The original record stays unchanged. Personal details may be redacted. Record corrections separately in the linked investigation.</p>
      <label className="sc-check"><input type="checkbox" checked={sourceReviewed} disabled={busy} onChange={e => setSourceReviewed(e.target.checked)} />I reviewed these stored report turns.</label>
      <label className="sc-check"><input type="checkbox" checked={vehicleConfirmed} disabled={busy || !vehicleId} onChange={e => setVehicleConfirmed(e.target.checked)} />I confirm this report concerns the selected vehicle{vehicleId ? ` (${vehicleId})` : ""}.</label>
      <button type="button" className="ghost" disabled={busy} onClick={() => useManual()}>Enter a separate manual report</button>
    </div> : !sourceBusy && <label className="sc-field sc-field-wide"><span>Owner report to investigate · manual operator transcription</span><textarea aria-label="Owner report to investigate" rows={3} maxLength={4000} value={text} disabled={busy} onChange={e => setText(e.target.value)} />
      <small>Manual text has no original interaction or reply link. Use a stored report to preserve its source identity.</small></label>}
    <div className="sc-inline sc-investigation-actions"><button disabled={busy || sourceBusy || !vehicle?.replies.length} onClick={() => loadSource(`/api/safety-campaigns/${encodeURIComponent(campaign.campaign_id)}/report-sources/replies/${encodeURIComponent(vehicleId)}/${encodeURIComponent(vehicle.replies.at(-1).reply_id)}`)}>Use latest recorded report</button>
      {campaign.synthetic_demo && <button disabled={busy || sourceBusy} onClick={() => useManual("Meri gaadi speed breaker par khat-khat karti hai aur kabhi steering left khinchti hai. Mujhe part ka naam nahi pata.")}>Fill synthetic Hinglish report</button>}
      <button className="primary" disabled={!canRun} onClick={() => run()}>{busy ? "Investigation request in progress…" : "Run sourced investigation"}</button>
      <button className="ghost" onClick={refreshRuns}>Refresh investigation history</button></div>
    {busy && <p role="status">Waiting for the server to finish the current request. A saved draft or a reported failure will appear here.</p>}
    <p className="sc-muted small">Uses at most two model calls and two read-only lookups per turn, up to three turns. A draft does not record an owner reply, approve outreach or clear a vehicle. Save consequential updates through the existing reviewed controls.</p>
    <details><summary>Comparison mode and older records</summary><label className="sc-field"><span>Assistance mode</span><select aria-label="Assistance mode" disabled={busy} value={assistanceMode} onChange={e => setAssistanceMode(e.target.value)}><option value="full_investigation">Full sourced investigation</option><option value="extraction_only">Extraction only · comparison condition</option></select></label>
      <p className="sc-muted small">The deterministic comparison uses the existing report, traceability and workshop controls without requesting AI. Extraction-only makes one logical call and no model-selected lookup or brief.</p>
      <div className="sc-inline"><button disabled={!vehicleId || busy} onClick={() => browseRecords("owner_history")}>Browse owner report history</button><button disabled={!vehicleId || busy} onClick={() => browseRecords("workshop_history")}>Browse workshop history</button></div>
      {recordPage && <section><p>{recordPage.total} stored record(s) · page beginning at {recordPage.offset + 1}. This read-only view makes no model call.</p>{(recordPage.sources || [recordPage.source]).filter(Boolean).map(source => <SourceRecord key={source.source_id} source={source} onOpen={openOriginal} />)}
        <button disabled={!recordPage.offset} onClick={() => browseRecords(recordPage.kind, Math.max(0, recordPage.offset-5))}>Newer records</button><button disabled={recordPage.next_offset == null} onClick={() => browseRecords(recordPage.kind, recordPage.next_offset)}>Older records</button></section>}
    </details>
    <details><summary>Independent review and measurement</summary><p>These workflows require actual reviewers. Opening a page or viewing model output does not complete human validation.</p><div className="sc-inline">
      {[["original-300", "Original 300-example review"], ["development", "Development label review"], ["fuel-complaints", "Fuel / propulsion review"], ["recalls", "Recall description review"], ["study", "Timed reviewer study"]].map(([id, title]) => <button key={id} className="ghost" onClick={() => openReview(id)}>{title} ↗</button>)}
    </div><p className="sc-muted small">Export completed reviews for validated import. Human accuracy and time savings remain unavailable until real reviews are submitted.</p></details>
    {runs.length > 0 && <label className="sc-field"><span>Recorded investigations</span><select aria-label="Recorded investigations" value={selected?.run_id || ""} disabled={busy} onChange={e => { const r = runs.find(x => x.run_id === e.target.value); if (r) choose(r); }}>
      <option value="">Select a saved run…</option>{[...runs].reverse().map(r => <option key={r.run_id} value={r.run_id}>{r.vehicle_id} · {new Date(r.started_at).toLocaleString()} · {r.status}</option>)}</select></label>}
    {selected && <div data-testid="investigation-result">
      {selected.replay && <p className="sc-mode-note">Recorded live Meta output on synthetic data · {selected.started_at}. Replayed from a saved source artifact; viewing this result makes no new model call.</p>}
      <div className="sc-inset"><strong>{selected.replay ? "Replayed Meta extraction" : selected.status === "running" ? "Investigation in progress" : selected.extraction?.mode?.startsWith("meta") ? "Saved Meta extraction" : "Manual review / fallback"}</strong>
        <p>Recorded at {selected.started_at}. {selected.extraction?.model_id || "No model output"} · {selected.elapsed_ms == null ? selected.status : `${(selected.elapsed_ms/1000).toFixed(1)} seconds`} · {selected.inference_outcome_uncertain || selected.model_calls == null ? "Model call count uncertain after interruption; prior spend retained" : `${selected.model_calls} logical model calls`}</p>
        {selected.stage && <p role="status">{stageLabels[selected.stage] || selected.stage}</p>}
        {selected.status === "erased" && <p role="status">The source was erased. This draft is unavailable and cannot be reviewed or used for an action.</p>}
        {["interrupted", "failed", "expired"].includes(selected.status) && <div><p>The saved request cannot complete. A new request can make new model calls; any prior spend remains recorded.</p>
          <button type="button" disabled={busy} onClick={prepareNewRequest}>Prepare a new investigation request</button></div>}
        {selected.extraction?.fallback_reason && <p>{selected.extraction.fallback_reason}</p>}
        {selected.error && <p role="alert">{selected.error}</p>}
        {stale && <p role="alert">Campaign evidence changed since this draft. Run an updated investigation before review.</p>}
      </div>
      <details><summary>Operation provenance and measured usage</summary><p>{selected.assistance_mode || "Legacy condition not recorded"}. Cost reservations and token-rate estimates are not provider invoices. No measured billed cost is available here.</p>
        {(selected.operations || []).map(op => <article className="sc-inset" key={op.attempt_id}><strong>{op.stage} · {selected.replay ? "Recorded replay" : op.live_transport ? "Live provider request" : "Synthetic test transport"}</strong><p>{op.model} · {op.started_at} · {op.status} · {op.elapsed_ms ?? "unknown"} ms</p><p>Input tokens: {op.prompt_tokens ?? "unknown"}; output tokens: {op.completion_tokens ?? "unknown"}; reserved: {op.reserved_upper_bound_usd}; token-rate cost estimate: {op.observed_token_cost_estimate_usd ?? "unknown"}</p><pre>{JSON.stringify({ prompt_sha256: op.prompt_sha256, schema_sha256: op.logical_schema_sha256 || op.schema_sha256, validation: op.validation, validation_reason: op.validation_reason }, null, 2)}</pre></article>)}
        {!selected.operations?.length && <p>{selected.model_calls === 0 ? "No model request was made by this run." : "Per-attempt telemetry was not recorded for this legacy or interrupted result."}</p>}<pre>{JSON.stringify({ versions: selected.versions, summary: selected.operational_summary }, null, 2)}</pre></details>
      <h3>Sourced observations</h3>
      <div className="sc-investigation-cards">{selected.extraction?.observations.map((o, i) => <article className="sc-inset" key={i}><strong>{o.field.replaceAll("_", " ")} · {o.polarity}</strong><p>{o.value}</p><blockquote>{o.evidence.quote}</blockquote>{citation(o.evidence)}{!selected.review && <InterpretationReview kind="observation" index={i} value={observationCorrections[i]} disabled={busy || stale} change={value => changeInterpretation("observation", i, value)} />}</article>)}</div>
      {!!(selected.extraction?.withheld_observations?.length || selected.brief?.withheld_claims?.length) && <details><summary>Withheld interpretations · source-support problems</summary><p>These outputs were withheld by narrow number, identifier or contradiction checks. Passing these checks does not establish semantic accuracy.</p>{[...(selected.extraction?.withheld_observations || []), ...(selected.brief?.withheld_claims || [])].map((item, index) => <pre key={index}>{JSON.stringify(item, null, 2)}</pre>)}</details>}
      {!selected.extraction?.observations.length && <p className="sc-muted">No accepted model observations. Read the source reports below.</p>}
      <p className="sc-muted">Unknown fields: {selected.extraction?.unknown_fields.join(", ") || "None reported by model; review independently"}.</p>
      <h3>Evidence lookups</h3><ol>{(selected.tool_trace || []).map((t, i) => <li key={i}>{t.tool.replaceAll("_", " ")} · {t.vehicle_id} · read only · campaign revision {t.snapshot_revision}</li>)}</ol>
      {!selected.tool_trace?.length && <p className="sc-muted">No model-selected lookups completed.</p>}
      {(selected.sources || []).filter(source => source.retrieval?.omitted_older_records > 0 || source.retrieval?.omitted_characters > 0).map(source => <p key={source.source_id} className="sc-mode-note">{source.source_id}: {source.retrieval.omitted_older_records ? `${source.retrieval.omitted_older_records} older report(s)` : `${source.retrieval.omitted_characters} characters`} were not retrieved. Review the full record before concluding that evidence is absent.</p>)}
      <h3>Investigation brief</h3>
      {selected.brief?.claims.map((claim, i) => <article className="sc-inset" key={i}><strong>{claim.relationship} · draft interpretation</strong><p>{claim.interpretation}</p>
        {claim.evidence.map(citation)}
        {!selected.review && <InterpretationReview kind="claim" index={i} value={corrections[i]} disabled={busy || stale} change={value => changeInterpretation("claim", i, value)} />}
      </article>)}
      {selected.brief?.fallback_reason && <p role="status">Brief unavailable: {selected.brief.fallback_reason}. Review the retrieved sources.</p>}
      <p><strong>Suggested next step:</strong> {selected.brief?.next_step_label || "Review source evidence"}</p>
      <details ref={snapshotRef}><summary>Complete source snapshot</summary>{(selected.sources || selected.report_sources || []).map(s => <SourceRecord key={s.source_id} source={s} onOpen={openOriginal} />)}</details>
      {sourceChanged && <p role="alert" className="banner banner-error">The original record differs from this draft's source snapshot. Create an updated investigation before reviewing it.</p>}
      {originalRecord && <section className="sc-inset" data-testid="original-source-record"><div className="sc-section-head"><h3>Original stored record</h3><button type="button" onClick={() => setOriginalRecord(null)}>Close original record</button></div><SourceRecord source={originalRecord} /></section>}
      {selected.parent_run_id && <p className="sc-mode-note">Linked revision of {selected.parent_run_id}. Earlier claims and reviews remain in investigation history.</p>}
      {selected.correction_context && <details><summary>Corrections carried into this revision</summary><pre>{JSON.stringify(selected.correction_context, null, 2)}</pre></details>}
      {selected.status === "complete" && selected.turn < 3 && <div className="sc-inset"><h3>Resolve missing information</h3><p>{selected.brief?.followup_question || "Add new source evidence if the reviewed record is incomplete."}</p>
        <label className="sc-field"><span>Follow-up evidence supplied by the operator</span><textarea ref={followupRef} aria-label="Follow-up evidence" rows={3} maxLength={4000} value={followup} disabled={busy} onChange={e => setFollowup(e.target.value)} /></label>
        {hasCorrections && <p className="sc-muted small">The recorded review will accompany this linked revision. Add any new evidence above, or revise using the saved review.</p>}
        <button disabled={busy || (!followup.trim() && !hasCorrections)} onClick={() => run(selected)}>{hasCorrections ? "Create revised investigation" : "Update investigation with follow-up"}</button></div>}
      {selected.review ? <p className="sc-inset">{selected.review.synthetic_demo ? "Demo review" : "Review"}: {selected.review.decision.replaceAll("_", " ")} · {selected.review.actor}<br />{selected.review.note}
        {selected.review.corrections?.length > 0 && <span className="sc-review-corrections">{selected.review.corrections.map(item => <span key={item.claim_index}>Claim {item.claim_index + 1}: {item.decision}{item.correction ? ` · ${item.correction}` : ""}</span>)}</span>}
        {selected.review.observation_corrections?.length > 0 && <span className="sc-review-corrections">{selected.review.observation_corrections.map(item => <span key={item.observation_index}>Observation {item.observation_index + 1}: {item.decision}{item.correction ? ` · ${item.correction}` : ""}</span>)}</span>}
      </p> : selected.status === "complete" && <form className="sc-form" onSubmit={review}>
        <h3>{campaign.synthetic_demo ? "Record a demo review" : "Engineer review"}</h3><label className="sc-field"><span>Draft decision</span><select aria-label="Draft decision" value={decision} onChange={e => setDecision(e.target.value)}><option value="needs_correction">Needs correction</option><option value="accepted_for_investigation" disabled={hasClaimChanges}>Accept as investigation evidence</option></select></label>
        {hasClaimChanges && <p className="sc-muted small">Corrected or rejected claims require a new draft. Save this review as “Needs correction”.</p>}
        <label className="sc-field"><span>Evidence review note</span><textarea required maxLength={2000} rows={2} value={note} onChange={e => setNote(e.target.value)} /></label>
        <label className="sc-check"><input type="checkbox" checked={attest} onChange={e => setAttest(e.target.checked)} />I reviewed the original sources and the draft interpretations.</label>
        {decision === "accepted_for_investigation" && !allInterpretationsReviewed && <p role="status">Review every model observation and claim individually before accepting this draft.</p>}
        <button disabled={busy || stale || sourceChanged || !attest || !note.trim() || invalidCorrection || (decision === "accepted_for_investigation" && !allInterpretationsReviewed)}>Record draft review</button>
      </form>}
      <p className="sc-muted small">Accept this draft review before continuing to the suggested action. Installation, workshop and repair decisions retain their separate evidence and permission checks.</p>
      <button className="ghost" disabled={stale || sourceChanged || selected.review?.decision !== "accepted_for_investigation"} onClick={advance}>{selected.brief?.next_step_label || "Review source evidence"} →</button>
      <p className="sc-muted small">{selected.note}</p>
    </div>}
  </section>;
}
