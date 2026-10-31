import evidence from "./mlImprovement.json";

const labels = {
  "defect.all_reports.rolling_defect.recall": "Campaign recall · all reports",
  "defect.all_reports.rolling_defect.mature_episode_precision": "Mature-alert precision · all reports",
  "defect.excluding_explicit_recall_reports.rolling_defect.recall": "Campaign recall · explicit recall mentions excluded",
  "defect.excluding_explicit_recall_reports.rolling_defect.mature_episode_precision": "Mature-alert precision · explicit recall mentions excluded",
  "fuel_holdout.method.recall": "Campaign recall · separate 2025 fuel holdout",
  "fuel_holdout.method.mature_episode_precision": "Mature-alert precision · separate 2025 fuel holdout",
  "category.labels.accuracy": "Category label diagnostic · authored examples",
  "category.descriptions.accuracy": "Category description diagnostic · authored examples",
};
const percent = value => value == null ? "Unavailable" : `${(100 * value).toFixed(1)}%`;

export default function MlImprovementEvidence() {
  return <section className="card" style={{ padding: 20, marginBottom: 20 }} aria-labelledby="ml-evidence-title" data-testid="ml-improvement-evidence">
    <h2 id="ml-evidence-title">ML evidence and research targets</h2>
    <p role="note"><strong>{evidence.notice}</strong></p>
    <p>Research ambition: {percent(evidence.targets.defect_precision)} mature-alert precision and {percent(evidence.targets.defect_recall)} campaign recall together. These targets have not been demonstrated.</p>
    <p>Human classification accuracy: <strong>Unavailable</strong> · {evidence.human_validation.labelled}/{evidence.human_validation.total} review rows labelled.</p>
    <p>Untouched evaluation: {evidence.untouched_test}.</p>
    <div className="defect-table-scroll">
      <table className="table">
        <caption style={{ textAlign: "left" }}>Verified baseline evidence; each row retains its own denominator and evaluation period</caption>
        <thead><tr><th>Metric</th><th>Numerator / denominator</th><th>Value</th><th>Descriptive 95% interval</th></tr></thead>
        <tbody>{evidence.metrics.map(m => <tr key={m.metric}>
          <th scope="row">{labels[m.metric] || m.metric}<details><summary>Definition and source</summary><p>{m.split}</p><p>Labels: {m.label_source}</p><p className="mono">{m.source}</p></details></th>
          <td>{m.numerator}/{m.denominator}</td><td>{percent(m.value)}</td>
          <td>{m.confidence_interval_95 ? m.confidence_interval_95.map(percent).join("–") : "Unavailable"}</td>
        </tr>)}</tbody>
      </table>
    </div>
    <p className="small">Recall counts eligible campaigns, including misses. Precision counts only alert episodes with complete follow-up. Unknown labels do not establish a match. Authored category examples assess implementation behavior; they do not establish human-reviewed accuracy.</p>
    <p className="small">Intervals are descriptive. Repeated alerts and related campaigns limit independent-sample interpretations. Recall matches do not establish identical physical defects or accidents prevented.</p>
    <details><summary>Evidence integrity</summary><p className="mono">{evidence.source}</p><p style={{ overflowWrap: "anywhere" }}>SHA-256: {evidence.source_sha256}</p></details>
  </section>;
}
