import { goHash } from "../src/ui/opsActions.js";

export default function UserJourneyGuide() {
  return <section className="panel" style={{ maxWidth: 900 }}>
    <h1>Operator guide</h1>
    <p>Start with an owner report. Cases keep individual reports and follow-ups; investigations compare reports with supporting records.</p>
    <ol style={{ lineHeight: 1.8 }}>
      <li><strong>Report:</strong> speak or type the complaint. Confirm safety, vehicle details and the recognized words. <button className="ghost" onClick={() => goHash("call")}>Start report</button></li>
      <li><strong>Cases:</strong> open the saved case. “Known now” shows captured facts; “Still needed” lets you request evidence and record your assessment. Review and save status changes; Undo reverses your last change. <button className="ghost" onClick={() => goHash("cases")}>Open Cases</button></li>
      <li><strong>Investigate:</strong> confirm the report and selected vehicle, inspect source records, then prepare or correct an evidence-backed draft. <button className="ghost" onClick={() => goHash("safety-campaigns?tab=investigate")}>Investigate</button></li>
      <li><strong>Review:</strong> verify the installation evidence and record the authorized decision. A suggestion does not approve repair or release a vehicle. <button className="ghost" onClick={() => goHash("safety-campaigns?tab=trace")}>Review evidence</button></li>
      <li><strong>Evidence:</strong> inspect the decision history and retain the packet. “Save case packet” in Cases saves to the local outbox with the draft, notes and evidence references; it does not contact the customer. <button className="ghost" onClick={() => goHash("safety-campaigns?tab=evidence")}>Open evidence</button></li>
    </ol>
    <p>The interface and replies are English. You can supply English or Hindi input. Speech quality depends on the browser and device; type instead when recognition is unreliable.</p>
    <details><summary>If something goes wrong</summary><p>Your draft stays visible after a failed save. Check the message, correct the fields or sign in with the required access, then retry. If an investigation was interrupted, check saved history before making another request.</p><p>A missing recall, photo or scan code does not prevent a manual review. Record uncertainty and the next action in your assessment.</p></details>
    <p>Setup, support and engineering tools live under <a href="#platform?tab=tools">Platform</a>.</p>
  </section>;
}
