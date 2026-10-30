"""Narrate and package the recorded UI as a three-minute MP4.

Uses the system Samantha TTS voice, not an impersonation or a human recording.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/"reports/hackathon/investigation_demo"
SEGMENTS = [
    (18, "A driver describes a worrying vehicle symptom. Trace X helps a quality engineer turn that report into reviewed evidence and a recorded repair. This walkthrough uses fictional records. The operations platform is reused; the sourced Meta investigation and follow-up workflow are new."),
    (22, "First, Muse Spark Open extracts observations from the owner's Hinglish report. These are actual saved outputs from a live Meta model call. Each interpretation is shown beside its original source sentence. The model preserves uncertainty about the part, instead of treating a reported sound as a confirmed mechanical cause."),
    (17, "The missing information matters. The agent selects a question asking for an existing installation or workshop record. It does not ask the owner to reproduce a dangerous symptom. An unidentified part stays unidentified until there is evidence to review."),
    (21, "Here an operator reviews the fictional installation record. This is a clearly simulated engineering decision. The supplier, part number and lot come from recorded installation fields. A vehicle model, a similar complaint, or the language model alone cannot establish an exact lot match."),
    (22, "After the record is available, the agent chooses the installed-part lookup. The saved follow-up result updates the investigation with that source. You can inspect its actual tool choice and citations. These tools read evidence; they cannot authorize outreach, choose a replacement part, or clear the vehicle."),
    (28, "The reviewed workflow now carries the same vehicle into workshop actions. We record fictional recovery and inspection evidence, then a replacement using the engineering-reviewed part and procedure. These controls run in the application. Every accepted action records who acted, when, and which campaign revision it changed. The demonstration is not claiming that a real vehicle was inspected or repaired."),
    (22, "A replacement entry alone is not a completed case. Repair verification is recorded separately, followed by the owner's follow-up and a reviewer disposition. Any unresolved vehicle remains visible. A later symptom report can reopen the case while preserving its earlier evidence."),
    (19, "The exported packet connects source reports, recorded Meta interpretations, read-only tool results, reviewer actions and repair records. Owner outreach remains simulated: no external message was sent. The packet gives another engineer something concrete to inspect and challenge."),
    (11, "Live integration works. Independent human labels and reviewer measurements are still pending. The current evidence does not establish prediction above eighty-six percent or accidents prevented."),
]


def run(args):
    result = subprocess.run(args, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-3000:])
    return result.stdout


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    elapsed = 0; transcript = []
    for index, (seconds, text) in enumerate(SEGMENTS):
        prefix = OUT/f"narration-{index:02}"
        text_path = prefix.with_suffix(".txt")
        cached_text = text_path.exists() and text_path.read_text() == text
        text_path.write_text(text)
        raw, rendered = prefix.with_suffix(".aiff"), prefix.with_suffix(".wav")
        if not cached_text or not raw.exists() or raw.stat().st_size <= 8192:
            run(["/usr/bin/say", "-v", "Samantha", "-r", "150", "-f", str(text_path), "-o", str(raw)])
        duration = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(raw)]).strip())
        speed = max(1.0, duration/(seconds-.35))
        run(["ffmpeg", "-y", "-v", "error", "-i", str(raw), "-af", f"atempo={speed},apad,atrim=0:{seconds}", "-ar", "48000", "-ac", "1", str(rendered)])
        transcript.append({"start": elapsed, "end": elapsed+seconds, "text": text}); elapsed += seconds
    listing = OUT/"narration-concat.txt"
    listing.write_text("".join(f"file 'narration-{i:02}.wav'\n" for i in range(len(SEGMENTS))))
    audio = OUT/"narration.wav"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(listing), "-c:a", "pcm_s16le", str(audio)])
    (OUT/"narration.json").write_text(json.dumps({"voice": "macOS Samantha text-to-speech", "synthetic_narration": True, "segments": transcript}, indent=2))
    video = OUT/"workflow.webm"
    if not video.exists():
        print("Narration ready. Run this command again once workflow.webm is recorded."); return
    raw_duration = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(video)]).strip())
    # Remove the recorder's initial page-loading time; actions themselves retain
    # their recorded timing. Narration aligns with the 180-second scene clock.
    offset = max(0.0, raw_duration-180.0)
    dest = OUT/"TraceX-investigation-demo.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-ss", str(offset), "-i", str(video), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0",
         "-vf", "tpad=stop_mode=clone:stop_duration=2", "-t", "180", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(dest)])
    info = json.loads(run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=codec_name,codec_type,width,height", "-of", "json", str(dest)]))
    info["initial_loading_trim_seconds"] = offset
    (OUT/"video_verification.json").write_text(json.dumps(info, indent=2))
    print(json.dumps({"video": str(dest), "duration": info["format"]["duration"], "bytes": info["format"]["size"]}))


if __name__ == "__main__": main()
