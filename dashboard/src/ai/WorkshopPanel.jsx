// [AI-LAYER] LotGuard workshop close-out: ranked inspection queue (visible for
// review), outcome recording (locked until approved), yield, packet export.
import { useCallback, useEffect, useState } from "react";
import { aiGet, aiPostJson } from "./aiApi.js";

const OUTCOMES = [
  ["crack_found", "Crack found"],
  ["wear_only", "Wear only"],
  ["no_issue", "No issue"],
];

export default function WorkshopPanel({ investigationId }) {
  const [w, setW] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    if (!investigationId) return;
    try {
      setW(await aiGet(`/api/ai/lotguard/${encodeURIComponent(investigationId)}/workshop`));
    } catch (e) {
      setErr(e.message);
    }
  }, [investigationId]);

  useEffect(() => {
    if (!investigationId) return;
    setW(null); setErr("");
    refresh();
    const t = window.setInterval(refresh, 4000);
    return () => window.clearInterval(t);
  }, [investigationId, refresh]);

  async function record(ownerId, outcome) {
    setBusy(true); setErr("");
    try {
      await aiPostJson(`/api/ai/lotguard/${encodeURIComponent(investigationId)}/outcomes`, {
        owner_id: ownerId, outcome,
      });
      await refresh();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function downloadPacket() {
    setErr("");
    try {
      const p = await aiGet(`/api/ai/lotguard/${encodeURIComponent(investigationId)}/packet`);
      const blob = new Blob([JSON.stringify(p, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `lotguard-packet-${investigationId}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setErr(e.message);
    }
  }

  if (!investigationId) return null;
  if (err && !w) return <div className="muted small">Workshop queue unavailable ({err}).</div>;
  if (!w) return <div className="muted small">Loading workshop queue…</div>;
  const y = w.yield || {};
  return (
    <section className="ai-workshop" data-testid="lotguard-workshop" style={{ marginTop: 12 }}>
      <h3 className="analytics-h" style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        Workshop inspections
        {w.locked
          ? <span className="chip">locked — awaiting supervisor approval</span>
          : <span className="chip">open · lane {w.lane}</span>}
      </h3>
      {w.locked && <p className="muted small" style={{ margin: "6px 0" }}>{w.lock_reason}</p>}
      <p style={{ margin: "6px 0" }}>
        Inspected <strong>{y.inspected}</strong> · cracks <strong>{y.crack_found}</strong> ·{" "}
        wear <strong>{y.wear_only}</strong> · clear <strong>{y.no_issue}</strong>
        {y.yield != null && <> · yield <strong>{(y.yield * 100).toFixed(0)}%</strong></>}
      </p>
      {err && <div className="banner banner-error small" role="alert" style={{ marginBottom: 10 }}>{err}</div>}
      <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
        <button type="button" className="btn btn-sm" onClick={downloadPacket}>
          Export evidence packet
        </button>
      </div>
      {(w.queue || []).length > 0 && (
        <table className="table small">
          <thead><tr><th>Owner</th><th>Score</th><th>Why</th><th>Outcome</th></tr></thead>
          <tbody>
            {(w.queue || []).map((q) => (
              <tr key={q.owner_id}>
                <td className="mono">{String(q.owner_id).slice(-8)}</td>
                <td>{q.score}</td>
                <td className="muted small">{(q.reasons || []).join("; ")}</td>
                <td>
                  {q.inspected ? (
                    <span className="chip">{q.outcome}</span>
                  ) : w.locked ? (
                    <span className="muted small">locked</span>
                  ) : (
                    <span style={{ display: "inline-flex", gap: 4, flexWrap: "wrap" }}>
                      {OUTCOMES.map(([v, label]) => (
                        <button key={v} type="button" className="btn btn-sm ghost" disabled={busy}
                          onClick={() => record(q.owner_id, v)}>
                          {label}
                        </button>
                      ))}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
