import { useEffect, useRef, useState } from "react";
import { apiHeaders } from "../src/apiAuth.js";
import CampaignInvestigation from "../src/ai/CampaignInvestigation.jsx";
import "./safety-campaigns.css";

const API = "/api/safety-campaigns";
const campaignTabs = new Set(["overview", "investigate", "trace", "outreach", "workshop", "evidence"]);
function campaignRoute() {
  const params = new URLSearchParams(window.location.hash.split("?")[1] || "");
  return { tab: campaignTabs.has(params.get("tab")) ? params.get("tab") : (params.get("interaction") || params.get("reply")) ? "investigate" : "overview",
    campaign: params.get("campaign") || "", vehicle: params.get("vehicle") || "", interaction: params.get("interaction") || "",
    reply: params.get("reply") || "",
    assistanceMode: params.get("assistance_mode") === "extraction_only" ? "extraction_only" : "full_investigation",
    action: ["inspection", "verify_repair"].includes(params.get("action")) ? params.get("action") : "inspection" };
}
const labels = {
  exact: "Verified lot match", possible: "Possible match", unknown: "Trace unknown", excluded: "Different verified lot",
  investigating: "Investigating", active: "Active", closed: "Closed", crack_found: "Crack found", wear_only: "Wear only",
  no_issue: "No issue found", inconclusive: "Inconclusive", clunk: "Clunk / knocking", uneven_wear: "Uneven tyre wear",
  steering_pull: "Steering pull", crack: "Visible crack", loss_of_control: "Loss of control", fire: "Fire / smoke",
  injury: "Injury", none: "No symptoms reported", other: "Other / uncertain", recovery: "Recovery required",
  inspect: "Workshop inspection", no_symptoms: "No symptoms at follow-up", symptoms_returned: "Symptoms returned",
  unreachable: "Owner unreachable", open: "Open", contained: "Contained", verified: "Verified",
};
const label = (s) => labels[s] || String(s || "Pending").replaceAll("_", " ");
const time = (s) => s ? new Date(s).toLocaleString() : "Pending";
const fields = {
  appointment: [["workshop", "Workshop"], ["due_date", "Due date", "date"], ["reference", "Booking / referral reference"]],
  recovery: [["reference", "Recovery job reference"], ["note", "Recovery record", "textarea"]],
  inspection: [["outcome", "Inspection finding", ["crack_found", "wear_only", "no_issue", "inconclusive"]], ["technician", "Technician"], ["evidence_ref", "Inspection report / evidence reference"], ["note", "Findings and inspection scope", "textarea"]],
  repair: [["replacement_part", "Reviewed replacement part"], ["replacement_lot", "Installed replacement lot / serial"], ["work_order", "Work order"], ["technician", "Technician"]],
  verify_repair: [["technician", "Verifying technician"], ["evidence_ref", "Verification report"], ["note", "Checks completed against the reviewed procedure", "textarea"]],
  followup: [["outcome", "Follow-up result", ["no_symptoms", "symptoms_returned", "unreachable"]], ["note", "Owner follow-up record", "textarea"]],
  resolve: [["evidence_ref", "Release / disposition reference"], ["note", "Reviewer rationale", "textarea"]],
  trace_review: [["supplier", "Verified supplier"], ["part_number", "Installed part number"], ["lot_id", "Installed lot"], ["source_ref", "Build / service installation record"], ["evidence_text", "Installation record contents", "textarea"], ["note", "Review rationale", "textarea"]],
  remedy: [["replacement_part", "Approved replacement part"], ["procedure_ref", "Manufacturer repair procedure"], ["approval_ref", "Engineering approval reference"], ["note", "Applicability and remedy scope", "textarea"]],
  supplier_action: [["owner", "Responsible quality owner"], ["due_date", "Due date", "date"], ["status", "Corrective action status", ["open", "contained", "verified"]], ["evidence_ref", "Supplier / verification report"], ["note", "Containment, root cause and corrective action", "textarea"]],
  close: [["regulatory_ref", "Manufacturer regulatory decision reference"], ["note", "Close-out rationale", "textarea"]],
};
const actionLabels = { appointment: "Plan workshop visit", recovery: "Record recovery", inspection: "Record inspection",
  repair: "Record part replacement", verify_repair: "Verify repair", followup: "Record follow-up", resolve: "Review vehicle resolution",
  trace_review: "Review installed part", remedy: "Review repair specification", supplier_action: "Supplier corrective action", close: "Close campaign" };

