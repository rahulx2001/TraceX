import { goHash } from "../src/ui/opsActions.js";
import { useEffect, useState } from "react";
import { aiStatus } from "../src/ai/aiApi.js";

export default function JudgeEntry() {
  const [ai, setAi] = useState(null);
  useEffect(() => {
    let live = true;
    aiStatus().then(value => { if (live) setAi(value); });
    return () => { live = false; };
  }, []);
  return <section className="sc-panel" style={{ maxWidth: 980, margin: "0 auto" }}>
    <p className="sc-muted">TraceX · For automotive quality and service engineers</p>
    <h1>From an owner report to a reviewable investigation</h1>
    <p>Capture the owner’s report, check what is known, request missing evidence and record the next action.</p>
    <p className="sc-muted">English interface and replies · English or Hindi input</p>
    <div>
      <p data-testid="demo-ai-notice">{!ai ? "Checking assistance availability…" : ai.unavailable
        ? "Assistance status is unavailable. You can check status and retry."
        : ai.mode === "enhanced"
          ? "AI assistance is on. Review the source evidence before accepting a suggested conclusion."
          : "AI assistance is off. Reports, record lookups and manual review remain available."}</p>
    </div>
    <ol style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 24, padding: 24 }}>
      <li><h2>Report</h2><p>Start voice or type a report. Confirm the words and the vehicle before handing it over. Saved reports and follow-ups live in Cases.</p><button className="primary" onClick={() => goHash("call")}>Start a report →</button></li>
      <li><h2>Investigate</h2><p>Follow the report into cited observations, selected lookups and a missing-record question.</p><button onClick={() => goHash("safety-campaigns?tab=investigate")}>Open investigation</button></li>
      <li><h2>Review</h2><p>Inspect the original evidence, correct the draft and record an authorized decision.</p><button onClick={() => goHash("safety-campaigns?tab=trace")}>Review installation evidence</button></li>
      <li><h2>Evidence</h2><p>Inspect the source lineage, recorded decisions and separate repair verification.</p><button onClick={() => goHash("safety-campaigns?tab=evidence")}>Open evidence packet</button></li>
    </ol>
    <p><a href="#cases">Open Cases</a> for an individual report, evidence requests and assessment notes. <a href="#safety-campaigns?tab=investigate">Investigate</a> to compare that report with supporting records.</p>
    <details><summary>Demonstration data and evidence limits</summary>
      <p>Prepared campaign and installation records are fictional and labelled in their workspaces. In the open local demonstration, the core workflow needs no sign-in; authority on authenticated installations comes from your account.</p>
      <p>Historical classifier validation is documented separately in the research evidence. Product usability, investigator time savings and real Hindi/Hinglish speech quality require observed sessions. The interface and replies are English. Saved replays retain their original source and time.</p>
      <p>Support and setup tools are available under <a href="#platform?tab=tools">Platform</a>.</p>
    </details>
  </section>;
}
