import { useEffect, useRef, useState } from "react";
import { apiHeaders } from "../src/apiAuth.js";
import { INCLUDE_SIM_KEY, SS, consumeSession, parseLocationHash, patchHashQuery } from "../src/ui/opsActions.js";
import {
  caseDescription,
  cleanFollowupDraft,
  packLabel,
  safetyFlagLabel,
  statusLabel,
} from "../src/ui/labels.js";
import { useDebounced, useFocusTrap, useLocalStorage } from "../src/ui/hooks.js";
// [AI-LAYER] photo evidence panel (optional Meta AI layer; upload works without a key)
import EvidencePanel from "../src/ai/EvidencePanel.jsx";
import { noteAuthor, operatorError } from "../src/ui/operatorErrors.js";

const SEV = ["All", "Critical", "Medium", "Low"];
const STATUS = ["All", "open", "pending_followup", "closed"];

function SevBadge({ severity }) {
  const s = (severity || "").toLowerCase();
  const cls = s === "critical" ? "red" : s === "medium" ? "orange" : "blue";
  return <span className={"chip " + cls}>{severity || "—"}</span>;
}

function PriorityPill({ priority }) {
  return (
    <span className="chip mono">
      P{priority}
    </span>
  );
}

function ChannelBadge({ channel }) {
  if (!channel) return <span className="faint">—</span>;
  const sim = channel === "simulated";
  return (
    <span className={"chip " + (sim ? "purple" : "teal")}>
      {sim ? "simulated" : channel}
    </span>
  );
}

