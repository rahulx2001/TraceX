// [AI-LAYER] Defect-level early warning (#defect-level).
//
// This page is a static view of reports/defect/example_flags.json, copied to
// src/ai/defectFlags.json by scripts/defect_backtest.py --phase test. The JSON
// is real test-window output: flags, their frozen defect labels, and the
// complaint excerpts the model saw. When the test has not run, the file says so
// and this page shows no numbers rather than a mock.
import { useState } from "react";
import defectFlags from "../src/ai/defectFlags.json";

function ModelTag() {
  return (
    <span className="chip ai-tag ai-tag-on" title="Defect labels were assigned by Muse Spark from the frozen train-only taxonomy.">
      Muse Spark
    </span>
  );
}

function RecallCell({ flag }) {
  if (flag.matched_recall) {
    const r = flag.matched_recall;
    return (
      <div>
        <span className="tag ok">recall</span>{" "}
        <span className="mono">{r.campno}</span>{" "}
        <span className="muted small">issued {r.rcdate}</span>
        <div className="muted small" style={{ marginTop: 4 }}>{r.desc_defect}</div>
      </div>
    );
  }
  return <span className="tag med">no recall by 2024-12-31</span>;
}

function Excerpts({ complaints }) {
  if (!complaints?.length) return <div className="muted small">No complaint excerpts in this file.</div>;
  return (
    <ol className="small" style={{ margin: "6px 0 0 18px", padding: 0 }}>
      {complaints.map((c) => (
        <li key={`${c.cmplid}-${c.date}`} style={{ marginBottom: 8 }}>
          <span className="mono">{c.cmplid}</span>{" "}
          <span className="muted">{c.date} · {c.year || "–"} {c.make} {c.model}</span>
          <div>{c.excerpt}</div>
        </li>
      ))}
    </ol>
  );
}

// The three empty-state facts. Read from defectFlags.json if the keys
// exist. If a key is missing, print "unknown". Do not hardcode a number that
// is not in the JSON or in a file read.
function SourcedFact({ value, source }) {
  if (!value || !source) return <>unknown</>;
  return <>{value} (<span className="mono">{source}</span>).</>;
}

export default function DefectLevel() {
  const [open, setOpen] = useState(0);
  const flags = defectFlags?.flags || [];
  const notRun = defectFlags?.status === "not run" || flags.length === 0;
  return (
    <div className="defect-level-page" data-testid="defect-level-page">
      <header className="page-header">
        <div>
          <h1>Defect-level early warning</h1>
          <p className="sub">
            Flags appear here only after the frozen 2021–2024 defect test has been run.
            Nothing on this page is estimated.
          </p>
        </div>
        {!notRun && (
          <div className="page-actions">
            <ModelTag />
          </div>
        )}
      </header>

      {notRun ? (
          <div className="hero-empty defect-empty" data-testid="defect-level-not-run">
            <span className="chip defect-status">Not run</span>
            <ul className="defect-facts">
              <li>
                <strong>Taxonomy:</strong>{" "}
                <SourcedFact value={defectFlags.taxonomy} source={defectFlags.taxonomy_source} />
              </li>
              <li>
                <strong>Human labels:</strong>{" "}
                <SourcedFact value={defectFlags.human_labels} source={defectFlags.human_labels_source} />
              </li>
              <li>
                <strong>Model test:</strong>{" "}
                {defectFlags.model_test ? `${defectFlags.model_test}. No flags and no recall numbers.` : "unknown"}
              </li>
            </ul>
            <div>
              <h3>What happens next</h3>
              <ol className="defect-next">
                <li>
                  Put <span className="mono">META_API_KEY</span> in the server{" "}
                  <span className="mono">.env</span> and restart the API.
                </li>
                <li>Classify the 300-row sample.</li>
                <li>
                  Fill the label column yourself, then run the one-shot test. This page updates only
                  when <span className="mono">example_flags.json</span> is copied to{" "}
                  <span className="mono">dashboard/src/ai/defectFlags.json</span>.
                </li>
              </ol>
            </div>
          </div>
      ) : (
        <>
          <div className="card" style={{ marginBottom: 14, overflowX: "auto" }}>
            <h3 className="analytics-h">Flags</h3>
            <table className="table table-clickable">
              <thead>
                <tr>
                  <th>Week</th>
                  <th>Make</th>
                  <th>Component</th>
                  <th>Defect label</th>
                  <th>Complaints</th>
                  <th>Later recall</th>
                </tr>
              </thead>
              <tbody>
                {flags.map((f, i) => (
                  <tr
                    key={f.flag_id || i}
                    className={open === i ? "selected" : undefined}
                    tabIndex={0}
                    aria-expanded={open === i}
                    onClick={() => setOpen(open === i ? -1 : i)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        setOpen(open === i ? -1 : i);
                      }
                    }}
                  >
                    <td className="mono">{f.week}</td>
                    <td>{f.make}</td>
                    <td>{f.component}</td>
                    <td><strong>{f.defect_label}</strong><div className="muted small mono">{f.defect_label_id}</div></td>
                    <td>{f.record_count}</td>
                    <td><RecallCell flag={f} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {flags.map((f, i) => (
            open === i && (
              <div className="card" key={`${f.flag_id || i}-excerpts`} style={{ marginBottom: 14 }}>
                <h3 className="analytics-h" style={{ marginTop: 0 }}>
                  {f.week} · {f.make} · {f.component} · {f.defect_label}
                </h3>
                <div className="muted small" style={{ marginBottom: 6 }}>
                  {f.record_count} complaints in this slice-week. Showing the {f.complaints?.length || 0} real
                  complaint excerpts stored with the flag.
                </div>
                <div style={{ maxHeight: 420, overflowY: "auto" }}>
                  <Excerpts complaints={f.complaints} />
                </div>
              </div>
            )
          ))}
        </>
      )}
      <div className="muted small" data-testid="defect-level-source">
        Source: <span className="mono">reports/defect/example_flags.json</span>, rendered from
        {" "}<span className="mono">dashboard/src/ai/defectFlags.json</span>.
      </div>
    </div>
  );
}
