import { useEffect, useState } from "react";
import { apiHeaders } from "../apiAuth.js";

export default function LotRiskPanel({ caseId }) {
  const [lot, setLot] = useState(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLot(null); setError("");
    fetch(`/api/frontline/cases/${encodeURIComponent(caseId)}/lot`, { headers: apiHeaders(), signal: controller.signal })
      .then(async r => { if (!r.ok) throw new Error("Lot records could not be loaded"); return r.json(); })
      .then(setLot).catch(e => { if (e.name !== "AbortError") setError(e.message); });
    return () => controller.abort();
  }, [caseId, retry]);
  if (error) return <p role="alert">{error} <button onClick={() => setRetry(v => v + 1)}>Retry lot records</button></p>;
  if (!lot) return <p className="muted">Loading lot records…</p>;
  if (!lot.available) return <p className="muted">{lot.reason}</p>;
  const e = lot.evaluation;
  const metrics = [["Owners in batch", lot.lot_size], ["Reported this week", lot.reported], ["Warned in simulation", lot.contacted], ["Still silent", lot.silent_after_warning]];
  return <section aria-label="Lot risk and outcomes" data-testid="lot-risk-panel">
    <h2 style={{ fontSize: 16 }}>Lot risk · EPS {lot.lot_id}</h2>
    <p className="muted small">All records are fictional; your saved changes are preserved. Messages and workshop outcomes are simulated.</p>
    <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 12 }}>
      {metrics.map(([label, count]) => <div key={label} style={{ padding: 12, background: "var(--bg-raised)", border: "1px solid var(--edge)", borderRadius: 8 }}><strong style={{ fontSize: 24 }}>{count}</strong><div className="small">{label}</div></div>)}
    </div>
    <p><strong>{lot.initially_silent}</strong> owners had never called when the warning campaign began.</p>
    <p>Reported symptoms per week: <strong>{lot.failure_trend.map(w => w.reports).join(" → ")}</strong>. Reports require diagnosis; this trend measures complaints.</p>
    <ol style={{ paddingLeft: 20 }}>
      <li>{lot.outcomes.opened_or_routed} opened / routed</li>
      <li>{lot.outcomes.bookings} workshop bookings</li>
      <li>{lot.outcomes.findings} confirmed fictional findings</li>
      <li>{lot.outcomes.resolved} verified and resolved</li>
    </ol>
    <p style={{ padding: 14, border: "1px solid #a6c8b2", borderRadius: 8 }}><strong style={{ fontSize: 26 }}>{lot.vehicles_warned_before_failure}</strong> vehicles warned and fixed before reported failure · simulation</p>
    <details><summary>Inspect the nine supporting vehicle records</summary><p className="small">{lot.metric_definition}</p>{lot.supporting_vehicle_ids.map(id => <p key={id}><a href={`#safety-campaigns?campaign=${lot.campaign_id}&tab=workshop&vehicle=${id}`}>{id} · inspection, repair, verification and resolution</a></p>)}</details>
    <p><a href={`#safety-campaigns?campaign=${lot.campaign_id}&tab=outreach`}>Review approved English / Hindi warning and owner replies</a></p>
    <p><a href={`#safety-campaigns?campaign=${lot.campaign_id}&tab=investigate&vehicle=EPS-CITY-000`}>Read the stored source investigation and review its draft</a></p>
    <details><summary>Linked cases · {lot.sibling_case_ids.length}</summary>{lot.sibling_case_ids.map(id => <p key={id}><a href={`#cases?id=${id}`}>{id}</a></p>)}</details>
    {e.verified ? <><p><strong>{(e.accuracy * 100).toFixed(1)}% accuracy · macro-F1 {e.macro_f1.toFixed(3)}</strong></p><p className="small">Challenger {(e.challenger_accuracy * 100).toFixed(1)}%: rejected. Evaluation published.</p><details><summary>Inspect evaluation source and limits</summary><p className="small">{e.accuracy_numerator}/{e.accuracy_denominator} judged historical records · {e.macro_f1_label_count} labels.</p><p className="small">{e.limitations}</p><p className="small mono">{e.source}</p></details></> : <p role="alert">{e.reason}</p>}
  </section>;
}
