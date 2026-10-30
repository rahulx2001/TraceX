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
  const on = s.mode === "enhanced";
  const m = s.models || {};
  const title = on
    ? `Server configuration: Meta ${m.text}. This badge does not mean the current operation called a model. Check each investigation's request provenance.`
    : "Server configuration: model calls disabled or unconfigured. A saved Meta result can still be replayed; its original model, time and provenance appear on that result.";
  return (
    <a href="#demo" className={"chip ai-mode-badge " + (on ? "ai-tag-on" : "ai-tag-off")} title={title} data-testid="ai-mode-badge">
      {on ? "Server: Meta configured" : "Server: offline / deterministic"}
    </a>
  );
}
