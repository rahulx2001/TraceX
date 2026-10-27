"""Consent-first local collection page for REAL Hindi/Hinglish/English complaints.

    python -m scripts.real_hindi_collect serve
    python -m scripts.real_hindi_collect list
    python -m scripts.real_hindi_collect transcribe --next
    python -m scripts.real_hindi_collect delete rh_20261026_ab12cd34

This is a standalone local page, not part of the product API. It binds to
127.0.0.1 by default and disables the access log, so it does not store IP
addresses. It never asks for a name, phone number or number plate, and it
refuses to save anything unless the person ticks the consent box.

Storage is one JSON file per submission plus one metadata-free WAV per voice
recording, under ``data/real_hindi/`` (gitignored, mode 0700). The original
upload filename and container metadata are discarded. FFmpeg is required for
voice uploads; without it the page still accepts typed stories and says so.

The page is deliberately plain: no analytics, no external assets, no cookies,
no inline script. The optional in-browser recorder is a same-origin JS file
that merely fills the normal file input; the server validates and transcodes
the upload like any other file.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

from eval.real_hindi.consent import CONSENT_SHA256, CONSENT_TEXT, CONSENT_VERSION

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = REPO_ROOT / "data" / "real_hindi"

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_AUDIO_SECONDS = 180.0
MIN_AUDIO_SECONDS = 0.4
MAX_TEXT_CHARS = 5000
MIN_TEXT_CHARS = 10
LANGS = ("hindi", "hinglish", "english", "mixed")
ID_RE = re.compile(r"^rh_[0-9]{8}_[0-9a-f]{8}$")
RECORDER_JS = r"""
(() => {
  const start = document.getElementById("rec-start");
  const stop = document.getElementById("rec-stop");
  const status = document.getElementById("rec-status");
  const preview = document.getElementById("rec-preview");
  const input = document.getElementById("audio-input");
  if (!start || !stop || !input) return;
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {
    if (status) status.textContent = "Recording is not available in this browser. Please upload a recording or type instead.";
    start.disabled = true;
    return;
  }
  let recorder = null;
  let chunks = [];
  let stream = null;
  let timer = null;
  let previewUrl = null;

  const setStatus = (text) => { if (status) status.textContent = text; };

  start.addEventListener("click", async () => {
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunks = [];
      recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (event) => { if (event.data && event.data.size) chunks.push(event.data); };
      recorder.onstop = () => {
        if (stream) stream.getTracks().forEach((track) => track.stop());
        stream = null;
        clearTimeout(timer);
        const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
        const ext = (blob.type.includes("ogg") ? "ogg" : "webm");
        const file = new File([blob], `recording.${ext}`, { type: blob.type });
        try {
          const transfer = new DataTransfer();
          transfer.items.add(file);
          input.files = transfer.files;
          setStatus("Recording ready. It will be saved when you submit the form.");
        } catch (err) {
          setStatus("Your browser could not attach the recording. Please upload a recording file instead.");
        }
        if (preview) {
          if (previewUrl) URL.revokeObjectURL(previewUrl);
          previewUrl = URL.createObjectURL(blob);
          preview.src = previewUrl;
          preview.hidden = false;
        }
        start.disabled = false;
        stop.disabled = true;
      };
      recorder.start();
      start.disabled = true;
      stop.disabled = false;
      setStatus("Recording. Speak in Hindi, Hinglish or English. Press stop when finished.");
      timer = setTimeout(() => {
        if (recorder && recorder.state === "recording") {
          recorder.stop();
          setStatus("Stopped at 3 minutes. The recording will be saved when you submit the form.");
        }
      }, 180000);
    } catch (err) {
      setStatus("Microphone permission was not granted. Please upload a recording or type instead.");
      start.disabled = false;
      stop.disabled = true;
    }
  });

  stop.addEventListener("click", () => {
    if (recorder && recorder.state === "recording") recorder.stop();
  });
})();
"""


class DataError(RuntimeError):
    """A local data file is missing or malformed. Never silently skipped."""


class AudioError(RuntimeError):
    """The upload could not be stored as a metadata-free WAV."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def audio_support() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _chmod(path: Path, mode: int) -> None:
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def ensure_layout(data_dir: Path) -> dict[str, Path]:
    data_dir = data_dir.expanduser().resolve()
    layout = {
        "data": data_dir,
        "records": data_dir / "records",
        "audio": data_dir / "audio",
        "tmp": data_dir / "tmp",
    }
    for path in layout.values():
        path.mkdir(parents=True, exist_ok=True)
        _chmod(path, 0o700)
    return layout


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(value, fh, ensure_ascii=False, indent=2, sort_keys=True)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        _chmod(Path(tmp_name), 0o600)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    _chmod(path, 0o600)


