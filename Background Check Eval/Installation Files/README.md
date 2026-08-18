# TouchPoint Background Check Evaluator

## Current component versions

- **Evaluator:** 3.1.3
- **Admin:** 3.1.2
- **Diagnostic:** 3.1.1

Each TouchPoint script is independently deployable and independently
versioned. A component version advances only when that component changes;
versions are not kept artificially aligned. Release notes identify the
affected component.

This project contains a nightly TouchPoint Python evaluator for volunteers
serving in qualifying Involvements.

## Version history

- **Evaluator 3.1.3 / Admin 3.1.2 — 2026-08-18:** Replaced
  tenant-specific installation defaults with safe empty values for public
  distribution. Existing saved `BCE.*` settings continue to prevail.
- **Evaluator 3.1.2 — 2026-08-18:** Renamed the Involvement coverage column to
  **Processing result** and clarified its values as **Evaluated successfully**
  and **Evaluation failed**.
- **3.1.1 — 2026-08-18:** Added a default-off church-wide switch that omits
  Process Builder reminder steps from evaluator reports and email while the
  integration is being tested.
- **3.1.0 — 2026-08-18:** Added the current Process Builder reminder step
  beneath Background Check Required and Meets Application Requirements.
- **3.0.4 — 2026-08-18:** Added privacy-safe Process Builder schema discovery
  to support future inline reminder-step status beneath the two eligibility
  results.
- **3.0.3 — 2026-08-18:** Ignore expired evaluate-through dates. Involvements
  with future meetings fall back to meeting evaluation; those with neither an
  active date nor future meetings drop from the report and comparison state.
- **3.0.2 — 2026-08-18:** Renamed the application column, removed the separate
  Exception column, highlighted failed check/application cells in red, and
  displays `N/A` for approved checks when the person is under the configured
  background-check age.
- **3.0.1 — 2026-08-18:** Use the standard Involvement EV only when
  `EvaluateBackgroundCheckThroughDate.DateValue` is populated; blank values
  fall back to meeting-based evaluation.
- **3.0.0 — 2026-08-18:** Replaced the deprecated
  `EvaluateBackgroundCheckThroughEndOfProgramYear` flag and separate Text
  Content dates with the date-valued Involvement EV
  `EvaluateBackgroundCheckThroughDate`.
- **2.0.3 — 2026-08-17:** Fixed Admin action routing by replacing the generic
  `action` form field with `BCEAdminAction`; failed requests now show status.
- **2.0.2 — 2026-08-17:** Fixed comparison-history reset by writing a valid
  versioned reset-state document instead of empty Text Content.
- **2.0.1 — 2026-08-17:** Finalized application evaluation and diagnostic
  coverage using the tenant-confirmed `AppStatus:`-qualified EV field names.
- **2.0.0 — 2026-08-17:** Removed the deprecated Volunteer Code path and Admin
  controls. Eligibility now uses only People EVs, with support for both
  code-only and `AppStatus:`-qualified application field storage. Expanded the
  aggregate diagnostic to expose the tenant's application EV storage shape.
- **1.2.4 — 2026-08-17:** Added the standard Bootstrap success/error classes
  to Admin toasts and simplified the successful confirmation to `Saved`.
- **1.2.3 — 2026-08-17:** Kept Admin saves, baseline initialization, and
  history reset inside the TouchPoint frame using in-place form responses.
- **1.2.2 — 2026-08-17:** Matched successful and failed Admin save feedback
  to the established TouchPoint bottom-center toast pattern.
- **1.2.1 — 2026-08-17:** Fixed the Admin form response so successful saves
  redisplay the page with the standard bottom toast, and made person Extra
  Values override corresponding legacy Volunteer Codes during migration.
- **1.2.0 — 2026-08-17:** Added the
  `EvaluateBackgroundCheckThroughEndOfProgramYear` Involvement Extra Value,
  per-Involvement program-year dates, evaluation without meetings, current-age
  qualification, nightly coverage/error reporting, and partial comparison
  state updates.