function demoValues(kind, initial) {
  const due = new Date(); due.setDate(due.getDate() + 2);
  const values = {
    workshop: "Demo Central Workshop", due_date: due.toISOString().slice(0, 10), reference: "SYN-DEMO-JOB-NEXT",
    technician: "Demo workshop technician", evidence_ref: "SYN-DEMO-REPORT-NEXT", replacement_part: initial.replacement_part || "SYN-CA-2302",
    replacement_lot: "SYN-LOT-C", work_order: "SYN-DEMO-WO-NEXT", supplier: "SYN-AXLEWORKS", part_number: "SYN-CA-2301",
    lot_id: "SYN-LOT-A", source_ref: "SYN-INSTALLATION-REVIEW", procedure_ref: "SYN-MANUAL-02", approval_ref: "SYN-ENG-01",
    evidence_text: `FICTIONAL INSTALLATION RECORD — DEMO ONLY. Vehicle ${initial.vehicle_id || "selected demo vehicle"}: supplier SYN-AXLEWORKS; installed part SYN-CA-2301; installed lot SYN-LOT-A. Reference SYN-INSTALLATION-REVIEW. This example is not evidence for a real vehicle.`,
    owner: "Demo supplier quality lead", status: "contained", regulatory_ref: "SYN-MANUFACTURER-REVIEW",
    outcome: kind === "followup" ? "no_symptoms" : "crack_found",
    note: "DEMO ONLY: fictional supporting record for this walkthrough; review the action and save when ready.",
  };
  return Object.fromEntries(fields[kind].map(([key]) => [key, values[key] || ""]));
}

async function request(path, data) {
  const response = await fetch(path, { credentials: "same-origin", headers: apiHeaders(data ? { "Content-Type": "application/json" } : {}),
    ...(data ? { method: "POST", body: JSON.stringify(data) } : {}) });
  let body;
  try { body = await response.json(); } catch { throw new Error(`Server returned ${response.status}. Please refresh.`); }
  if (!response.ok) {
    if (response.status === 404 && path === API) throw new Error("Safety campaigns are not available on this server yet. Restart the app server to load the update, then retry.");
    throw new Error(typeof body.detail === "string" ? body.detail : `Request failed (${response.status}). Check the required fields.`);
  }
  return body;
}

