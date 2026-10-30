import { useCallback, useEffect, useRef, useState } from "react";
import { apiHeaders } from "../src/apiAuth.js";
import {
  fetchOpenP1Cases,
  goHash,
  includeSimQuery,
  openCases,
  openConsole,
  openIssue,
  openWarning,
  readIncludeSimulated,
  simulateTraffic,
} from "../src/ui/opsActions.js";
import { dayGreeting } from "../src/ui/greeting.js";
import { formatSnapshotTs } from "../src/ui/formatTime.js";
import { issueCategoryLabel, packLabel } from "../src/ui/labels.js";
import "./command-center.css";

async function dashboardJson(url, signal, timeout = 8000) {
  const ctrl = new AbortController();
  const abort = () => ctrl.abort();
  signal.addEventListener("abort", abort, { once: true });
  if (signal.aborted) ctrl.abort();
  const timer = setTimeout(abort, timeout);
  try {
    const response = await fetch(url, { headers: apiHeaders(), signal: ctrl.signal });
    if (!response.ok) throw new Error(`${url.split("?")[0]} ${response.status}`);
    return await response.json();
  } catch (ex) {
    if (ctrl.signal.aborted && !signal.aborted) {
      throw new Error(`${url.split("?")[0]} timed out. Try Refresh.`);
    }
    throw ex;
  } finally {
    clearTimeout(timer);
    signal.removeEventListener("abort", abort);
  }
}

function fmtUSD(x) {
  if (x === null || x === undefined || Number.isNaN(Number(x))) return null;
  return `$${Math.round(Number(x)).toLocaleString()}`;
}

/** Hottest fleet issue = max dollars at risk among live clusters, else max live cases. */
function pickHottest(liveRisk, dollarRows, estimates, gaps) {
  const live = Array.isArray(liveRisk) ? liveRisk : [];
  if (!live.length) return null;
  const dolById = new Map((dollarRows || []).map((r) => [String(r.cluster_id), r]));
  const estById = new Map((estimates || []).map((e) => [String(e.cluster_id), e]));
  const gapById = new Map((gaps || []).map((g) => [String(g.cluster_id), g]));
  let best = null;
  let bestKey = -1;
  for (const r of live) {
    const id = String(r.cluster_id);
    const est = estById.get(id);
    const dol = dolById.get(id);
    const dollars = est?.total_risk_usd ?? dol?.dollar_impact ?? 0;
    const key = Number(dollars) * 1e6 + Number(r.live_case_count || 0);
    if (key > bestKey) {
      bestKey = key;
      best = { ...r, _est: est || null, _dol: dol || null, _category: gapById.get(id)?.category || null };
    }
  }
  if (!best || bestKey <= 0) {
    // No dollars anywhere — hottest by live volume, if any cases exist.
    const byVol = [...live].sort((a, b) => (b.live_case_count || 0) - (a.live_case_count || 0))[0];
    if (!byVol || !(byVol.live_case_count > 0)) return null;
    return { ...byVol, _est: null, _dol: null, _category: gapById.get(String(byVol.cluster_id))?.category || null };
  }
  return best;
}

/**
 * Command Center — flagship wallboard.
 * One glance at live ops before diving into voice / cases.
 */