- **1.1.0 — 2026-08-16:** Added People Extra Value eligibility rules,
  transition support for legacy Volunteer Codes, an Admin migration toggle,
  privacy-safe migration diagnostics, and versioned JSON comparison state.
- **1.0.0 — 2026-07-28:** Added the church-wide configurator, age exemption,
  one-row-per-person output, and new-versus-ongoing nightly comparison.

## Locked business rules

- Qualifying hierarchy:
  - Program: `Administration`
  - Division: `Requires Volunteer Application`
- Include an active qualifying Involvement when either:
  - it has a non-cancelled meeting from the run date through the configured
    lookahead window; or
  - its `EvaluateBackgroundCheckThroughDate` Involvement EV has a `DateValue`
    on or after the evaluation date.
- For an Involvement without that EV, evaluate current, non-pending members against
  its latest qualifying meeting in the lookahead window.
- For an Involvement with that EV, evaluate all current, non-pending members—even
  when it has no upcoming meeting—against the EV's `DateValue`.
- A volunteer passes only when:
  - at least one non-training, non-MVR background check is `Approved`;
  - once the person has actually reached the configured minimum age, that
    approval is no more than 33 calendar months old on the required-through
    date;
  - both People Extra Values are checked:
    - `AppStatus:Application Approved:1`
    - `AppStatus:Application on File:1`
  - neither People Extra Value is checked:
    - `College Student (no background check):1`
    - `Individual Refuses Background Check:1`
- Legacy Volunteer Codes are deprecated and are never read by the evaluator.
- A newer pending check does not invalidate another currently valid approved
  check.
- Produce one report row per person. Combine that person's affected service
  dates, Involvements, and unique exception reasons within the row.
- Compare each successful production run with the prior successful run and
  show new exceptions before ongoing exceptions.
- When email is enabled, send a nightly report on every completed run,
  including coverage, exceptions, and recoverable Involvement errors.
- Send a separate failure notification for missing or invalid evaluate-through dates,
  Involvement-level query failures, or a fatal evaluator failure.
- Never change people, memberships, meetings, checks, or volunteer records.

## Email configuration

Email configuration defaults to empty and delivery defaults to disabled.
Use the Admin app to select the queued-by person and recipients and enter the
sender name and address. Complete a controlled staff-only preview and email
test before enabling nightly delivery.

## Phase 1: schema diagnostic

Install `BackgroundCheckEvalDiagnostic.py` temporarily under:

`Admin > Advanced > Special Content > Python Scripts`

Suggested name: `BackgroundCheckEvalDiagnostic`

Run it manually as an administrator. It performs read-only metadata and
aggregate queries and sends no email. Return the rendered results so the
production query can be finalized without guessing:

- application and `AppStatus` People EV field/type/value storage
- MVR identification fields
- qualifying Program and Division IDs
- background-check date/status columns
- `dbo.PeopleExtra` columns, target field names, data types, and aggregate
  migration coverage
- `dbo.OrganizationExtra` columns and all qualifying Involvements with
  `EvaluateBackgroundCheckThroughDate`

Do not enable the production evaluator in Morning Batch until these results
have been reviewed.

## Diagnostic review

Run and review the diagnostic in the live tenant before deploying the
evaluator. Confirm the qualifying Program and Division, background-check
storage, excluded training report type, and Extra Value field names. It
intentionally
returns only schema information and aggregate counts—never names, People IDs,
email addresses, or person-level values. Confirm that all four target rows use
`Type = Bit` and that checked rows use `BitValue = 1`.

## Phase 2: production evaluator

Install `BackgroundCheckEvaluator.py` as a TouchPoint Python Script with the
suggested name `BackgroundCheckEvaluator`.

Email defaults to disabled through the church-wide setting. Run the evaluator
manually and verify:

