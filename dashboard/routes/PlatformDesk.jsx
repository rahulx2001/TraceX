import { lazy, Suspense } from "react";
const PlatformOS = lazy(() => import("./PlatformOS.jsx"));
const EnterpriseOps = lazy(() => import("./EnterpriseOps.jsx"));
import { hashQueryObject, patchHashQuery } from "../src/ui/opsActions.js";

const TABS = [
  { id: "tools", label: "Tools & settings" },
  { id: "learn", label: "Learning" },
  { id: "ops", label: "Ops" },
];

export default function PlatformDesk({ refreshKey }) {
  const tab = hashQueryObject().tab || "tools";

  return (
    <div>
      <header className="page-header">
        <div>
          <h1>Platform</h1>
          <p className="sub">Setup, support and engineering tools. Owner reports and case work stay in the pilot workflow.</p>
        </div>
      </header>
      <div className="tabs" role="tablist" aria-label="Platform">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            className={"tab" + (tab === t.id ? " active" : "")}
            onClick={() => patchHashQuery({ tab: t.id })}
          >
            {t.label}
          </button>
        ))}
      </div>
      {tab === "tools" ? <section className="panel" aria-label="Platform tools">
        <p>Choose a tool when you need it. <a href="#cases">Cases</a> hold individual reports and follow-ups; <a href="#safety-campaigns?tab=investigate">Investigate</a> brings reports and supporting records together.</p>
        <ul style={{ lineHeight: 2.2 }}>
          {[["settings", "Settings"], ["console", "Live supervisor console"], ["command", "Operational overview"], ["ai-status", "AI assistance & diagnostics"], ["warning", "Early warning"], ["defect-level", "Defect research evidence"], ["analytics", "Analytics"], ["audits", "Audit records"], ["ai-tools", "Road-safety tools"]].map(([id, label]) => <li key={id}><a href={`#${id}`}>{label}</a></li>)}
        </ul>
      </section> : <Suspense fallback={<p role="status">Loading platform tools…</p>}>{tab === "ops" ? (
        <EnterpriseOps refreshKey={refreshKey} embedded />
      ) : (
        <PlatformOS refreshKey={refreshKey} embedded />
      )}</Suspense>}
    </div>
  );
}