export default function CommandCenter({ refreshKey }) {
  const [health, setHealth] = useState(null);
  const [wall, setWall] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [usage, setUsage] = useState(null);
  const [drain, setDrain] = useState(null);
  const [p1Cases, setP1Cases] = useState(null);
  const [hot, setHot] = useState(null);
  const [cites, setCites] = useState(null);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(true);
  const [simBusy, setSimBusy] = useState(false);
  const [tick, setTick] = useState(() => new Date());
  const pending = useRef(null);
  const [coreReady, setCoreReady] = useState(false);

  const load = useCallback(async (force = false) => {
    if (pending.current) {
      if (!force) return;
      pending.current.abort();
    }
    const ctrl = new AbortController();
    pending.current = ctrl;
    const json = (url) => dashboardJson(url, ctrl.signal);
    setErr("");
    setLoading(true);
    try {
      const sim = includeSimQuery();
      // Render each operational snapshot as soon as it arrives. Optional
      // analytics and the audit export must not hold the floor view hostage.
      const core = await Promise.allSettled([
        ...[
        ["/health", setHealth],
        [`/api/frontline/wallboard?include_simulated=${sim}`, setWall],
        [`/api/frontline/metrics?include_simulated=${sim}`, setMetrics],
        ["/api/frontline/usage", setUsage],
        ["/api/frontline/ops/drain", setDrain],
      ].map(async ([url, apply]) => {
        const data = await json(url);
        if (!ctrl.signal.aborted) apply(data);
      }),
        fetchOpenP1Cases(8, { getJson: json }).then((cases) => {
          if (!ctrl.signal.aborted) setP1Cases(cases);
        }),
      ]);
      if (ctrl.signal.aborted) return;
      const failures = core.filter((r) => r.status === "rejected");
      setErr(failures.map((r) => String(r.reason?.message || r.reason)).join(" · "));
      setLoading(false);
      if (core[1].status === "fulfilled") setCoreReady(true);
      setTick(new Date());
      // The hero always includes rehearsal traffic (labeled): in production
      // there is none, so this is a no-op there.
      const [early, copq, fin, gaps] = await Promise.all([
        "/api/frontline/early-warning?window_days=30&include_simulated=true",
        "/api/frontline/copq/rank?window_days=30&include_simulated=true",
        "/api/frontline/analytics/financial-impact",
        "/api/frontline/insights/product-gap?window_days=30&limit=8&include_simulated=true",
      ].map((url) => json(url).catch(() => null)));
      if (ctrl.signal.aborted) return;
      if (!early && !copq && !fin && !gaps) return;
      let hotPick = pickHottest(early?.live_risk, copq?.clusters, fin?.estimates, gaps?.top_issues);
      if (!hotPick) {
        // Corpus fallback: no live traffic yet — hottest product-gap issue.
        const top = [...(gaps?.top_issues || [])].sort((a, b) => (b.volume || 0) - (a.volume || 0))[0];
        if (top && top.volume > 0 && top.cluster_id !== null && top.cluster_id !== undefined) {
          hotPick = {
            cluster_id: top.cluster_id,
            pack_id: null,
            live_case_count: top.volume,
            critical_count: top.severity_mix?.Critical || 0,
            _est: null,
            _dol: null,
            _category: top.category || null,
            _corpus: true,
          };
        }
      }
      if (hotPick) {
        // Corpus context: top terms, record volume, backtest lead vs advisory.
        try {
          const context = await json(`/api/frontline/clusters/${encodeURIComponent(hotPick.cluster_id)}/context`);
          hotPick = { ...hotPick, _ctx: context };
        } catch {
          /* hero works without context */
        }
        // Dollarized fallback: no costed cases yet → exposure estimate from
        // corpus volume × the pack's own cost-per-case, always labeled est.
        const hasRealDollars = (hotPick._est?.total_risk_usd ?? hotPick._dol?.dollar_impact ?? 0) > 0;
        if (!hasRealDollars) {
          const cpc = Number(fin?.cost_per_case);
          const vol = Number(hotPick._ctx?.record_count);
          if (cpc > 0 && vol > 0) hotPick = { ...hotPick, _estDollars: vol * cpc };
        }
      }
      if (!ctrl.signal.aborted) setHot(hotPick);
    } catch (ex) {
      if (!ctrl.signal.aborted) setErr(String(ex.message || ex));
    } finally {
      if (pending.current === ctrl) {
        pending.current = null;
        if (!ctrl.signal.aborted) setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 12000);
    return () => {
      clearInterval(t);
      pending.current?.abort();
      pending.current = null;
    };
  }, [load, refreshKey]);

  // Grounded-citation count streams in once (slow export — never on the 12s tick).
  useEffect(() => {
    if (!coreReady) return;
    const ctrl = new AbortController();
    dashboardJson("/api/frontline/audits/export?limit=60", ctrl.signal, 30000)
      .then((d) => {
        if (!d || ctrl.signal.aborted) return;
        let g = 0;
        let t = 0;
        for (const row of d.interactions || []) {
          g += Number(row.audit?.grounded_actions) || 0;
          t += Number(row.audit?.total_actions) || 0;
        }
        if (t > 0) setCites({ grounded: g, total: t });
      })
      .catch(() => {});
    return () => ctrl.abort();
  }, [coreReady]);

  async function runSimulate() {
    setSimBusy(true);
    setMsg("");
    setErr("");
    try {
      const d = await simulateTraffic({ count: 15 });
      setMsg(
        `Simulated traffic loaded · completed ${d.completed ?? d.count ?? "?"} · cases created ${d.cases_created ?? "—"}`,
      );
      await load(true);
    } catch (e) {
      setErr(String(e.message || e));
    } finally {
      setSimBusy(false);
    }
  }

  const live = Array.isArray(wall?.live_contacts) ? wall.live_contacts : [];
  const clusters = wall?.top_risk_clusters || wall?.top_clusters || [];
  const liveCount =
    wall ? (wall.active_contacts ?? wall.active_count ?? wall.live_count ?? live.length) : "—";
  const p1 = wall ? (wall.critical_open ?? wall.p1_open ?? 0) : "—";
  const openCaseCount = wall ? (wall.open_cases ?? 0) : "—";
  const draining = Boolean(drain?.draining);

  const hotDollars = fmtUSD(hot?._est?.total_risk_usd ?? hot?._dol?.dollar_impact ?? hot?._estDollars);
  const hotLead = hot?.lead_time_weeks ?? hot?._dol?.lead_time_weeks ?? hot?._ctx?.backtest?.lead_time_weeks;
  const hotAdv = hot?.matched_advisory ?? hot?._dol?.matched_advisory ?? hot?._ctx?.backtest?.advisory_id;
  const hotCategory = issueCategoryLabel(hot?._category || hot?._ctx?.category);
  const maxClusterCases = Math.max(1, ...clusters.map((c) => Number(c.open_cases) || 0));
  const readiness = [
    ["API status", health?.status || "Awaiting status", health ? (health.status === "ok" ? "ok" : "warn") : "neutral"],
    ["Authentication", health?.auth_required == null ? "—" : health.auth_required ? "API key required" : "Open local", "neutral"],
    ["Database", health?.db_ok == null ? "—" : health.db_ok ? "Reachable" : "Check connection", health?.db_ok == null ? "neutral" : health.db_ok ? "ok" : "warn"],
    ["Pack load", health?.pack_ok == null ? "—" : health.pack_ok ? "Loaded" : "Failed", health?.pack_ok == null ? "neutral" : health.pack_ok ? "ok" : "warn"],
    ["LLM", health?.llm_available == null ? "—" : health.llm_available ? "Available" : "Off", health?.llm_available ? "ok" : "neutral"],
    ["Embedding", health?.embedding?.mode || "—", "neutral"],
  ];
  const pilotMetrics = [
    ["Open status", metrics?.cases?.open],
    ["Critical open", metrics?.cases?.critical_open],
    ["Pending follow-up", metrics?.cases?.pending_followup],
    ["Investigations", metrics?.investigations?.open],
    ["Active calls", metrics?.interactions_active],
    ["Dead letters", metrics?.alert_dead_letters_pending],
    ["Connector pending", metrics?.connector_deliveries_pending],
    ["Case notes", metrics?.case_notes_in_window],
    ["Fixes recorded", metrics?.fix_loop?.fixes_recorded],
  ].filter(([, value]) => value != null);
  const usageLabel = (key) => ({ contacts: "Contacts", llm_spend_usd: "LLM spend", alerts: "Alerts" }[key] || key.replaceAll("_", " "));

  return (
    <div className="command-page">
      <header className="cc-overview-header">
        <div>
          <h1 className="cc-greeting">{dayGreeting(tick)}</h1>
          <p className="cc-subtitle">Your live operations, priorities and system health.</p>
        </div>
        <div className="cc-header-actions">
          <button type="button" className="ghost" onClick={() => load(true)} disabled={loading}>
            {loading ? "Refreshing…" : "Refresh"}
          </button>
          <button type="button" className="primary" onClick={() => goHash("call")}>Start a contact <span aria-hidden="true">↗</span></button>
          <button type="button" onClick={() => goHash("safety-campaigns")}>Safety campaigns <span aria-hidden="true">↗</span></button>
        </div>
      </header>

      {msg && <div className="banner banner-ok" role="status">{msg}</div>}
      {err && <div className="banner banner-error" role="alert">Could not load command center: <span className="mono">{err}</span></div>}

      {hot && (
        <section className="panel cc-priority" aria-labelledby="cc-priority-title">
          <div className="cc-priority-copy">
            <div className="cc-priority-label"><span className="cc-status-dot" aria-hidden="true" />Priority issue <span className="cc-muted">· Group #{hot.cluster_id}</span></div>
            <h2 id="cc-priority-title">{hotCategory}</h2>
            <p className="cc-subtitle">{hot.critical_count > 0 ? `${hot.critical_count} critical · ` : ""}{hot._corpus ? "Historical complaint sample" : "30-day issue window"} · includes test traffic</p>
          </div>
          {(hotDollars || hotLead != null) && <dl className="cc-priority-facts">
            {hotDollars && <div><dt>Estimated risk</dt><dd>{hotDollars}</dd></div>}
            {hotLead != null && <div><dt>Historical lead</dt><dd>{Number(hotLead) === 0 ? "Same week" : `${Math.abs(Number(hotLead))}w ${Number(hotLead) > 0 ? "early" : "later"}`}<span className="cc-muted">{hotAdv ? `vs ${hotAdv}` : "vs matched advisory"}</span></dd></div>}
          </dl>}
          <div className="cc-priority-actions">
            <button type="button" onClick={() => openIssue(hot.cluster_id)}>Open issue <span aria-hidden="true">→</span></button>
            <button type="button" className="cc-text-button" onClick={() => openWarning({ clusterId: hot.cluster_id, packId: hot.pack_id })}>Early warning</button>
          </div>
        </section>
      )}

      <div className="cc-snapshot-line">
        <span>{readIncludeSimulated() ? "Including test traffic · managed in Early warning" : "Live traffic overview"}</span>
        <span>{wall?.ts ? `Updated ${formatSnapshotTs(wall.ts)}` : "Awaiting snapshot"}</span>
      </div>
      <div className="stat-grid cc-stat-grid">
        <button type="button" className="stat-card stat-card-btn" onClick={() => openConsole()} title="Open live console">
          <div className="label">Live contacts <span aria-hidden="true">↗</span></div>
          <div className="value">{liveCount}</div><div className="hint">Active now</div>
        </button>
        <button type="button" className={`stat-card ${Number(p1) > 0 ? "danger" : ""} stat-card-btn`} onClick={() => openCases({ severity: "Critical", status: "open" })} title="Open Critical case queue">
          <div className="label">Critical open <span aria-hidden="true">↗</span></div>
          <div className="value">{p1}</div><div className="hint">Open and follow-up</div>
        </button>
        <button type="button" className="stat-card stat-card-btn" onClick={() => openCases({ status: "open" })} title="Open case queue">
          <div className="label">Open cases <span aria-hidden="true">↗</span></div>
          <div className="value">{openCaseCount}</div><div className="hint">Open and follow-up</div>
        </button>
        <button type="button" className={`stat-card ${draining ? "danger" : ""} stat-card-btn`} onClick={() => goHash("settings?tab=lab&view=ops")} title="Open drain controls in Feature lab">
          <div className="label">Contact intake <span aria-hidden="true">↗</span></div>
          <div className="value cc-intake-value">{!drain ? "—" : draining ? "Draining" : "Ready"}</div>
          <div className="hint">{!drain ? "Awaiting server status" : draining ? `${drain.active_count ?? 0} still active` : "New contacts accepted"}</div>
        </button>
      </div>

      <div className="cc-operations-grid">
        <div className="cc-operations-main">
          <section className="panel cc-live-panel" aria-labelledby="cc-live-title">
            <div className="cc-panel-heading">
              <h2 id="cc-live-title">Live contacts <span className="cc-count">{wall ? liveCount : "—"}</span></h2>
              <button type="button" className="cc-text-button" onClick={() => openConsole()}>Open console <span aria-hidden="true">↗</span></button>
            </div>
            {live.length === 0 ? (
              <div className="cc-live-empty">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true"><path d="M4 14v-3a8 8 0 0 1 16 0v3M4 12H3v6h3v-6H4Zm16 0h1v6h-3v-6h2ZM20 18a4 4 0 0 1-4 4h-4" /></svg>
                <div><strong>{wall ? "No active contacts" : "Loading live activity"}</strong><p>{wall ? "New contacts will appear here as they start." : "Waiting for the latest contact snapshot."}</p></div>
              </div>
            ) : (
              <div className="live-feed">
                {live.map((row) => <button type="button" className="live-row live-row-btn" key={row.interaction_id} onClick={() => openConsole(row.interaction_id)} title="Open in live console">
                  <span className="dot" aria-hidden="true" />
                  <div className="cc-live-details"><strong>{row.category || "Intake in progress"}</strong><span className="id" title={row.interaction_id}>{row.interaction_id}</span></div>
                  <span className="meta">{packLabel(row.pack_id)}</span><span className="chan">{row.channel === "simulated" ? "Test traffic" : row.channel || "Open →"}</span>
                </button>)}
                {Number(liveCount) > live.length && <p className="cc-footnote">Showing {live.length} of {liveCount} active contacts.</p>}
              </div>
            )}
          </section>

          <section className="panel cc-queue-panel" aria-labelledby="cc-queue-title">
            <div className="cc-panel-heading">
              <div><h2 id="cc-queue-title">Critical queue</h2><p className="cc-subtitle">{p1Cases ? `${p1Cases.length} latest cases with open status` : "Loading open Critical cases"}</p></div>
              <button type="button" className="cc-text-button" onClick={() => openCases({ severity: "Critical", status: "open" })}>View queue <span aria-hidden="true">→</span></button>
            </div>
            {!p1Cases?.length ? (
              <div className="cc-queue-empty">
                <p>{p1Cases ? "No open Critical cases in this view." : "Waiting for the Critical case snapshot."}</p>
                <div className="cc-header-actions"><button type="button" className="ghost" onClick={runSimulate} disabled={simBusy}>{simBusy ? "Seeding…" : "Seed demo traffic"}</button><button type="button" className="ghost" onClick={() => openCases({ status: "open" })}>All open cases</button></div>
              </div>
            ) : (
              <div className="cc-queue-scroll"><table className="cc-queue-table">
                <thead><tr><th scope="col">Case / category</th><th scope="col">Status</th><th scope="col"><span className="sr-only">Action</span></th></tr></thead>
                <tbody>{p1Cases.map((c) => <tr key={c.case_id} onClick={() => openCases({ severity: "Critical", status: "open", caseId: c.case_id })}>
                  <td><strong>{issueCategoryLabel(c.category)}</strong><span className="cc-case-id" title={c.case_id}>{c.case_id}</span></td>
                  <td><span className="cc-case-status"><i aria-hidden="true" />{c.status}</span></td>
                  <td><button type="button" className="cc-text-button" aria-label={`Open case ${c.case_id}`} onClick={(e) => { e.stopPropagation(); openCases({ severity: "Critical", status: "open", caseId: c.case_id }); }}>Open <span aria-hidden="true">↗</span></button></td>
                </tr>)}</tbody>
              </table></div>
            )}
          </section>
        </div>

        <section className="panel cc-clusters-panel" aria-labelledby="cc-clusters-title">
          <div className="cc-panel-heading"><div><h2 id="cc-clusters-title">{clusters.length > 0 && clusters.every((c) => c.pack_id === "automotive_nhtsa") ? "Recurring vehicle issues" : "Recurring issues"}</h2><p className="cc-subtitle">Similar complaints grouped by problem. Most open cases first.</p></div></div>
          {clusters.length === 0 ? <div className="cc-queue-empty"><p>{wall ? "No open cases grouped by issue yet." : "Loading recurring issues…"}</p><button type="button" className="ghost" onClick={() => openWarning()}>Open early warning</button></div> : (
            <div className="cc-cluster-list">{clusters.map((c, i) => (
              <button type="button" className="cc-cluster-row" key={`${c.pack_id}-${c.cluster_id}`} onClick={() => openWarning({ clusterId: c.cluster_id, packId: c.pack_id })} aria-label={`View ${issueCategoryLabel(c.category)}, group ${c.cluster_id}, ${packLabel(c.pack_id)}, ${c.open_cases} open cases including follow-up. Highest reported severity: ${c.max_severity || "unknown"}.`}>
                <span className="cc-cluster-rank" aria-hidden="true">{String(i + 1).padStart(2, "0")}</span>
                <div className="cc-cluster-main">
                  <div className="cc-cluster-title"><strong>{issueCategoryLabel(c.category)}</strong><span className={`cc-severity cc-severity-${String(c.max_severity || "").toLowerCase()}`}>{c.max_severity ? `${c.max_severity} reported` : "Severity unreported"}</span></div>
                  <span className="cc-cluster-pack">Group #{c.cluster_id} · {packLabel(c.pack_id)}</span>
                  <span className="cc-cluster-track" aria-hidden="true"><span style={{ width: `${Math.max(0, Number(c.open_cases) || 0) / maxClusterCases * 100}%` }} /></span>
                </div>
                <span className="cc-cluster-count">{Number(c.open_cases).toLocaleString()}<small>open {Number(c.open_cases) === 1 ? "case" : "cases"}</small><span className="cc-cluster-arrow" aria-hidden="true">↗</span></span>
              </button>
            ))}</div>
          )}
          {clusters.length > 0 && <p className="cc-footnote cc-cluster-note">Counts include cases awaiting follow-up. Severity shows the highest level reported in each group.</p>}
          <button type="button" className="cc-text-button cc-cluster-more" onClick={() => openWarning()}>View all recurring issues <span aria-hidden="true">→</span></button>
        </section>
      </div>

      <section className="panel cc-system-panel" aria-labelledby="cc-system-title">
        <div className="cc-panel-heading"><div><h2 id="cc-system-title">System readiness</h2><p className="cc-subtitle">Service health at a glance</p></div></div>
        <dl className="cc-readiness">{readiness.map(([label, value, tone]) => <div key={label}><dt>{label}</dt><dd><i className={`cc-health-dot cc-health-${tone}`} aria-hidden="true" />{value}</dd></div>)}</dl>
        {cites && <p className="cc-footnote cc-audit-note">Audit sample · {cites.grounded.toLocaleString()} / {cites.total.toLocaleString()} grounded actions across up to 60 contacts, including test traffic.</p>}
      </section>

      <div className="cc-details-grid">
        <section className="panel" aria-labelledby="cc-usage-title">
          <div className="cc-panel-heading"><div><h2 id="cc-usage-title">Usage metering</h2><p className="cc-subtitle">{usage ? `${usage.month} · ${usage.tenant_id}` : "Current billing period"}</p></div></div>
          {usage ? <dl className="cc-usage-list">{Object.entries(usage.metrics || {}).map(([key, value]) => <div key={key}><dt>{usageLabel(key)}</dt><dd>{key === "llm_spend_usd" ? Number(value).toLocaleString(undefined, { style: "currency", currency: "USD", minimumFractionDigits: 2 }) : typeof value === "number" ? value.toLocaleString() : String(value)}</dd></div>)}</dl> : <div className="cc-queue-empty">Waiting for the usage snapshot.</div>}
        </section>
        <section className="panel" aria-labelledby="cc-pilot-title">
          <div className="cc-panel-heading"><div><h2 id="cc-pilot-title">Pilot metrics</h2><p className="cc-subtitle">{metrics?.window_days ? `${metrics.window_days}-day snapshot` : "Operational snapshot"}</p></div>{metrics?.ts && <span className="cc-asof">{formatSnapshotTs(metrics.ts)}</span>}</div>
          {metrics ? <dl className="cc-pilot-list">{pilotMetrics.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{typeof value === "number" ? value.toLocaleString() : String(value)}</dd></div>)}</dl> : <div className="cc-queue-empty">Waiting for the metrics snapshot.</div>}
        </section>
      </div>
    </div>
  );
}
