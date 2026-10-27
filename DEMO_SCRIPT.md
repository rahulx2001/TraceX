# TraceX + Meta AI layer: demo script

> The timestamps below are planned script cues, not measured durations. The demo
> has not been timed end to end on this machine.
>
> **Mission: help vehicle manufacturers reduce road accidents by recording
> vehicle faults from real customer contacts and predicting them early,
> before they become crashes, fires or injuries.**

Setup (one command, local, nothing deployed):

```bash
bash scripts/judge_setup.sh          # venv, deps, dashboard build, demo DBs, India scenario, serves :8000
# then open http://127.0.0.1:8000/ui/#demo, Sign in → "Have an operator API key?" → paste the key the script printed
```

> **Evidence status (2026-10-27):** no live Meta API call has been made in this
> project. The Meta-enhanced steps below are designed/mocked paths, not a
> demonstrated live run; with no key the demo is deterministic. All 84
> Hindi/Hinglish eval calls are synthetic and were added on 2026-10-21 IST, the
> same day as the deterministic lexicon. See `HACKATHON.md` §4.2 and §6.

Without a Meta key everything below runs on the deterministic path, and the badge
reads **Deterministic**. With `META_API_KEY` (or `MODEL_API_KEY`) set the
badge is intended to read **Meta AI enhanced** and the Meta model tags light up;
that path has not been exercised against the live API.
No numbers in this script are made up. Backtest figures come from
`reports/nhtsa/backtest_safety_2015_2024.md`, OOS figures from
`reports/oos/`, and eval figures from `reports/hindi_safety/HINDI_EVAL.md`.

---

## 0:00–0:20 The problem (title card, then the `#demo` page header)

Voice-over:
"Every recall starts as a few customer calls that nobody connects. In India
most of those calls are in Hindi or Hinglish. TraceX records each call as a
structured fault, clusters calls across a fleet, and warns the manufacturer
early. Today we'll add Meta's models on top of that without letting them
override any safety rule."

On screen: `#demo` page, mission banner, the **AI mode badge** in the top bar.

## 0:20–0:55 Screen 1: a Hindi/Hinglish call plus a photo

- Click **Run seeded India scenario** (or show the call widget, with the speech
  language set to **हिन्दी / Hinglish (hi-IN)**).
- Transcript: *"Namaste. Meri Honda CR-V 2019 ke brakes fail ho gaye, pedal
  neeche tak chala jata hai aur grinding ki awaaz aati hai."*
- **The key moment, shown honestly:**
  - *Pack lexicon alone (English-only)*: it does **not** match Hinglish
    "brakes fail ho gaye". Verified 2026-10-26:
    `src.ai_layer.demo.safety_contrast(...)` on this exact sentence returns
    `original_kill_switch: null`.
  - *Deterministic path that actually runs today (no Meta key)*: the pre-event
    `hindi_safety.py` layer glosses the Hinglish safety phrase and the existing
    pack lexicon fires on the gloss. Verified 2026-10-26 by running
    `python -m scripts.ai_demo_seed` on an isolated DB: the seeded case finished
    at **Critical** with safety flags `["brakes failed", "escalation"]`.
    See `reports/demo_seed_check.txt`. The seeded scenario is labelled SYNTHETIC.
  - *Meta AI enhanced* (**NOT RUN LIVE; mocked tests only**): Muse Spark is
    intended to normalise Hinglish to English, then the **existing** pack
    kill-switch runs on the translation. Because the deterministic Hindi layer
    already raises this example, Meta is **not required** for this emergency
    stop; the live Meta path has not been exercised. AI can only raise severity,
    never lower it.
- A photo of the brake rotor is attached to the case. In the demo it is a
  labelled **SYNTHETIC** image, never a real customer photo.

Tags on screen **when a key is set** (intended, **NOT RUN LIVE**): `Muse Spark 1.3`
(language normalisation). With no key the badge and tags read `Deterministic`; the
Hindi emergency stop still works through `hindi_safety.py`.

