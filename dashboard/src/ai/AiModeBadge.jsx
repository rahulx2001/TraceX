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
    ? `Meta AI layer on · text ${m.text} · vision ${m.vision} · segmentation ${m.segmentation}. Deterministic path stays the fallback.`
    : "Meta layer is off or no key is configured: the deterministic regex/gazetteer/rules path is running (including local Hindi safety checks). Photo upload still works.";
  return (
    <a href="#demo" className={"chip ai-mode-badge " + (on ? "ai-tag-on" : "ai-tag-off")} title={title} data-testid="ai-mode-badge">
      {on ? `AI: ${s.verified_against_live_api ? "Live verified" : "Configured"} · Meta` : "AI: Deterministic"}
    </a>
  );
}
