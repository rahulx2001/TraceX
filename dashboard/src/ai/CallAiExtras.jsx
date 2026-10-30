// [AI-LAYER] Call-widget add-ons: optional hi-IN speech recognition and
// mid-call photo upload. Defaults leave the existing call flow untouched.
import { useEffect, useState } from "react";
import { aiSpeechLang, setAiSpeechLang } from "./aiApi.js";
import EvidencePanel from "./EvidencePanel.jsx";
import {
  getPreferredVoiceURI,
  pickBestVoice,
  previewVoice,
  rankVoices,
  setPreferredVoiceURI,
} from "../ttsVoice.js";

function SpeechVoiceSelect({ lang }) {
  const [voices, setVoices] = useState([]);
  const [voiceURI, setVoiceURI] = useState(() => getPreferredVoiceURI());

  useEffect(() => {
    const synth = typeof window !== "undefined" ? window.speechSynthesis : null;
    if (!synth) return undefined;
    const load = () => setVoices(synth.getVoices() || []);
    load();
    // Chrome loads system voices asynchronously.
    synth.addEventListener?.("voiceschanged", load);
    return () => synth.removeEventListener?.("voiceschanged", load);
  }, []);

  useEffect(() => {
    if (!voices.length || !voiceURI) return;
    if (!voices.some((v) => v.voiceURI === voiceURI || v.name === voiceURI)) {
      setVoiceURI("");
      setPreferredVoiceURI("");
    }
  }, [voices, voiceURI]);

  const ranked = rankVoices(voices, lang);
  const auto = pickBestVoice(voices, lang, "");
  const onChange = (e) => {
    const next = e.target.value;
    setVoiceURI(next);
    setPreferredVoiceURI(next);
  };

  return (
    <div
      className="small muted"
      style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}
    >
      <label style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
        Agent voice
        <select value={voiceURI} aria-label="Agent voice" onChange={onChange}>
          <option value="">
            {auto ? `Auto — ${auto.name} (${auto.lang})` : "Auto — browser default"}
          </option>
          {ranked.map((v) => (
            <option key={v.voiceURI || v.name} value={v.voiceURI || v.name}>
              {v.name} · {v.lang}
            </option>
          ))}
        </select>
      </label>
      <button
        type="button"
        className="ghost small"
        onClick={() => previewVoice({ lang, voiceURI })}
      >
        Test voice
      </button>
    </div>
  );
}

export function SpeechLangSelect({ showVoice = false } = {}) {
  const [lang, setLang] = useState(aiSpeechLang() || "en-US");
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <label className="small muted" style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
        Report recognition language
        <select
          value={lang}
          aria-label="Speech recognition language"
          onChange={(e) => {
            setLang(e.target.value);
            setAiSpeechLang(e.target.value);
          }}
        >
          <option value="en-US">English (default)</option>
          <option value="en-IN">English (India)</option>
          <option value="hi-IN">हिन्दी (India)</option>
        </select>
        <span>saved for browser/server recognition when the report starts</span>
      </label>
      {showVoice && <SpeechVoiceSelect lang={lang} />}
    </div>
  );
}

export default function CallAiExtras({ interactionId, caseId, showLanguage = true, serverVoice = {}, textOnly = false }) {
  return (
    <div className="ai-call-extras" style={{ marginTop: 10 }}>
      {showLanguage && <SpeechLangSelect />}
      {textOnly ? <p>Spoken playback is off for this text report.</p>
        : serverVoice.tts ? <p>Deepgram voice: {serverVoice.tts_model || "configured English voice"}. English replies use this provider; Hindi text falls back to a browser voice when available.</p>
          : <SpeechVoiceSelect lang={aiSpeechLang() || "en-US"} />}
      <p className="small">The selected language is sent to recognition and saved with the report. Reply scripts currently remain in English. Hindi and mixed Hindi/English recognition quality still need real-audio validation.</p>
      {(caseId || interactionId) && (
        <EvidencePanel caseId={caseId || undefined} interactionId={caseId ? undefined : interactionId}
          title="Photo of the fault (optional)" />
      )}
    </div>
  );
}