def load_records(data_dir: Path) -> list[dict[str, Any]]:
    records_dir = data_dir.expanduser().resolve() / "records"
    if not records_dir.exists():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(records_dir.glob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise DataError(f"cannot parse {path}: {type(e).__name__}") from e
        if not isinstance(value, dict):
            raise DataError(f"{path} does not contain a JSON object")
        if value.get("id") != path.stem:
            raise DataError(f"{path} id does not match its filename")
        out.append(value)
    out.sort(key=lambda r: (str(r.get("created_at") or ""), str(r.get("id") or "")))
    return out


def record_id(records_dir: Path) -> str:
    for _ in range(20):
        rid = "rh_" + datetime.now(timezone.utc).strftime("%Y%m%d") + "_" + secrets.token_hex(4)
        if not (records_dir / f"{rid}.json").exists():
            return rid
    raise RuntimeError("could not allocate a unique record id")


def probe_audio(path: Path) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise AudioError("ffprobe is not installed")
    proc = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries",
         "format=duration:format_tags:stream=codec_type,sample_rate,channels:stream_tags",
         "-of", "json", str(path)],
        capture_output=True, text=True, timeout=30, check=False,
    )
    if proc.returncode != 0:
        raise AudioError("ffprobe could not read the audio")
    try:
        return json.loads(proc.stdout or "{}")
    except ValueError as e:
        raise AudioError("ffprobe returned invalid JSON") from e


def _tags_present(meta: dict[str, Any]) -> bool:
    if (meta.get("format") or {}).get("tags"):
        return True
    for stream in meta.get("streams") or []:
        if stream.get("tags"):
            return True
    return False


def transcode_audio(src: Path, dst: Path) -> tuple[float, str]:
    """Transcode to 16 kHz mono WAV and prove metadata was removed.

    Returns (duration_seconds, output_sha256). Raises AudioError on any doubt.
    """
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise AudioError("ffmpeg is not installed")
    before = probe_audio(src)
    try:
        in_duration = float((before.get("format") or {}).get("duration") or 0)
    except (TypeError, ValueError):
        in_duration = 0.0
    # Streaming WebM from MediaRecorder often has no duration in its header.
    # When it is present, use it as a cheap pre-check; always check the
    # decoded output duration below.
    if in_duration and in_duration <= MIN_AUDIO_SECONDS:
        raise AudioError("the recording is too short")
    if in_duration > MAX_AUDIO_SECONDS:
        raise AudioError(f"the recording is longer than {int(MAX_AUDIO_SECONDS)} seconds")
    if not any((s.get("codec_type") == "audio") for s in (before.get("streams") or [])):
        raise AudioError("the upload has no audio track")
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg, "-nostdin", "-y", "-i", str(src),
        "-map_metadata", "-1", "-map_chapters", "-1", "-vn",
        "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        "-fflags", "+bitexact", "-flags:a", "+bitexact",
        "-f", "wav", str(dst),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
    if proc.returncode != 0:
        try:
            dst.unlink()
        except OSError:
            pass
        raise AudioError("ffmpeg could not convert the recording")
    _chmod(dst, 0o600)
    after = probe_audio(dst)
    if _tags_present(after):
        try:
            dst.unlink()
        except OSError:
            pass
        raise AudioError("metadata is still present after transcoding; refusing to store it")
    try:
        duration = float((after.get("format") or {}).get("duration") or 0)
    except (TypeError, ValueError):
        duration = 0.0
    if duration <= MIN_AUDIO_SECONDS:
        raise AudioError("the converted recording is empty")
    if duration > MAX_AUDIO_SECONDS + 0.5:
        raise AudioError(f"the converted recording is longer than {int(MAX_AUDIO_SECONDS)} seconds")
    streams = [s for s in (after.get("streams") or []) if s.get("codec_type") == "audio"]
    if not streams:
        raise AudioError("the converted file has no audio track")
    stream = streams[0]
    if str(stream.get("sample_rate")) != "16000":
        raise AudioError("the converted recording is not 16 kHz")
    try:
        channels = int(stream.get("channels") or 0)
    except (TypeError, ValueError):
        channels = 0
    if channels != 1:
        raise AudioError("the converted recording is not mono")
    return round(duration, 3), file_sha256(dst)


