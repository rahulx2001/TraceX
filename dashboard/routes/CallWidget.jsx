import { useEffect, useRef, useState } from "react";
import { apiHeaders, sendWsAuth } from "../src/apiAuth.js";
import { openCases } from "../src/ui/opsActions.js";
import { IconHangup, IconMic, IconSpeaker } from "../src/icons.jsx";
import {
  BARGE_IN_GRACE_MS,
  CALL_STATE,
  buildSlotEntries,
  callStateLabel,
  capabilitySnapshot,
  fatalWsErrorMessage,
  greetingSpeakText,
  isFatalWsError,
  mapInteractionEnded,
  mergeTranscriptTurn,
  shouldAcceptSpeechResult,
  shouldAllowBargeIn,
  shouldReconnectOnClose,
  shouldResumeListeningOnOpen,
  slotProgress,
  transcriptFromResume,
  POST_TTS_COOLDOWN_MS,
  STT_FINAL_DEBOUNCE_MS,
  RECOG_RESTART_MS,
  looksLikeAgentEcho,
  coalesceSpeechFinals,
  IDLE_LISTEN_REPROMPT_MS,
  decideSpeechFinal,
  createTurnQueue,
  socketIsLive,
  advancePlayback,
  SERVER_AUDIO_WAIT_MS,
  SERVER_AUDIO_MAX_BYTES,
  SERVER_CAPTURE_SILENCE_MS,
  SERVER_CAPTURE_MAX_MS,
  serverVoiceSelection,
  userAudioFrame,
} from "../src/voiceHelpers.js";
import { getPreferredVoiceURI, pickBestVoice } from "../src/ttsVoice.js";
// [AI-LAYER] optional Meta AI layer add-ons
import CallAiExtras, { SpeechLangSelect } from "../src/ai/CallAiExtras.jsx";
import { aiSpeechLang } from "../src/ai/aiApi.js";
import { recordingMime, responseSpeechLocale, sendIntakeSurvey, speechLocale, voiceActivity } from "../src/voiceExperience.js";
import { createPcmRecorder, microphonePreflight } from "../src/voiceCapture.js";
import "./voice-report.css";

// Backoff caps at 5s, so 8 tries ≈ 25s of retrying — comfortably inside the
// server's reconnect grace (FRONTLINE_WS_RECONNECT_GRACE_S, default 120s).
const RECONNECT_MAX_ATTEMPTS = 8;