export default function CaseQueue() {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterSev, setFilterSev] = useState("All");
  const [filterStatus, setFilterStatus] = useState("All");
  const [searchQ, setSearchQ] = useState("");
  const searchDebounced = useDebounced(searchQ, 400);
  const [selectedId, setSelectedId] = useState(null);
  const selectedRef = useRef(null);
  selectedRef.current = selectedId;
  const detailRequestRef = useRef(0);
  const drawerRef = useRef(null);
  const skipHashWrite = useRef(true);
  useFocusTrap(drawerRef, !!selectedId, () => setSelectedId(null));
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [followupDraft, setFollowupDraft] = useState("");
  const [noteBody, setNoteBody] = useState("");
  const [statusDraft, setStatusDraft] = useState("open");
  const [undoStatus, setUndoStatus] = useState(null);
  const [saving, setSaving] = useState(false);
  const [drafting, setDrafting] = useState(false);
  const [noteSaving, setNoteSaving] = useState(false);
  const noteRequestRef = useRef(null);
  const [error, setError] = useState(null);
  const [exportMsg, setExportMsg] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [actionMsg, setActionMsg] = useState(null);
  const [includeSimulated, setIncludeSimulated] = useLocalStorage(INCLUDE_SIM_KEY, false);
  const [clusterFilter, setClusterFilter] = useState("");
  const [hasMore, setHasMore] = useState(false);
  const [nextOffset, setNextOffset] = useState(0);

  async function load({ append = false, offset = 0 } = {}) {
    setLoading(true);
    const params = new URLSearchParams({
      limit: "100",
      offset: String(offset),
      include_simulated: includeSimulated ? "true" : "false",
    });
    if (filterSev !== "All") params.set("severity", filterSev);
    if (filterStatus !== "All") params.set("status", filterStatus);
    if (searchDebounced.trim()) params.set("q", searchDebounced.trim());
    if (clusterFilter) params.set("cluster", clusterFilter);
    try {
      const r = await fetch(`/api/frontline/cases?${params.toString()}`, {
        headers: apiHeaders(),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      const list = d.cases || [];
      setCases((prev) => (append ? [...prev, ...list] : list));
      const pag = d.pagination || {};
      setHasMore(Boolean(pag.has_more));
      setNextOffset(pag.next_offset != null ? pag.next_offset : offset + list.length);
    } catch (e) {
      setError(operatorError(e));
    } finally {
      setLoading(false);
    }
  }

  // Deep-link from hash, then sessionStorage fallback.
  useEffect(() => {
    const { params } = parseLocationHash();
    const sev = params.get("severity") || consumeSession(SS.caseSev);
    const st = params.get("status") || consumeSession(SS.caseStatus);
    const q = params.get("q") || consumeSession(SS.caseSearch);
    const pick = params.get("id") || consumeSession(SS.caseSelect);
    const cluster = params.get("cluster");
    if (sev) setFilterSev(sev);
    if (st) setFilterStatus(st);
    if (q) setSearchQ(q);
    if (cluster) setClusterFilter(cluster);
    if (pick) setTimeout(() => openCase(pick), 0);
    skipHashWrite.current = true;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    load({ append: false, offset: 0 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterSev, filterStatus, searchDebounced, includeSimulated, clusterFilter]);

  useEffect(() => {
    if (skipHashWrite.current) {
      skipHashWrite.current = false;
      return;
    }
    patchHashQuery({
      id: selectedId || null,
      severity: filterSev !== "All" ? filterSev : null,
      status: filterStatus !== "All" ? filterStatus : null,
      q: searchDebounced.trim() || null,
      cluster: clusterFilter || null,
    });
  }, [selectedId, filterSev, filterStatus, searchDebounced, clusterFilter]);

  useEffect(() => {
    if (!selectedId) return undefined;
    const onEsc = () => setSelectedId(null);
    window.addEventListener("frontline-escape", onEsc);
    const onKey = (e) => {
      if (e.key === "Escape") setSelectedId(null);
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("frontline-escape", onEsc);
      window.removeEventListener("keydown", onKey);
    };
  }, [selectedId]);

  async function downloadCasesCsv() {
    setActionMsg(null);
    try {
      const params = new URLSearchParams({
        limit: "500",
        include_simulated: includeSimulated ? "true" : "false",
      });
      if (filterSev !== "All") params.set("severity", filterSev);
      if (filterStatus !== "All") params.set("status", filterStatus);
      if (searchDebounced.trim()) params.set("q", searchDebounced.trim());
      if (clusterFilter) params.set("cluster", clusterFilter);
      const r = await fetch(`/api/frontline/cases/export?${params.toString()}`, {
        headers: apiHeaders(),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "cases_export.csv";
      a.click();
      URL.revokeObjectURL(url);
      setError(null);
      setActionMsg(`CSV downloaded (${r.headers.get("X-Export-Count") || "?"} rows)`);
    } catch (e) {
      setActionMsg(null);
      setError(operatorError(e));
    }
  }

  async function exportCase(caseId) {
    setExportMsg(null);
    setExporting(true);
    try {
      if (followupDraft !== cleanFollowupDraft(detail?.followup_draft || "")) {
        if (!await saveCasePatch({ followup_draft: followupDraft })) return;
      }
      const r = await fetch(
        `/api/frontline/connectors/export/${encodeURIComponent(caseId)}`,
        { method: "POST", headers: apiHeaders() }
      );
      const text = await r.text();
      let body = {};
      try {
        body = JSON.parse(text);
      } catch {
        body = { detail: text };
      }
      if (!r.ok) {
        throw new Error(body.detail || `HTTP ${r.status}`);
      }
      if (!body.ok || body.status !== "success") throw new Error("Packet not saved");
      setExportMsg("Case packet saved to the local outbox with its audit trail. Customer message not sent.");
    } catch (e) {
      setExportMsg(operatorError(e, "save the case packet"));
    } finally {
      setExporting(false);
    }
  }

  async function openCase(caseId) {
    const request = ++detailRequestRef.current;
    selectedRef.current = caseId;
    setSelectedId(caseId);
    setDetail(null);
    setFollowupDraft("");
    setNoteBody("");
    setUndoStatus(null);
    setExportMsg(null);
    setActionMsg(null);
    setError(null);
    setDetailLoading(true);
    setDetailError("");
    try {
      const r = await fetch(`/api/frontline/cases/${encodeURIComponent(caseId)}`, {
        headers: apiHeaders(),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      if (request !== detailRequestRef.current || selectedRef.current !== caseId) return;
      setDetail(d);
      setStatusDraft(d.status || "open");
      setFollowupDraft(cleanFollowupDraft(d.followup_draft || ""));
    } catch (e) {
      if (request === detailRequestRef.current && selectedRef.current === caseId) setDetailError(operatorError(e, "load this case"));
    } finally {
      if (request === detailRequestRef.current && selectedRef.current === caseId) setDetailLoading(false);
    }
  }

  async function refreshDetail(caseId = selectedRef.current) {
    if (!caseId || selectedRef.current !== caseId) return;
    const request = ++detailRequestRef.current;
    try {
      const r = await fetch(`/api/frontline/cases/${encodeURIComponent(caseId)}`, { headers: apiHeaders() });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      if (request !== detailRequestRef.current || selectedRef.current !== caseId) return;
      setDetail(d);
      setDetailError("");
    } catch (e) {
      if (request === detailRequestRef.current && selectedRef.current === caseId) setDetailError(operatorError(e, "refresh evidence status"));
    }
  }

  function focusEvidence(selector, upload = false) {
    const input = drawerRef.current?.querySelector(selector);
    if (!input || input.disabled) return;
    const panel = input.closest("details");
    if (panel) panel.open = true;
    input.scrollIntoView({ block: "center", behavior: "smooth" });
    input.focus();
    if (upload) input.click();
  }

  function requestEvidence(kind) {
    const question = kind === "photo"
      ? "If it is available and safe to take, please share a photo of the affected part. Do not drive to take a photo."
      : "If you already have a scan report, please share the fault codes shown. You do not need a new scan to continue this case.";
    setFollowupDraft(current => current.includes(question) ? current : `${current.trim()}\n\n${question}`.trim());
    focusEvidence('#followup-draft-input');
    setActionMsg("Request added to the follow-up draft. Review and save it before contacting the customer.");
  }

  async function saveCasePatch(patch, { undo = false } = {}) {
    if (!selectedId || saving) return false;
    const caseId = selectedId;
    const previousStatus = detail?.status;
    setSaving(true);
    setActionMsg(null);
    try {
      const r = await fetch(`/api/frontline/cases/${encodeURIComponent(selectedId)}`, {
        method: "PATCH",
        headers: { ...apiHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`);
      const d = await r.json();
      if (selectedRef.current !== caseId) return false;
      setDetail((prev) => ({ ...prev, ...d, notes: prev?.notes || [] }));
      setError(null);
      if (patch.status) {
        setStatusDraft(patch.status);
        setUndoStatus(undo ? null : previousStatus);
      }
      setActionMsg(patch.status ? `Status saved: ${statusLabel(patch.status)}.` : "Follow-up draft saved. Customer message not sent.");
      await refreshDetail(caseId);
      await load();
      return true;
    } catch (e) {
      if (selectedRef.current !== caseId) return false;
      setActionMsg(null);
      setError(operatorError(e, "save these changes"));
      return false;
    } finally {
      setSaving(false);
    }
  }

  async function draftNote() {
    if (!selectedId) return;
    const caseId = selectedId;
    setDrafting(true);
    setActionMsg(null);
    try {
      const r = await fetch(
        `/api/frontline/cases/${encodeURIComponent(selectedId)}/draft-note`,
        { method: "POST", headers: apiHeaders() }
      );
      if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`);
      const d = await r.json();
      if (selectedRef.current !== caseId) return;
      setNoteBody(d.draft || "");
      focusEvidence('#operator-notes-input');
      setActionMsg("Assessment draft ready. Check it against the report, then Add note.");
    } catch (e) {
      if (selectedRef.current === caseId) setError(operatorError(e, "prepare an assessment draft"));
    } finally {
      setDrafting(false);
    }
  }

  async function addNote() {
    if (!selectedId || !noteBody.trim() || noteSaving) return;
    const caseId = selectedId;
    const submitted = noteBody;
    const material = `${caseId}\n${submitted.trim()}`;
    if (noteRequestRef.current?.material !== material) noteRequestRef.current = { material, key: crypto.randomUUID() };
    setNoteSaving(true);
    setActionMsg(null);
    try {
      const r = await fetch(
        `/api/frontline/cases/${encodeURIComponent(selectedId)}/notes`,
        {
          method: "POST",
          headers: { ...apiHeaders(), "Content-Type": "application/json", "Idempotency-Key": noteRequestRef.current.key },
          body: JSON.stringify({ body: noteBody.trim() }),
        }
      );
      if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`);
      const note = await r.json();
      if (selectedRef.current !== caseId) return;
      setDetail((prev) =>
        prev
          ? { ...prev, notes: [note, ...(prev.notes || [])] }
          : prev
      );
      setNoteBody((current) => current === submitted ? "" : current);
      setError(null);
      setActionMsg("Note added.");
      noteRequestRef.current = null;
      await refreshDetail(caseId);
    } catch (e) {
      setActionMsg(null);
      if (selectedRef.current === caseId) setError(operatorError(e, "add this note"));
    } finally {
      setNoteSaving(false);
    }
  }

  return (
    <div className="page-enter">
      <header className="page-header">
        <div>
          <h1>Case queue</h1>
          <p className="sub">
            Find an owner report, review what is known and record the next action. Investigations bring related reports and supporting evidence together.
          </p>
        </div>
        <div className="page-actions">
          <span className="build-stamp">Queue filters</span>
          <label className="check-row" style={{ fontSize: 12, margin: 0 }}>
            <input
              type="checkbox"
              checked={includeSimulated}
              onChange={(e) => setIncludeSimulated(e.target.checked)}
              aria-label="Include simulated traffic"
            />
            Include simulated
          </label>
          <button type="button" className="ghost" onClick={downloadCasesCsv}>
            Export CSV
          </button>
          <button type="button" onClick={() => load({ append: false, offset: 0 })} disabled={loading}>
            {loading ? "Loading…" : "Refresh"}
          </button>
        </div>
      </header>

      {error && !selectedId && (
        <div className="banner banner-error" role="alert">
          {error}{" "}
          <button type="button" className="ghost" onClick={() => setError(null)}>
            Dismiss
          </button>
        </div>
      )}

      {actionMsg && !selectedId && (
        <div className="banner banner-ok" role="status">
          {actionMsg}
        </div>
      )}

      <div className="filter-bar">
        <div className="field" style={{ flex: 1, minWidth: 200 }}>
          <label>Search</label>
          <input
            value={searchQ}
            onChange={(e) => setSearchQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && load()}
            placeholder="case id, category, text…"
            aria-label="Search cases"
          />
        </div>
        <div className="field">
          <label>Severity</label>
          <div className="filter-chips" role="group" aria-label="Severity filter">
            {SEV.map((s) => (
              <button
                key={s}
                type="button"
                className={
                  "filter-chip" +
                  (filterSev === s ? " active" : "") +
                  (s === "Critical" ? " danger" : "")
                }
                onClick={() => setFilterSev(s)}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
        <div className="field">
          <label>Status</label>
          <div className="filter-chips" role="group" aria-label="Status filter">
            {STATUS.map((s) => (
              <button
                key={s}
                type="button"
                className={"filter-chip" + (filterStatus === s ? " active" : "")}
                onClick={() => setFilterStatus(s)}
              >
                {statusLabel(s)}
              </button>
            ))}
          </div>
        </div>
        <button className="primary" onClick={() => load({ append: false, offset: 0 })} disabled={loading}>
          Search
        </button>
        <span className="toolbar-count">{loading ? "loading…" : `${cases.length} cases`}</span>
        {clusterFilter ? (
          <button type="button" className="ghost" onClick={() => setClusterFilter("")}>
            Cluster {clusterFilter} ×
          </button>
        ) : null}
      </div>

      <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
        <div className="table-wrap case-table-desktop">
          <table className="table-clickable">
            <thead>
              <tr>
                <th>Case ID</th>
                <th>Category</th>
                <th>Severity</th>
                <th>Priority</th>
                <th>Safety flags</th>
                <th>Advisory</th>
                <th>Cluster</th>
                <th>Investigation</th>
                <th>Peak frustration</th>
                <th>Channel</th>
              </tr>
            </thead>
            <tbody>
              {cases.length === 0 && !loading && (
                <tr>
                  <td colSpan={10}>
                    <div className="hero-empty" style={{ margin: 16, border: "none" }}>
                      <h3>No cases match</h3>
                      <p>Try clearing filters, or create a contact from Voice agent.</p>
                      <button type="button" className="primary" onClick={() => (window.location.hash = "call")}>
                        Start a contact
                      </button>
                    </div>
                  </td>
                </tr>
              )}
              {cases.map((c) => (
                <tr
                  key={c.case_id}
                  className={c.case_id === selectedId ? "selected" : ""}
                  tabIndex={0}
                  onClick={() => openCase(c.case_id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      openCase(c.case_id);
                    }
                  }}
                >
                  <td className="mono">{c.case_id}</td>
                  <td>{c.category || "—"}</td>
                  <td>
                    <SevBadge severity={c.severity} />
                  </td>
                  <td>
                    <PriorityPill priority={c.priority} />
                  </td>
                  <td>
                    {c.safety_flags && Object.keys(c.safety_flags).length ? (
                      Object.entries(c.safety_flags)
                        .filter(([, v]) => v)
                        .map(([k]) => (
                          <span className="chip red" key={k}>
                            {safetyFlagLabel(k)}
                          </span>
                        ))
                    ) : (
                      <span className="faint">—</span>
                    )}
                  </td>
                  <td className="mono">
                    {c.advisory_match_id ? (
                      <span className="chip green">{c.advisory_match_id}</span>
                    ) : (
                      <span className="faint">—</span>
                    )}
                  </td>
                  <td className="mono">
                    {c.cluster_match_id != null ? (
                      <span className="chip teal">cluster {c.cluster_match_id}</span>
                    ) : (
                      <span className="faint">—</span>
                    )}
                  </td>
                  <td className="mono">
                    {c.investigation_id ? (
                      <span className="chip teal">{c.investigation_id}</span>
                    ) : (
                      <span className="faint">—</span>
                    )}
                  </td>
                  <td className="mono">
                    {c.peak_frustration != null ? c.peak_frustration.toFixed(2) : "—"}
                  </td>
                  <td>
                    <ChannelBadge channel={c.channel} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="case-card-list">
          {cases.length === 0 && !loading && (
            <div className="hero-empty" style={{ margin: 8, border: "none" }}>
              <h3>No cases match</h3>
              <p>Try clearing filters, or start a contact.</p>
              <button type="button" className="primary" onClick={() => (window.location.hash = "call")}>
                Start a contact
              </button>
            </div>
          )}
          {cases.map((c) => (
            <button
              type="button"
              key={`card-${c.case_id}`}
              className={"case-card" + (c.case_id === selectedId ? " selected" : "")}
              onClick={() => openCase(c.case_id)}
            >
              <div className="case-card-top">
                <span className="case-card-cat">{c.category || "Uncategorized"}</span>
                <SevBadge severity={c.severity} />
              </div>
              <div className="case-card-id">{c.case_id}</div>
              <div className="case-card-meta">
                <span>{statusLabel(c.status)}</span>
                {c.cluster_match_id != null ? <span>Cluster {c.cluster_match_id}</span> : null}
                <ChannelBadge channel={c.channel} />
              </div>
            </button>
          ))}
        </div>
        {hasMore && (
          <div className="row" style={{ padding: 12, justifyContent: "center" }}>
            <button
              type="button"
              className="ghost"
              disabled={loading}
              onClick={() => load({ append: true, offset: nextOffset })}
            >
              {loading ? "Loading…" : "Load more"}
            </button>
          </div>
        )}
      </div>

      {selectedId && (
        <div
          className="drawer-scrim"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setSelectedId(null);
          }}
        >
          <div className="drawer" ref={drawerRef} role="dialog" aria-modal="true" aria-label="Case detail">
            <header>
              <div>
                <strong>{detail?.category || "Case"}</strong>{" "}
                {detail && <SevBadge severity={detail.severity} />}
                <div className="mono faint" style={{ fontSize: 11 }}>{selectedId}</div>
              </div>
              <button className="ghost icon-btn" onClick={() => setSelectedId(null)} aria-label="Close">
                ×
              </button>
            </header>
            <div className="body">
            {error && <div className="banner banner-warn" role="alert">{error}</div>}
            {actionMsg && <div className="banner" role="status">{actionMsg}</div>}
            {detailLoading && <div className="empty">loading…</div>}
            {detailError && <div className="banner banner-warn" role="alert">
              {detailError} <button type="button" className="ghost" onClick={() => detail ? refreshDetail() : openCase(selectedId)}>Retry case</button>
            </div>}
            {!detailLoading && !detail && !detailError && (
              <div className="empty">Case not found.</div>
            )}
            {detail && (
              <>
                <section aria-label="Known now" data-testid="case-known-now">
                <h2 style={panelHeading}>Known now</h2>
                <p className="muted" style={{ marginTop: 0 }}>
                  {detail.severity || "—"} · {statusLabel(detail.status)}
                  {detail.channel === "simulated" ? " · simulated" : ""}
                </p>
                <p>{caseDescription(detail.description_summary) || "The report summary could not be loaded. Check the original conversation before deciding the next action."}</p>
                <div className="kvs">
                  <span className="k">Domain</span>
                  <span className="v">{packLabel(detail.pack_id)}</span>
                  <span className="k">Vehicle reported</span>
                  <span className="v">{Object.values(detail.completeness?.reported_vehicle || {}).filter(Boolean).join(" ") || "Vehicle details not recorded"}</span>
                  <span className="k">Recall link</span>
                  <span className="v">{detail.advisory_match_id || "No linked recall"}</span>
                </div>
                {(detail.completeness?.vehicle_details_missing || []).length > 0 && <p className="muted small">Please confirm the vehicle {detail.completeness.vehicle_details_missing.join(", ")} in the follow-up. These details are not recorded.</p>}
                {detail.completeness?.advisory?.reason && (
                  <p className="muted" style={{ fontSize: 12 }}>{detail.completeness.advisory.reason}</p>
                )}
                <div className="row">{Object.entries(detail.safety_flags || {}).filter(([, value]) => value).map(([name]) => <span className="chip red" key={name}>{safetyFlagLabel(name)}</span>)}</div>
                {detail.investigation_id && <p><a href={`#issue/${encodeURIComponent(detail.investigation_id)}`}>Open related investigation</a></p>}
                </section>
                <div className="h-divider" />
                <section aria-label="Still needed" data-testid="case-evidence-guidance" style={{ fontSize: 12, marginTop: 12 }}>
                  <h2 style={panelHeading}>Still needed</h2>
                  <strong>{detail.completeness?.complete ? "Evidence recorded" : "Choose the next action"}</strong>
                  <p className="muted">Photos and scan codes are optional: add them when available, or request them in a follow-up. Record your assessment and next action in an operator note.</p>
                  {(!detail.completeness || (detail.completeness.unavailable || []).length > 0) && <p role="alert">
                    Some evidence records could not be loaded. Their absence is not confirmed.
                    {" "}<button type="button" className="ghost" onClick={() => refreshDetail()}>Retry evidence status</button>
                  </p>}
                  <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
                    {(detail.completeness?.missing || []).includes("photos") && <><button type="button" className="ghost" onClick={() => requestEvidence('photo')}>Request photo</button><button type="button" className="ghost" onClick={() => focusEvidence('[aria-label="Upload photo evidence"]', true)}>Add a photo</button></>}
                    {(detail.completeness?.missing || []).includes("fault_codes") && <><button type="button" className="ghost" onClick={() => requestEvidence('codes')}>Request scan codes</button><button type="button" className="ghost" onClick={() => focusEvidence('[aria-label="Fault codes"]')}>Add scan codes</button></>}
                    <button type="button" className="ghost" onClick={() => focusEvidence('#followup-draft-input')}>Draft follow-up</button>
                    <button type="button" className="ghost" onClick={() => focusEvidence('#operator-notes-input')}>Record assessment</button>
                    <button type="button" className="ghost" disabled={drafting || Boolean(noteBody.trim())} onClick={draftNote}>{drafting ? "Preparing…" : "Draft note"}</button>
                  </div>
                </section>

                <div className="h-divider" />
                <h2 style={panelHeading}>Status</h2>
                <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
                  <select aria-label="Case status" value={statusDraft} disabled={saving} onChange={e => setStatusDraft(e.target.value)}>{["open", "pending_followup", "closed"].map(s => <option key={s} value={s}>{statusLabel(s)}</option>)}</select>
                  <button type="button" disabled={saving || statusDraft === detail.status} onClick={() => saveCasePatch({ status: statusDraft })}>Save status</button>
                  {undoStatus && <button type="button" className="ghost" disabled={saving} onClick={() => saveCasePatch({ status: undoStatus }, { undo: true })}>Undo status change</button>}
                </div>

                <div className="h-divider" />
                <details>
                <summary>Follow-up draft{followupDraft.trim() ? " · prepared" : ""}</summary>
                <h2 style={panelHeading} id="followup-draft-heading">Follow-up Draft</h2>
                <p className="muted small">Save the reviewed message for your case record. Customer delivery is not connected in this pilot.</p>
                <textarea
                  id="followup-draft-input"
                  aria-labelledby="followup-draft-heading"
                  aria-label="Follow-up Draft"
                  value={followupDraft}
                  onChange={(e) => setFollowupDraft(e.target.value)}
                  placeholder="Draft a follow-up message…"
                  style={{ width: "100%" }}
                />
                <button
                  className="ghost"
                  disabled={saving}
                  style={{ marginTop: 8 }}
                  onClick={() => saveCasePatch({ followup_draft: followupDraft })}
                >
                  Save follow-up
                </button>
                </details>

                {/* [AI-LAYER] photo evidence for this case */}
                <details style={{ marginTop: 16 }}><summary>Photos & scan codes</summary>
                <EvidencePanel key={detail.case_id || selectedId} caseId={detail.case_id || selectedId} onEvidenceChanged={() => refreshDetail(detail.case_id || selectedId)} />
                </details>

                <div className="h-divider" />
                <details>
                <summary>Assessment notes{detail.notes?.length ? ` · ${detail.notes.length} recorded` : ""}</summary>
                <h2 style={panelHeading} id="operator-notes-heading">Operator notes</h2>
                <textarea
                  id="operator-notes-input"
                  aria-labelledby="operator-notes-heading"
                  aria-label="Operator notes"
                  value={noteBody}
                  onChange={(e) => setNoteBody(e.target.value)}
                  placeholder="Add a note for the pilot team…"
                  style={{ width: "100%", minHeight: 60 }}
                />
                <div className="row" style={{ gap: 8, marginTop: 8 }}>
                  <button
                    className="primary"
                    disabled={!noteBody.trim() || noteSaving}
                    onClick={addNote}
                  >
                    Add note
                  </button>
                </div>
                {(detail.notes || []).length > 0 && (
                  <ul style={{ marginTop: 12, paddingLeft: 18, fontSize: 12 }}>
                    {detail.notes.map((n) => (
                      <li key={n.note_id} style={{ marginBottom: 8 }}>
                        <span className="mono muted">{n.created_at}</span>{" "}
                        <strong>{noteAuthor(n.author)}</strong>: {n.body}
                      </li>
                    ))}
                  </ul>
                )}
                </details>
              </>
            )}
          </div>
          <div className="footer">
            {(noteBody.trim() || (detail && statusDraft !== detail.status)) && <span className="muted small">Save your note and status before creating the packet.</span>}
            {exportMsg && (
              <span className="muted" role="status" style={{ fontSize: 11, marginRight: 8 }}>
                {exportMsg}
              </span>
            )}
            {detail && (
              <button
                className="ghost"
                disabled={exporting || saving || Boolean(noteBody.trim()) || statusDraft !== detail.status}
                onClick={() => exportCase(detail.case_id || selectedId)}
                title={noteBody.trim() || statusDraft !== detail.status ? "Save your note and status before creating the case packet" : "Save the case, follow-up draft and evidence references to the local outbox"}
              >
                {exporting ? "Saving packet…" : "Save case packet"}
              </button>
            )}
            {detail?.audit_report_url && (
              <a
                className="button ghost"
                style={{ textDecoration: "none" }}
                href={`#audits?tab=reports&id=${encodeURIComponent(detail.interaction_id || "")}`}
                onClick={() => {
                  sessionStorage.setItem(
                    "frontline:audit_interaction_id",
                    detail.interaction_id
                  );
                  setSelectedId(null);
                }}
              >
                View audit report →
              </a>
            )}
            <button className="ghost" onClick={() => setSelectedId(null)}>
              Close
            </button>
          </div>
          </div>
        </div>
      )}
    </div>
  );
}

const panelHeading = {
  margin: "0 0 8px",
  fontSize: 12,
  fontWeight: 600,
  color: "var(--text-dim)",
  textTransform: "uppercase",
  letterSpacing: "0.06em",
};
