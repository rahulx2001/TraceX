// [AI-LAYER] Top-bar badge: AI layer mode from GET /api/ai/status.
import { useEffect, useState } from "react";
import { aiStatus } from "./aiApi.js";

export default function AiModeBadge() {
  const [s, setS] = useState(null);
  useEffect(() => {
    let live = true;
    aiStatus().then((v) => live && setS(v));
    return () => { live = false; };
  }, []);
  if (!s) return null;
  const on = !s.unavailable && s.mode === "enhanced";
  const title = s.unavailable
    ? "Assistance status could not be loaded. Open status and retry."
    : on
    ? "AI assistance is available. Each result identifies whether it used AI or rules."
    : "Reports, record lookups and manual reviews remain available using rules. AI assistance is off.";
  return (
    <a href="#ai-status" className={"chip ai-mode-badge " + (on ? "ai-tag-on" : "ai-tag-off")} title={title} data-testid="ai-mode-badge">
      {s.unavailable ? "AI assistance: unavailable" : on ? "AI assistance: on" : "AI assistance: off"}
    </a>
  );
}
