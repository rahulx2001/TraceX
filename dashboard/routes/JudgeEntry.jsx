import { goHash } from "../src/ui/opsActions.js";

export default function JudgeEntry() {
  return <section className="sc-panel" style={{ maxWidth: 980, margin: "0 auto" }}>
    <p className="sc-muted">TraceX · For automotive quality and service engineers</p>
    <h1>From an owner report to a reviewable investigation</h1>
    <p>Capture a multilingual report, inspect cited evidence, resolve missing information and document the reviewed next action.</p>
    <div className="sc-mode-note">
      <strong>Before the demonstration</strong>
      <p>The prepared campaign and installation records are fictional. The local replay server shows saved Meta output and makes no new model call. Each saved investigation identifies its mode, model and time; deterministic or fallback handling remains labelled.</p>
    </div>
    <ol style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 24, padding: 24 }}>
      <li><h2>Report</h2><p>Start voice or type a report. Confirm the words and the vehicle before handing it over.</p><button className="primary" onClick={() => goHash("call")}>Start a report →</button></li>
      <li><h2>Investigate</h2><p>Follow the report into cited observations, selected lookups and a missing-record question.</p><button onClick={() => goHash("safety-campaigns?tab=investigate")}>Open investigation</button></li>
      <li><h2>Review</h2><p>Inspect the original evidence, correct the draft and record an authorized decision.</p><button onClick={() => goHash("safety-campaigns?tab=trace")}>Review installation evidence</button></li>
      <li><h2>Evidence</h2><p>Inspect the source lineage, recorded decisions and separate repair verification.</p><button onClick={() => goHash("safety-campaigns?tab=evidence")}>Open evidence packet</button></li>
    </ol>
    <p className="sc-muted">Human accuracy and time savings remain pending real reviewer participation. The scoped historical matching result is research evidence; this demonstration shows investigation support.</p>
    <details><summary>Advanced tools and earlier platform tour</summary><p>Expand Advanced tools in the sidebar for the reused operations platform. <a href="#legacy-demo">Open the earlier intake and LotGuard tour</a>.</p></details>
  </section>;
}