1. Only meetings in the qualifying Program and Division appear.
2. Meeting dates cover today through 30 calendar days ahead.
3. Current, non-pending Involvement members are included.
4. Person and Involvement links open the expected TouchPoint records.
5. Each exception reason agrees with the person’s Volunteer and Extra Values
   tabs.
6. MVR and training records are not treated as qualifying background checks.
7. A person with an older valid Approved check and a newer Pending check still
   passes the background-check portion.
8. A check exactly 33 calendar months old on the required-through date passes.
9. Both AppStatus application EVs are required; legacy Volunteer Codes are
   ignored.
10. College and refusal EVs cause the applicable exception.
11. An Involvement with `EvaluateBackgroundCheckThroughDate` appears without
    meetings and uses that EV date.
13. A person does not require a background check before their actual 18th
    birthday, even when the required-through date is later.
13. A missing evaluate-through DateValue appears as a failed Involvement in the
    nightly report and also triggers the failure notification.

After live preview validation, conduct one controlled staff-only email test.
Only then enable delivery in the configurator. Finally, call the script from
the existing `MorningBatch` script:

```python
print(model.CallScript("BackgroundCheckEvaluator"))
```

The evaluator sends the nightly report even when the exception list is empty.
A fatal failure that prevents a reliable report sends only the failure
notification, leaves comparison history unchanged, and re-raises the error so
the batch run is marked failed.

## Church-wide configurator

Install `BackgroundCheckEvaluatorAdmin.py` as a TouchPoint Python Script named
`BackgroundCheckEvaluatorAdmin`. It requires the `Admin` role and manages one
church-wide evaluator configuration.

Open it through `/PyScript/BackgroundCheckEvaluatorAdmin`. If it is registered
as a Custom Report, keep both the Python script directive and the Custom Report
menu role restricted to `Admin`; menu visibility is configured separately from
script authorization. Form submissions and live person searches are routed to
`/PyScriptForm/BackgroundCheckEvaluatorAdmin` by the page.

The configurator controls:

- Program, Division, and lookahead window
- read-only visibility into Involvement evaluate-through dates
- background-check validity period
- minimum background-check age
- required and excluded People Extra Values
- email sender, coordinator, and recipients
- production email activation

The background-check age requirement begins only after the person has actually
reached the configured minimum age as of the nightly run date. Future birthdays
are not anticipated. Application and exclusion rules still apply regardless of
age. A missing birthdate cannot establish the exemption and therefore still
requires a background check.

The evaluator uses safe defaults when a setting has not yet been saved. Email
defaults to disabled.

Settings are stored with the compact `BCE.` prefix because TouchPoint limits
`Setting.Id` to 50 characters. Earlier `BackgroundCheckEvaluator.*` setting
names are intentionally ignored; this avoids loading any partial configuration
left by a failed save using the original, overlong namespace.

The configurator manages these Settings keys:

- `BCE.EmailEnabled`
- `BCE.ShowProcessReminderSteps` (defaults to `false`)
- `BCE.QueuedByPeopleId`
- `BCE.ReportRecipientPeopleIds`
- `BCE.FailureRecipientPeopleIds`
- `BCE.FromAddress` and `BCE.FromName`
- `BCE.ProgramId` and `BCE.DivisionId`
- `BCE.LookaheadDays`, `BCE.BackgroundCheckValidMonths`,
  `BCE.MinimumBackgroundCheckAge`, and `BCE.TrainingReportTypeId`

The coordinator and recipient controls use live TouchPoint person search.
Administrators search by name, email address, or People ID and select the
matching person by displayed name. The configurator stores People IDs
internally because they remain stable if a person's name or email changes.

### Involvement evaluate-through dates

The Admin app displays only active qualifying Involvements whose
`EvaluateBackgroundCheckThroughDate` is today or later. Blank and expired
values are ignored. If such an Involvement has a future meeting, it falls back
to meeting-based evaluation; otherwise it drops from the report and comparison
state. Administrators change the date on the Involvement's Extra Values tab;
the evaluator does not write Involvement records.

