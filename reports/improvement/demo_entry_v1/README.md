# Account-free local demo entry

Requested by Rahul Kumar Singh on 2026-11-01. A local server explicitly
reporting `auth_required: false` opens the demo without an account page.
Sign-in and sign-up bookmarks redirect to the demo or their valid internal
destination. The account forms do not flash during startup, and account
buttons are absent from the desktop and mobile navigation.

Authentication-required deployments retain their login flow and backend
authorization. Open-mode visitors still have agent authority; this change
does not mint credentials or grant supervisor permissions. The missing
`SESSION_SECRET` error from attempting account entry is avoided because the
local demo no longer enters that flow.

Validation: native-loader dashboard build passed, seven existing auth-wiring
tests passed, and the real browser harness passed against temporary open and
authenticated servers. It tests fresh sign-in/sign-up bookmarks, internal and
invalid destinations, no mounted account form, absent desktop/mobile account
controls, mobile Report navigation, authenticated rejection/acceptance, and
the existing ML evidence and voice workflow assertions.

The first browser run tried to close the mobile menu by clicking the header
behind its overlay. That test interaction timed out. The corrected test uses
the visible Report navigation item; its successful run is in `browser_retry/`.
No application change was needed for that test interaction.

Build and browser commands use the existing handover validation runner with a
new output directory; it clears provider keys and uses native Vite config
loading to preserve shared dependencies. Logs and metadata retain the exact
commands and hashes. The recorded code commit is the parent; `validation.json`
pins the working-tree source files exercised before this change was committed.

Both prospective freezes, baseline scores, `main` and the original checkout
were verified unchanged. No fitting, collection, merge, promotion or paid call
occurred. This updates the demo interface; it adds no model-performance evidence.