## 0:55–1:25 Screen 2: the case with photo evidence

- Open the case from the demo link (Case queue → **Photo evidence** panel).
- Click **Analyze** (requires a Meta key; **NOT RUN LIVE**): **SAM 3.1** is
  intended to return region boxes that are drawn as an overlay on the photo.
  **Muse Spark** (vision) is intended to add a short description and a component
  guess. Only mocked tests cover this path.
- Call out the safety rules: a vision finding can only *add* a flag; the photo
  is validated (type, size, magic bytes), stored on the box and linked to the
  case and its cluster/investigation; it appears in the DSR erase.

Tags: `SAM 3.1`, `Muse Spark 1.3 (vision)`.

## 1:25–1:55 Screen 3: the grounded brief

- Issue desk → the investigation the call joined (HONDA · SERVICE BRAKES).
- **Grounded brief** panel: every claim cites warehouse record IDs or recall
  advisory IDs. Each claim passes the existing **Qubot auditor**; claims that
  fail are dropped and counted, not shown.
- **Safety risk chip** (High / Elevated / Normal): computed from the
  safety-critical component tier and the crash/fire/injury mentions in the
  warehouse records. It is deterministic, not AI. In this demo the warehouse is
  the synthetic seed, so those counts are synthetic demo counts.
- **Recommended action**: the matched recall remedy comes first. Then come the
  deterministic inspection playbook steps for the component. AI-suggested
  steps are labelled "requires engineering review".

Tags: `Muse Spark 1.3` (brief wording; **NOT RUN LIVE**), `Qubot audited`.
The deterministic brief and recommended actions still render with no key.

## 1:55–2:35 Screen 4: the early-warning board

- Early-warning board → **Safety-risk board**: open investigations ranked by
  safety risk first, then by case count.
- **Backtest headline** (real NHTSA data, Honda/Toyota/Ford/Hyundai/Kia, model
  years 2015–2024; read live from `reports/nhtsa/backtest_safety.json`; this is
  the **production detector, in-sample**): **535 of 1,172 recall campaigns
  (45.6%)** had a flag episode on the same make + component within the 52 weeks
  before NHTSA received the recall report. The median lead was **11 weeks**
  (mean 15.9), scored only on complaints that had arrived by that date. Episode
  precision is 0.64 (36% of flag episodes had no later recall). In those windows
  NHTSA received **1,379 complaints marked CRASH, 712 marked FIRE and 882 with
  injuries** on the flagged slices. The separate OOS **tuned** config scored
  62.7% on 2021–2024; production `abs5` was **NOT RUN** on that test window, and
  its in-sample 2015–2020 score was 33.6%. Do not present 62.7% as production
  performance.
- Say the caveat out loud: "These are complaints filed during the window
  between our flag and the recall. They show correlation and potential
  exposure. We do not claim lives saved."

## 2:35–2:50 Close

"Meta's models are intended to make the system hear Hindi, see the part, and
write the brief. The deterministic safety rules still have the final say. We
have not made a live Meta call yet; without a key every Meta feature returns the
deterministic result. Two pre-event deterministic layers run with no key: the
Hindi/Hinglish safety layer and the OBD-II fault-code capture/severity floor.
Both can only add a kill-switch hit, slot or severity floor, never lower
anything."

Show: `reports/hindi_safety/HINDI_EVAL.md`. All **84** labelled calls are
synthetic (60 original + 24 fresh), added on 2026-10-21 IST, the same day as the
deterministic lexicon. The rules-only path recalls the kill-switch on 100% of the
English calls but on **0% of the Hindi calls**; adding `hindi_safety.py` takes
Hindi to 4/4 (original) and 6/6 (fresh), and Hinglish to 4/4 and 6/6, with one
false alarm in the fresh set. The optional Meta-enhanced column is **NOT RUN**
(no key); no live Meta call has been made.
