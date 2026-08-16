# TouchPoint User Interface Standards

These conventions are based on the Volunteer Schedule Report and apply to new
and updated TouchPoint projects in this workspace. A project may depart from a
convention only when its workflow requires it; document the reason in that
project's README or `AGENTS.md`.

## Design goals

- Make the primary task obvious without requiring TouchPoint expertise.
- Prefer plain language, progressive disclosure, and safe defaults.
- Keep operational setup, report output, and administrative configuration
  visually and functionally distinct.
- Preserve TouchPoint's familiar Bootstrap-style controls while adding only
  narrowly scoped project CSS.
- Design every interface for desktop, narrow screens, email, and printing as
  applicable.

## Application versioning and release history

- Assign every TouchPoint project an application version using semantic
  versioning: `MAJOR.MINOR.PATCH`.
- Keep the current application version in one code constant such as
  `APP_VERSION`. Render that same value in the primary setup or administration
  screen header so operators can identify the deployed version without opening
  the script editor.
- Place a concise, dated version-history block in the header of every
  independently deployed Python script. Keep TouchPoint-required directives,
  especially first-line `#Roles=`, in their required positions ahead of the
  version block.
- Include the following author attribution in the code header of every
  TouchPoint project script in this workspace:

  ```python
  # Written by: Brian Bullock with Codex assistance
  # Email: bbbullock@mac.com
  # GitHub: https://github.com/bbbullock/TouchPoint
  ```

- For each version-history entry, record significant user-facing features,
  data or configuration migrations, authorization changes, delivery or
  automation changes, and important operational safeguards. Do not clutter the
  header with inconsequential refactors or formatting-only edits.
- Increment `MAJOR` for incompatible behavior or configuration changes,
  `MINOR` for backward-compatible features, and `PATCH` for
  backward-compatible fixes. Remove prerelease labels such as `beta` only as a
  deliberate release decision.
- Keep application versions separate from versioned JSON or other stored-data
  schema versions. Changing the application version must not silently change a
  configuration document version or break existing saved data.
- Mirror the code-header history in the project README, and add a source or
  rendering test that confirms the version constant matches the version shown
  in the interface.

## Page structure and visual hierarchy

- Use one centered content shell with a practical maximum width of roughly
  1,180 pixels.
- Use `"Helvetica Neue", Helvetica, Arial, sans-serif` as the standard font
  stack for TouchPoint project interfaces and report output. This closely
  matches TouchPoint's clean, open typography while retaining system-safe
  fallbacks without downloading a web font.
- Prefer regular or light-looking heading weights (approximately 300–400 when
  available) and regular body text. Use heavier weight selectively for labels,
  table headings, and operational exceptions; do not simulate thin type at
  small sizes.
- Place related settings in white panels or sections with a light border,
  modest radius, consistent padding, and clear section headings.
- Use a two-column grid for related desktop fields and collapse it to one
  column at approximately 700 pixels.
- Let complex selectors, notices, and action rows span the full grid width.
- Keep spacing consistent between labels, controls, help text, selected items,
  and action groups.
- Use semantic heading levels in order. Avoid duplicate page titles in a
  report-only preview.

## Labels, explanations, and terminology

- Use short, task-oriented labels such as `Staff Recipients`, `Start date`, and
  `Preview report`.
- Avoid presenting two similar checkboxes when one is a type or status and the
  other is an action. Display type as informational text; reserve checkboxes
  for user-controlled on/off behavior.
- Put concise, muted help text immediately below any control whose effect may
  be misunderstood.
- State irreversible changes before the action and require confirmation when
  the user performs them.
- Use consistent terminology across the operational app, Admin app, report,
  email, documentation, and error messages.

## Controls and actions

- Use TouchPoint/Bootstrap-compatible controls: `form-control`, `btn`,
  `btn-primary`, `btn-default`, `btn-danger`, `alert`, and `help-block` where
  available.
- Use the primary button style for the main safe action on a screen.
- Use the default/secondary style for optional or supporting actions.
- Use the danger style only for destructive actions and require an explicit
  confirmation before deletion.
- Disable unavailable actions and explain why nearby. Do not rely on a disabled
  control alone to communicate a rule.
- Preserve entered values and selections after validation errors.
- Warn before replacing unsaved form changes when loading another preset or
  record.
- Do not let merely selecting a preset trigger email, automation, persistence,
  or another external effect.

## Search and multi-select behavior

- Search by a human-friendly value and stable TouchPoint ID where practical.
- Begin live search only after enough input is present to avoid noisy queries.
- Display matching name, stable ID, and relevant contact information in search
  results when authorized and useful.
