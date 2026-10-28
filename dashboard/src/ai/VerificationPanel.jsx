// [AI-LAYER] LotGuard owner verification: simulated symptom-check notices,
// structured replies, live counters and a computed recommendation.
// Nothing is sent anywhere; every payload carries the mock label.
import { useCallback, useEffect, useState } from "react";
import { aiGet, aiPostJson } from "./aiApi.js";

const SYMPTOMS = [
  ["clunk", "Clunk"],
  ["uneven_wear", "Wear"],
  ["steering_pull", "Pull"],
  ["none", "None"],
];

const REC_LABEL = {
  collecting: "Collecting replies",
  watch: "Watch — keep collecting",
  escalate: "Escalate — proceed to approval",
  de_escalate: "De-escalate — recommend monitoring",
};

export default function VerificationPanel({ investigationId }) {
  const [s, setS] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    if (!investigationId) return;
    try {
      setS(await aiGet(`/api/ai/lotguard/${encodeURIComponent(investigationId)}/verification`));
    } catch (e) {
      setErr(e.message);
    }
  }, [investigationId]);

  useEffect(() => {
    if (!investigationId) return;
    setS(null); setErr("");
    refresh();
    const t = window.setInterval(refresh, 3000);
    return () => window.clearInterval(t);
  }, [investigationId, refresh]);

  async function notify() {
    setBusy(true); setErr("");
    try {
      await aiPostJson(`/api/ai/lotguard/${encodeURIComponent(investigationId)}/notify`, {});
      await refresh();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function reply(ownerId, symptoms) {
    setBusy(true); setErr("");
    try {
      await aiPostJson(`/api/ai/lotguard/${encodeURIComponent(investigationId)}/replies`, {
        owner_id: ownerId, symptoms,
      });
      await refresh();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  if (!investigationId) return null;
  if (err && !s) return <div className="muted small">Verification unavailable ({err}).</div>;
  if (!s) return <div className="muted small">Loading verification…</div>;
  return (
    <section className="ai-verification" data-testid="lotguard-verification" style={{ marginTop: 12 }}>
      <h3 className="analytics-h" style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        Owner symptom check
        <span className="chip">simulated channel</span>
        <span className="chip">{REC_LABEL[s.recommendation] || s.recommendation}</span>
      </h3>
      <p className="muted small" style={{ margin: "6px 0" }}>{s.mock_label}</p>
      <p style={{ margin: "6px 0" }}>
        Notified <strong>{s.notified}</strong> · replied <strong>{s.replied}</strong> ·{" "}
        matching <strong>{s.matched}</strong> · none <strong>{s.none_count}</strong> ·{" "}
        photos <strong>{s.photo_count}</strong>
      </p>
      <p className="muted small" style={{ margin: "6px 0" }}>{s.reason}</p>
      {s.recommendation === "de_escalate" && (
        <div className="banner banner-ok small" role="status" style={{ marginBottom: 10 }}>
          NONE majority: recommend moving this investigation to monitoring via Ownership below.
        </div>
      )}
      {s.recommendation === "escalate" && (
        <div className="banner banner-warn small" role="status" style={{ marginBottom: 10 }}>
          Symptom cluster verified by owners: proceed to the supervisor approval gate.
        </div>
      )}
      {err && <div className="banner banner-error small" role="alert" style={{ marginBottom: 10 }}>{err}</div>}
      <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
        <button type="button" className="btn btn-sm" onClick={notify} disabled={busy}>
          {s.notified > 0 ? "Re-run owner check" : "Start owner check"}
        </button>
      </div>
      {(s.owners || []).length > 0 && (
        <table className="table small">
          <thead><tr><th>Owner</th><th>Channel</th><th>State</th><th>Simulate reply</th></tr></thead>
          <tbody>
            {(s.owners || []).map((o) => (
              <tr key={o.owner_id}>
                <td className="mono">{String(o.owner_id).slice(-8)}</td>
                <td>{o.channel}</td>
                <td>{o.replied ? "replied" : o.notified ? "notified" : "registered"}</td>
                <td>
                  {o.notified && !o.replied ? (
                    <span style={{ display: "inline-flex", gap: 4, flexWrap: "wrap" }}>
                      {SYMPTOMS.map(([v, label]) => (
                        <button key={v} type="button" className="btn btn-sm ghost" disabled={busy}
                          onClick={() => reply(o.owner_id, [v])}>
                          {label}
                        </button>
                      ))}
                    </span>
                  ) : (
                    <span className="muted small">{o.replied ? "recorded" : "notify first"}</span>
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