function download(name, content, type = "application/json") {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = document.createElement("a"); a.href = url; a.download = name; a.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function Field({ spec, value, onChange, prefix }) {
  const [name, title, type] = spec;
  const id = `${prefix}-${name}`;
  const props = { id, name, value: value || "", required: true, onChange: (e) => onChange(name, e.target.value) };
  return <label className={`sc-field ${type === "textarea" ? "sc-field-wide" : ""}`} htmlFor={id}>
    <span>{title}</span>
    {Array.isArray(type) ? <select {...props}><option value="">Select…</option>{type.map((s) => <option key={s} value={s}>{label(s)}</option>)}</select>
      : type === "textarea" ? <textarea {...props} rows={3} maxLength={name === "evidence_text" ? 8000 : 2000} /> : <input {...props} type={type || "text"} maxLength={300} />}
  </label>;
}

function ActionForm({ kind, initial = {}, busy, onSave, demo }) {
  const [values, setValues] = useState(() => Object.fromEntries(fields[kind].map(([key]) => [key, initial[key] || ""])));
  return <form className="sc-form" onSubmit={(e) => { e.preventDefault(); onSave(kind, values); }}>
    {demo && <button type="button" className="ghost" disabled={busy} onClick={() => setValues(demoValues(kind, initial))}>Fill demo example</button>}
    <div className="sc-fields">{fields[kind].map((spec) => <Field key={spec[0]} spec={spec} prefix={kind} value={values[spec[0]]}
      onChange={(key, value) => setValues((v) => ({ ...v, [key]: value }))} />)}</div>
    <button type="submit" className="primary" disabled={busy}>{busy ? "Saving…" : `${demo ? "Save demo: " : ""}${actionLabels[kind].toLowerCase()}`}</button>
  </form>;
}

function CreateForm({ onCreate, busy }) {
  const source = new URLSearchParams(window.location.hash.split("?")[1] || "").get("investigation") || "";
  const [values, setValues] = useState({ requires_recovery: true, investigation_id: source });
  const specs = [["title", "Campaign title"], ["component_name", "Component"], ["supplier", "Supplier"], ["part_number", "Installed part number"],
    ["lot_id", "Suspected supplier lot"], ["seed_evidence", "Initial finding and source reference", "textarea"]];
  return <form className="sc-form" onSubmit={(e) => { e.preventDefault(); onCreate(values); }}>
    <p className="sc-muted">Start from a documented finding. Import vehicle installation records next to establish the affected scope.</p>
    <div className="sc-fields">{specs.map((spec) => <Field key={spec[0]} spec={spec} prefix="create" value={values[spec[0]]}
      onChange={(key, value) => setValues((v) => ({ ...v, [key]: value }))} />)}</div>
    <label className="sc-check"><input type="checkbox" checked={values.requires_recovery} onChange={(e) => setValues({ ...values, requires_recovery: e.target.checked })} />Critical finding: keep affected vehicles parked and arrange recovery</label>
    {source && <p className="sc-muted">Linked investigation: <span className="mono">{source}</span></p>}
    <button className="primary" disabled={busy}>Create campaign</button>
  </form>;
}

function ReplyForm({ vehicle, campaign, busy, save }) {
  const [text, setText] = useState("");
  const [symptoms, setSymptoms] = useState([]);
  const [analysis, setAnalysis] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState("");
  const generation = useRef(0);
  async function analyze() {
    setAnalyzing(true); setError("");
    const g = ++generation.current;
    try { const result = await request(`${API}/analyze-reply`, { text }); if (g === generation.current) setAnalysis(result); }
    catch (e) { if (g === generation.current) setError(e.message); }
    finally { setAnalyzing(false); }
  }
  function toggle(s) { setSymptoms((prev) => s === "none" ? ["none"] : prev.includes(s) ? prev.filter((v) => v !== s) : [...prev.filter((v) => v !== "none"), s]); }
  return <div>
    <div className="sc-transcript">{vehicle.replies.length ? vehicle.replies.map((r) => <blockquote key={r.reply_id}>
      <p>{r.text}</p><footer>{time(r.at)} · {r.symptoms.map(label).join(", ")}{r.urgent_review && " · urgent review"}</footer>
    </blockquote>) : <p className="sc-muted">No owner report recorded. Silence does not rule out a defect.</p>}</div>
    <form className="sc-form" onSubmit={async (e) => { e.preventDefault(); const ok = await save("reply", { vehicle_id: vehicle.vehicle_id, text, symptoms }); if (ok) { setText(""); setSymptoms([]); setAnalysis(null); } }}>
      {campaign.synthetic_demo && <button type="button" className="ghost" disabled={busy || analyzing} onClick={() => {
        generation.current++; setAnalysis(null); setText("Meri gaadi se phir khat-khat awaaz aa rahi hai aur steering left ki taraf khinchti hai."); setSymptoms(["clunk", "steering_pull"]);
      }}>Fill example owner update</button>}
      <label className="sc-field"><span>{campaign.synthetic_demo ? "Simulated owner reply" : "Owner report · entered by operator"}</span>
        <textarea required rows={3} maxLength={4000} value={text} onChange={(e) => { setText(e.target.value); setAnalysis(null); generation.current++; }} placeholder="Record the owner's words in English, Hindi or Hinglish…" /></label>
      <div className="sc-inline"><button type="button" disabled={!text.trim() || analyzing || busy} onClick={analyze}>{analyzing ? "Analysing…" : "Suggest symptoms with Meta"}</button><span className="sc-muted small">Optional AI draft · human review required</span></div>
      {error && <p role="alert" className="sc-danger">{error}</p>}
      {analysis && <div className="sc-inset" role="status"><strong>{analysis.mode === "meta" ? `Draft · ${analysis.model_id}` : "Manual review"}</strong>
        <p>{analysis.fallback_reason || analysis.note}</p>
        {analysis.suggestions.length > 0 && <><p>Suggested: {analysis.suggestions.map((s) => label(s.symptom)).join(", ")}</p>
          <button type="button" onClick={() => setSymptoms([...new Set(analysis.suggestions.map((s) => s.symptom))])}>Use suggestions after review</button></>}
      </div>}
      <fieldset className="sc-symptoms"><legend>Reviewed symptoms</legend>{["clunk", "uneven_wear", "steering_pull", "crack", "loss_of_control", "fire", "injury", "other", "none"].map((s) =>
        <label key={s} className="sc-check"><input type="checkbox" checked={symptoms.includes(s)} onChange={() => toggle(s)} />{label(s)}</label>)}</fieldset>
      <button className="primary" disabled={busy || !symptoms.length || analyzing}>{busy ? "Saving…" : "Record owner update"}</button>
    </form>
  </div>;
}

function VehicleDetail({ vehicle: v, c, busy, save, tab, initialAction = "inspection" }) {
  const [kind, setKind] = useState(initialAction);
  if (!v) return <p className="sc-muted">Select a vehicle to review its evidence and next action.</p>;
  const stages = [["Owner reply", v.replies.at(-1)?.at], ["Workshop booking", v.appointment?.at], ["Recovery", v.recovery?.at],
    ["Inspection", v.inspection?.at], ["Part replacement", v.repair?.at], ["Repair verification", v.repair_verification?.at],
    ["Follow-up", v.followup?.at], ["Reviewer disposition", v.resolution?.at]];
  return <aside className="sc-panel sc-detail">
    <div className="sc-section-head"><div><h3>{v.vehicle_id}</h3><p className="sc-muted">{v.owner_ref} · {v.model}</p></div><span className={`sc-tag ${v.safety_hold ? "sc-tag-danger" : ""}`}>{v.safety_hold ? "Keep parked · recovery" : v.resolution ? "Reviewed resolution" : "Review pending"}</span></div>
    {tab === "outreach" ? <ReplyForm key={v.vehicle_id} vehicle={v} campaign={c} busy={busy} save={save} /> : <>
      <dl className="sc-facts"><div><dt>Installed part</dt><dd>{v.part_number || "Unknown"}</dd></div><div><dt>Lot</dt><dd>{v.lot_id || "Unknown"}</dd></div>
        <div><dt>Trace evidence</dt><dd>{v.source_ref} · {label(v.match)}</dd></div><div><dt>Latest finding</dt><dd>{label(v.inspection?.outcome)}</dd></div></dl>
      <details><summary>Vehicle history</summary><ol className="sc-timeline">{stages.map(([name, at]) => <li key={name}><span>{name}</span><time>{time(at)}</time></li>)}</ol></details>
      {tab === "trace" ? <>
        <div className="sc-inset"><h4>Installation evidence</h4>
          {v.installation_evidence ? <><p className="sc-source-text">{v.installation_evidence.text}</p><p className="sc-muted small">Reference: {v.installation_evidence.source_ref || v.source_ref}</p>
            <p className="sc-muted small">Reviewed by {v.trace_review?.by || v.installation_evidence.by || "Unknown"} ({v.trace_review?.role || "role unavailable"}) · {time(v.trace_review?.at || v.installation_evidence.at)}</p>
            <details><summary>Recorded installation hash</summary><code>{v.installation_evidence.sha256}</code></details></> : <p>No installation document has been attached for review.</p>}
          {v.source_asserted_trace_status && <p className="sc-muted small">Imported source assertion: {v.source_asserted_trace_status}. This assertion alone is not a reviewer-confirmed lot match.</p>}
          {v.import_provenance && <details><summary>Import provenance</summary><pre>{JSON.stringify(v.import_provenance, null, 2)}</pre></details>}
        </div>
        <h4>Verify or correct installed-part evidence</h4><p className="sc-muted small">Use a build or service installation record. A VIN or model match alone does not establish the supplier lot.</p>
        <ActionForm key={`${v.vehicle_id}-trace`} kind="trace_review" initial={v} busy={busy} demo={c.synthetic_demo} onSave={(k, data) => save(k, { ...data, vehicle_id: v.vehicle_id })} /></> : <>
        <label className="sc-field sc-action-picker"><span>Next workshop action</span><select value={kind} onChange={(e) => setKind(e.target.value)}>
          {["appointment", "recovery", "inspection", "repair", "verify_repair", "followup", "resolve"].map((k) => <option key={k} value={k}>{actionLabels[k]}</option>)}</select></label>
        <p className="sc-muted small">{kind === "inspection" ? "Record factual findings even while outreach approval is pending." : kind === "resolve" ? "A reviewer must confirm the inspection, any required repair, and follow-up. This is not a regulatory recall exemption." : kind === "repair" ? "Use the engineering-reviewed part and procedure shown in the campaign remedy." : v.safety_hold ? "Keep the vehicle parked. Arrange professional recovery; do not ask the owner to drive to a workshop." : "Follow the authorised workshop's assessment and procedure."}</p>
        <ActionForm key={`${v.vehicle_id}-${kind}-${c.remedy?.at || ""}`} kind={kind} initial={kind === "repair" ? { replacement_part: c.remedy?.replacement_part || "" } : {}} busy={busy} demo={c.synthetic_demo}
          onSave={(k, data) => save(k, { ...data, vehicle_id: v.vehicle_id })} />
      </>}
    </>}
  </aside>;
}

export default function SafetyCampaigns() {
  const [campaigns, setCampaigns] = useState([]);
  const [c, setC] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [route, setRoute] = useState(campaignRoute);
  const [tab, setTab] = useState(() => campaignRoute().tab);
  const [workshopAction, setWorkshopAction] = useState(() => campaignRoute().action);
  const [creating, setCreating] = useState(Boolean(new URLSearchParams(window.location.hash.split("?")[1] || "").get("investigation")));
  const [vehicleId, setVehicleId] = useState(() => campaignRoute().vehicle);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [csv, setCsv] = useState("");
  const [filename, setFilename] = useState("");
  const [lane, setLane] = useState("recovery");
  const [reviewNote, setReviewNote] = useState("");
  const pending = useRef(null);
  const loadVersion = useRef(0);
  const submitLock = useRef(false);

  async function load(id) {
    const version = ++loadVersion.current;
    setLoading(true); setError("");
    try {
      const list = await request(API);
      const selected = id || list.campaigns[0]?.campaign_id;
      const detail = selected ? await request(`${API}/${encodeURIComponent(selected)}`) : null;
      if (version !== loadVersion.current) return;
      setCampaigns(list.campaigns); setC(detail); setLane(detail?.approval?.lane || (detail?.requires_recovery ? "recovery" : "inspect"));
      setVehicleId((current) => detail?.vehicles.some((v) => v.vehicle_id === current) ? current : detail?.vehicles.find((v) => v.inspection?.outcome === "crack_found" && !v.repair)?.vehicle_id || detail?.vehicles[0]?.vehicle_id || "");
      return true;
    } catch (e) { if (version === loadVersion.current) setError(e.message); return false; }
    finally { if (version === loadVersion.current) setLoading(false); }
  }
  useEffect(() => {
    function readRoute() { const next = campaignRoute(); setRoute(next); setTab(next.tab); setWorkshopAction(next.action); if (next.vehicle) setVehicleId(next.vehicle); }
    window.addEventListener("hashchange", readRoute);
    return () => window.removeEventListener("hashchange", readRoute);
  }, []);
  useEffect(() => { load(route.campaign); return () => { loadVersion.current++; }; }, [route.campaign]);
  async function create(values, demo = false) {
    if (submitLock.current) return;
    submitLock.current = true; setBusy(true); setError(""); setMessage("");
    try { const created = await request(demo ? `${API}/demo` : API, demo ? {} : values); setCreating(false); setTab(route.interaction ? "investigate" : "overview"); setVehicleId(""); if (await load(created.campaign_id)) setMessage(demo ? "Ready demo loaded with owner replies, inspections, repairs and follow-up. All records are fictional; your saved changes are preserved." : "Campaign created. Import installation records to establish scope."); }
    catch (e) { setError(e.message); } finally { submitLock.current = false; setBusy(false); }
  }
  async function save(kind, data) {
    if (submitLock.current || !c) return false;
    submitLock.current = true; setBusy(true); setError(""); setMessage("");
    const signature = JSON.stringify([c.campaign_id, c.revision, kind, data]);
    if (pending.current?.signature !== signature) pending.current = { signature, id: crypto.randomUUID() };
    try {
      const next = await request(`${API}/${c.campaign_id}/actions/${kind}`, { revision: c.revision, request_id: pending.current.id, data });
      setC(next); setCampaigns((items) => items.map((item) => item.campaign_id === next.campaign_id ? next : item)); pending.current = null;
      setMessage(kind === "outreach" ? "Eligible notices recorded in the simulated outbox. No messages were sent." : "Update saved to the campaign evidence history.");
      return true;
    } catch (e) { setError(e.message); return false; } finally { submitLock.current = false; setBusy(false); }
  }
  async function exportPacket() {
    try { const packet = await request(`${API}/${c.campaign_id}/packet`); download(`${c.campaign_id}-evidence.json`, JSON.stringify(packet, null, 2)); }
    catch (e) { setError(e.message); }
  }
  function changeCampaign(id) {
    setVehicleId(""); setReviewNote(""); setCsv(""); setFilename(""); setFilter("all"); setMessage("");
    const params = new URLSearchParams({ tab, campaign: id }); if (route.interaction) params.set("interaction", route.interaction);
    window.location.hash = `safety-campaigns?${params}`;
  }
  function openStep(vid, nextTab, action = "inspection") {
    setVehicleId(vid); setTab(nextTab); setWorkshopAction(action); setFilter("all"); setSearch("");
    const params = new URLSearchParams({ tab: nextTab, campaign: c.campaign_id, vehicle: vid });
    if (nextTab === "workshop") params.set("action", action);
    if (route.interaction) params.set("interaction", route.interaction);
    history.replaceState(null, "", `#safety-campaigns?${params}`);
  }
  const m = c?.metrics || {};
  const selected = c?.vehicles.find((v) => v.vehicle_id === vehicleId) || null;
  const vehicles = (c?.vehicles || []).filter((v) => (filter === "all" || (filter === "hold" ? v.safety_hold : filter === "unresolved" ? !v.resolution && v.match !== "excluded" : v.match === filter)) &&
    [v.vehicle_id, v.owner_ref, v.model, v.lot_id].some((value) => value?.toLowerCase().includes(search.toLowerCase())));
  const eligible = (c?.vehicles || []).filter((v) => ["exact", "possible"].includes(v.match) && v.contact_consent && !v.notice).length;

  return <div className="sc-page">
    <header className="sc-header"><div><h1>Safety campaigns</h1><p className="sc-muted">Review owner reports, check installed-part records and document the next action.</p></div>
      <div className="sc-inline"><button disabled={busy || loading} onClick={() => load(c?.campaign_id)}>Refresh</button><button onClick={() => setCreating(!creating)} disabled={busy}>New campaign</button>
        <button className="primary" disabled={busy || loading} onClick={() => create({}, true)}>{busy ? "Preparing…" : "Load ready demo"}</button></div></header>
    {error && <div role="alert" className="banner banner-error">{error}</div>}
    {message && <div role="status" className="banner banner-ok">{message}</div>}
    {creating && <section className="sc-panel"><div className="sc-section-head"><h2>New safety campaign</h2><button className="ghost" onClick={() => setCreating(false)}>Cancel</button></div><CreateForm busy={busy} onCreate={create} /></section>}
    {loading ? <p role="status" className="sc-muted">Loading safety campaigns…</p> : !c && error ? <section className="sc-panel sc-empty">
      <h2>Campaigns could not be loaded</h2><p className="sc-muted">Reconnect before creating or reviewing a campaign.</p><button disabled={busy} onClick={() => load()}>Retry connection</button>
    </section> : !c ? <section className="sc-panel sc-empty">
      <div className="sc-empty-path" aria-hidden="true"><span>01<br />Find</span><span>→</span><span>02<br />Trace</span><span>→</span><span>03<br />Protect</span><span>→</span><span>04<br />Verify</span></div>
      <h2>One finding. A coordinated response.</h2><p>Trace a suspect component lot to vehicles, collect owner reports, and track inspections through repair and follow-up.</p>
      <p className="sc-muted">The ready demo includes 12 fictional vehicles, owner replies, workshop inspections, completed repairs and open follow-ups.</p>
      <button className="primary" disabled={busy} onClick={() => create({}, true)}>{busy ? "Preparing the walkthrough…" : "Load the complete demo"}</button>
    </section> : <>
      <section className="sc-campaign-header"><label className="sc-field"><span>Campaign</span><select aria-label="Select safety campaign" value={c.campaign_id} disabled={busy} onChange={(e) => changeCampaign(e.target.value)}>
        {campaigns.map((item) => <option key={item.campaign_id} value={item.campaign_id}>{item.synthetic_demo ? "Demo · " : ""}{item.title}</option>)}</select></label>
        <div className="sc-campaign-meta"><span className="sc-tag">{label(c.status)}</span><span className="mono">{c.component.part_number} / {c.component.lot_id}</span><button className="ghost" onClick={exportPacket}>Export evidence ↗</button></div>
      </section>
      <div className="sc-mode-note">{c.synthetic_demo ? "Synthetic demo · fictional vehicles, supplier and workshop evidence. Decisions are rehearsal records." : "Pilot campaign · recorded evidence requires qualified review."} Outreach is simulated; no WhatsApp, SMS or email is sent.</div>
      <div className="sc-metrics">{[["Verified lot matches", m.exact, `${m.possible} possible · ${m.unknown} trace unknown`], ["Open vehicle reviews", m.unresolved, `${m.safety_holds} safety holds · ${m.overdue} overdue`],
        ["Confirmed cracks", m.confirmed_cracks, `${m.inspected} recorded inspections`], ["Verified repairs", m.repair_verified, `${m.resolved} reviewed resolutions`]].map(([title, value, hint]) =>
        <div key={title} className="sc-metric"><span>{title}</span><strong>{value}</strong><small>{hint}</small></div>)}</div>
      <nav className="sc-tabs" aria-label="Campaign sections">{[["overview", "Overview"], ["investigate", "Meta investigation"], ["trace", "Vehicle traceability"], ["outreach", "Owner outreach"], ["workshop", "Workshop & repair"], ["evidence", "Evidence & close-out"]].map(([id, title]) =>
        <button key={id} aria-current={tab === id ? "page" : undefined} className={tab === id ? "active" : ""} onClick={() => { setTab(id); setError(""); }}>{title}</button>)}</nav>

      {tab === "overview" && <div className="sc-overview-grid">
        {c.demo_version && <section className="sc-panel sc-full sc-demo-guide"><div><h2>Your demo is ready</h2><p className="sc-muted">Explore the evidence already recorded, then use “Fill demo example” to try the next action.</p></div>
          <div className="sc-inline">{[["trace", "DEMO-CAR-010", "Review unknown lot"], ["outreach", "DEMO-CAR-003", "Read owner reports"], ["workshop", "DEMO-CAR-003", "Continue a repair"], ["workshop", "DEMO-CAR-001", "View a resolved vehicle"], ["evidence", "", "Supplier & audit trail"]].map(([nextTab, vid, text]) =>
            <button key={text} onClick={() => { setTab(nextTab); if (vid) setVehicleId(vid); }}>{text} →</button>)}</div>
        </section>}
        <section className="sc-panel"><div className="sc-section-head"><h2>The finding</h2>{c.requires_recovery && <span className="sc-tag sc-tag-danger">Critical seed finding</span>}</div>
          <h3>{c.component.component_name}</h3><p>{c.seed_evidence}</p><dl className="sc-facts"><div><dt>Supplier</dt><dd>{c.component.supplier}</dd></div><div><dt>Opened</dt><dd>{time(c.opened_at)}</dd></div></dl>
          {c.investigation_id && <a href={`#issue/${encodeURIComponent(c.investigation_id)}`}>Open source investigation ↗</a>}
          <div className="sc-inset"><strong>{m.safety_holds ? "Act on the finding. Do not wait for a majority." : "Build the evidence before deciding scope."}</strong><p>{m.safety_holds ? "Affected vehicles stay parked pending qualified review. Coordinate recovery, record inspections and keep unresolved owners visible." : "Use installation records and workshop findings. A matching model or a quiet owner inbox does not establish safety."}</p></div>
        </section>
        <section className="sc-panel"><h2>Traceability coverage</h2><p className="sc-muted">{m.registered} registered vehicles · match to this supplier, part and lot</p>
          <div className="sc-scope-bar" role="img" aria-label={`${m.exact} verified matches, ${m.possible} possible, ${m.unknown} unknown, ${m.excluded} different verified lot`}>
            {["exact", "possible", "unknown", "excluded"].map((key) => m[key] > 0 && <span key={key} className={`sc-scope-${key}`} style={{ flex: m[key] }} />)}</div>
          <dl className="sc-coverage">{["exact", "possible", "unknown", "excluded"].map((key) => <div key={key}><dt><i className={`sc-scope-${key}`} />{label(key)}</dt><dd>{m[key]}</dd></div>)}</dl>
          <p className="sc-muted small">A different verified lot excludes only this campaign's lot match. It is not a vehicle safety certificate.</p><button onClick={() => setTab("trace")}>Review vehicle records →</button>
        </section>
        <section className="sc-panel sc-full"><div className="sc-section-head"><div><h2>Response progress</h2><p className="sc-muted">Recorded milestones can overlap. Notices below are simulated.</p></div><button onClick={() => setTab("workshop")}>Open workshop queue →</button></div>
          <div className="sc-progress">{[["Simulated notices", m.outreach_simulated], ["Owner responses", m.replied], ["Inspections", m.inspected], ["Part replacements", m.repair_recorded], ["Verified repairs", m.repair_verified], ["Reviewed resolutions", m.resolved]].map(([title, count], index) =>
            <div key={title}><span className="sc-step">0{index + 1}</span><strong>{count}</strong><span>{title}</span><div className="sc-track"><i style={{ width: `${m.registered ? count / m.registered * 100 : 0}%` }} /></div></div>)}</div>
        </section>
      </div>}

      {tab === "investigate" && <CampaignInvestigation key={`${c.campaign_id}-${route.interaction}-${route.reply}`} campaign={c} initialVehicleId={route.vehicle} interactionId={route.interaction} replyId={route.reply} initialAssistanceMode={route.assistanceMode} onOpenStep={openStep} />}

      {tab === "trace" && <section className="sc-panel"><div className="sc-section-head"><div><h2>Import installed-part records</h2><p className="sc-muted">Use VINs or your fleet's vehicle references. Import current installation records, including documented replacements.</p></div>
        <button onClick={() => download("vehicle-traceability-template.csv", "vehicle_id,owner_ref,model,supplier,part_number,lot_id,trace_status,source_ref,contact_consent,channel\n", "text/csv")}>CSV template ↓</button></div>
        <div className="sc-inline"><label className="sc-file">Choose CSV<input type="file" accept=".csv,text/csv" disabled={busy} onChange={async (e) => { const file = e.target.files?.[0]; if (!file) return; if (file.size > 500000) { setError("CSV must be at most 500 KB"); return; } setCsv(await file.text()); setFilename(file.name); }} /></label>
          <span className="sc-muted">{filename || "Up to 500 rows per import"}</span><button disabled={busy || !csv} onClick={async () => { if (await save("import", { csv })) { setCsv(""); setFilename(""); } }}>Import records</button></div>
        <details><summary>CSV field guidance</summary><p className="sc-muted small">trace_status: verified, unverified or unknown. A verified value is a source assertion, not a reviewed match. A reviewer must attach and check the installation record to confirm the supplier, part and lot. contact_consent: yes or no. channel: whatsapp, sms, phone or email. Use owner references; do not include phone numbers or email addresses. Existing vehicle IDs must be corrected through trace review. Importing changes scope and resets outreach approval.</p></details>
      </section>}

      {tab === "outreach" && <section className="sc-panel"><div className="sc-section-head"><div><h2>Review owner outreach</h2><p className="sc-muted">{eligible} eligible for a new simulated notice · {m.awaiting_reply} awaiting a reply · {m.delivered} delivered</p></div><span className="sc-tag">Simulation only</span></div>
        <div className="sc-outreach-grid"><div className="sc-message-preview"><span>Message preview</span><p>{c.notice_previews?.[lane] || c.notice_preview || c.approval?.message || "Refresh to load the reviewed message preview."}</p></div>
          <form className="sc-form" onSubmit={(e) => { e.preventDefault(); save("approve", { lane, note: reviewNote }); }}>
            <label className="sc-field"><span>Response lane</span><select value={lane} onChange={(e) => setLane(e.target.value)}><option value="recovery">Keep parked · arrange recovery</option><option value="inspect" disabled={c.requires_recovery}>Authorised workshop inspection</option></select></label>
            <label className="sc-field"><span>Scope and message review</span><textarea required rows={3} value={reviewNote} onChange={(e) => setReviewNote(e.target.value)} placeholder="Record why this part/lot scope and response are appropriate…" /></label>
            {c.synthetic_demo && <button type="button" className="ghost" disabled={busy} onClick={() => setReviewNote("DEMO: installation records and the critical seed finding reviewed. Keep exact and possible lot matches parked and arrange professional recovery.")}>Fill demo review note</button>}
            <div className="sc-inline"><button className="primary" disabled={busy}>{c.synthetic_demo ? "Simulate reviewer approval" : "Approve as supervisor"}</button><button type="button" disabled={busy || !c.approval || !eligible} onClick={() => save("outreach", {})}>Record simulated notices</button></div>
            <p className="sc-muted small">{c.approval ? `${c.approval.simulated ? "Simulated review" : "Reviewed"} by ${c.approval.by} · ${time(c.approval.at)}` : "Approval is required before notices. Unknown traceability and contacts without consent are withheld."}</p>
          </form></div></section>}

      {tab === "workshop" && <section className="sc-panel"><div className="sc-section-head"><div><h2>Reviewed repair specification</h2><p className="sc-muted">Exact parts and procedures come from engineering records.</p></div><span className="sc-tag">{c.remedy ? "Specification recorded" : "Awaiting engineering review"}</span></div>
        {c.remedy && <dl className="sc-facts"><div><dt>Replacement part</dt><dd>{c.remedy.replacement_part}</dd></div><div><dt>Procedure</dt><dd>{c.remedy.procedure_ref}</dd></div><div><dt>Approval</dt><dd>{c.remedy.approval_ref}</dd></div></dl>}
        <details><summary>{c.remedy ? "Review updated specification" : "Add approved repair specification"}</summary><ActionForm key={c.campaign_id} kind="remedy" busy={busy} demo={c.synthetic_demo} onSave={save} /></details>
      </section>}

      {["trace", "outreach", "workshop"].includes(tab) && <div className={`sc-workspace ${selected ? "sc-with-detail" : ""}`}>
        <section className="sc-panel sc-vehicle-list"><div className="sc-section-head"><h2>{tab === "workshop" ? "Workshop queue" : "Vehicles"} <span className="sc-muted">{vehicles.length}</span></h2></div>
          <div className="sc-filters"><input aria-label="Search vehicles" placeholder="Search vehicle, owner or lot…" value={search} onChange={(e) => setSearch(e.target.value)} /><select aria-label="Filter vehicles" value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="all">All vehicles</option><option value="hold">Safety holds</option><option value="unresolved">Unresolved</option>{["exact", "possible", "unknown", "excluded"].map((s) => <option key={s} value={s}>{label(s)}</option>)}</select></div>
          <div className="sc-table-wrap"><table className="sc-table"><thead><tr><th>Vehicle</th><th>{tab === "trace" ? "Part / lot evidence" : tab === "outreach" ? "Owner response" : "Inspection / next step"}</th><th>Status</th></tr></thead><tbody>
            {vehicles.map((v) => <tr key={v.vehicle_id} className={selected?.vehicle_id === v.vehicle_id ? "sc-selected" : ""}><td><button className="sc-vehicle-button" onClick={() => setVehicleId(v.vehicle_id)}>{v.vehicle_id}<span>{v.owner_ref}</span></button></td>
              <td>{tab === "trace" ? <>{v.lot_id || "Unknown"}<small>{label(v.match)}</small></> : tab === "outreach" ? <>{v.replies.length ? `${v.replies.length} recorded update(s)` : v.notice ? "Awaiting reply" : !v.contact_consent ? "No consent · withheld" : "Not contacted"}<small>{v.notice ? "Simulated notice" : label(v.match)}</small></> : <>{label(v.inspection?.outcome)}<small>{v.repair_verification ? "Repair verified" : v.repair ? "Verify repair next" : v.appointment ? `Due ${v.appointment.due_date}` : "Review and schedule"}</small></>}</td>
              <td><span className={`sc-status ${v.safety_hold ? "sc-danger" : ""}`}>{v.safety_hold ? "Recovery / review" : v.resolution ? "Resolved" : v.match === "excluded" ? "Outside lot scope" : "Unresolved"}</span></td></tr>)}
            {!vehicles.length && <tr><td colSpan={3} className="sc-muted">{c.vehicles.length ? "No vehicles match this filter." : "Import installation records to build the vehicle list."}</td></tr>}
          </tbody></table></div>
        </section>
        {selected && <VehicleDetail key={`${c.campaign_id}-${selected.vehicle_id}-${tab}-${workshopAction}`} vehicle={selected} c={c} busy={busy} save={save} tab={tab} initialAction={workshopAction} />}
      </div>}

      {tab === "evidence" && <div className="sc-overview-grid"><section className="sc-panel"><h2>Supplier corrective action</h2>
        {c.supplier_action && <p className="sc-muted">{c.supplier_action.owner} · {label(c.supplier_action.status)} · due {c.supplier_action.due_date}<br />{c.supplier_action.note}</p>}
        <ActionForm key={c.campaign_id} kind="supplier_action" initial={c.supplier_action || {}} busy={busy} demo={c.synthetic_demo} onSave={save} />
      </section><section className="sc-panel"><h2>Close-out review</h2><p>{m.unresolved} unresolved vehicles · {m.unknown + m.possible} uncertain installation records</p>
        <p className="sc-muted">Close after vehicle dispositions, verified traceability and supplier corrective action. Record the manufacturer's regulatory decision; targeted repairs may still form part of a recall.</p>
        {c.closure && c.status === "closed" ? <div className="sc-inset">Closed by {c.closure.by} · {time(c.closure.at)}<p>{c.closure.regulatory_ref}</p></div> : <ActionForm kind="close" busy={busy} demo={c.synthetic_demo} onSave={save} />}
      </section><section className="sc-panel sc-full"><div className="sc-section-head"><h2>Evidence timeline</h2><button onClick={exportPacket}>Export complete packet ↓</button></div>
        <p className="sc-muted small">Every accepted change records its actor, input, campaign revision and time. Historical findings remain available after a vehicle reopens.</p>
        <ol className="sc-audit">{[...(c.events || [])].reverse().map((event) => <li key={event.event_id}><span className="sc-audit-revision">{event.revision}</span><div><strong>{label(event.kind)}{event.payload.simulated || c.synthetic_demo ? " · demo" : ""}</strong><p>{event.payload.input?.vehicle_id || c.component.lot_id} · {event.actor} ({event.actor_role})</p><details><summary>Evidence details</summary><pre>{JSON.stringify(event.payload, null, 2)}</pre></details></div><time>{time(event.at)}</time></li>)}</ol>
      </section></div>}
      <p className="sc-method">{c.method}</p>
    </>}
  </div>;
}