A missing or invalid date does not stop other Involvements. The affected
Involvement is marked failed in the nightly coverage table, its corrective
error is included in the nightly report, and the failure recipients receive a
separate notification. That Involvement's prior comparison state is retained.

### Volunteer Extra Value storage

TouchPoint stores items from this checkbox-list Extra Value as separate
`dbo.PeopleExtra` rows. The tenant diagnostic confirmed that the physical
`Field` values are `AppStatus:Application Approved` and
`AppStatus:Application on File`; both must have `BitValue = 1`. The aggregate
diagnostic reports the matching application fields, types, and stored values
without exposing person identity.

Disabling email with `BCE.EmailEnabled` stops report and failure email while
retaining manual preview capability.

`BCE.ShowProcessReminderSteps` controls only the optional Process Builder
status lines. It defaults to disabled. When disabled, reminder-process details
are omitted from both manual reports and nightly email; all background-check,
application, exclusion, age, coverage, history, and email-delivery evaluation
continues normally.

### Nightly comparison history

The evaluator stores a small versioned JSON comparison record in Text Content
named `BackgroundCheckEvaluatorState`. It contains only:

- a version number;
- the production-run timestamp and incomplete-run status;
- failed Organization IDs; and
- required-through metadata and exception People IDs by Organization ID.

Version 1.2.0 reads the original line-based and version 2 JSON formats and
writes JSON schema version 3 on the next production update. If that first v3
run is incomplete, the older flat People-ID baseline is retained until a
complete run can replace it safely.

Each report now presents:

1. **New exceptions** — people absent from the prior successful run;
2. **Ongoing exceptions** — people present in both runs; and
3. a count of people no longer listed since the prior run.

The comparison is person-based, so a volunteer still appears only once even
when multiple services or exception reasons apply.

History advances after the nightly report is successfully queued. Completed
Involvements replace their own prior state. Failed Involvements retain their
previous state so skipped work cannot create false resolutions. Preview runs
with email disabled do not change history. A complete run with no exceptions
saves empty per-Involvement exception lists so a later reappearance is treated
as new.

The configurator's **Nightly comparison history** card provides two
administrator actions:

- **Initialize current results as baseline** evaluates the current data,
  stores those People IDs, and sends no report email. Use this before the first
  nightly run if the existing list should begin as ongoing rather than new.
- **Reset comparison history** removes the baseline. The next successful
  production run will treat all current exceptions as new.

### Deprecated Volunteer Codes

Version 2.0.0 no longer queries the legacy Volunteer Code assignment table or
uses the previous `BCE.UseLegacyVolCodes` and Volunteer Code ID settings.
that `PeopleId` joins to `dbo.Volunteer.PeopleId` and `ApprovalId` joins to
`lookup.VolunteerCodes.Id`. The production evaluator now uses this exact
physical name.

The diagnostic's direct-access count query also now uses the confirmed table
name and avoids `RowCount` as an unquoted alias.

## Privacy behavior

The evaluator report contains volunteer names, required-through dates,
Involvement names, eligibility status, coverage status, and exception or error
reasons. It does not include email addresses or phone numbers. Every configured
report recipient receives the complete report. Recipient selection is
therefore limited to the Admin-only configurator and should contain only
authorized staff.

## Local validation

Run:

```bash
python3 -m unittest discover -s "Development Resources/tests" -v
python3 -m py_compile "Installation Files/BackgroundCheckEvaluator.py" \
  "Installation Files/BackgroundCheckEvaluatorAdmin.py" \
  "Installation Files/BackgroundCheckEvalDiagnostic.py"
```

Local tests cannot establish production success. The remaining live checks are
the version 2.0.0 diagnostic, Admin rendering of every flagged Involvement,
manual previews with configured and deliberately missing dates, preview in
EV-only mode, a controlled staff-only two-email error test, a clean controlled
nightly email, the following Morning Batch execution, and the resulting
version 3 `BackgroundCheckEvaluatorState` update.
