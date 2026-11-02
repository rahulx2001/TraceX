// [AI-LAYER] Visible model attribution: "Powered by Muse Spark" or the
// deterministic fallback with its reason. Never hides which path produced a value.
export default function MetaTag({ models, mode, fallbackReason, style }) {
  const list = (models || []).filter(Boolean);
  if (mode === "enhanced" && list.length) {
    return (
      <details style={style}><summary className="chip ai-tag ai-tag-on">AI-assisted</summary><span className="muted small">Model: {list.join(" + ")}. Check this result against its source evidence.</span></details>
    );
  }
  return (
    <details style={style}><summary className="chip ai-tag ai-tag-off">Rules-based</summary><span className="muted small">Produced using rules.{fallbackReason ? ` Technical reason: ${fallbackReason}.` : ""}</span></details>
  );
}
