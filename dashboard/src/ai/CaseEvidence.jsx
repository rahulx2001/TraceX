import EvidencePanel from "./EvidencePanel.jsx";

export default function CaseEvidence({ cases, caseId, onSelect, onEvidenceChanged }) {
  return <div>
    <label>Review case evidence
      <select aria-label="Select evidence case" value={caseId} onChange={e => onSelect(e.target.value)} style={{ width: "100%", marginBottom: 12 }}>
        {cases.map(c => <option key={c.case_id} value={c.case_id} style={{ fontWeight: c.synthetic_demo ? 700 : 400 }}>
          {c.demo_hero && c.synthetic_demo ? "★ Demo · " : ""}{c.category} · {c.case_id}
        </option>)}
      </select>
    </label>
    <EvidencePanel key={caseId} caseId={caseId} onEvidenceChanged={onEvidenceChanged} />
  </div>;
}
