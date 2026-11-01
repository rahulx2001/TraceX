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
  const m = s.models || {};
  const title = s.unavailable
    ? "AI configuration could not be loaded. Check API status in Command center and refresh."
    : on
    ? `Server configuration: Meta ${m.text}. This badge does not mean the current operation called a model. Check each investigation's request provenance.`
    : "The server is responding. Reports and lookups use local rules; hosted model calls are disabled or unconfigured. Saved model results, when present, are labelled separately.";
  return (
    <a href="#demo" className={"chip ai-mode-badge " + (on ? "ai-tag-on" : "ai-tag-off")} title={title} data-testid="ai-mode-badge">
      {s.unavailable ? "AI status unavailable" : on ? "AI: Meta configured" : "AI: local rules"}
    </a>
  );
}
