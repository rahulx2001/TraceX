// [AI-LAYER] LotGuard lot card: which supplier lot this investigation points at,
// why (rationale with linked-record counts), and the deterministic risk behind it.
import { useEffect, useState } from "react";
import { aiGet } from "./aiApi.js";
import SafetyRiskChip from "./SafetyRiskChip.jsx";

export default function LotCard({ investigationId }) {
  const [c, setC] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    if (!investigationId) return;
    let live = true;
    setC(null); setErr("");
    aiGet(`/api/ai/lotguard/${encodeURIComponent(investigationId)}`)
      .then((d) => live && setC(d))
      .catch((e) => live && setErr(e.message));
    return () => { live = false; };
  }, [investigationId]);
  if (!investigationId) return null;
  if (err) return <div className="muted small">Lot card unavailable ({err}).</div>;
  if (!c) return <div className="muted small">Loading lot card…</div>;
  const r = c.risk || {};
  const m = r.mentions || {};
  const s = c.slice || {};
  return (
    <section className="ai-lot-card" data-testid="lot-card" style={{ marginTop: 12 }}>
      <h3 className="analytics-h" style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        Supplier lot <SafetyRiskChip risk={r} />
        {c.synthetic_demo && <span className="chip">synthetic demo data</span>}
        {c.fallback_slice_only && <span className="chip">slice match — no lot attached</span>}
      </h3>
      {c.lot ? (
        <div className="kvs" style={{ marginTop: 8 }}>
          <span className="k">Supplier</span><span className="v">{c.lot.supplier}</span>
          <span className="k">Lot</span><span className="v mono">{c.lot.lot_id}</span>
          {c.lot.lot_start && (
            <><span className="k">Build window</span><span className="v">{c.lot.lot_start} → {c.lot.lot_end || "open"}</span></>
          )}
          <span className="k">Slice</span>
          <span className="v">{[s.entity_1, s.entity_2, s.entity_3, s.category].filter(Boolean).join(" · ") || "—"}</span>
          <span className="k">Owners registered</span><span className="v">{c.owners_registered}</span>
        </div>
      ) : (
        <p className="muted small">No supplier lot is attached to this slice yet; owners are matched by slice only.</p>
      )}
      {(c.rationale || []).map((line, i) => (
        <p key={i} className="muted small" style={{ margin: "6px 0" }}>{line}</p>
      ))}
      {r.records_scanned > 0 && (
        <p className="muted small">
          Of {r.records_scanned} complaints in scope, {r.records_with_hazard_mention} mention a crash, fire or injury
          (crash {m.crash || 0} · fire {m.fire || 0} · injury {m.injury || 0}). Ordering heuristic, not a crash prediction.
        </p>
      )}
    </section>
  );
}
