// [AI-LAYER] Defect-level early warning (#defect-level).
//
// This page is a static view of reports/defect/example_flags.json, copied to
// src/ai/defectFlags.json by scripts/defect_backtest.py --phase test. The JSON
// is real test-window output: flags, their frozen defect labels, and the
// complaint excerpts the model saw. When the test has not run, the file says so
// and this page shows no numbers rather than a mock.
import { useState } from "react";
import defectFlags from "../src/ai/defectFlags.json";
import prediction from "../src/ai/defectPrediction.json";
import "./defect-level.css";

function ModelTag() {
  return (
    <span className="chip ai-tag ai-tag-on" title="Defect labels were assigned by Muse Spark from the frozen train-only taxonomy.">
      Muse Spark
    </span>
  );
}

function RecallCell({ flag, detailed = false }) {
  if (flag.matched_recall) {
    const r = flag.matched_recall;
    return (
      <div className="defect-recall">
        <div><span className="defect-recall-status">Recall</span>{" "}<span className="mono">{r.campno}</span></div>
        <div className="muted small">Issued {r.rcdate}</div>
        {detailed && <p className="defect-recall-description">{r.desc_defect}</p>}
      </div>
    );
  }
  return (
    <div className="defect-recall">
      <div className="defect-recall-pending">No recall</div>
      <div className="muted small">By 2024-12-31</div>
    </div>
  );
}

