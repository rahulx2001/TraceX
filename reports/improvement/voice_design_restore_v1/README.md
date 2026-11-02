# Restore the owner's voice-page design

The local demo now serves the owner's voice presentation at
<http://127.0.0.1:60861/ui/#call>, with sign-in still disabled in open demo mode.
The restored layout includes the compact language/pause controls, Voice options
menu, microphone illustration, conversation bubbles, report brief and progress
indicator, green accents, and responsive cards.

The apparent regression came from serving the separate worktree, which had an
older voice layout. Before this restoration, the component and CSS were
identical at `b490dd5` and `1285749`. The owner's newer visual changes were still
uncommitted in the original checkout. The user specifically requested restoring
that design; only its voice presentation was brought into this worktree. The
original files remain unchanged. Their source hashes are in `restoration.json`.

The call state machine, WebSocket behavior, authentication and stored-source
handoff remain the existing tested implementation. Unrelated auth/session
changes and an unfinished model-review API feature in the original checkout
were not imported. No frozen analysis code or model was edited.

Validation passed:

- Production dashboard build using Vite's native config loader.
- Existing browser harness against real, isolated API servers: account-free
  access, text contact, source handoff, manual investigation, review and export.
- Existing speech UI fixtures: correction history, mute/interrupt/end controls,
  pause handling, interim words, failure/retry behavior and responsive reflow.
- Sampled text contrast: minimum 5.98:1; primary Start control 9.06:1.
- Preservation checks for `main`, the original checkout and both freezes.

`validation.json` records commands, exit codes and hashes. `screenshots/` holds
the restored layout rendered by the existing synthetic voice UI test; those
images are software-test fixtures, not real speech or human-review evidence.
The real-audio quality and human-label status are unchanged. No paid calls,
prospective collection, merge or promotion occurred.
