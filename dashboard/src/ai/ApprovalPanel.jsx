// [AI-LAYER] LotGuard approval gate: supervisor approve (with lane) / reject.
// The decision is ledgered server-side before it is shown; latest wins.
// Unapproved investigations keep the workshop queue locked (Step 5).
import { useCallback, useEffect, useState } from "react";
import { aiGet, aiPostJson } from "./aiApi.js";

const LANES = [
  ["inspect_7d", "Inspect within 7 days"],
  ["do_not_drive", "Do not drive — arrange pickup"],
];

export default function ApprovalPanel({ investigationId, onDecided }) {
  const [a, setA] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const [err, setErr] = useState("");
  const [lane, setLane] = useState("inspect_7d");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    if (!investigationId) return;
    try {
      const d = await aiGet(`/api/ai/lotguard/${encodeURIComponent(investigationId)}/approval`);
      setA(d.approval || null);
      setLoaded(true);
    } catch (e) {
      setErr(e.message);
    }
  }, [investigationId]);

  useEffect(() => {
    setA(null); setLoaded(false); setErr("");
    refresh();
  }, [investigationId, refresh]);

  async function decide(decision) {
    setBusy(true); setErr("");
    try {
      const d = await aiPostJson(
        `/api/ai/lotguard/${encodeURIComponent(investigationId)}/decision`,
        decision === "approve" ? { decision, lane, note } : { decision, note }
      );
      setA({ ...d, created_at: new Date().toISOString() });
      if (onDecided) onDecided(d);
    } catch (e) {
      setErr(e.message === "403"
        ? "Supervisor session required — sign in as supervisor to decide."
        : e.message);
    } finally {
      setBusy(false);
    }
  }

  if (!investigationId) return null;
  if (!loaded && !err) return <div className="muted small">Loading approval state…</div>;
  const v = (a && a.verification) || {};
  return (
    <section className="ai-approval" data-testid="lotguard-approval" style={{ marginTop: 12 }}>
      <h3 className="analytics-h" style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        Supervisor approval
        {a ? (
          <span className="chip">{a.decision === "approve" ? `approved · ${a.lane}` : "rejected"}</span>
        ) : (
          <span className="chip">undecided — workshop queue locked</span>
        )}
      </h3>
      {a && (
        <p className="muted small" style={{ margin: "6px 0" }}>
          Decided by {a.decided_by} ({a.decided_role}) · saw {v.matched} matching / {v.none_count} none
          of {v.replied} replies · {a.created_at}
          {a.note ? <> · note: {a.note}</> : null}
        </p>
      )}
      {err && <div className="banner banner-error small" role="alert" style={{ marginBottom: 10 }}>{err}</div>}
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 8 }}>
        <label className="muted small" htmlFor="lotguard-lane">Lane</label>
        <select id="lotguard-lane" value={lane} onChange={(e) => setLane(e.target.value)} disabled={busy}>
          {LANES.map(([val, label]) => <option key={val} value={val}>{label}</option>)}
        </select>
        <input
          aria-label="Decision note"
          placeholder="Note (optional)"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          disabled={busy}
          style={{ flex: "1 1 180px" }}
        />
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <button type="button" className="btn btn-sm btn-primary" disabled={busy} onClick={() => decide("approve")}>
          Approve
        </button>
        <button type="button" className="btn btn-sm ghost" disabled={busy} onClick={() => decide("reject")}>
          Reject
        </button>
      </div>
      <p className="muted small" style={{ margin: "6px 0 0" }}>
        Review the grounded brief above before deciding. The decision is written to the audit ledger first.
      </p>
    </section>
  );
}