function Excerpts({ complaints }) {
  if (!complaints?.length) return <div className="muted small">No complaint excerpts in this file.</div>;
  return (
    <ol className="defect-excerpts">
      {complaints.map((c, i) => (
        <li key={`${c.cmplid}-${c.date}`}>
          <details open={i === 0}>
            <summary>
              <span className="defect-excerpt-vehicle">{c.year || "–"} {c.make} {c.model}</span>
              <span className="muted small">{c.date}</span>
              <span className="defect-chevron" aria-hidden="true">⌄</span>
            </summary>
            <div className="defect-excerpt-body">
              <div className="muted small">Complaint <span className="mono">{c.cmplid}</span></div>
              <p>{c.excerpt}</p>
            </div>
          </details>
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

function PredictionEvidence() {
  const all = prediction.blocks.all_reports;
  const clean = prediction.blocks.excluding_explicit_recall_reports;
  const percent = value => value == null ? "Unavailable" : `${(value * 100).toFixed(1)}%`;
  const holdout = prediction.temporal_holdout;
  return (
    <section className="card" style={{ padding: 20, marginBottom: 20 }} aria-labelledby="prediction-evidence-heading">
      <h2 id="prediction-evidence-heading">Repaired historical comparison</h2>
      <p className="muted">{prediction.scope}</p>
      <p>{prediction.coverage.model_labelled_complaints.toLocaleString()} / {prediction.coverage.complaints.toLocaleString()} complaints classified, with complete recall vehicle scope.</p>
      <div className="defect-table-scroll">
        <table className="table">
          <caption style={{ textAlign: "left" }}>Campaign recall at equal alert budgets</caption>
          <thead><tr><th>Strategy</th><th>All reports</th><th>Excluding recall/campaign mentions</th></tr></thead>
          <tbody>
            <tr><th>Rolling defect detector</th><td>{all.detector.hits}/{all.detector.campaigns} · {percent(all.detector.campaign_recall)}</td><td>{clean.detector.hits}/{clean.detector.campaigns} · {percent(clean.detector.campaign_recall)}</td></tr>
            <tr><th>Complaint-count reference</th><td>{all.count.hits}/{all.count.campaigns} · {percent(all.count.campaign_recall)}</td><td>{clean.count.hits}/{clean.count.campaigns} · {percent(clean.count.campaign_recall)}</td></tr>
            <tr><th>Random reference, {all.random_draws} runs</th><td>{percent(all.random_mean_recall)} mean</td><td>{percent(clean.random_mean_recall)} mean</td></tr>
          </tbody>
        </table>
      </div>
      <p className="small">Each strategy receives {all.detector.alerts} alerts on all reports and {clean.detector.alerts} after excluding recall mentions. Detector precision among alerts with complete follow-up: {percent(all.detector.episode_precision)} and {percent(clean.detector.episode_precision)}, respectively.</p>
      <p className="small">In the recall-mention sensitivity, {(clean.random_at_least_detector * 100).toFixed(0)}% of random runs matched or exceeded detector recall. The measured advantage remains exploratory.</p>
      <p><strong>Human review:</strong> {prediction.human_review.reviewed}/{prediction.human_review.total} labelled.</p>
      <p className="muted small">{prediction.note}</p>
      {holdout && (
        <div style={{ borderTop: "1px solid var(--border, #d8dedb)", marginTop: 20, paddingTop: 16 }}>
          <h3>Separate 2025 holdout</h3>
          <p><strong>{holdout.method.hits}/{holdout.method.campaigns} campaigns detected · {percent(holdout.method.campaign_recall)}</strong></p>
          <p>Alerts matching later campaigns with complete follow-up: {holdout.method.confirmed_mature_alerts}/{holdout.method.mature_alerts}
            {" "}· {percent(holdout.method.episode_precision)} precision.
            {" "}Total alerts: {holdout.method.alerts}; outcomes observed through {holdout.outcome_end}.</p>
          <p>Count policy recall: {percent(holdout.count_baseline.campaign_recall)}.
            {" "}Random reference mean: {percent(holdout.random_mean_recall)}.</p>
          <p className="small">{percent(holdout.random_at_least_method)} of {holdout.random_draws} random runs matched or exceeded this recall.
            {" "}Descriptive 95% recall interval: {percent(holdout.method.recall_wilson95[0])}–{percent(holdout.method.recall_wilson95[1])}; the campaign sample is small and may be correlated.</p>
          <p><strong>Above-86% target: {holdout.target_met ? "Measured target met" : "Not met"}.</strong>
            {!holdout.protocol_qualified && " The experimental method also failed the development precision gate."}</p>
          <p className="muted small">Expanded fuel/propulsion inputs; method selected before evaluating 2025.
            {" "}{holdout.note} Matches use make and defect category; they do not verify the same affected vehicle or physical defect.
            {" "}This uses a different period and input set from the earlier comparison.</p>
        </div>
      )}
    </section>
  );
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
            {notRun
              ? "Flags appear after the frozen 2021–2024 defect test has been run."
              : "Historical evaluation and source complaint evidence."}
          </p>
        </div>
        {!notRun && (
          <div className="page-actions">
            <ModelTag />
          </div>
        )}
      </header>

      <PredictionEvidence />

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
          <section className="card defect-flags" aria-labelledby="defect-flags-heading">
            <div className="defect-section-heading">
              <h2 id="defect-flags-heading">Earlier partial experiment: flags <span className="muted">({flags.length})</span></h2>
              <span className="muted small">Select a flag to view evidence</span>
            </div>
            <p className="muted small">These examples belong to the original incomplete run. They are retained for traceability and do not supply the repaired comparison above.</p>
            <div className="defect-table-scroll" role="region" aria-label="Defect flags" tabIndex={0}>
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
                      onClick={() => setOpen(open === i ? -1 : i)}
                    >
                      <td className="mono defect-week">{f.week}</td>
                      <td>{f.make}</td>
                      <td>{f.component}</td>
                      <td>
                        <button
                          type="button"
                          className="defect-flag-button"
                          aria-label={`${f.week} ${f.make}: ${f.defect_label} details`}
                          aria-expanded={open === i}
                          aria-controls={open === i ? `defect-detail-${i}` : undefined}
                          onClick={(e) => {
                            e.stopPropagation();
                            setOpen(open === i ? -1 : i);
                          }}
                        >
                          <span>{f.defect_label}</span>
                          <span className="defect-chevron" aria-hidden="true">⌄</span>
                        </button>
                      </td>
                      <td>{f.record_count}</td>
                      <td><RecallCell flag={f} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          {flags.map((f, i) => (
            open === i && (
              <section className="card defect-detail" key={`${f.flag_id || i}-excerpts`} id={`defect-detail-${i}`} aria-labelledby={`defect-detail-heading-${i}`}>
                <div className="defect-detail-heading">
                  <div>
                    <h2 id={`defect-detail-heading-${i}`}>{f.defect_label}</h2>
                    <p className="muted small">{f.week} · {f.make} · {f.component}</p>
                  </div>
                  <span className="muted small">Label ID: <span className="mono">{f.defect_label_id}</span></span>
                </div>
                <div className="defect-detail-recall">
                  <h3>Later recall</h3>
                  <RecallCell flag={f} detailed />
                </div>
                <div className="defect-evidence">
                  <div className="defect-section-heading">
                    <h3>Complaint excerpts</h3>
                    <span className="muted small">{f.complaints?.length || 0} stored excerpts · {f.record_count} complaints in this slice-week</span>
                  </div>
                  <Excerpts complaints={f.complaints} />
                </div>
              </section>
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