- Represent selected records as removable pills or chips.
- Store stable IDs in hidden form fields; resolve current display and contact
  data at runtime.
- Deduplicate selected records and recipients.

## Defaults and progressive disclosure

- Default optional and privacy-sensitive choices to off.
- Hide conditional notices and secondary controls until their triggering
  option is selected.
- When a conditional option is cleared, disable or clear dependent behavior as
  needed so hidden state cannot cause an unexpected action.
- Display record type or automation eligibility as status text. Show conversion
  controls only when conversion is possible.
- Keep automated delivery disabled when creating or converting a profile until
  an Administrator explicitly enables it.

## Feedback and validation

- Show success feedback with `alert-success`, informational status with
  `alert-info`, and errors with `alert-danger`.
- Place feedback near the top of the affected panel or page so it is visible
  after submission.
- Write errors as corrective instructions, not implementation details.
- Validate on the server even when JavaScript also guides or disables controls.
- Escape all rendered feedback and database-derived content.
- Preserve other profiles or records when one operation fails.

## Privacy and email disclosure

- Keep email address and phone display options unchecked by default.
- Show the Contact Information Notice only while at least one contact field is
  selected.
- Explain that every recipient receives the complete report when that is true.
- Require affirmative authorization before saving volunteer delivery that
  exposes contact details.
- Keep recipient selection separate from choosing which contact columns appear
  in the report.
- Display email-disabled status and configuration guidance beside the email
  action.

## Profiles and administrative behavior

- Clearly distinguish standalone/manual profiles from automated profiles in
  selectors, lists, and Admin screens.
- Permit operational users to use an automated profile as a preset without
  allowing them to edit its automated configuration.
- Keep automation management in an Admin-only interface.
- Present profile type as status. Use a separate, clearly worded checkbox for
  whether the automated profile is currently enabled.
- Treat conversion to an automated profile as a deliberate, confirmed action;
  do not enable automated delivery as a side effect of conversion.
- Use unique, case-insensitive profile names and stable profile IDs.
- Do not save one-time report dates in reusable profiles unless the project
  explicitly requires fixed dates.

## Report presentation

- Lead with the report title, inclusive date window, and the most important
  operational totals.
- Keep a small set of related metrics in a single row when it remains readable.
  Collapse or simplify gracefully on narrow screens.
- Use consistent status colors: green for confirmed/covered, amber for pending,
  and red for vacancies, unresolved substitutions, errors, or other critical
  exceptions.
- Show both summary-level exception counts and the specific affected job or
  record so users can act on the problem.
- Put definitions and interpretation guidance at the bottom in smaller,
  footnote-like text.
- Escape names, contact details, labels, and other dynamic report content.

## Preview behavior

- Open a report preview in a separate browser tab when users benefit from
  keeping their setup parameters available.
- Render only the report in the preview tab. Do not repeat setup forms,
  administrative panels, or redundant TouchPoint page headings.
- Preview must use the exact submitted parameters and must not save, send, or
  update automated processing state.
- Display validation errors in the preview tab if submitted parameters cannot
  produce a report.

## Print behavior

- Make `Print Report` a prominent primary action on the report-only preview.
- Print an isolated copy of the report instead of the surrounding TouchPoint
  page. Include the report's own styles and exclude navigation, setup controls,
  and action buttons.
- Use `no-print` classes and print media rules as a fallback.
- Avoid page breaks inside a single job, slot, card, or other compact unit when
  practical.
- Verify actual browser print-preview thumbnails; an on-screen preview alone
  does not validate print behavior.

## Accessibility and resilience

- Use real `label` elements and descriptive button text.
- Use `type="button"` for buttons that must not submit a form.
- Provide accessible names for icon-only remove controls and titles for helper
  frames where used.
- Do not communicate status by color alone; include visible text and counts.
- Maintain usable contrast and readable font sizes.
- Ensure the core form and server-side actions remain understandable if
  JavaScript enhancements fail.

## Required UI validation

- Test initial defaults, conditional visibility, validation-error state,
  successful state, edit state, read-only state, and destructive confirmation.
- Test selectors with no results, duplicate selections, inactive IDs, and
  missing contact information.
- Test both Admin and non-Admin authorization behavior.
- Test desktop and narrow-screen layouts.
- Test report-only preview, email rendering where applicable, print-preview
  thumbnails, and printed/PDF output.
- Add source or rendering tests for critical labels, safe defaults, conditional
  notices, escaping, preview isolation, and print isolation.
