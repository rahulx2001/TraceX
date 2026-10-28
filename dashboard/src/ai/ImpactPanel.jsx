// [AI-LAYER] LotGuard impact panel: exposed vs verified vs confirmed, and the
// time-to-protect clock. Every number comes from warehouse rows; the method
// line states what is NOT claimed.
import { useCallback, useEffect, useState } from "react";
import { aiGet } from "./aiApi.js";

function fmt(ts) {
  if (!ts) return "pending";
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return String(ts);
  }
}

export default function ImpactPanel({ investigationId }) {
  const [p, setP] = useState(null);
  const [err, setErr] = useState("");

  const refresh = useCallback(async () => {
    if (!investigationId) return;
    try {
      setP(await aiGet(`/api/ai/lotguard/${encodeURIComponent(investigationId)}/packet`));
    } catch (e) {
      setErr(e.message);
    }
  }, [investigationId]);

  useEffect(() => {
    if (!investigationId) return;
    setP(null); setErr("");
    refresh();
    const t = window.setInterval(refresh, 5000);
    return () => window.clearInterval(t);
  }, [investigationId, refresh]);

  if (!investigationId) return null;
  if (err && !p) return <div className="muted small">Impact unavailable ({err}).</div>;
  if (!p) return <div className="muted small">Loading impact…</div>;
  const v = p.verification || {};
  const y = p.yield || {};
  const t = p.timeline || {};
  const avoided = Math.max(0, (p.owners_registered || 0) - (y.inspected || 0));
  return (
    <section className="ai-impact" data-testid="lotguard-impact" style={{ marginTop: 12 }}>
      <h3 className="analytics-h" style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        Campaign impact
        {p.synthetic_demo && <span className="chip">synthetic demo data</span>}
      </h3>
      <div className="kvs" style={{ marginTop: 8 }}>
        <span className="k">Exposed (lot)</span><span className="v">{p.owners_registered}</span>
        <span className="k">Verified at-risk</span><span className="v">{v.matched} of {v.replied} replies</span>
        <span className="k">Confirmed defective</span><span className="v">{y.crack_found} of {y.inspected} inspected</span>
        <span className="k">Inspected vs lot</span>
        <span className="v">{y.inspected} inspected · {avoided} spared a blanket recall visit</span>
      </div>
      <p className="muted small" style={{ margin: "6px 0" }}>
        Opened {fmt(t.opened_at)} · approved {fmt(t.approved_at)} · first inspection {fmt(t.first_outcome_at)}
      </p>
      <p className="muted small" style={{ margin: "6px 0" }}>{p.method}</p>
    </section>
  );
}
