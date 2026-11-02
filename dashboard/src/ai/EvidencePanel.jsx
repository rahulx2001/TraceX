// [AI-LAYER] Photo evidence: upload (JPEG/PNG/WebP), list, SAM 3.1 box overlay,
// Muse Spark defect description mapped to the pack's component categories.
// Without a Meta key the upload still works and analysis shows "not run".
import { useCallback, useEffect, useRef, useState } from "react";
import { apiHeaders } from "../apiAuth.js";
import { aiGet, aiPostJson, aiUpload, aiStatus } from "./aiApi.js";
import MetaTag from "./MetaTag.jsx";
import FaultCodesPanel from "./FaultCodesPanel.jsx"; // [AI-LAYER] fault codes as evidence

function listPath({ caseId, interactionId, investigationId }) {
  if (caseId) return `/api/cases/${encodeURIComponent(caseId)}/evidence`;
  if (interactionId) return `/api/interactions/${encodeURIComponent(interactionId)}/evidence`;
  if (investigationId) return `/api/ai/investigations/${encodeURIComponent(investigationId)}/evidence`;
  return null;
}

function useEvidenceImage(id) {
  // Fetched with the API key header (an <img src> cannot carry it), shown via an object URL.
  const [url, setUrl] = useState(null);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let live = true;
    let obj = null;
    setUrl(null);
    setError(false);
    fetch(`/api/evidence/${encodeURIComponent(id)}/file`, { headers: apiHeaders(), credentials: "same-origin" })
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.blob(); })
      .then((b) => { if (b && live) { obj = URL.createObjectURL(b); setUrl(obj); } })
      .catch(() => { if (live) setError(true); });
    return () => { live = false; if (obj) URL.revokeObjectURL(obj); };
  }, [id, attempt]);
  return { url, error, retry: () => setAttempt((n) => n + 1), fail: () => setError(true) };
}

function Overlay({ ev }) {
  const { url: src, error, retry, fail } = useEvidenceImage(ev.evidence_id);
  const seg = ev.analysis && ev.analysis.segmentation;
  const boxes = (seg && seg.boxes) || [];
  return (
    <div className="ai-evidence-frame" style={{ position: "relative", display: "inline-block", maxWidth: "100%" }}>
      {error ? <div className="muted small" role="alert">
        Photo preview unavailable. <button type="button" className="ghost" onClick={retry}>Retry photo</button>
      </div> : src ? <img
        src={src}
        onError={fail}
        alt={ev.filename || "evidence photo"}
        style={{ maxWidth: "100%", maxHeight: 260, display: "block", borderRadius: 6 }}
      /> : <div className="muted small" style={{ width: 160, height: 90 }}>loading photo…</div>}
      {src && !error && boxes.filter((b) => b.pct).map((b, i) => (
        <div
          key={i}
          className="ai-sam-box"
          title={`${seg.concept} · SAM 3.1 match ${i + 1}`}
          style={{
            position: "absolute",
            left: `${b.pct.left}%`, top: `${b.pct.top}%`, width: `${b.pct.width}%`, height: `${b.pct.height}%`,
            border: "2px solid #ff4d4f", boxShadow: "0 0 0 1px rgba(0,0,0,.4)", borderRadius: 3, pointerEvents: "none",
          }}
        />
      ))}
    </div>
  );
}

function Analysis({ ev, enabled, onAnalyze, busy }) {
  const a = ev.analysis || {};
  const v = a.vision;
  const seg = a.segmentation;
  const models = [v && v.model_id, seg && seg.model_id].filter(Boolean);
  if (ev.analysis_status === "not_run") {
    return (
      <div className="muted small">
        Stored and attached. {enabled ? "Analysis not run yet." : "Photo analysis is currently unavailable. You can still review the attached photo."}
        {enabled && <button className="ghost" style={{ marginLeft: 8 }} disabled={busy} onClick={onAnalyze}>Analyze</button>}
      </div>
    );
  }
  if (ev.analysis_status === "pending") return <div className="muted small">Analysing photo…</div>;
  return (
    <div className="small" style={{ marginTop: 6 }}>
      <MetaTag mode={models.length ? "enhanced" : "deterministic"} models={models} fallbackReason={ev.analysis_status} />
      {v && (
        <div style={{ marginTop: 6 }}>
          <div><strong>{v.damaged_part || "part"}</strong>: {v.defect_description}</div>
          <div className="muted">
            Proposed category {v.proposed_category} ({Math.round((v.confidence || 0) * 100)}%)
            {v.mapped_category ? <> → pack category <span className="chip">{v.mapped_category}</span></> : " → not mapped (low confidence or not in pack)"}
          </div>
          {v.visible_hazard && <div className="chip sev-critical" style={{ marginTop: 4 }}>Visible hazard: {v.hazard_reason || "flagged by model"}</div>}
        </div>
      )}
      {seg && <div className="muted">SAM 3.1 · "{seg.concept}" · {seg.count} region(s)</div>}
      {(a.errors || []).length > 0 && <div className="muted">Partial: {a.errors.join(", ")}</div>}
      <div className="muted">Advisory only: the case category and severity are never changed by photo analysis.</div>
    </div>
  );
}