function getSpeechRecognition() {
  if (typeof window === "undefined") return null;
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

export default function CallWidget() {
  const [state, setState] = useState(CALL_STATE.IDLE);
  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);
  const [transcript, setTranscript] = useState([]);
  const [slots, setSlots] = useState({});
  const [pack, setPack] = useState(null);
  const [interactionId, setInteractionId] = useState(null);
  const [handoff, setHandoff] = useState(false);
  const [handoffStatus, setHandoffStatus] = useState("");
  const [ended, setEnded] = useState(null);
  const [wsStatus, setWsStatus] = useState("idle");
  const [textFallback, setTextFallback] = useState("");
  const [activity, setActivity] = useState(null);
  const [micGranted, setMicGranted] = useState(null);
  const [inputLevel, setInputLevel] = useState(0);
  const [preflight, setPreflight] = useState({ busy: false, note: "" });
  const [automaticInterrupt, setAutomaticInterrupt] = useState(false);
  const automaticInterruptRef = useRef(false);
  const noiseFloorRef = useRef(.008), pcmRecorderRef = useRef(null), preRollPendingRef = useRef(false);
  const reportLocaleRef = useRef(speechLocale(aiSpeechLang()));
  const startRequestRef = useRef(null), acceptedMimeRef = useRef(null);
  // Server voice (Deepgram STT/TTS) as advertised by the WS `ready` frame.
  const [serverVoice, setServerVoice] = useState({ stt: false, tts: false });
  const [turnCount, setTurnCount] = useState(0);
  const [speakPhase, setSpeakPhase] = useState("normal"); // 'greeting' | 'normal'
  const [muted, setMuted] = useState(false);
  const [textOnly, setTextOnly] = useState(false);
  const textOnlyRef = useRef(false);
  const [driving, setDriving] = useState(false);
  const [frustration, setFrustration] = useState(0);
  const [latency, setLatency] = useState(null);
  const [consent, setConsent] = useState(null);
  const [safetyMode, setSafetyMode] = useState(false);
  const [callSecs, setCallSecs] = useState(0);
  const [survey, setSurvey] = useState({ csat: 0, sent: false });
  const [region, setRegion] = useState(() => {
    try { return localStorage.getItem("skew_region") || ""; } catch { return ""; }
  });

  const hasSR = !!getSpeechRecognition();
  const hasTTS = typeof window !== "undefined" && "speechSynthesis" in window;

  const wsRef = useRef(null);
  const recogRef = useRef(null);
  const speakingRef = useRef(false);
  const speakPhaseRef = useRef("normal"); // 'greeting' | 'normal'
  const ttsStartedAtRef = useRef(0);
  const bargeStreakRef = useRef(0);
  const audioCtxRef = useRef(null);
  const analyserRef = useRef(null);
  const micStreamRef = useRef(null);
  const bargeRafRef = useRef(null);
  const transcriptEndRef = useRef(null);
  const transcriptScrollRef = useRef(null);
  const intentionalCloseRef = useRef(false);
  const callEndedRef = useRef(false);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef(null);
  const activeWsUrlRef = useRef(null);
  const interactionIdRef = useRef(null);
  const turnSeqRef = useRef(0);
  const speakWatchdogRef = useRef(null);
  const lastAgentTextRef = useRef("");
  const listenReadyAtRef = useRef(0);
  const bargeRecoverRef = useRef(false);
  const speakQueueRef = useRef([]);
  const drainingSpeakRef = useRef(false);
  const sttBufferRef = useRef({ text: "", at: 0 });
  const sttFlushTimerRef = useRef(null);
  const recogRestartTimerRef = useRef(null);
  const lastInterimRef = useRef({ text: "", at: 0 });
  const thinkingTimeoutRef = useRef(null);
  const stateRef = useRef(CALL_STATE.IDLE);
  const wsSeqRef = useRef(0);
  const callStartRef = useRef(0);
  const callTimerRef = useRef(null);
  const callGenRef = useRef(0);
  const mutedRef = useRef(false);
  const voiceDeniedRef = useRef(false);
  const utteranceSeqRef = useRef(0);
  const currentUtteranceRef = useRef(null);
  const humanControlRef = useRef(false);
  const controlGenRef = useRef(0);
  const pendingTerminalRef = useRef(null);
  const turnQueueRef = useRef(createTurnQueue());
  const pendingTurnRef = useRef(null);
  const playbackRef = useRef({ status: "", text: "", utteranceId: "" });
  const socketLiveRef = useRef({ open: false, authenticated: false, attached: false });
  // Resolved STT/TTS path for this call ({ stt: server|browser|text, tts: server|browser|none }).
  const voiceModeRef = useRef({ stt: "browser", tts: "browser" });
  const mediaRecorderRef = useRef(null);
  const serverChunksRef = useRef([]);
  const serverCaptureRef = useRef({ active: false, voiced: false, lastVoiceAt: 0, startedAt: 0, stopTimer: null, mime: "" });
  const agentAudioRef = useRef(null);
  const pendingAgentAudioRef = useRef(new Map());
  const audioWaitRef = useRef({ timer: null, token: 0 });
  const listeningSinceRef = useRef(0);
  const [voiceDenied, setVoiceDenied] = useState(false);
  const [humanControl, setHumanControl] = useState(false);
  useEffect(() => {
    stateRef.current = state;
  }, [state]);
  useEffect(() => {
    if (state === CALL_STATE.IDLE || state === CALL_STATE.ENDED) {
      return undefined;
    }
    if (!callStartRef.current) callStartRef.current = Date.now();
    const id = window.setInterval(() => {
      setCallSecs(Math.floor((Date.now() - callStartRef.current) / 1000));
    }, 1000);
    callTimerRef.current = id;
    return () => {
      window.clearInterval(id);
      if (callTimerRef.current === id) callTimerRef.current = null;
    };
  }, [state]);

  function packLocale() {
    return reportLocaleRef.current;
  }
  function newTurnId() {
    try {
      if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
    } catch { /* ignore */ }
    return `t_${Date.now().toString(36)}_${Math.floor(Math.random() * 1e6)}`;
  }

  function clearSpeakWatchdog() {
    if (speakWatchdogRef.current) {
      clearTimeout(speakWatchdogRef.current);
      speakWatchdogRef.current = null;
    }
  }

  /**
   * Recovery if the TTS engine never fires onend/onerror (throttled tab,
   * headset switch, dropped utterance). Without this the call wedges in
   * AGENT_SPEAKING with the mic gated off forever.
   */
  function armSpeakWatchdog(full) {
    clearSpeakWatchdog();
    if (typeof window === "undefined") return;
    const ms = Math.min(
      45000,
      Math.max(10000, 6000 + String(full || "").length * 120),
    );
    speakWatchdogRef.current = window.setTimeout(() => {
      speakWatchdogRef.current = null;
      if (!speakingRef.current) return;
      try {
        window.speechSynthesis.cancel();
      } catch {
        /* ignore */
      }
      stopAgentAudio();
      clearAudioWait();
      speakingRef.current = false;
      speakPhaseRef.current = "normal";
      setSpeakPhase("normal");
      drainingSpeakRef.current = false;
      speakQueueRef.current = [];
      if (finalizePendingTerminal()) return;
      armListenCooldown();
      setInfo("Voice output stalled — mic is live, keep speaking or type below");
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        setState(CALL_STATE.LISTENING);
        startRecognitionSafe();
      }
    }, ms);
  }

  function pickVoice(lang) {
    try {
      return pickBestVoice(
        window.speechSynthesis.getVoices() || [],
        lang || packLocale() || "en-US",
        getPreferredVoiceURI()
      );
    } catch {
      return null;
    }
  }

  function markCallTerminal() {
    // Prevent onclose reconnect from treating a normal server hangup as a drop.
    callGenRef.current += 1;
    intentionalCloseRef.current = true;
    callEndedRef.current = true;
    activeWsUrlRef.current = null;
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (thinkingTimeoutRef.current) {
      clearTimeout(thinkingTimeoutRef.current);
      thinkingTimeoutRef.current = null;
    }
  }

  function finalizePendingTerminal() {
    if (!pendingTerminalRef.current) return false;
    const summary = pendingTerminalRef.current;
    pendingTerminalRef.current = null;
    markCallTerminal();
    setEnded(summary);
    setState(CALL_STATE.ENDED);
    setWsStatus("disconnected");
    cleanupCall();
    closeWsQuietly();
    return true;
  }

  /** Ask the server to finalize the contact (REST path, works with no socket). */
  function releaseInteraction() {
    const iid = interactionIdRef.current;
    if (!iid) return;
    interactionIdRef.current = null;
    fetch(`/api/interactions/${iid}/end`, {
      method: "POST",
      headers: apiHeaders(),
    }).catch(() => {});
  }

  function closeWsQuietly() {
    try {
      wsRef.current?.close();
    } catch {
      /* ignore */
    }
  }

  function pushTurn(entry) {
    turnSeqRef.current += 1;
    const withId = { ...entry, id: entry.id || `t${turnSeqRef.current}` };
    setTranscript((t) => mergeTranscriptTurn(t, withId));
    if (!entry.interim) setTurnCount((n) => n + 1);
  }

  function stopRecognition() {
    stopServerCapture(true);
    try {
      recogRef.current?.stop();
    } catch {
      /* ignore */
    }
  }

  function clearThinkingTimeout() {
    if (thinkingTimeoutRef.current) {
      clearTimeout(thinkingTimeoutRef.current);
      thinkingTimeoutRef.current = null;
    }
  }

  function enterThinking() {
    // Mic pauses while the server works so background noise during the
    // 5-10s enrichment window cannot pile up duplicate user_turns.
    stopRecognition();
    setState(CALL_STATE.THINKING);
    clearThinkingTimeout();
    thinkingTimeoutRef.current = window.setTimeout(() => {
      thinkingTimeoutRef.current = null;
      if (callEndedRef.current || intentionalCloseRef.current) return;
      if (stateRef.current !== CALL_STATE.THINKING) return;
      setInfo("Still working — if the agent stays quiet, speak or type again");
      setState(CALL_STATE.LISTENING);
      startRecognitionSafe();
    }, 12000);
  }

  function startRecognitionSafe() {
    if (textOnlyRef.current) return;
    if (mutedRef.current || voiceDeniedRef.current) return;
    if (callEndedRef.current || pendingTerminalRef.current) return;
    if (speakingRef.current) return;
    if (drainingSpeakRef.current) return;
    if (stateRef.current === CALL_STATE.THINKING) return;
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    const now = Date.now();
    if (listenReadyAtRef.current && now < listenReadyAtRef.current) {
      const wait = listenReadyAtRef.current - now;
      if (recogRestartTimerRef.current) clearTimeout(recogRestartTimerRef.current);
      recogRestartTimerRef.current = window.setTimeout(() => {
        recogRestartTimerRef.current = null;
        startRecognitionSafe();
      }, wait + 20);
      return;
    }
    if (recogRestartTimerRef.current) {
      clearTimeout(recogRestartTimerRef.current);
      recogRestartTimerRef.current = null;
    }
    if (voiceModeRef.current.stt === "server") {
      // Server STT owns segmentation (VAD tick); the interim debounce below is browser-only.
      startServerCapture();
      return;
    }
    if (!recogRef.current) return;
    try {
      recogRef.current.start();
    } catch {
      /* already started */
    }
    if (!listeningSinceRef.current) listeningSinceRef.current = Date.now();
    scheduleSpeechDecision();
  }

  function armListenCooldown() {
    listenReadyAtRef.current = Date.now() + POST_TTS_COOLDOWN_MS;
  }

  function scheduleSpeechDecision() {
    if (sttFlushTimerRef.current) clearTimeout(sttFlushTimerRef.current);
    const now = Date.now();
    const latest = Math.max(
      Number(sttBufferRef.current && sttBufferRef.current.at) || 0,
      Number(lastInterimRef.current && lastInterimRef.current.at) || 0,
    );
    const wait = latest
      ? Math.max(40, STT_FINAL_DEBOUNCE_MS - (now - latest))
      : Math.min(STT_FINAL_DEBOUNCE_MS, IDLE_LISTEN_REPROMPT_MS);
    sttFlushTimerRef.current = window.setTimeout(() => {
      sttFlushTimerRef.current = null;
      if (callEndedRef.current || intentionalCloseRef.current) return;
      const decision = decideSpeechFinal({
        lastSpeechAt: Math.max(
          Number(sttBufferRef.current && sttBufferRef.current.at) || 0,
          Number(lastInterimRef.current && lastInterimRef.current.at) || 0,
        ),
        lastInterimAt: Number(lastInterimRef.current && lastInterimRef.current.at) || 0,
        committedAt: Number(sttBufferRef.current && sttBufferRef.current.at) || 0,
        now: Date.now(),
        debounceMs: STT_FINAL_DEBOUNCE_MS,
        idleRepromptMs: IDLE_LISTEN_REPROMPT_MS,
        listeningSince: listeningSinceRef.current || 0,
      });
      if (decision.flush) {
        flushCustomerUtterance();
        return;
      }
      if (decision.reprompt && stateRef.current === CALL_STATE.LISTENING) {
        setInfo("I'm still listening — go ahead when you're ready");
        listeningSinceRef.current = Date.now();
        return;
      }
      if (decision.reason === "interim" || decision.reason === "waiting") {
        scheduleSpeechDecision();
      }
    }, wait);
  }

  function notePlayback(status, text, utteranceId) {
    const next = advancePlayback(playbackRef.current, {
      status,
      text,
      utteranceId: utteranceId || "",
    });
    playbackRef.current = next;
    sendWs({
      type: "playback",
      status: next.status,
      text: next.text,
      utterance_id: next.utteranceId,
    });
  }

  function flushCustomerUtterance() {
    if (mutedRef.current || voiceDeniedRef.current) {
      if (sttFlushTimerRef.current) {
        clearTimeout(sttFlushTimerRef.current);
        sttFlushTimerRef.current = null;
      }
      sttBufferRef.current = { text: "", at: 0 };
      lastInterimRef.current = { text: "", at: 0 };
      return;
    }
    if (sttFlushTimerRef.current) {
      clearTimeout(sttFlushTimerRef.current);
      sttFlushTimerRef.current = null;
    }
    const buf = sttBufferRef.current;
    sttBufferRef.current = { text: "", at: 0 };
    // Single-word answers ("yes") often arrive as interim only and would be
    // lost forever — promote the last interim to a final on flush.
    const fallback = lastInterimRef.current && lastInterimRef.current.text
      ? lastInterimRef.current.text
      : "";
    lastInterimRef.current = { text: "", at: 0 };
    const raw = (buf && buf.text ? buf.text : "") || fallback;
    const text = raw.replace(/\s+/g, " ").trim();
    if (!text) return;
    if (looksLikeAgentEcho(text, lastAgentTextRef.current)) {
      setInfo("Ignored speaker echo — say your answer after the agent finishes");
      return;
    }
    const pending = pendingTurnRef.current;
    let turnId;
    if (pending && pending.text === text && !pending.accepted && pending.turnId) {
      turnId = pending.turnId;
    } else {
      wsSeqRef.current += 1;
      turnId = newTurnId();
    }
    const queued = turnQueueRef.current.submit(turnId, text);
    if (queued.status === "rejected") {
      setError("That turn could not be queued");
      return;
    }
    if (queued.status === "duplicate" && queued.accepted) {
      return;
    }
    const sent = sendWs({
      type: "user_turn", text, final: true,
      turn_id: turnId, turn_seq: wsSeqRef.current,
      // Web Speech exposes confidence for an entire phrase, not for a vehicle
      // slot. Do not send it: older API servers treated it as entity_1 and
      // looped on a confirmation of every partial phrase.
      locale: packLocale(),
      region: (region || "").trim() || undefined,
      drive_hint: driving || undefined,
    });
    pendingTurnRef.current = { turnId, text, accepted: false };
    if (!sent) {
      setError("Connection was lost before your reply could be sent. Please reconnect and try again.");
      setState(CALL_STATE.LISTENING);
      startRecognitionSafe();
      return;
    }
    pushTurn({ speaker: "customer", text });
    listeningSinceRef.current = 0;
    // Mic pauses here. Acceptance waits for the server turn_result.
    enterThinking();
  }

  function queueCustomerFinal(txt) {
    const piece = String(txt || "").trim();
    const prev = String((sttBufferRef.current && sttBufferRef.current.text) || "").trim();
    if (piece && prev === piece) return;
    const { buffer } = coalesceSpeechFinals(sttBufferRef.current, txt, Date.now(), STT_FINAL_DEBOUNCE_MS);
    sttBufferRef.current = buffer;
    scheduleSpeechDecision();
  }

  /**
   * Server-STT capture: bounded PCM WAV, or negotiated MediaRecorder fallback,
   * uploaded once per utterance. Calibrated voice activity ends capture after
   * ~900ms trailing silence or 30 seconds. Silence alone never sends.
   */
  function startServerCapture() {
    const cap = serverCaptureRef.current;
    if (cap.active) return;
    const stream = micStreamRef.current;
    if (!stream || (!pcmRecorderRef.current && typeof MediaRecorder === "undefined")) {
      if (recogRef.current) {
        try { recogRef.current.start(); } catch { /* already started */ }
      } else {
        setInfo("Microphone unavailable — type your reply below");
      }
      return;
    }
    let mime = "";
    const usePcm = !!pcmRecorderRef.current && (!acceptedMimeRef.current || acceptedMimeRef.current.includes("audio/wav"));
    try {
      mime = usePcm ? "audio/wav" : recordingMime(m => MediaRecorder.isTypeSupported(m) && (!acceptedMimeRef.current || acceptedMimeRef.current.includes(m.split(";")[0])));
    } catch { mime = ""; }
    let rec = null;
    if (!mime) { setInfo("No mutually supported recording format. Type your reply below."); return; }
    try {
      if (!usePcm) rec = new MediaRecorder(stream, { mimeType: mime });
    } catch {
      setInfo("Voice capture failed in this browser — type your reply below");
      return;
    }
    serverChunksRef.current = [];
    const captureId = (cap.captureId || 0) + 1;
    cap.captureId = captureId;
    cap.active = true;
    cap.voiced = usePcm && preRollPendingRef.current;
    cap.lastVoiceAt = cap.voiced ? Date.now() : 0;
    cap.startedAt = Date.now();
    cap.lastPromptAt = cap.startedAt;
    cap.pcm = usePcm;
    cap.mime = (rec?.mimeType || mime).split(";")[0];
    if (rec) {
      rec.ondataavailable = (ev) => { if (cap.captureId === captureId && ev.data && ev.data.size) serverChunksRef.current.push(ev.data); };
      rec.onstop = () => { if (cap.captureId === captureId) finishServerCapture(); };
      rec.onerror = () => { if (cap.captureId === captureId) stopServerCapture(true); };
    }
    mediaRecorderRef.current = rec;
    try {
      if (usePcm) { pcmRecorderRef.current.start(preRollPendingRef.current); preRollPendingRef.current = false; }
      else rec.start(250);
    } catch {
      stopServerCapture(true);
      return;
    }
    if (!listeningSinceRef.current) listeningSinceRef.current = Date.now();
    const tick = () => {
      const c = serverCaptureRef.current;
      if (!c.active) return;
      const analyser = analyserRef.current;
      let rms = 0;
      if (analyser) {
        const data = new Uint8Array(analyser.frequencyBinCount);
        analyser.getByteTimeDomainData(data);
        let sum = 0;
        for (let i = 0; i < data.length; i += 8) {
          const v = (data[i] - 128) / 128;
          sum += v * v;
        }
        rms = Math.sqrt(sum / (data.length / 8));
      }
      const now = Date.now();
      const activity = voiceActivity(rms, noiseFloorRef.current);
      noiseFloorRef.current = activity.noiseFloor;
      if (activity.voiced) {
        c.voiced = true;
        c.lastVoiceAt = now;
      }
      const silenceMs = c.voiced ? now - c.lastVoiceAt : 0;
      const elapsed = now - c.startedAt;
      if (!c.voiced && now - c.lastPromptAt >= IDLE_LISTEN_REPROMPT_MS && stateRef.current === CALL_STATE.LISTENING) {
        setInfo("I'm still listening — go ahead when you're ready");
        c.lastPromptAt = now;
      }
      if ((c.voiced && silenceMs >= SERVER_CAPTURE_SILENCE_MS) || elapsed >= SERVER_CAPTURE_MAX_MS) {
        stopServerCapture(false);
        return;
      }
      c.stopTimer = window.setTimeout(tick, 120);
    };
    cap.stopTimer = window.setTimeout(tick, 120);
  }

  /** Stop capture. cancel=true discards (barge/mute/speak); false finalizes + sends. */
  function stopServerCapture(cancel) {
    const cap = serverCaptureRef.current;
    if (cap.stopTimer) {
      clearTimeout(cap.stopTimer);
      cap.stopTimer = null;
    }
    const rec = mediaRecorderRef.current;
    mediaRecorderRef.current = null;
    if (cap.pcm && cap.active) {
      if (cancel) { pcmRecorderRef.current?.cancel(); cap.active = false; serverChunksRef.current = []; }
      else finishServerCapture();
      return;
    }
    if (!rec || !cap.active) {
      cap.active = false;
      return;
    }
    if (cancel) {
      cap.active = false;
      serverChunksRef.current = [];
      try {
        if (rec.state !== "inactive") rec.stop();
      } catch { /* ignore */ }
      return;
    }
    try {
      if (rec.state !== "inactive") rec.stop();
      else finishServerCapture();
    } catch {
      cap.active = false;
    }
  }

  function restartServerListen() {
    if (callEndedRef.current || pendingTerminalRef.current) return;
    if (stateRef.current !== CALL_STATE.LISTENING) return;
    startRecognitionSafe();
  }

  function finishServerCapture() {
    const cap = serverCaptureRef.current;
    const wasActive = cap.active;
    cap.active = false;
    if (cap.stopTimer) {
      clearTimeout(cap.stopTimer);
      cap.stopTimer = null;
    }
    mediaRecorderRef.current = null;
    let chunks = serverChunksRef.current;
    if (cap.pcm) {
      try { const wav = pcmRecorderRef.current?.finish(); chunks = wav ? [new Blob([wav], { type: "audio/wav" })] : []; }
      catch { chunks = []; setInfo("Audio capture could not be finalized; type your report instead."); }
    }
    serverChunksRef.current = [];
    if (!wasActive || callEndedRef.current || pendingTerminalRef.current) return;
    if (!cap.voiced || !chunks.length) {
      restartServerListen();
      return;
    }
    let blob = null;
    try {
      blob = new Blob(chunks, { type: cap.mime || "audio/webm" });
    } catch {
      restartServerListen();
      return;
    }
    if (!blob.size || blob.size > SERVER_AUDIO_MAX_BYTES) {
      setInfo("That reply was too long — try a shorter answer");
      restartServerListen();
      return;
    }
    const reader = new FileReader();
    const generation = callGenRef.current, sourceInteraction = interactionIdRef.current, sourceCapture = cap.captureId;
    reader.onload = () => {
      if (generation !== callGenRef.current || sourceInteraction !== interactionIdRef.current || sourceCapture !== serverCaptureRef.current.captureId || callEndedRef.current) return;
      const url = String(reader.result || "");
      const b64 = url.includes(",") ? url.split(",", 2)[1] : "";
      if (!b64) {
        restartServerListen();
        return;
      }
      sendUserAudio(b64, cap.mime || "audio/webm");
    };
    reader.onerror = () => { restartServerListen(); };
    try {
      reader.readAsDataURL(blob);
    } catch {
      restartServerListen();
    }
  }

  function sendUserAudio(b64, mime) {
    if (mutedRef.current || voiceDeniedRef.current) return;
    if (callEndedRef.current || pendingTerminalRef.current) return;
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError("Connection was lost before your reply could be sent. Please reconnect and try again.");
      setState(CALL_STATE.LISTENING);
      startRecognitionSafe();
      return;
    }
    wsSeqRef.current += 1;
    const turnId = newTurnId();
    const queued = turnQueueRef.current.submit(turnId, "[voice]");
    if (queued.status === "rejected") {
      setError("That turn could not be queued");
      return;
    }
    const sent = sendWs(userAudioFrame({
      audio: b64,
      mime,
      turnId,
      turnSeq: wsSeqRef.current,
      locale: packLocale(),
      region: (region || "").trim() || undefined,
      driving: driving || undefined,
    }));
    pendingTurnRef.current = { turnId, text: "", audio: b64, mime, accepted: false };
    if (!sent) {
      setError("Connection was lost before your reply could be sent. Please reconnect and try again.");
      setState(CALL_STATE.LISTENING);
      startRecognitionSafe();
      return;
    }
    listeningSinceRef.current = 0;
    enterThinking();
  }

  function stopAgentAudio() {
    const el = agentAudioRef.current;
    agentAudioRef.current = null;
    if (el) {
      try { el.pause(); } catch { /* ignore */ }
      try { el.removeAttribute("src"); } catch { /* ignore */ }
    }
  }

  function clearAudioWait() {
    const wait = audioWaitRef.current;
    audioWaitRef.current = { timer: null, token: 0 };
    if (wait && wait.timer) {
      try { clearTimeout(wait.timer); } catch { /* ignore */ }
    }
  }

  function revokePendingAgentAudio() {
    const cache = pendingAgentAudioRef.current;
    cache.forEach((entry) => {
      try { URL.revokeObjectURL(entry.url); } catch { /* ignore */ }
    });
    cache.clear();
  }

  /** Hold an `agent_audio` frame until its utterance starts (usually already waiting). */
  function cacheAgentAudio(msg) {
    const b64 = msg && msg.audio;
    if (!b64 || typeof b64 !== "string") return;
    const key = String((msg && (msg.utterance_id || msg.turn_id)) || "");
    let url = null;
    try {
      const bin = atob(b64);
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      const blob = new Blob([bytes], { type: msg.mime || "audio/mpeg" });
      url = URL.createObjectURL(blob);
    } catch {
      return;
    }
    const wait = audioWaitRef.current;
    if (wait && wait.timer && String(wait.key || "") === key && wait.token === utteranceSeqRef.current) {
      clearTimeout(wait.timer);
      audioWaitRef.current = { timer: null, token: 0 };
      playAgentAudio(url, wait.full, wait.phase, wait.meta, wait.token, wait.finishSpeaking);
      return;
    }
    if (key) {
      const cache = pendingAgentAudioRef.current;
      cache.set(key, { url, at: Date.now() });
      while (cache.size > 5) {
        const oldest = cache.keys().next().value;
        try { URL.revokeObjectURL(cache.get(oldest).url); } catch { /* ignore */ }
        cache.delete(oldest);
      }
    } else {
      try { URL.revokeObjectURL(url); } catch { /* ignore */ }
    }
  }

  function playAgentAudio(url, full, phase, meta, token, finishSpeaking) {
    if (token !== utteranceSeqRef.current) {
      try { URL.revokeObjectURL(url); } catch { /* ignore */ }
      return;
    }
    stopAgentAudio();
    const fallBack = () => {
      agentAudioRef.current = null;
      try { URL.revokeObjectURL(url); } catch { /* ignore */ }
      speakWithBrowserTts(full, phase, meta, token, finishSpeaking);
    };
    let el = null;
    try {
      el = new Audio(url);
    } catch {
      fallBack();
      return;
    }
    agentAudioRef.current = el;
    el.onplay = () => {
      if (token !== utteranceSeqRef.current) return;
      ttsStartedAtRef.current = Date.now();
      bargeStreakRef.current = 0;
      notePlayback("started", full, meta.utteranceId || null);
      if (phase !== "greeting") {
        startBargeWatch();
      }
    };
    el.onended = () => {
      try { URL.revokeObjectURL(url); } catch { /* ignore */ }
      if (agentAudioRef.current === el) agentAudioRef.current = null;
      notePlayback("completed", full, meta.utteranceId || null);
      finishSpeaking();
    };
    el.onerror = () => {
      if (token !== utteranceSeqRef.current) return;
      fallBack();
    };
    try {
      const p = el.play();
      if (p && p.catch) {
        p.catch(() => {
          if (token !== utteranceSeqRef.current) return;
          fallBack();
        });
      }
    } catch {
      fallBack();
      return;
    }
    if (phase !== "greeting" && !ttsStartedAtRef.current) {
      ttsStartedAtRef.current = Date.now();
      startBargeWatch();
    }
  }

  function waitForServerAudio(full, phase, meta, token, finishSpeaking) {
    const key = meta.utteranceId || null;
    const cached = key ? pendingAgentAudioRef.current.get(key) : null;
    if (cached) {
      pendingAgentAudioRef.current.delete(key);
      playAgentAudio(cached.url, full, phase, meta, token, finishSpeaking);
      return;
    }
    const timer = window.setTimeout(() => {
      audioWaitRef.current = { timer: null, token: 0 };
      if (token !== utteranceSeqRef.current) return;
      // Server audio never arrived: speak locally rather than wedge the call.
      speakWithBrowserTts(full, phase, meta, token, finishSpeaking);
    }, SERVER_AUDIO_WAIT_MS);
    audioWaitRef.current = { timer, token, key: key || "", full, phase, meta, finishSpeaking };
  }

  /**
   * Speak agent text. opts.phase === 'greeting' disables barge-in so speaker
   * bleed cannot cancel the pack greeting mid-word ("than" from "Thanks").
   * Queue later agent turns instead of cancel+speak — Chrome drops the next
   * question when cancel and speak run back-to-back.
   */
  function enqueueSpeak(text, opts = {}) {
    const full = greetingSpeakText(text);
    if (!full) return;
    if (textOnlyRef.current) {
      if (!finalizePendingTerminal() && !callEndedRef.current) setState(CALL_STATE.LISTENING);
      return;
    }
    const speaker = opts.speaker || "agent";
    if (humanControlRef.current && speaker !== "supervisor") return;
    lastAgentTextRef.current = full;
    notePlayback("queued", full, opts.utteranceId || null);
    speakQueueRef.current.push({
      full,
      phase: opts.phase || "normal",
      speaker,
      utteranceId: opts.utteranceId || null,
    });
    if (!drainingSpeakRef.current && !speakingRef.current) {
      drainSpeakQueue();
    }
  }

  function drainSpeakQueue() {
    const next = speakQueueRef.current.shift();
    if (!next) {
      drainingSpeakRef.current = false;
      if (finalizePendingTerminal()) return;
      armListenCooldown();
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN && !humanControlRef.current) {
        setState(CALL_STATE.LISTENING);
        startRecognitionSafe();
      } else if (humanControlRef.current && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        setState(CALL_STATE.LISTENING);
        startRecognitionSafe();
      }
      return;
    }
    drainingSpeakRef.current = true;
    speakNow(next.full, next.phase, next);
  }

  function speakNow(full, phase, meta = {}) {
    const token = ++utteranceSeqRef.current;
    currentUtteranceRef.current = meta.utteranceId || null;
    speakPhaseRef.current = phase;
    setSpeakPhase(phase);
    bargeStreakRef.current = 0;
    const serverTts = voiceModeRef.current.tts === "server" && typeof Audio !== "undefined";

    if (!hasTTS && !serverTts) {
      notePlayback("failed", full, meta.utteranceId || null);
      clearSpeakWatchdog();
      speakingRef.current = false;
      speakPhaseRef.current = "normal";
      setSpeakPhase("normal");
      drainSpeakQueue();
      return;
    }
    speakingRef.current = true;
    setState(CALL_STATE.AGENT_SPEAKING);
    stopRecognition();
    armSpeakWatchdog(full);

    const finishSpeaking = () => {
      if (token !== utteranceSeqRef.current) return;
      clearSpeakWatchdog();
      speakingRef.current = false;
      speakPhaseRef.current = "normal";
      setSpeakPhase("normal");
      bargeStreakRef.current = 0;
      if (bargeRafRef.current) {
        cancelAnimationFrame(bargeRafRef.current);
        bargeRafRef.current = null;
      }
      drainSpeakQueue();
    };

    if (serverTts && phase !== "greeting" && responseSpeechLocale(full, packLocale()) !== "hi-IN") {
      // The REST greeting has no server audio; everything else prefers it.
      waitForServerAudio(full, phase, meta, token, finishSpeaking);
      return;
    }
    speakWithBrowserTts(full, phase, meta, token, finishSpeaking);
  }

  function speakWithBrowserTts(full, phase, meta, token, finishSpeaking) {
    if (token !== utteranceSeqRef.current) return;
    if (!hasTTS) {
      notePlayback("failed", full, meta.utteranceId || null);
      finishSpeaking();
      return;
    }
    window.setTimeout(() => {
      if (token !== utteranceSeqRef.current) return;
      if (!speakingRef.current) return;
      const u = new SpeechSynthesisUtterance(full);
      u.rate = 0.98;
      u.pitch = 1;
      const speakLang = responseSpeechLocale(full, packLocale());
      try { u.lang = speakLang; } catch { u.lang = "en-US"; }
      const voice = pickVoice(speakLang);
      if (voice) {
        u.voice = voice;
        if (voice.lang) {
          try { u.lang = voice.lang; } catch { /* keep pack locale */ }
        }
      }
      u.onstart = () => {
        if (token !== utteranceSeqRef.current) return;
        ttsStartedAtRef.current = Date.now();
        bargeStreakRef.current = 0;
        notePlayback("started", full, meta.utteranceId || null);
        if (phase !== "greeting") {
          startBargeWatch();
        }
      };
      u.onend = () => {
        notePlayback("completed", full, meta.utteranceId || null);
        finishSpeaking();
      };
      u.onerror = () => {
        notePlayback("failed", full, meta.utteranceId || null);
        finishSpeaking();
      };
      try {
        window.speechSynthesis.speak(u);
      } catch {
        finishSpeaking();
      }
      if (phase !== "greeting" && !ttsStartedAtRef.current) {
        ttsStartedAtRef.current = Date.now();
        startBargeWatch();
      }
    }, 60);
  }

  function cancelAiSpeech() {
    notePlayback("interrupted", playbackRef.current.text, currentUtteranceRef.current);
    utteranceSeqRef.current += 1;
    currentUtteranceRef.current = null;
    speakQueueRef.current = speakQueueRef.current.filter((item) => item.speaker === "supervisor");
    clearSpeakWatchdog();
    stopAgentAudio();
    clearAudioWait();
    if (hasTTS) {
      try { window.speechSynthesis.cancel(); } catch { /* ignore */ }
    }
    speakingRef.current = false;
    drainingSpeakRef.current = false;
    speakPhaseRef.current = "normal";
    setSpeakPhase("normal");
    if (bargeRafRef.current) {
      cancelAnimationFrame(bargeRafRef.current);
      bargeRafRef.current = null;
    }
    if (speakQueueRef.current.length) {
      drainSpeakQueue();
    } else {
      if (finalizePendingTerminal()) return;
      if (!callEndedRef.current && !mutedRef.current) {
        listenReadyAtRef.current = Date.now();
        setState(CALL_STATE.LISTENING);
        startRecognitionSafe();
      }
    }
  }

  function interruptPlayback() {
    if (!speakingRef.current && !drainingSpeakRef.current) return;
    sendWs({ type: "barge_in", elapsed_ms: Math.max(0, Date.now() - (ttsStartedAtRef.current || Date.now())),
      utterance_id: currentUtteranceRef.current || undefined });
    // Explicit interruption cancels all queued playback, including a specialist.
    speakQueueRef.current = [];
    cancelAiSpeech();
    if (!callEndedRef.current) {
      setState(CALL_STATE.LISTENING);
      setInfo("Playback stopped. Speak or type your correction.");
    }
  }

  function startBargeWatch() {
    // Explicit interruption is the default until device echo behavior is measured.
    if (!automaticInterruptRef.current) return;
    const ctx = audioCtxRef.current;
    const analyser = analyserRef.current;
    if (!ctx || !analyser) return;
    if (bargeRafRef.current) cancelAnimationFrame(bargeRafRef.current);
    const data = new Uint8Array(analyser.frequencyBinCount);
    const started = ttsStartedAtRef.current || Date.now();

    const tick = () => {
      if (!speakingRef.current) {
        bargeRafRef.current = null;
        bargeStreakRef.current = 0;
        return;
      }
      // Never barge during pack greeting.
      if (speakPhaseRef.current === "greeting") {
        bargeRafRef.current = requestAnimationFrame(tick);
        return;
      }
      analyser.getByteTimeDomainData(data);
      let sum = 0;
      for (let i = 0; i < data.length; i += 8) {
        const v = (data[i] - 128) / 128;
        sum += v * v;
      }
      const rms = Math.sqrt(sum / (data.length / 8));
      const elapsedMs = Date.now() - started;
      const high = rms >= 0.14;
      if (high) bargeStreakRef.current += 1;
      else bargeStreakRef.current = 0;

      if (
        shouldAllowBargeIn({
          phase: speakPhaseRef.current,
          elapsedMs,
          graceMs: BARGE_IN_GRACE_MS,
          rms,
          rmsThreshold: 0.14,
          highRmsStreak: bargeStreakRef.current,
          streakNeeded: 4,
        })
      ) {
        utteranceSeqRef.current += 1;
        try {
          window.speechSynthesis.cancel();
        } catch {
          /* ignore */
        }
        stopAgentAudio();
        clearAudioWait();
        clearSpeakWatchdog();
        speakingRef.current = false;
        speakPhaseRef.current = "normal";
        setSpeakPhase("normal");
        bargeStreakRef.current = 0;
        try {
          const elapsedMs = Date.now() - (ttsStartedAtRef.current || Date.now());
          sendWs({
            type: "barge_in",
            elapsed_ms: Math.max(0, elapsedMs),
            utterance_id: currentUtteranceRef.current || undefined,
          });
        } catch {
          sendWs({ type: "barge_in", utterance_id: currentUtteranceRef.current || undefined });
        }
        speakQueueRef.current = [];
        drainingSpeakRef.current = false;
        notePlayback("interrupted", playbackRef.current.text, currentUtteranceRef.current);
        // The words that stopped playback must not wait out the bleed cooldown.
        bargeRecoverRef.current = true;
        listenReadyAtRef.current = Date.now();
        setState(CALL_STATE.LISTENING);
        preRollPendingRef.current = voiceModeRef.current.stt === "server" && !!pcmRecorderRef.current;
        setInfo(preRollPendingRef.current ? "Playback stopped; keeping the start of your correction." : "Playback stopped. Browser recognition resumes now; repeat any words spoken before it stopped, or type the correction.");
        startRecognitionSafe();
        bargeRafRef.current = null;
        return;
      }
      bargeRafRef.current = requestAnimationFrame(tick);
    };
    bargeRafRef.current = requestAnimationFrame(tick);
  }

  function sendWs(obj) {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      try {
        ws.send(JSON.stringify(obj));
        return true;
      } catch {
        return false;
      }
    }
    return false;
  }

  function applyControl(msg) {
    const gen = Number(msg.generation || 0);
    if (gen && controlGenRef.current && gen < controlGenRef.current) return;
    if (gen) controlGenRef.current = gen;
    const supervised = msg.supervised === true || msg.state === "SUPERVISED";
    humanControlRef.current = supervised;
    setHumanControl(supervised);
    if (supervised) {
      setHandoffStatus("joined");
      cancelAiSpeech();
      setInfo("A human specialist has this call");
    } else {
      setHandoffStatus(previous => previous === "joined" ? "" : previous);
    }
  }

  function handleWsMessage(msg) {
    switch (msg.type) {
      case "agent_turn": {
        const speaker = msg.speaker || "agent";
        if (humanControlRef.current && speaker !== "supervisor") break;
        const agentText = greetingSpeakText(msg.text || "");
        clearThinkingTimeout();
        if (msg.drive_mode) setDriving(true);
        if (msg.consent_required) setConsent((c) => c || { script: agentText });
        // Safety escalation dominates the UI (Tier-B #13).
        try {
          const t = (agentText || "").toLowerCase();
          if (t.includes("safety specialist") || t.includes("emergency services")) {
            setSafetyMode(true);
          }
        } catch { /* ignore */ }
        pushTurn({ speaker, text: agentText });
        if (speaker === "supervisor") setInfo("A human specialist is responding");
        enqueueSpeak(agentText, {
          phase: msg.closing ? "normal" : "normal",
          speaker,
          utteranceId: msg.utterance_id || msg.turn_id || null,
        });
        break;
      }
      case "control_state": {
        applyControl(msg);
        break;
      }
      case "frustration": {
        try { setFrustration(Number(msg.value || 0)); } catch { /* ignore */ }
        break;
      }
      case "turn_latency": {
        try {
          setLatency({
            elapsed_ms: Number(msg.elapsed_ms || 0),
            over_budget: !!msg.over_budget,
            budget_ms: Number(msg.budget_ms || 1500),
          });
        } catch { /* ignore */ }
        break;
      }
      case "consent_required": {
        try {
          setConsent({ script: String(msg.script || ""), region: msg.region || "", version: msg.version || "" });
          setInfo("Recording consent required — say 'I consent' or tap Consent");
        } catch { /* ignore */ }
        break;
      }
      case "barge_in_reconciled": {
        try {
          setActivity({ agent: "voice_reconciler", action_type: "spoken_turn_truncated", summary: String(msg.audible_text || "[INTERRUPTED]") });
        } catch { /* ignore */ }
        break;
      }
      case "agent_audio": {
        if (!textOnlyRef.current) cacheAgentAudio(msg);
        break;
      }
      case "voice_fallback": {
        setInfo(msg.reason || "Speech playback fell back; the transcript remains available.");
        break;
      }
      case "heard_turn": {
        if (msg.text) pushTurn({ speaker: "customer", text: String(msg.text) });
        break;
      }
      case "stt_empty": {
        clearThinkingTimeout();
        setInfo("Didn't catch that — go ahead");
        setState(CALL_STATE.LISTENING);
        startRecognitionSafe();
        break;
      }
      case "ready": {
        socketLiveRef.current = {
          open: true,
          authenticated: msg.authenticated === true,
          attached: msg.attached === true,
        };
        if (socketIsLive(socketLiveRef.current)) setWsStatus("live");
        try {
          const sel = textOnlyRef.current ? { stt: "text", tts: "none" } : serverVoiceSelection({
            serverStt: !!(msg.voice && msg.voice.server_stt),
            serverTts: !!(msg.voice && msg.voice.server_tts),
            mediaRecorder: !!pcmRecorderRef.current || typeof MediaRecorder !== "undefined",
            audioElement: typeof Audio !== "undefined",
            hasSpeechRecognition: hasSR,
            hasSpeechSynthesis: hasTTS,
          });
          acceptedMimeRef.current = Array.isArray(msg.voice?.accepted_audio_mime) ? msg.voice.accepted_audio_mime : null;
          voiceModeRef.current = sel;
          setServerVoice({ ...msg.voice, stt: sel.stt === "server", tts: sel.tts === "server" });
        } catch {
          /* keep the browser path */
        }
        if (msg.unheard_prompt) {
          const unheard = String(msg.unheard_prompt);
          pushTurn({ speaker: "agent", text: unheard });
          enqueueSpeak(unheard);
        }
        const pending = pendingTurnRef.current;
        if (pending && pending.turnId && !pending.accepted) {
          if (pending.audio) {
            sendWs(userAudioFrame({
              audio: pending.audio,
              mime: pending.mime || "audio/webm",
              turnId: pending.turnId,
              turnSeq: wsSeqRef.current,
              locale: packLocale(),
              region: (region || "").trim() || undefined,
            }));
          } else {
            sendWs({
              type: "user_turn",
              text: pending.text,
              final: true,
              turn_id: pending.turnId,
              turn_seq: wsSeqRef.current,
              locale: packLocale(),
              region: (region || "").trim() || undefined,
            });
          }
        }
        break;
      }
      case "turn_result": {
        const ack = turnQueueRef.current.acknowledge(msg.turn_id, msg);
        if (pendingTurnRef.current && pendingTurnRef.current.turnId === msg.turn_id) {
          pendingTurnRef.current = { ...pendingTurnRef.current, accepted: ack.accepted === true };
        }
        if (msg.status === "rejected") {
          clearThinkingTimeout();
          setInfo(msg.reason || "That turn was not accepted — please say it again");
          setState(CALL_STATE.LISTENING);
          startRecognitionSafe();
          break;
        }
        if (speakingRef.current || stateRef.current === CALL_STATE.AGENT_SPEAKING) break;
        break;
      }
      case "duplicate_dropped": {
        // Proven replay (same turn_id seen twice) — stay live and ask for a
        // fresh turn instead of wedging in THINKING until the 12s timeout.
        clearThinkingTimeout();
        setState(CALL_STATE.LISTENING);
        setInfo("That turn arrived twice — please say it once more");
        startRecognitionSafe();
        break;
      }
      case "agent_activity": {
        if (msg.action_type === "handoff_unfulfilled") { setHandoff(true); setHandoffStatus("unavailable"); }
        if (msg.action_type === "handoff_accepted") { setHandoff(true); setHandoffStatus("queued"); }
        setActivity({
          agent: msg.agent,
          action_type: msg.action_type,
          summary: msg.summary || msg.output_summary || "",
        });
        try {
          if (msg.action_type === "supervisor_whisper") setInfo("Supervisor coaching live on console");
          if (msg.action_type === "drive_mode_detected") setDriving(true);
          if (msg.action_type === "vin_captured") setInfo(String(msg.summary || "VIN captured"));
        } catch { /* ignore */ }
        break;
      }
      case "slots_update": {
        setSlots(msg.slots || {});
        break;
      }
      case "handoff_offer": {
        setHandoff(true);
        setInfo("A supervisor can take over this contact");
        break;
      }
      case "interaction_ended": {
        // Server sends flat case_id / investigation_id — not nested payload.
        // Mark terminal BEFORE close so onclose does not reconnect / wipe summary.
        // Closing audio already queued is allowed to finish; user hangup still cancels.
        const summary = mapInteractionEnded(msg);
        markCallTerminal();
        interactionIdRef.current = null;
        stopRecognition();
        pendingTerminalRef.current = summary;
        setEnded(summary);
        if (!speakingRef.current && !drainingSpeakRef.current && speakQueueRef.current.length === 0) {
          pendingTerminalRef.current = null;
          setState(CALL_STATE.ENDED);
          setWsStatus("disconnected");
          cleanupCall();
          closeWsQuietly();
        }
        break;
      }
      case "resumed": {
        // Server accepted the re-attach. Its turn list is authoritative — we may
        // have missed turns while the socket was down.
        applyControl(msg);
        const rows = transcriptFromResume(msg.turns);
        if (rows) {
          setTranscript(rows);
          setTurnCount(rows.length);
          turnSeqRef.current = rows.length;
        }
        setError(null);
        setInfo("Reconnected — the contact is still live");
        socketLiveRef.current = { open: true, authenticated: true, attached: true };
        if (socketIsLive(socketLiveRef.current)) setWsStatus("live");
        break;
      }
      case "error": {
        if (isFatalWsError(msg)) {
          // Retrying cannot help: stop the reconnect loop and close out cleanly
          // instead of looping the raw "active interaction not found" detail.
          markCallTerminal();
          setError(fatalWsErrorMessage(msg));
          setInfo(null);
          setEnded((prev) => prev || { reason: "connection_lost" });
          setState(CALL_STATE.ENDED);
          setWsStatus("disconnected");
          cleanupCall();
          closeWsQuietly();
          break;
        }
        setError(msg.detail || msg.message || "Server error");
        break;
      }
      default:
        break;
    }
  }

  function cleanupCall() {
    utteranceSeqRef.current += 1;
    stopRecognition();
    stopAgentAudio();
    clearAudioWait();
    revokePendingAgentAudio();
    clearSpeakWatchdog();
    clearThinkingTimeout();
    if (sttFlushTimerRef.current) {
      clearTimeout(sttFlushTimerRef.current);
      sttFlushTimerRef.current = null;
    }
    if (recogRestartTimerRef.current) {
      clearTimeout(recogRestartTimerRef.current);
      recogRestartTimerRef.current = null;
    }
    speakQueueRef.current = [];
    drainingSpeakRef.current = false;
    pendingTerminalRef.current = null;
    sttBufferRef.current = { text: "", at: 0 };
    lastInterimRef.current = { text: "", at: 0 };
    if (bargeRafRef.current) cancelAnimationFrame(bargeRafRef.current);
    bargeRafRef.current = null;
    if (hasTTS) {
      try {
        window.speechSynthesis.cancel();
      } catch {
        /* ignore */
      }
    }
    speakingRef.current = false;
    pcmRecorderRef.current?.close();
    pcmRecorderRef.current = null;
    preRollPendingRef.current = false;
    setInputLevel(0);
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((t) => t.stop());
      micStreamRef.current = null;
    }
    if (audioCtxRef.current && audioCtxRef.current.state !== "closed") {
      audioCtxRef.current.close().catch(() => {});
    }
    audioCtxRef.current = null;
    analyserRef.current = null;
  }

  async function setupMic(gen) {
    let stream = null;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
      if (gen !== callGenRef.current || callEndedRef.current) {
        stream.getTracks().forEach((t) => t.stop());
        return false;
      }
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const src = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 512;
      src.connect(analyser);
      if (gen !== callGenRef.current || callEndedRef.current) {
        stream.getTracks().forEach((t) => t.stop());
        ctx.close().catch(() => {});
        return false;
      }
      micStreamRef.current = stream;
      audioCtxRef.current = ctx;
      analyserRef.current = analyser;
      try {
        pcmRecorderRef.current = createPcmRecorder(ctx, stream, { noiseFloor: noiseFloorRef.current,
          onLevel: ({ rms }) => setInputLevel(rms), onFull: () => { if (serverCaptureRef.current.active) stopServerCapture(false); } });
      } catch { /* MediaRecorder remains available without PCM pre-roll. */ }
      await ctx.resume();
      setMicGranted(true);
      return true;
    } catch {
      if (stream) stream.getTracks().forEach((t) => t.stop());
      if (gen !== callGenRef.current || callEndedRef.current) return false;
      setMicGranted(false);
      setInfo("Microphone blocked — use the text box to talk");
      return false;
    }
  }

  function retrySpeechInput() {
    voiceDeniedRef.current = false;
    setVoiceDenied(false);
    setError(null);
    setInfo("Trying speech recognition again");
    if (!recogRef.current) setupSpeechRecognition();
    if (stateRef.current === CALL_STATE.LISTENING && !pendingTerminalRef.current) {
      startRecognitionSafe();
    }
  }

  async function checkMicrophone() {
    setPreflight({ busy: true, note: "Keep quiet briefly while the microphone noise floor is measured. Audio stays on this device." });
    try {
      const result = await microphonePreflight(setInputLevel);
      noiseFloorRef.current = result.noiseFloor;
      setPreflight({ busy: false, note: `${result.device}: input samples received and quiet-room level recorded. This is a setup check, not speech-quality validation.` });
    } catch (error) { setPreflight({ busy: false, note: error.message || "Microphone unavailable. Type instead remains available." }); }
    finally { setInputLevel(0); }
  }

  function finishSpeaking() {
    if (serverCaptureRef.current.active) { serverCaptureRef.current.voiced = true; stopServerCapture(false); }
    else if (recogRef.current) { try { recogRef.current.stop(); } catch { /* recognition already stopped */ } }
  }

  function toggleMute() {
    const next = !mutedRef.current;
    mutedRef.current = next;
    setMuted(next);
    pcmRecorderRef.current?.mute(next);
    try {
      const tracks = (micStreamRef.current && micStreamRef.current.getAudioTracks()) || [];
      tracks.forEach((t) => { t.enabled = !next; });
    } catch { /* ignore */ }
    if (next) {
      if (sttFlushTimerRef.current) {
        clearTimeout(sttFlushTimerRef.current);
        sttFlushTimerRef.current = null;
      }
      if (recogRestartTimerRef.current) {
        clearTimeout(recogRestartTimerRef.current);
        recogRestartTimerRef.current = null;
      }
      sttBufferRef.current = { text: "", at: 0 };
      lastInterimRef.current = { text: "", at: 0 };
      setTranscript((rows) => (Array.isArray(rows) ? rows.filter((t) => !t.interim) : rows));
      stopRecognition();
    } else if (stateRef.current === CALL_STATE.LISTENING) startRecognitionSafe();
  }

  function setupSpeechRecognition() {
    if (textOnlyRef.current) return null;
    const SR = getSpeechRecognition();
    if (!SR) return null;
    const recog = new SR();
    recog.continuous = true;
    recog.interimResults = true;
    // [AI-LAYER] optional hi-IN / en-IN recognition override; unset = existing behaviour
    try { recog.lang = packLocale(); } catch { recog.lang = "en-US"; }
    recog.onresult = (ev) => {
      // While thinking the mic is paused — drop late STT so it cannot stack
      // a second user_turn behind the one the server is already answering.
      if (stateRef.current === CALL_STATE.THINKING) return;
      if (mutedRef.current || voiceDeniedRef.current) return;

      let interim = "";
      const finals = [];
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        const res = ev.results[i];
        const txt = (res[0].transcript || "").trim();
        if (!txt) continue;
        if (res.isFinal) finals.push(txt);
        else interim += (interim ? " " : "") + txt;
      }
      const sample = finals[0] || interim;
      const interrupting = bargeRecoverRef.current;
      const accept = shouldAcceptSpeechResult({
        speaking: speakingRef.current,
        wsOpen: !!(wsRef.current && wsRef.current.readyState === WebSocket.OPEN),
        listenReadyAt: listenReadyAtRef.current,
        now: Date.now(),
        text: sample,
        interrupting,
      });
      if (!accept) return;
      if (interrupting) bargeRecoverRef.current = false;

      for (const txt of finals) {
        if (looksLikeAgentEcho(txt, lastAgentTextRef.current)) continue;
        lastInterimRef.current = { text: "", at: 0 };
        queueCustomerFinal(txt);
      }
      if (interim && !looksLikeAgentEcho(interim, lastAgentTextRef.current)) {
        lastInterimRef.current = { text: interim, at: Date.now() };
        pushTurn({ speaker: "customer", text: interim, interim: true });
        scheduleSpeechDecision();
      }
    };
    recog.onerror = (e) => {
      if (e.error === "no-speech" || e.error === "aborted") return;
      if (e.error === "not-allowed" || e.error === "service-not-allowed") {
        voiceDeniedRef.current = true;
        setVoiceDenied(true);
        setMicGranted(false);
        setInfo("Speech recognition denied — type your replies below");
        stopRecognition();
        return;
      }
      setError(`Speech: ${e.error}`);
    };
    recog.onend = () => {
      if (mutedRef.current || voiceDeniedRef.current) return;
      if (speakingRef.current) return;
      if (speakPhaseRef.current === "greeting") return;
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
      if (intentionalCloseRef.current) return;
      if (stateRef.current === CALL_STATE.THINKING) {
        // A short answer ("yes") may end the session with only interim text
        // buffered — promote it to a final instead of dropping the turn.
        if (sttBufferRef.current.text || lastInterimRef.current.text) {
          flushCustomerUtterance();
        }
        return;
      }
      if (!sttBufferRef.current.text && lastInterimRef.current.text) {
        queueCustomerFinal(lastInterimRef.current.text);
        lastInterimRef.current = { text: "", at: 0 };
      }
      // Chrome may end a recognition session between pieces of one spoken
      // sentence. Keep the debounce window alive and restart recognition so
      // "my car has ... been stuck" becomes one turn, not two competing turns.
      if (recogRestartTimerRef.current) clearTimeout(recogRestartTimerRef.current);
      recogRestartTimerRef.current = window.setTimeout(() => {
        recogRestartTimerRef.current = null;
        startRecognitionSafe();
      }, RECOG_RESTART_MS);
    };
    recogRef.current = recog;
    return recog;
  }

  async function startCall({ textOnly: useText = false } = {}) {
    if (![CALL_STATE.IDLE, CALL_STATE.ENDED].includes(stateRef.current)) return;
    const gen = ++callGenRef.current;
    textOnlyRef.current = useText;
    reportLocaleRef.current = speechLocale(aiSpeechLang());
    automaticInterruptRef.current = automaticInterrupt;
    setTextOnly(useText);
    stateRef.current = CALL_STATE.CONNECTING;
    setError(null);
    setInfo(null);
    setTranscript([]);
    setInteractionId(null);
    interactionIdRef.current = null;
    setTextFallback("");
    setSlots({});
    setHandoff(false);
    setHandoffStatus("");
    setEnded(null);
    setActivity(null);
    setTurnCount(0);
    // A new report owns a new queue. Same-report reconnect still reuses it.
    turnQueueRef.current = createTurnQueue();
    pendingTurnRef.current = null;
    turnSeqRef.current = 0;
    wsSeqRef.current = 0;
    speakPhaseRef.current = "normal";
    setSpeakPhase("normal");
    setMicGranted(null);
    setServerVoice({ stt: false, tts: false });
    voiceModeRef.current = useText ? { stt: "text", tts: "none" } : { stt: "browser", tts: "browser" };
    revokePendingAgentAudio();
    clearAudioWait();
    setMuted(false);
    mutedRef.current = false;
    voiceDeniedRef.current = false;
    setVoiceDenied(false);
    humanControlRef.current = false;
    setHumanControl(false);
    controlGenRef.current = 0;
    pendingTerminalRef.current = null;
    callEndedRef.current = false;
    intentionalCloseRef.current = false;
    setDriving(false);
    setFrustration(0);
    setLatency(null);
    setConsent(null);
    setSafetyMode(false);
    setSurvey({ csat: 0, sent: false });
    callStartRef.current = Date.now();
    setCallSecs(0);
    sttBufferRef.current = { text: "", at: 0 };
    lastInterimRef.current = { text: "", at: 0 };
    if (thinkingTimeoutRef.current) {
      clearTimeout(thinkingTimeoutRef.current);
      thinkingTimeoutRef.current = null;
    }
    setWsStatus("connecting");
    setState(CALL_STATE.CONNECTING);

    // Ask for microphone access in parallel with contact creation. Waiting for
    // getUserMedia before opening the WebSocket made a permission prompt (or a
    // slow Bluetooth device) look like a slow connection.
    const micReady = useText ? Promise.resolve(false) : setupMic(gen);
    let startRes;
    try {
      try { localStorage.setItem("skew_region", region || ""); } catch { /* ignore */ }
      const qs = new URLSearchParams({ channel: useText ? "web_text" : "web_voice", locale: reportLocaleRef.current });
      if ((region || "").trim()) qs.set("region", region.trim());
      const signature = qs.toString();
      if (startRequestRef.current?.signature !== signature) startRequestRef.current = { signature, id: newTurnId() };
      const r = await fetch(`/api/interactions/start?${qs.toString()}`, {
        method: "POST",
        headers: apiHeaders({ "Idempotency-Key": startRequestRef.current.id }),
      });
      if (!r.ok) {
        const detail = await r.text().catch(() => "");
        throw new Error(`Could not start call (${r.status})${detail ? `: ${detail.slice(0, 120)}` : ""}`);
      }
      startRes = await r.json();
      startRequestRef.current = null;
    } catch (e) {
      if (gen !== callGenRef.current) return;
      setError(String(e.message || e));
      setState(CALL_STATE.IDLE);
      void micReady.then(() => cleanupCall());
      return;
    }
    if (gen !== callGenRef.current) {
      const staleId = startRes && startRes.interaction_id;
      if (staleId) {
        fetch(`/api/interactions/${encodeURIComponent(staleId)}/end`, {
          method: "POST",
          headers: apiHeaders(),
        }).catch(() => {});
      }
      return;
    }

    setInteractionId(startRes.interaction_id);
    interactionIdRef.current = startRes.interaction_id;
    setPack(startRes.pack || null);
    intentionalCloseRef.current = false;
    callEndedRef.current = false;
    reconnectAttemptRef.current = 0;

    // Warm up the TTS voice list inside the user gesture so the first
    // utterance is not dropped by engines that load voices lazily.
    try {
      if (hasTTS && !useText) {
        window.speechSynthesis.getVoices();
        window.speechSynthesis.onvoiceschanged = () => {
          try {
            window.speechSynthesis.getVoices();
          } catch {
            /* ignore */
          }
        };
      }
    } catch {
      /* ignore */
    }

    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${proto}//${window.location.host}${startRes.ws_url}`;
    activeWsUrlRef.current = wsUrl;

    function bindWs(ws, { isReconnect }) {
      const boundGen = gen;
      wsRef.current = ws;
      ws.onopen = () => {
        if (boundGen !== callGenRef.current) {
          try { ws.close(); } catch { /* ignore */ }
          return;
        }
        if (
          !shouldResumeListeningOnOpen({
            intentionalClose: intentionalCloseRef.current,
            callEnded: callEndedRef.current,
            isReconnect,
          }) &&
          isReconnect
        ) {
          // Call already ended while reconnect was queued — stay quiet.
          setWsStatus("disconnected");
          closeWsQuietly();
          return;
        }
        sendWsAuth(ws);
        socketLiveRef.current = { open: true, authenticated: false, attached: false };
        if (!socketIsLive(socketLiveRef.current)) setWsStatus("connecting");
        reconnectAttemptRef.current = 0;
        if (!isReconnect && startRes.greeting_text) {
          // Full pack greeting — transcript + TTS must match start response.
          const greet = greetingSpeakText(startRes.greeting_text);
          pushTurn({ speaker: "agent", text: greet });
          enqueueSpeak(greet, { phase: "greeting" });
        } else if (
          shouldResumeListeningOnOpen({
            intentionalClose: intentionalCloseRef.current,
            callEnded: callEndedRef.current,
            isReconnect: true,
          }) ||
          !isReconnect
        ) {
          // Reconnect resume OR first open without greeting path.
          if (isReconnect || !startRes.greeting_text) {
            speakingRef.current = false;
            setState(CALL_STATE.LISTENING);
            startRecognitionSafe();
          }
        }
      };
      ws.onmessage = (ev) => {
        if (boundGen !== callGenRef.current) return;
        try {
          handleWsMessage(JSON.parse(ev.data));
        } catch {
          /* ignore bad frames */
        }
      };
      ws.onerror = () => {
        if (boundGen !== callGenRef.current) return;
        if (callEndedRef.current || intentionalCloseRef.current) return;
        // onerror fires on every failed reconnect attempt; do not overwrite
        // the "reconnecting…" info line. onclose owns the terminal banner.
        if (reconnectAttemptRef.current > 0 || isReconnect) return;
        setError("WebSocket connection error");
      };
      ws.onclose = () => {
        if (boundGen !== callGenRef.current) return;
        if (
          !shouldReconnectOnClose({
            intentionalClose: intentionalCloseRef.current,
            callEnded: callEndedRef.current,
          })
        ) {
          setWsStatus("disconnected");
          return;
        }
        if (reconnectAttemptRef.current >= RECONNECT_MAX_ATTEMPTS) {
          setWsStatus("disconnected");
          setState(CALL_STATE.ENDED);
          setEnded((prev) => prev || { reason: "connection_lost" });
          markCallTerminal();
          cleanupCall();
          // Release the contact server-side now instead of leaving it parked
          // until the reconnect grace expires.
          releaseInteraction();
          return;
        }
        setWsStatus("reconnecting");
        setInfo(
          `Connection dropped — reconnecting (${reconnectAttemptRef.current + 1}/${RECONNECT_MAX_ATTEMPTS})…`
        );
        const delay = Math.min(5000, 400 * Math.pow(1.6, reconnectAttemptRef.current));
        reconnectAttemptRef.current += 1;
        reconnectTimerRef.current = setTimeout(() => {
          if (
            !shouldReconnectOnClose({
              intentionalClose: intentionalCloseRef.current,
              callEnded: callEndedRef.current,
            }) ||
            !activeWsUrlRef.current
          ) {
            return;
          }
          bindWs(new WebSocket(activeWsUrlRef.current), { isReconnect: true });
        }, delay);
      };
    }

    bindWs(new WebSocket(wsUrl), { isReconnect: false });
    // Recognition itself does not require a MediaStream, but wait until the
    // microphone request settles so barge-in analysis and browser permissions
    // are ready before we begin listening.
    void micReady.finally(() => {
      if (gen !== callGenRef.current || callEndedRef.current || intentionalCloseRef.current) return;
      if (useText) return;
      setupSpeechRecognition();
      if (stateRef.current === CALL_STATE.LISTENING) startRecognitionSafe();
    });
  }

  function endCall() {
    markCallTerminal();
    setWsStatus("disconnected");
    sendWs({ type: "hangup" });
    setState(CALL_STATE.ENDED);
    setEnded((prev) => prev || { reason: "user_hangup" });
    cleanupCall();
    releaseInteraction();
    closeWsQuietly();
  }

  // Cleanup on unmount: arm intentional close + clear reconnect timer (no ghost reconnects).
  useEffect(() => {
    return () => {
      markCallTerminal();
      cleanupCall();
      // Leaving the page is a deliberate hangup — do not park the contact for
      // the whole reconnect grace window.
      releaseInteraction();
      closeWsQuietly();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-scroll transcript to newest turn
  useEffect(() => {
    const el = transcriptScrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [transcript]);

  function submitTextFallback(e) {
    e.preventDefault();
    const text = textFallback.trim();
    if (!text) return;
    if (callEndedRef.current || pendingTerminalRef.current) return;
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError("Not connected — start a call first");
      return;
    }
    // If agent is speaking, cancel TTS so we don't talk over ourselves.
    // speechSynthesis.cancel often does not fire utterance onend — resume STT
    // explicitly and clear speakPhase so recog.onend is not stuck on greeting.
    if (speakingRef.current && hasTTS) {
      utteranceSeqRef.current += 1;
      try {
        window.speechSynthesis.cancel();
      } catch {
        /* ignore */
      }
      clearSpeakWatchdog();
      speakingRef.current = false;
    }
    speakQueueRef.current = [];
    drainingSpeakRef.current = false;
    speakPhaseRef.current = "normal";
    setSpeakPhase("normal");
    wsSeqRef.current += 1;
    const turnId = newTurnId();
    turnQueueRef.current.submit(turnId, text);
    const sent = sendWs({
      type: "user_turn", text, final: true,
      turn_id: turnId, turn_seq: wsSeqRef.current,
      locale: packLocale(), region: (region || "").trim() || undefined,
      drive_hint: driving || undefined,
    });
    pendingTurnRef.current = { turnId, text, accepted: false };
    if (!sent) {
      setError("Connection was lost before your reply could be sent. Please reconnect and try again.");
      return;
    }
    pushTurn({ speaker: "customer", text });
    setTextFallback("");
    lastInterimRef.current = { text: "", at: 0 };
    enterThinking();
  }

  function sendConsent() {
    if (callEndedRef.current || pendingTerminalRef.current) return;
    wsSeqRef.current += 1;
    const txt = "I consent";
    const sent = sendWs({
      type: "user_turn", text: txt, final: true,
      turn_id: newTurnId(), turn_seq: wsSeqRef.current,
      locale: packLocale(), region: (region || "").trim() || undefined,
    });
    if (!sent) {
      setError("Connection was lost before your consent could be sent. Please reconnect and try again.");
      return;
    }
    pushTurn({ speaker: "customer", text: txt });
    setConsent(null);
    enterThinking();
  }

  async function requestHuman() {
    const iid = interactionIdRef.current;
    if (!iid) {
      setError("Not connected — start a call first");
      return;
    }
    try {
      const r = await fetch(`/api/interactions/${iid}/handoff/accept`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...apiHeaders() },
        body: JSON.stringify({ force: true }),
      });
      const body = await r.json().catch(() => ({}));
      if (!r.ok || body.accepted === false) {
        throw new Error(body.reason || `handoff failed (${r.status})`);
      }
      setHandoff(true);
      setHandoffStatus("queued");
      setInfo(body.already_pending
        ? "Specialist request already queued. You can continue this report while waiting."
        : "Specialist request queued. A joined specialist will be shown here.");
    } catch (e) {
      setHandoffStatus("unavailable");
      setError(`Specialist request unavailable: ${String((e && e.message) || e).slice(0, 120)}`);
    }
  }

  function openLiveConsole() {
    try {
      const iid = interactionIdRef.current || interactionId;
      const base = window.location.href.split("#")[0];
      const target = `${base}#console${iid ? `?id=${encodeURIComponent(iid)}` : ""}`;
      const opened = window.open(target, "_blank", "noopener");
      if (opened) {
        setInfo("Supervisor console opened in a new tab. This call remains connected here.");
      } else {
        setInfo("Your browser blocked the new supervisor tab. This call remains connected here.");
      }
      return;
    } catch { /* ignore */ }
    setInfo("Unable to open the supervisor console. This call remains connected here.");
  }

  function copyReceipt() {
    try {
      const lines = transcript.map((t) => `[${t.speaker}] ${t.text}`).join("\n");
      const body = `TraceX contact ${interactionId || ""}\n${lines}\nCase: ${ended?.case_id || "—"}`;
      navigator.clipboard.writeText(body).then(
        () => setInfo("Transcript copied — receipt ready to email"),
        () => setInfo("Copy blocked — select the transcript manually"),
      );
    } catch { /* ignore */ }
  }

  async function sendSurvey() {
    if (!interactionId || survey.sent || !survey.csat) return;
    setError(null);
    try {
      await sendIntakeSurvey(fetch, `/api/interactions/${encodeURIComponent(interactionId)}/outcome`,
        apiHeaders({ "Content-Type": "application/json" }), survey.csat);
      setSurvey((s) => ({ ...s, sent: true }));
      setInfo("Thanks — report-capture feedback recorded");
    } catch (e) {
      setError(e.message || "Feedback was not saved. Please retry.");
    }
  }

  const slotEntries = buildSlotEntries(pack, slots);
  const progress = slotProgress(slotEntries);
  const caps = capabilitySnapshot({
    hasSpeechRecognition: hasSR,
    hasSpeechSynthesis: hasTTS,
    hasMicStream: !!micStreamRef.current || micGranted === true,
  });
  const inCall = state !== CALL_STATE.IDLE && state !== CALL_STATE.ENDED;
  const canStart = !inCall;
  const needsText = textOnly || voiceDenied || (!hasSR && !serverVoice.stt);
  const captured = slotEntries.filter(s => s.value);
  const missing = slotEntries.filter(s => !s.value);
  const composeRef = useRef(null);
  const nextStep = state === CALL_STATE.ENDED
    ? "Review the stored report and confirm its vehicle before investigating."
    : state === CALL_STATE.AGENT_SPEAKING
      ? "Listen to the question, or interrupt playback to give a correction."
      : state === CALL_STATE.THINKING
        ? "Your answer is being processed. The next question will appear in the transcript."
        : inCall ? "Reply below. Correct any captured detail before ending the report."
          : "Start a voice report or type instead. You can review the stored words before investigating.";

  useEffect(() => {
    if (!inCall) return undefined;
    const beforeUnload = e => { e.preventDefault(); e.returnValue = ""; };
    const beforeRoute = e => {
      if (String(e.detail?.next || "").replace(/^#/, "").split("?")[0] === "call") return;
      if (!window.confirm("Leaving ends this active report. Stored turns remain available, but refresh does not resume the call. Leave this report?")) e.preventDefault();
    };
    const beforeLink = e => {
      const anchor = e.target.closest?.("a[href]");
      if (!anchor || anchor.target === "_blank") return;
      const url = new URL(anchor.href, window.location.href);
      if (url.origin === window.location.origin && url.pathname === window.location.pathname && (!url.hash || url.hash === "#main" || url.hash.replace(/^#/, "").split("?")[0] === "call")) return;
      if (!window.confirm("Leaving ends this active report. Stored turns remain available, but refresh does not resume the call. Leave this report?")) {
        e.preventDefault(); e.stopPropagation();
      }
    };
    window.addEventListener("beforeunload", beforeUnload);
    window.addEventListener("tracex:before-route", beforeRoute);
    document.addEventListener("click", beforeLink, true);
    return () => {
      window.removeEventListener("beforeunload", beforeUnload);
      window.removeEventListener("tracex:before-route", beforeRoute);
      document.removeEventListener("click", beforeLink, true);
    };
  }, [inCall]);

  function correctDetail(label) {
    setTextFallback(`Correction: ${label} should be `);
    composeRef.current?.focus();
  }

  return (
    <div className="voice-page page-enter" data-testid="voice-report">
      <header className="page-header">
        <div>
          <h1>Voice report</h1>
          <p className="sub">Describe the owner's experience, review what was captured, then pass the report to an engineer for investigation.</p>
        </div>
        <div className="page-actions voice-controls" aria-label="Report controls">
          {canStart ? <>
            <button type="button" disabled={preflight.busy} className="primary voice-cta" onClick={() => startCall()}><IconMic aria-hidden="true" />Start voice report</button>
            <button type="button" disabled={preflight.busy} className="ghost" onClick={() => startCall({ textOnly: true })}>Type instead</button>
          </> : <>
            <button type="button" className="ghost" onClick={toggleMute} disabled={needsText || state === CALL_STATE.CONNECTING} aria-pressed={muted}>
              <IconMic aria-hidden="true" />{muted ? "Unmute microphone" : "Mute microphone"}
            </button>
            <button type="button" className="ghost" onClick={interruptPlayback} disabled={state !== CALL_STATE.AGENT_SPEAKING}>
              <IconSpeaker aria-hidden="true" />Interrupt playback
            </button>
            <button type="button" className="danger voice-cta" onClick={endCall}><IconHangup aria-hidden="true" />End call</button>
          </>}
        </div>
      </header>

      {canStart && <section className="voice-start-options" aria-label="Before starting">
        <SpeechLangSelect />
        <p>Type instead does not request a microphone. Chrome is the tested UI browser; real speech quality on devices remains unmeasured. Replies use the installed script, currently English; Hindi and Hinglish recognition need real-audio validation.</p>
        <button type="button" disabled={preflight.busy} onClick={checkMicrophone}>{preflight.busy ? "Checking microphone…" : "Check microphone"}</button>
        {preflight.note && <p role="status">{preflight.note}</p>}
        <details><summary>Interruption settings</summary><label><input type="checkbox" checked={automaticInterrupt} onChange={e => setAutomaticInterrupt(e.target.checked)} />Automatic speech interruption (experimental; headphones recommended)</label>
          <p>Default: select Interrupt playback, then speak. Optional server PCM capture keeps 450 ms before an automatic interruption. Browser recognition cannot recover words spoken while it was paused.</p></details>
      </section>}
      {(preflight.busy || (inCall && !textOnly && micGranted)) && <section className="voice-input-meter" aria-label="Microphone input">
        <label>Input level <meter aria-label="Microphone input level" min="0" max="0.25" value={Math.min(.25, inputLevel)} /></label>
        <span>{muted ? "Muted" : inputLevel < .003 ? "Very quiet / no input" : "Microphone samples arriving"}</span>
        {inCall && <button type="button" className="ghost" disabled={muted || state !== CALL_STATE.LISTENING} onClick={finishSpeaking}>Finish speaking</button>}
        <p className="voice-note">If quiet speech is not detected, finish manually or type. The meter is input feedback, not transcription-quality evidence.</p>
      </section>}
      {error && <div className="banner banner-error" role="alert">{error}{" "}<button type="button" className="ghost" onClick={() => setError(null)}>Dismiss</button></div>}
      {info && !error && <div className="banner banner-ok" role="status">{info}{" "}<button type="button" className="ghost" onClick={() => setInfo(null)}>Dismiss</button></div>}
      {consent && <div className="banner banner-warn" role="alert">
        {consent.script || "This call may be recorded. Say 'I consent' to continue."}{" "}
        <button type="button" className="primary" onClick={sendConsent}>I consent</button>
      </div>}
      {safetyMode && inCall && <div className="banner banner-error" role="alert">Safety escalation active — follow the specialist script. Do not drive until reviewed.</div>}
      {needsText && inCall && <div className="banner banner-warn" role="status">
        {textOnly ? "Text report active. Microphone and spoken playback are off." : "Speech recognition is unavailable. Type your replies below."}
        {!textOnly && voiceDenied && hasSR && <button type="button" className="ghost" onClick={retrySpeechInput}>Try microphone again</button>}
      </div>}

      <div className="call-layout">
        <section className="call-stage" aria-labelledby="report-transcript-title">
          <div className="voice-status" role="status">
            <span className={"status-pip " + (wsStatus === "live" ? "ok" : "")} aria-hidden="true" />
            <strong>{muted && inCall && !needsText ? "Microphone muted" : callStateLabel(state, { speakPhase, textOnly: needsText })}</strong>
            {inCall && <span>{Math.floor(callSecs / 60)}:{String(callSecs % 60).padStart(2, "0")}</span>}
            {humanControl && inCall && <span>Specialist joined</span>}
          </div>
          <h2 id="report-transcript-title">Report transcript</h2>
          <div className="transcript" role="log" aria-label="Report transcript" tabIndex={0}
            ref={node => { transcriptScrollRef.current = node; transcriptEndRef.current = node; }} aria-live="polite" aria-relevant="additions">
            {transcript.length === 0 && <div className="empty-state"><p className="empty-state-text">
              {canStart ? "Your conversation will appear here. Start a voice report or choose Type instead above." : "Opening the report and waiting for the first question…"}
            </p></div>}
            {transcript.map(t => <div key={t.id || `${t.speaker}-${t.text.slice(0, 12)}`} className={"turn " + t.speaker + (t.interim ? " interim" : "")}>
              <div className="who">{t.speaker === "customer" ? "Owner report" : t.speaker === "supervisor" ? "Specialist" : "Assistant"}{t.interim ? " · being recognized" : ""}</div>
              <div>{t.text}</div>
            </div>)}
          </div>
          <form className="call-compose" onSubmit={submitTextFallback}>
            <input ref={composeRef} aria-label="Type a reply or correction" placeholder={canStart ? "Choose a start option above" : "Type a reply or correction — Enter to send"}
              value={textFallback} onChange={e => setTextFallback(e.target.value)} disabled={canStart || state === CALL_STATE.CONNECTING} autoComplete="off" />
            <button type="submit" className="primary" disabled={!inCall || state === CALL_STATE.CONNECTING || !textFallback.trim()}>Send</button>
          </form>
          {inCall && <p className="voice-note">Leaving this page or refreshing ends the report. A temporary connection drop on this page can reconnect.</p>}

          {handoff && inCall && <div className="banner banner-ok" role="status">
            {humanControl ? "Specialist joined." : handoffStatus === "queued" ? "Specialist request queued. No pickup time is guaranteed." : handoffStatus === "unavailable" ? "Specialist request unavailable. You can retry from Next step." : "A specialist can review this report. Request support to join the queue."}{" "}
            <button type="button" className="ghost" onClick={openLiveConsole}>Open supervisor console in new tab</button>
          </div>}

          {ended && state === CALL_STATE.ENDED && <section className="result-card" aria-label="Completed report">
            <h2>Report ended</h2>
            <p>Inspect the stored source turns and confirm the vehicle on the next page. Opening the handoff does not run an investigation or approve an action.</p>
            {interactionId && <a className="voice-handoff" href={`#safety-campaigns?tab=investigate&interaction=${encodeURIComponent(interactionId)}`}>Investigate this report →</a>}
            <div className="row voice-secondary-actions">
              <button type="button" className="ghost" onClick={copyReceipt}>Copy transcript</button>
              {ended.case_id && <button type="button" className="ghost" onClick={() => openCases({ caseId: ended.case_id, status: "open" })}>Open case queue</button>}
            </div>
            <fieldset className="voice-feedback">
              <legend>How well was your report captured? 1 = poorly, 5 = accurately</legend>
              <div className="row">{[1, 2, 3, 4, 5].map(n => <button key={n} type="button" aria-label={`Capture rating ${n}`} aria-pressed={survey.csat === n}
                disabled={survey.sent} className={survey.csat === n ? "primary" : "ghost"} onClick={() => setSurvey(s => ({ ...s, csat: n }))}>{n}</button>)}
                <button type="button" className="ghost" disabled={survey.sent || !survey.csat} onClick={sendSurvey}>{survey.sent ? "Feedback saved" : "Save feedback"}</button>
              </div>
              <p className="voice-note">This records feedback about intake. Repair and vehicle safety still require separate evidence and review.</p>
            </fieldset>
          </section>}
        </section>

        <aside className="stack" aria-label="Report details">
          <section className="panel">
            <h2>What we understood</h2>
            <p className="voice-note">Captured details are provisional. Correct them through the conversation to preserve the original report.</p>
            {!captured.length ? <p>No details captured yet.</p> : captured.map(s => <div className="voice-fact" key={s.key || s.label}>
              <span>{s.label}</span><strong>{String(s.value)}</strong>
              {inCall && <button type="button" className="ghost" disabled={state === CALL_STATE.CONNECTING} aria-label={`Correct ${s.label}`} onClick={() => correctDetail(s.label)}>Correct</button>}
            </div>)}
            {progress.total > 0 && <p>{progress.filled} of {progress.total} requested details captured</p>}
          </section>
          <section className="panel">
            <h2>Still needed</h2>
            {missing.length ? <ul>{missing.map(s => <li key={s.key || s.label}>{s.label}</li>)}</ul> : <p>{inCall ? "Review the transcript for missing or incorrect details." : "The report's questions will identify what is needed."}</p>}
          </section>
          <section className="panel">
            <h2>Next step</h2><p>{nextStep}</p>
            {inCall && <div className="voice-secondary-actions">
              <button type="button" className={driving ? "primary" : "ghost"} onClick={() => setDriving(d => !d)} aria-pressed={driving}>{driving ? "Driving reported" : "I'm driving"}</button>
              <button type="button" className="ghost" disabled={humanControl} onClick={requestHuman}>{humanControl ? "Specialist joined" : "Request specialist"}</button>
            </div>}
          </section>
          <details className="panel voice-diagnostics">
            <summary>Voice settings and diagnostics</summary>
            <p>These describe the speech connection, not a new Meta investigation.</p>
            <div className="kvs">
              <span className="k">Connection</span><span className="v">{wsStatus}</span>
              <span className="k">Interaction</span><span className="v mono">{interactionId || "Not started"}</span>
              <span className="k">Recognition</span><span className="v">{textOnly ? "Off · text report" : serverVoice.stt ? "Deepgram server STT" : caps.stt}</span>
              <span className="k">Playback</span><span className="v">{textOnly ? "Off · text report" : serverVoice.tts ? "Deepgram server TTS" : caps.tts}</span>
              <span className="k">Microphone</span><span className="v">{micGranted === true ? "Granted" : micGranted === false ? "Blocked" : "Not requested"}</span>
              <span className="k">Pack</span><span className="v">{pack?.display_name || pack?.id || "Selected when report starts"}</span>
              {latency && <><span className="k">Server turn duration</span><span className="v">{latency.elapsed_ms} ms · excludes audible playback</span></>}
              {frustration > 0 && <><span className="k">Heuristic frustration</span><span className="v">{frustration.toFixed(2)} · unvalidated</span></>}
              {ended && <><span className="k">End reason</span><span className="v">{ended.reason || "ended"}</span><span className="k">Case</span><span className="v">{ended.case_id || "Not created"}</span><span className="k">Audit</span><span className="v">{ended.audit_pending ? "Pending" : "Not reported"}</span></>}
            </div>
            {activity && <p>{activity.agent}: {activity.summary || activity.action_type}</p>}
            <label>Region for consent <input aria-label="Region for consent" value={region} onChange={e => setRegion(e.target.value)} placeholder="CA" /></label>
            <CallAiExtras interactionId={interactionId} caseId={ended?.case_id} showLanguage={false} serverVoice={serverVoice} textOnly={textOnly} />
          </details>
        </aside>
      </div>
    </div>
  );
}
