/** Bounded local PCM capture. Nothing is uploaded until finish() is called. */
import { pcmWav, voiceActivity } from "./voiceExperience.js";

export function createSampleBuffer(sampleRate, { preRollMs = 450, maxMs = 30000 } = {}) {
  const preLimit = Math.ceil(sampleRate * preRollMs / 1000), maxLimit = Math.ceil(sampleRate * maxMs / 1000);
  let rolling = [], rollingSize = 0, chunks = null, size = 0;
  return {
    push(input) {
      const block = Float32Array.from(input);
      if (chunks && size < maxLimit) { const part = block.slice(0, maxLimit - size); chunks.push(part); size += part.length; }
      rolling.push(block); rollingSize += block.length;
      while (rollingSize > preLimit && rolling.length) {
        const excess = rollingSize - preLimit;
        if (rolling[0].length <= excess) rollingSize -= rolling.shift().length;
        else { rolling[0] = rolling[0].slice(excess); rollingSize -= excess; }
      }
      return { full: size >= maxLimit, samples: size };
    },
    start(withPreRoll = false) { chunks = withPreRoll ? rolling.map(x => x.slice()) : []; size = chunks.reduce((n, x) => n + x.length, 0); },
    finish() { const result = chunks; chunks = null; size = 0; return result?.length ? pcmWav(result, sampleRate) : null; },
    cancel() { chunks = null; size = 0; },
    clear() { chunks = null; size = 0; rolling = []; rollingSize = 0; },
    get active() { return chunks !== null; },
  };
}

export function createPcmRecorder(context, stream, { noiseFloor = .008, onLevel = () => {}, onFull = () => {} } = {}) {
  if (!context.createScriptProcessor) throw new Error("PCM capture unavailable");
  if (context.sampleRate < 16000 || context.sampleRate > 192000) throw new Error("PCM microphone sample rate unavailable");
  const source = context.createMediaStreamSource(stream);
  const processor = context.createScriptProcessor(2048, 1, 1);
  const sink = context.createGain(); sink.gain.value = 0;
  const buffer = createSampleBuffer(context.sampleRate);
  let floor = noiseFloor, enabled = true, lastLevel = 0;
  processor.onaudioprocess = event => {
    event.outputBuffer.getChannelData(0).fill(0);
    if (!enabled) return;
    const data = event.inputBuffer.getChannelData(0);
    const rms = Math.sqrt(data.reduce((sum, x) => sum + x * x, 0) / data.length);
    const activity = voiceActivity(rms, floor);
    if (buffer.active) floor = activity.noiseFloor;
    const status = buffer.push(data);
    if (performance.now() - lastLevel >= 100) { lastLevel = performance.now(); onLevel({ ...activity, rms }); }
    if (status.full && buffer.active) onFull();
  };
  source.connect(processor); processor.connect(sink); sink.connect(context.destination);
  return { start: preRoll => buffer.start(preRoll), finish: () => buffer.finish(), cancel: () => buffer.cancel(),
    mute(value) { enabled = !value; buffer.clear(); }, clear: () => buffer.clear(),
    close() { enabled = false; buffer.clear(); processor.onaudioprocess = null; source.disconnect(); processor.disconnect(); sink.disconnect(); } };
}

export async function microphonePreflight(onLevel, durationMs = 1800) {
  let stream, context, recorder;
  const levels = [];
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
    context = new (window.AudioContext || window.webkitAudioContext)();
    await context.resume();
    recorder = createPcmRecorder(context, stream, { onLevel: level => { levels.push(level.rms); onLevel(level.rms); } });
    await new Promise(resolve => window.setTimeout(resolve, durationMs));
    if (!levels.length) throw new Error("No microphone samples arrived; use text or check the input device.");
    levels.sort((a, b) => a - b);
    return { noiseFloor: Math.min(.04, Math.max(.003, levels[Math.floor(levels.length * .8)])),
      samples: levels.length, device: stream.getAudioTracks()[0]?.label || "Selected microphone" };
  } finally { recorder?.close(); stream?.getTracks().forEach(track => track.stop()); await context?.close().catch(() => {}); }
}