export default function EvidencePanel({ caseId, interactionId, investigationId, readOnly = false, title = "Photo evidence", onEvidenceChanged }) {
  const [rows, setRows] = useState([]);
  const [err, setErr] = useState("");
  const [loadError, setLoadError] = useState("");
  const [loading, setLoading] = useState(true);
  const [loaded, setLoaded] = useState(false);
  const [needSignin, setNeedSignin] = useState(false);
  const [busy, setBusy] = useState("");
  const [enabled, setEnabled] = useState(false);
  const fileRef = useRef(null);
  const path = listPath({ caseId, interactionId, investigationId });
  const reqGenRef = useRef(0);

  const load = useCallback(async () => {
    if (!path) return;
    const currentGen = ++reqGenRef.current;
    setLoading(true);
    setLoadError("");
    try {
      const d = await aiGet(path);
      if (currentGen === reqGenRef.current) {
        setRows(d.evidence || []);
        setLoaded(true);
        setLoadError("");
      }
    } catch (e) {
      if (currentGen === reqGenRef.current) {
        setLoadError(`Photos could not be loaded. Saved photos may still exist. ${e.message}`);
      }
    } finally {
      if (currentGen === reqGenRef.current) setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    setRows([]);
    setErr("");
    setLoaded(false);
    setNeedSignin(false);
    load();
    let live = true;
    setEnabled(false);
    aiStatus().then((s) => { if (live) setEnabled(s.mode === "enhanced"); })
      .catch(() => { if (live) setEnabled(false); });
    return () => { live = false; ++reqGenRef.current; };
  }, [load]);
  useEffect(() => {
    if (!rows.some((r) => r.analysis_status === "pending")) return undefined;
    const t = setTimeout(load, 2500);
    return () => clearTimeout(t);
  }, [rows, load]);

  async function onFile(e) {
    const f = e.target.files && e.target.files[0];
    if (!f || !path || investigationId) return;
    setBusy("upload"); setErr("");
    try {
      await aiUpload(path, f);
      await load();
      onEvidenceChanged?.();
    } catch (ex) {
      setErr(`Upload rejected: ${ex.message}`);
    } finally {
      setBusy("");
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function analyze(id) {
    setBusy("analysis"); setErr("");
    try { await aiPostJson(`/api/evidence/${encodeURIComponent(id)}/analyze`, {}); setNeedSignin(false); await load(); }
    catch (ex) {
      const forbidden = ex.status === 403;
      setNeedSignin(forbidden);
      setErr(forbidden
        ? "Photo analysis needs a supervisor sign-in (the operator key cannot run it)."
        : `Analysis failed: ${ex.message}`);
    }
    finally { setBusy(""); }
  }

  if (!path) return null;
  return (
    <section className="ai-evidence-panel" data-testid="evidence-panel" style={{ marginTop: 12 }}>
      <h3 className="analytics-h" style={{ display: "flex", gap: 8, alignItems: "center" }}>
        {title} {!loading && !loadError && loaded && <span className="muted small">({rows.length})</span>}
      </h3>
      {!readOnly && !investigationId && (
        <label
          className="ghost"
          style={{ display: "inline-block", cursor: "pointer" }}
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              fileRef.current?.click();
            }
          }}
        >
          <input
            ref={fileRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={onFile}
            disabled={Boolean(busy)}
            style={{ position: "absolute", width: 1, height: 1, padding: 0, margin: -1, overflow: "hidden", clip: "rect(0, 0, 0, 0)", border: 0 }}
            aria-label="Upload photo evidence"
          />
          <span className="chip">{busy === "upload" ? "Uploading…" : "+ Add photo (JPEG/PNG/WebP, ≤ 8 MB)"}</span>
        </label>
      )}
      {loading && <div className="muted small" role="status">Loading photos…</div>}
      {!loading && loadError && <div className="banner banner-warn small" role="alert" style={{ marginTop: 6 }}>
        {loadError} <button type="button" className="ghost" onClick={load}>Retry photos</button>
      </div>}
      {err && (
        <div className="banner banner-warn small" role="alert" style={{ marginTop: 6 }}>
          {err}
          {needSignin && <> <a href="#signin">Open sign-in →</a></>}
        </div>
      )}
      {!loading && !loadError && loaded && rows.length === 0 && <div className="muted small" style={{ marginTop: 6 }}>No photos attached. Add a customer or operator photo if it is available and safe to take, or request one in the follow-up. You can review the report without a photo.</div>}
      {readOnly && rows.length > 3 && <div className="muted small">Showing 3 of {rows.length}; open the cases for the rest.</div>}
      {(readOnly ? rows.slice(0, 3) : rows).map((ev) => (
        <div key={ev.evidence_id} className="ai-evidence-item" style={{ marginTop: 10 }}>
          <Overlay ev={ev} />
          <div className="mono muted small">{ev.evidence_id} · {ev.mime} · {ev.width}×{ev.height}{ev.case_id ? ` · ${ev.case_id}` : ""}</div>
          <Analysis ev={ev} enabled={enabled} busy={Boolean(busy)} onAnalyze={() => analyze(ev.evidence_id)} />
        </div>
      ))}
      {/* [AI-LAYER] OBD-II fault codes next to the photos */}
      {caseId && <FaultCodesPanel caseId={caseId} readOnly={readOnly} onEvidenceChanged={onEvidenceChanged} />}
    </section>
  );
}