async def save_upload(upload: UploadFile, tmp_dir: Path) -> tuple[Path, int]:
    fd, name = tempfile.mkstemp(prefix="upload.", suffix=".bin", dir=tmp_dir)
    os.close(fd)
    path = Path(name)
    size = 0
    try:
        with path.open("wb") as fh:
            while True:
                chunk = await upload.read(1 << 20)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise ValueError("the upload is larger than 25 MB")
                fh.write(chunk)
        if size == 0:
            raise ValueError("the uploaded recording is empty")
        _chmod(path, 0o600)
        return path, size
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def _paragraphs(text: str) -> str:
    parts = [html.escape(p.strip()) for p in text.split("\n\n") if p.strip()]
    return "".join(f"<p>{p}</p>" for p in parts)


def _wordmark(version: str) -> str:
    return f"<span class=\"mono\">data/real_hindi/</span> · consent {html.escape(version)}"


def render_page(csrf: str, *, audio_ok: bool, error: str = "") -> str:
    lang_options = "\n".join(
        f'<option value="{lang}">{label}</option>'
        for lang, label in (
            ("hindi", "Hindi (हिंदी)"),
            ("hinglish", "Hinglish (Hindi in English letters)"),
            ("english", "English"),
            ("mixed", "Mixed"),
        )
    )
    audio_block = (
        """
        <fieldset>
          <legend>Record a voice message (optional)</legend>
          <p class="small muted">You can record here, or upload a recording, or type below. One of them is enough.</p>
          <div class="row">
            <button type="button" id="rec-start">Start recording</button>
            <button type="button" id="rec-stop" disabled>Stop</button>
          </div>
          <p id="rec-status" class="small" aria-live="polite"></p>
          <audio id="rec-preview" controls hidden></audio>
          <label class="block" for="audio-input">Upload a voice recording</label>
          <input id="audio-input" type="file" name="audio" accept="audio/*">
          <p class="small muted">Voice uploads are converted to a metadata-free WAV before saving. The original file and its metadata are discarded.</p>
        </fieldset>
        """
    ) if audio_ok else (
        """
        <fieldset>
          <legend>Voice recording</legend>
          <p class="small muted">Voice uploads are disabled on this machine because ffmpeg/ffprobe are not installed. You can still type your story below.</p>
        </fieldset>
        """
    )
    error_block = f'<div class="error" role="alert">{html.escape(error)}</div>' if error else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow">
  <title>Share a real car or bike problem</title>
  <style>
    :root {{ color-scheme: light; }}
    body {{ font: 16px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; background: #f7f7f5; color: #171716; }}
    main {{ max-width: 760px; margin: 0 auto; padding: 28px 20px 72px; }}
    h1 {{ font-size: 1.65rem; line-height: 1.2; margin: 0 0 8px; }}
    h2 {{ font-size: 1.12rem; margin: 26px 0 8px; }}
    p {{ margin: 0 0 12px; }}
    fieldset {{ border: 1px solid #d7d7d1; border-radius: 10px; padding: 14px 16px; margin: 18px 0; background: #fff; }}
    legend {{ font-weight: 650; padding: 0 6px; }}
    label {{ font-weight: 600; }}
    .block {{ display: block; margin: 12px 0 6px; }}
    input[type=file], select, textarea {{ width: 100%; box-sizing: border-box; font: inherit; }}
    select, textarea {{ padding: 10px 11px; border: 1px solid #bdbdb6; border-radius: 8px; background: #fff; }}
    textarea {{ min-height: 150px; resize: vertical; }}
    button {{ font: inherit; padding: 10px 16px; border-radius: 8px; border: 1px solid #171716; background: #171716; color: #fff; cursor: pointer; }}
    button:disabled {{ opacity: .45; cursor: not-allowed; }}
    button.secondary {{ background: #fff; color: #171716; }}
    .row {{ display: flex; gap: 10px; flex-wrap: wrap; }}
    .check {{ display: flex; gap: 10px; align-items: flex-start; margin: 14px 0; font-weight: 500; }}
    .check input {{ margin-top: 4px; width: 18px; height: 18px; flex: 0 0 auto; }}
    .consent {{ background: #fff; border: 1px solid #d7d7d1; border-radius: 10px; padding: 16px 18px; }}
    .consent p {{ margin: 0 0 10px; }}
    .small {{ font-size: .88rem; }}
    .muted {{ color: #66665f; }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .9em; }}
    .error {{ background: #fff1ee; border: 1px solid #e2b3a8; color: #7a2414; padding: 12px 14px; border-radius: 8px; margin: 14px 0; }}
    .note {{ background: #f1f1ec; border-radius: 8px; padding: 10px 12px; }}
    footer {{ margin-top: 34px; color: #66665f; font-size: .84rem; }}
  </style>
  <script src="/static/recorder.js" defer></script>
</head>
<body>
<main>
  <h1>Describe a real problem you or your family had with a car or bike, in your own words.</h1>
  <p class="muted">This is a research evaluation of a safety system. It is not a repair service; I cannot fix your vehicle or contact the manufacturer.</p>
  {error_block}

  <div class="consent">
    <h2 style="margin-top:0">Before you start: what this is and what happens to your story</h2>
    {_paragraphs(CONSENT_TEXT)}
  </div>

  <form method="post" action="/submit" enctype="multipart/form-data" autocomplete="off">
    <input type="hidden" name="csrf" value="{html.escape(csrf)}">

    <fieldset>
      <legend>Your story</legend>
      <label class="block" for="reported-language">Which language did you use?</label>
      <select id="reported-language" name="reported_language" required>
        <option value="">Choose one</option>
        {lang_options}
      </select>
      <label class="block" for="story-text">Type your story here</label>
      <textarea id="story-text" name="text" maxlength="{MAX_TEXT_CHARS}" spellcheck="true"></textarea>
      <p class="small muted">Please do not type your name, phone number, or number plate. If you upload a recording, you can also type what you said here.</p>
    </fieldset>

    {audio_block}

    <fieldset>
      <legend>Consent</legend>
      <label class="check">
        <input type="checkbox" name="no_identifiers" value="yes" required>
        <span>I did not include my name, phone number, or number plate.</span>
      </label>
      <label class="check">
        <input type="checkbox" name="consent" value="yes" required>
        <span>I have read the information above and I agree to take part, including sending the text of my story to Meta's AI service for evaluation.</span>
      </label>
      <p class="small muted">If you do not agree, please close this page. Nothing will be saved.</p>
    </fieldset>

    <button type="submit">Submit my story</button>
  </form>

  <p class="note small">You can stop at any time before submitting. After submitting, save the ID shown on the next page; it is the only way I can find and delete an anonymous story.</p>
  <footer>{_wordmark(CONSENT_VERSION)} · no analytics, no cookies, no access log</footer>
</main>
</body>
</html>"""


def render_message(title: str, message: str, *, status: int = 400) -> HTMLResponse:
    body = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>{html.escape(title)}</title>
<style>body{{font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;max-width:680px;margin:0 auto;padding:48px 20px;color:#171716}}h1{{font-size:1.5rem}}a{{color:#171716}}</style>
</head><body><h1>{html.escape(title)}</h1><p>{html.escape(message)}</p><p><a href="/">Back to the form</a></p></body></html>"""
    return HTMLResponse(body, status_code=status)


def render_success(rid: str) -> HTMLResponse:
    body = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>Story saved</title>
<style>body{{font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;max-width:680px;margin:0 auto;padding:48px 20px;color:#171716}}
code{{font:1.05rem ui-monospace,SFMono-Regular,Menlo,monospace;background:#f1f1ec;padding:8px 10px;border-radius:6px;display:inline-block}}a{{color:#171716}}</style>
</head><body><h1>Thank you. Your story was saved.</h1>
<p>Please save this ID if you may want the story deleted later:</p>
<p><code>{html.escape(rid)}</code></p>
<p>Because the story is anonymous, this ID is the only way I can find it. I will not publish your story.</p>
<p><a href="/">Add another story</a></p></body></html>"""
    return HTMLResponse(body, headers={"Cache-Control": "no-store"})


def create_app(data_dir: Path, *, csrf_token: str | None = None, audio_ok: bool | None = None) -> FastAPI:
    data_dir = data_dir.expanduser().resolve()
    token = csrf_token or secrets.token_urlsafe(24)
    can_audio = audio_support() if audio_ok is None else bool(audio_ok)
    app = FastAPI(title="Real complaint collection", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.data_dir = data_dir
    app.state.csrf_token = token
    app.state.audio_ok = can_audio

    @app.middleware("http")
    async def _headers(request, call_next):
        response = await call_next(request)
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        response.headers["Permissions-Policy"] = "camera=(), geolocation=(), microphone=(self)"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'; script-src 'self'; "
            "media-src 'self' blob:; img-src 'self'; form-action 'self'; "
            "base-uri 'none'; frame-ancestors 'none'"
        )
        return response

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return HTMLResponse(render_page(token, audio_ok=can_audio))

    @app.get("/static/recorder.js")
    async def recorder_js():
        return Response(RECORDER_JS, media_type="application/javascript", headers={"Cache-Control": "no-store"})

    @app.get("/consent.txt", response_class=PlainTextResponse)
    async def consent_text():
        return PlainTextResponse(
            f"Consent version: {CONSENT_VERSION}\nConsent SHA-256: {CONSENT_SHA256}\n\n{CONSENT_TEXT}\n"
        )

    @app.get("/healthz", response_class=PlainTextResponse)
    async def healthz():
        return PlainTextResponse("ok")

    @app.post("/submit", response_class=HTMLResponse)
    async def submit(
        csrf: str = Form(""),
        reported_language: str = Form(""),
        text: str = Form(""),
        consent: str = Form(""),
        no_identifiers: str = Form(""),
        audio: UploadFile | None = File(None),
    ):
        if not secrets.compare_digest(str(csrf), token):
            return render_message("Page expired", "The form token was missing or invalid. Please reload the form and try again. Nothing was saved.", status=403)
        if consent != "yes":
            return render_message("Consent is required", "You did not agree to take part, so nothing was saved. You can close this page.", status=400)
        if no_identifiers != "yes":
            return render_message("Please confirm", "Please confirm that you did not include a name, phone number, or number plate. Nothing was saved.", status=400)
        lang = str(reported_language).strip().lower()
        if lang not in LANGS:
            return render_message("Choose a language", "Please choose the language you used. Nothing was saved.", status=400)
        story = str(text or "").strip()
        if story and len(story) < MIN_TEXT_CHARS:
            return render_message("Story too short", f"Please write at least {MIN_TEXT_CHARS} characters, or upload a recording. Nothing was saved.", status=400)
        if len(story) > MAX_TEXT_CHARS:
            return render_message("Story too long", f"Please keep the typed story under {MAX_TEXT_CHARS} characters. Nothing was saved.", status=400)
        has_audio = bool(audio is not None and getattr(audio, "filename", ""))
        if not story and not has_audio:
            return render_message("Nothing to save", "Please type your story or upload a recording. Nothing was saved.", status=400)
        if has_audio and not can_audio:
            return render_message("Voice uploads are disabled", "ffmpeg/ffprobe are not installed on this machine, so a voice upload cannot be stored safely. You can type your story instead. Nothing was saved.", status=503)

        layout = ensure_layout(data_dir)
        rid = record_id(layout["records"])
        audio_path = layout["audio"] / f"{rid}.wav"
        tmp_path: Path | None = None
        try:
            duration = None
            digest = None
            if has_audio:
                assert audio is not None
                tmp_path, _size = await save_upload(audio, layout["tmp"])
                duration, digest = transcode_audio(tmp_path, audio_path)
            now = utc_now()
            record = {
                "id": rid,
                "schema_version": 1,
                "collection": "local_consent_page_v1",
                "created_at": now,
                "synthetic": False,
                "consent": True,
                "consent_version": CONSENT_VERSION,
                "consent_text_sha256": CONSENT_SHA256,
                "consent_at": now,
                "ai_processing_consent": True,
                "no_identifiers_confirmed": True,
                "reported_language": lang,
                "input_type": "text+audio" if (story and has_audio) else "audio" if has_audio else "text",
                "narrative": story,
                "narrative_chars": len(story),
                "narrative_sha256": hashlib.sha256(story.encode("utf-8")).hexdigest() if story else None,
                "transcript_source": "typed" if story else "none",
                "audio_file": f"audio/{rid}.wav" if has_audio else None,
                "audio_seconds": duration,
                "audio_sha256": digest,
                "audio_format": "wav" if has_audio else None,
                "audio_sample_rate": 16000 if has_audio else None,
                "audio_channels": 1 if has_audio else None,
                "audio_metadata_stripped": True if has_audio else None,
            }
            write_json_atomic(layout["records"] / f"{rid}.json", record)
        except ValueError as e:
            try:
                audio_path.unlink()
            except OSError:
                pass
            return render_message("Upload not saved", f"{e}. Nothing was saved.", status=413)
        except (AudioError, subprocess.TimeoutExpired) as e:
            try:
                audio_path.unlink()
            except OSError:
                pass
            return render_message("Recording not saved", f"{e}. Nothing was saved. You can retry with a shorter recording or type your story.", status=400)
        except Exception:
            try:
                audio_path.unlink()
            except OSError:
                pass
            raise
        finally:
            if tmp_path is not None:
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
        return render_success(rid)

    return app


def _confirm(prompt: str) -> bool:
    try:
        return input(prompt).strip().lower() in ("delete", "yes", "y")
    except EOFError:
        return False


def delete_record(data_dir: Path, rid: str, *, assume_yes: bool = False) -> dict[str, Any]:
    if not ID_RE.fullmatch(rid):
        raise DataError("that is not a valid record id")
    data_dir = data_dir.expanduser().resolve()
    record_path = data_dir / "records" / f"{rid}.json"
    if not record_path.exists():
        raise DataError(f"no record with id {rid}")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    if not assume_yes and not _confirm(f"Delete {rid} and its audio? Type DELETE to confirm: "):
        raise DataError("deletion cancelled")
    audio_deleted = False
    audio_rel = record.get("audio_file")
    if audio_rel:
        audio_path = (data_dir / str(audio_rel)).resolve()
        audio_dir = (data_dir / "audio").resolve()
        if audio_dir not in audio_path.parents:
            raise DataError("audio path is outside the data directory; refusing to delete")
        if audio_path.exists():
            audio_path.unlink()
            audio_deleted = True
    record_path.unlink()
    entry = {"id": rid, "deleted_at": utc_now(), "audio_deleted": audio_deleted, "record_deleted": True}
    log = data_dir / "deletions.jsonl"
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
    _chmod(log, 0o600)
    return entry


def _play_audio(path: Path) -> bool:
    player = shutil.which("afplay") if sys.platform == "darwin" else None
    if not player:
        player = shutil.which("ffplay")
        if player:
            proc = subprocess.run([player, "-nodisp", "-autoexit", "-loglevel", "error", str(path)], check=False)
            return proc.returncode == 0
    if player:
        proc = subprocess.run([player, str(path)], check=False)
        return proc.returncode == 0
    return False


def transcribe_record(data_dir: Path, rid: str | None, *, next_missing: bool, replace: bool,
                      play: bool = True) -> dict[str, Any]:
    data_dir = data_dir.expanduser().resolve()
    records = load_records(data_dir)
    if next_missing:
        candidates = [r for r in records if r.get("audio_file") and not str(r.get("narrative") or "").strip()]
        if not candidates:
            raise DataError("no audio record is missing a transcript")
        record = candidates[0]
    else:
        if not rid or not ID_RE.fullmatch(rid):
            raise DataError("pass a valid --id or --next")
        record = next((r for r in records if r.get("id") == rid), None)
        if record is None:
            raise DataError(f"no record with id {rid}")
    if not record.get("audio_file"):
        raise DataError("that record has no audio file")
    if str(record.get("narrative") or "").strip() and not replace:
        raise DataError("that record already has a transcript; pass --replace to overwrite it")
    audio_path = (data_dir / str(record["audio_file"])).resolve()
    if not audio_path.exists():
        raise DataError("the audio file is missing")
    print(f"Record {record['id']} · {record.get('created_at')} · {record.get('audio_seconds')}s · {audio_path}")
    if play:
        if not _play_audio(audio_path):
            print("No audio player was available; open the file above and listen to it.")
    try:
        transcript = input("Type the transcript, then press Enter (blank aborts):\n> ").strip()
    except EOFError:
        transcript = ""
    if not transcript:
        raise DataError("no transcript entered; nothing changed")
    if len(transcript) > MAX_TEXT_CHARS:
        raise DataError(f"transcript is longer than {MAX_TEXT_CHARS} characters; nothing changed")
    record["narrative"] = transcript
    record["narrative_chars"] = len(transcript)
    record["narrative_sha256"] = hashlib.sha256(transcript.encode("utf-8")).hexdigest()
    record["transcript_source"] = "manual"
    record["transcript_updated_at"] = utc_now()
    write_json_atomic(data_dir / "records" / f"{record['id']}.json", record)
    print(f"Saved a {len(transcript)}-character transcript. No AI call was made.")
    return record


def list_records(data_dir: Path) -> None:
    data_dir = data_dir.expanduser().resolve()
    records = load_records(data_dir)
    if not records:
        print(f"No records in {data_dir}")
        return
    audio = sum(1 for r in records if r.get("audio_file"))
    missing = sum(1 for r in records if r.get("audio_file") and not str(r.get("narrative") or "").strip())
    print(f"{len(records)} record(s) in {data_dir}: {audio} with audio, {missing} audio without a transcript")
    print("id, created_at, reported_language, input_type, narrative_chars, audio_seconds")
    for r in records:
        print(",".join([
            str(r.get("id") or ""),
            str(r.get("created_at") or ""),
            str(r.get("reported_language") or ""),
            str(r.get("input_type") or ""),
            str(r.get("narrative_chars") or 0),
            "" if r.get("audio_seconds") is None else str(r.get("audio_seconds")),
        ]))


def _is_loopback(host: str) -> bool:
    return host in ("127.0.0.1", "localhost", "::1")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Consent-first local collection for real Hindi/Hinglish/English complaints")
    p.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    sub = p.add_subparsers(dest="cmd", required=True)

    serve = sub.add_parser("serve", help="run the local consent page")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--allow-lan", action="store_true", help="allow a non-loopback bind; there is no authentication")

    sub.add_parser("list", help="list records (metadata only; never prints stories)")

    delete = sub.add_parser("delete", help="delete one record and its audio")
    delete.add_argument("id")
    delete.add_argument("--yes", action="store_true")

    tr = sub.add_parser("transcribe", help="type a transcript for an audio record (no AI)")
    tr.add_argument("--id")
    tr.add_argument("--next", action="store_true", help="pick the oldest audio record without a transcript")
    tr.add_argument("--replace", action="store_true")
    tr.add_argument("--no-play", action="store_true")

    sub.add_parser("consent", help="print the exact consent text, version and hash")

    args = p.parse_args(argv)
    data_dir = Path(args.data_dir)

    if args.cmd == "serve":
        if not _is_loopback(args.host) and not args.allow_lan:
            print("REFUSED: there is no authentication. Pass --allow-lan only on a trusted network.", file=sys.stderr)
            return 3
        ensure_layout(data_dir)
        app = create_app(data_dir)
        if not _is_loopback(args.host):
            print("WARNING: this page has no authentication. Anyone who can reach this port can submit.")
            print("WARNING: use a trusted network; stop the server when you are finished.")
        host_display = args.host
        if args.host in ("0.0.0.0", "::"):
            try:
                host_display = socket.gethostbyname(socket.gethostname())
            except OSError:
                host_display = "this-machine"
        print(f"Serving http://{host_display}:{args.port}/")
        print(f"Data: {data_dir.resolve()} (gitignored, mode 0700)")
        print(f"Consent: {CONSENT_VERSION} sha256={CONSENT_SHA256[:16]}…")
        print("No access log, no cookies, no analytics. Press Ctrl+C to stop.")
        import uvicorn

        uvicorn.run(app, host=args.host, port=args.port, access_log=False, log_level="warning")
        return 0

    if args.cmd == "list":
        list_records(data_dir)
        return 0

    if args.cmd == "delete":
        try:
            entry = delete_record(data_dir, args.id, assume_yes=args.yes)
        except DataError as e:
            print(f"REFUSED: {e}", file=sys.stderr)
            return 3
        print(json.dumps(entry, indent=2))
        print("If data/real_hindi/labels.csv exists, re-export it or remove this id; a stale label row will be refused.")
        return 0

    if args.cmd == "transcribe":
        try:
            rec = transcribe_record(data_dir, args.id, next_missing=args.next, replace=args.replace,
                                    play=not args.no_play)
        except DataError as e:
            print(f"REFUSED: {e}", file=sys.stderr)
            return 3
        print(f"Updated {rec['id']}; narrative_chars={rec['narrative_chars']}")
        return 0

    if args.cmd == "consent":
        print(f"Consent version: {CONSENT_VERSION}")
        print(f"Consent SHA-256: {CONSENT_SHA256}")
        print()
        print(CONSENT_TEXT)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
