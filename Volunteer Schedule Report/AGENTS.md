# Volunteer Schedule Report Instructions

- Keep this project confined to this directory. Do not stage or edit sibling
  TouchPoint projects.
- TouchPoint scripts run in the hosted IronPython environment. Do not use
  f-strings, type annotations, third-party packages, or local filesystem APIs.
- Keep reporting read-only. The only permitted writes are the extension's own
  Settings/Text Content configuration and successful-send state.
- Email must default to disabled. Validate previews against the live Scheduler
  before enabling delivery.
- Each Python script must remain independently deployable in TouchPoint.
- Run `python3 -m unittest discover -s tests -v`, compilation checks, and
  `git diff --check` before handoff.
