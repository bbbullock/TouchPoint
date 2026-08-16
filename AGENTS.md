# TouchPoint Project Standards

These standards apply to every TouchPoint project under this directory unless
a project-specific `AGENTS.md` adds stricter requirements.

All new or materially updated user interfaces must also follow
`TOUCHPOINT_UI_STANDARDS.md`. Project-specific exceptions must be documented.

## Scope and change control

- Keep work confined to the requested project directory. Do not edit, stage,
  commit, or deploy sibling projects.
- Treat existing working-tree changes as belonging to the user. Preserve them
  and stage only explicitly requested files.
- Begin unfamiliar integrations and schema-dependent reports with a read-only
  diagnostic. Confirm tenant-specific behavior before implementing writes or
  enabling delivery.
- Make small, reviewable changes. Use a preview-first workflow for report,
  email, print, and user-interface changes.
- Clearly distinguish local implementation, local validation, TouchPoint
  deployment, and live production verification.

## TouchPoint runtime compatibility

- Assume hosted IronPython compatibility. Do not use f-strings, type
  annotations, third-party packages, or local filesystem APIs in deployed
  TouchPoint scripts.
- Keep every Python script independently deployable through TouchPoint.
- Treat the first-line `#Roles=` directive as the single source of truth for a
  script's normal interactive authorization. Do not duplicate the same role in
  `model.UserIsInRole(...)`; TouchPoint evaluates the directive before running
  the script. Use explicit runtime role checks only for actions within the
  script that require stricter authorization, such as administration or batch
  processing. Keep Custom Reports menu roles aligned separately because menu
  visibility is a distinct configuration layer.
- Load Custom Reports through `/PyScript/`. Submit forms and live-search/AJAX
  requests through `/PyScriptForm/`, and set `model.Form` when rendering forms.
- Escape all user-, person-, Involvement-, and database-derived values before
  placing them in HTML or JavaScript.
- Use stable TouchPoint IDs for stored references. Resolve current names and
  contact details at runtime.

## Data and SQL safety

- Keep reports read-only with respect to people, Involvements, meetings,
  attendance, assignments, commitments, and other TouchPoint source records.
- Permit writes only to the extension's own Settings, Text Content
  configuration, and narrowly defined processing state.
- Use parameterized SQL for user-controlled values. Validate any ID lists
  before interpolating their validated integer values into `IN` clauses.
- Use half-open date windows: midnight at the beginning of the first selected
  date through, but not including, midnight following the final selected date.
- Bind SQL date parameters as midnight .NET `DateTime` values in TouchPoint.
- Deduplicate history or assignment records deterministically and document the
  applicable status and exclusion rules.

## Configuration and automation

- Store compact global settings under an extension-specific prefix.
- Store structured configuration and state as versioned JSON in Text Content.
  Preserve backward compatibility explicitly when adding fields.
- Separate manual profiles/actions from automated profiles/actions. Manual
  activity must not update automated duplicate-send state.
- Make scheduled processing idempotent, isolate individual profile failures,
  and continue processing remaining profiles when safe.
- Require `Admin` for configuration and automation. Grant operational report
  access only to the minimum additional role needed by the project.

## Email and privacy

- Email must default to disabled. Do not enable it as part of deployment.
- Validate the live report against TouchPoint before any email test. Begin with
  a controlled staff-only test before enabling volunteer or broad delivery.
- Require configured queued-by identity, sender name/address, and appropriate
  failure recipients before enabling email.
- Minimize contact information by default. Email and phone display options
  should begin unchecked unless the project explicitly requires otherwise.
- Clearly disclose when recipients will receive a complete report containing
  other people's contact information, and require affirmative confirmation
  before saving that delivery configuration.
- Resolve recipient email addresses at send time, deduplicate recipients, and
  report people without usable addresses.

## Reports and user interface

- Follow the detailed conventions in `TOUCHPOINT_UI_STANDARDS.md`.
- Use plain-language labels and short explanations for controls whose effects
  could be confused.
- Show notices only when they are relevant to the options currently selected.
- Keep report previews separate from setup controls when practical.
- Print only an isolated report view; exclude TouchPoint navigation, setup
  controls, and print buttons from printed output.
- Preserve readable print layouts and visually emphasize vacancies, unresolved
  substitute needs, failures, and other operational exceptions.

## GitHub project structure and publication

- Use two sister folders within each published project:
  - `Installation Files` contains the project README, deployable source and
    scripts, required installation or diagnostic assets, and a `Screenshots`
    folder when visual examples are useful.
  - `Development Resources` contains automated tests and other maintainer-only
    resources that are useful for validating or extending the project but are
    not required for installation.
- Keep project files out of the project root except when a tool requires a
  root-level control file such as `.gitignore`, a package manifest, or a
  platform-specific configuration. Document any exception in the README.
- Include only diagnostics that an installer may need to run. Never publish
  completed diagnostic output, tenant exports, generated reports, temporary
  files, caches, local configuration, credentials, secrets, or production
  data.
- Do not publish project-specific `AGENTS.md` or other internal agent-working
  instructions. Repository-wide standards may remain at the repository root.
- Place screenshots under `Installation Files/Screenshots`. Use only current,
  purposeful examples and remove or replace all real names, email addresses,
  phone numbers, People IDs, tenant identifiers, credentials, and other
  private information before publication.
- Keep regression tests in `Development Resources/tests` rather than removing
  them merely to simplify installation. Installation documentation must use
  paths that match the published folder structure.
- Before staging or pushing, review the exact Git file list and scan new text,
  images, PDFs, exports, and configuration files for sensitive or unnecessary
  content. Removing a file in a later commit does not remove it from Git
  history; treat history rewriting as a separate, explicitly approved action.

## Validation, documentation, and handoff

- Add or update tests for boundaries, permissions, status rules, escaping,
  privacy defaults, saved configuration, automation safeguards, and failure
  isolation as applicable.
- Before handoff, run the project's full unit-test suite, Python compilation
  checks for every deployed script, and `git diff --check`.
- Document installation, script names, Custom Report registration, Settings and
  Text Content keys, Morning Batch setup, privacy behavior, validation steps,
  and rollback or disable procedures.
- Do not claim production success from local tests. Identify the exact live
  preview, controlled email, batch, log, or state checks still required.
- Commit only the intended project files. Leave unrelated and intentionally
  unstaged files untouched.
