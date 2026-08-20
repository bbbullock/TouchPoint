# TouchPoint Background Check Evaluator

## Current component versions

- **Evaluator:** 3.3.0
- **Volunteer Status Updater:** 1.9.0
- **Volunteer Status Updater Admin:** 1.12.0
- **Background Check Evaluator Admin:** 3.3.0
- **Diagnostic:** 3.7.0

Each TouchPoint script is independently deployable and independently
versioned. A component version advances only when that component changes;
versions are not kept artificially aligned. Release notes identify the
affected component.

This project contains a nightly TouchPoint Python evaluator for volunteers
serving in qualifying Involvements and a separate updater for the standard
person Extra Value `Approved for Role`.

## Version history

- **Evaluator 3.3.0 / Evaluator Admin 3.3.0 / Updater 1.9.0 / Updater Admin
  1.12.0 / Diagnostic 3.7.0 — 2026-08-20:** Standardized user-facing
  terminology as background check and MVR. Added independently configured MVR
  service codes, a 12-month MVR validity period, latest-result MVR approval,
  `PrimaryVolunteerMVR`, and automatic fallback to `PrimaryVolunteer` when
  the background check remains valid but the MVR is expired or not Approved.
- **Evaluator 3.2.0 / Evaluator Admin 3.2.0 / Updater 1.8.0 / Updater Admin
  1.11.0 — 2026-08-20:** Added independent, required positive allowlists of
  provider `ServiceCode` values for qualifying background checks.
  MVR, training, legacy-ambiguous, and future unknown codes cannot satisfy the
  background-check requirement. A complete application with only a current
  Approved MVR now produces `MissingInfo`; only a latest background-check `Not
  Approved` result produces `Denied`.
- **Diagnostic 3.6.0 — 2026-08-20:** Added privacy-safe background-check
  label definitions, provider classification fields, and aggregate correlation
  with legacy MVR and training dates so regular checks can be distinguished
  without displaying names or People IDs.
- **Updater 1.7.0 / Updater Admin 1.10.0 / Diagnostic 3.5.0 — 2026-08-19:**
  Removed `NotApproved` as an `Approved for Role` option and excluded deceased
  and archived people from evaluation. The background-check result `Not
  Approved` continues to produce `Denied`.
- **Updater 1.6.0 / Updater Admin 1.9.0 / Diagnostic 3.4.0 — 2026-08-19:**
  Changed incomplete applications to `MissingInfo` and removed the obsolete
  newer Denied/Adverse override from the decision table.
- **Updater 1.5.0 / Updater Admin 1.8.0 / Diagnostic 3.3.0 — 2026-08-19:**
  Added `Denied` when the latest qualifying background check is `Not Approved`
  or the Boolean person Extra Value `Ineligible Volunteer` is checked. Added
  both inputs to candidate discovery and added readiness/diagnostic coverage.
- **Updater Admin 1.7.0 — 2026-08-18:** Removed exception-based lookup
  termination. TouchPoint was appending a `SystemExit` traceback after valid
  lookup JSON, causing all three live searches to reject the response.
- **Updater Admin 1.6.0 — 2026-08-18:** Live-search failures now display a
  bounded HTTP status or response summary to Admins instead of hiding every
  server or routing failure behind the generic `Lookup failed` message.
- **Updater Admin 1.5.0 — 2026-08-18:** Aligned all updater live-search
  routing and browser requests with the live-proven implementation in
  `BackgroundCheckEvaluatorAdmin`.
- **Updater Admin 1.4.0 — 2026-08-18:** Repaired Volunteer Application
  Involvement, queued-by person, and recipient live search. Explicit lookup
  actions now route independently, and the Involvement control is excluded
  from person-picker initialization.
- **Updater 1.4.0 / Updater Admin 1.3.0 — 2026-08-18:** Made current,
  non-pending membership in the configured Volunteer Application Involvement
  the sole authority for Application on File. The updater now checks the value
  for members and clears it for pending, inactive, or absent candidates.
- **Updater 1.3.0 / Updater Admin 1.2.0 — 2026-08-18:** Added an
  Admin-selected Volunteer Application Involvement. Current, non-pending
  members become candidates and have Application on File set to checked before
  their Approved for Role value is evaluated.
- **Updater 1.2.0 / Updater Admin 1.1.0 — 2026-08-18:** Removed
  Involvement Program/Division scope. Candidates now come from existing
  `Approved for Role`, checked application EVs, or a current Approved
  background check.
- **Updater 1.1.0 / Updater Admin 1.0.0 — 2026-08-18:** Separated all
  updater configuration into `VolunteerStatusUpdaterAdmin` and made runtime
  scope, validity, age, sender, recipient, email, and activation settings
  independently owned under `VSU.*`.
- **Updater 1.0.0 / Diagnostic 3.2.0 — 2026-08-18:** Added
  preview-first `Approved for Role` evaluation, default-off changed-only
  writes, optional change/failure email, Admin activation safeguards and run
  summary, and privacy-safe definition/storage diagnostics.
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

## Evaluator business rules

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
  - at least one background check with an Admin-configured qualifying regular
    provider `ServiceCode` is `Approved`;
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
- The evaluator never changes people, memberships, meetings, checks, volunteer
  records, or person Extra Values.

## Approved for Role updater rules

The updater writes only the standard person Code Extra Value named
`Approved for Role`, using exactly one of these configured options:

- `PrimaryVolunteer`
- `PrimaryVolunteerMVR`
- `SecondaryVolunteer`
- `SecondaryVolunteerExpiredBackground`
- `Denied`
- `MissingInfo`

Its candidate population is the union of:

- people who currently have any stored `Approved for Role` value;
- people with `AppStatus:Application on File` checked;
- people with `AppStatus:Application Approved` checked;
- people with `Ineligible Volunteer` checked;
- people with a current Approved background check or MVR, or a latest
  background check of `Not Approved`; or
- current, non-pending members of the configured Volunteer Application
  Involvement.

Program and Division are not used. The only membership considered is the
Admin-selected Volunteer Application Involvement. Having any one of these
candidate conditions causes the complete decision table to be applied.
Deceased and archived people are excluded from evaluation.

Membership in the Volunteer Application Involvement is the sole authority for
whether the application is on file. For every candidate, the updater checks
`AppStatus:Application on File` when the person is a current, non-pending
member and clears it when the person is pending, inactive, or absent. Preview
reports each proposed set or clear. Production synchronizes that checkbox
before calculating and writing Approved for Role.

The status is calculated as of the Morning Batch run date:

- A latest background check of `Not Approved`, or a checked
  `Ineligible Volunteer` Boolean Extra Value, produces `Denied`. This rule
  takes precedence over all other outcomes.
- Both `AppStatus:Application on File` and
  `AppStatus:Application Approved` must be checked. Otherwise the result is
  `MissingInfo`.
- A complete application plus a current Approved, in-date background check
  and a latest Approved, in-date MVR produces `PrimaryVolunteerMVR`.
- A complete application plus a current Approved, in-date background check
  without a valid MVR produces `PrimaryVolunteer`. This includes automatic
  fallback from `PrimaryVolunteerMVR` when the MVR expires or its latest
  result is not Approved.
- A complete application with no Approved check of any type produces
  `SecondaryVolunteer`; Pending, Error, and Cancelled records do not count as
  approval.
- A complete application with an expired Approved background check produces
  `SecondaryVolunteerExpiredBackground`.
- A complete application with only a current Approved MVR produces
  `MissingInfo`.
- A newer Pending background-check result does not invalidate a current
  background-check approval. The latest MVR record must itself be Approved.
- MVR validity uses its configured calendar-month period and expires on the
  anniversary date; the default is 12 months.
- A person below the configured minimum background-check age with a complete
  application is `SecondaryVolunteer`. A missing birthdate follows the normal
  adult background-check rules.
- College and refusal flags do not override these updater rules.

The updater changes only values that differ. A failure for one person is
reported without preventing safe updates for the remaining people.

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
- background-check label definitions, provider classification fields, and
  aggregate MVR/training date correlation
- qualifying Program and Division IDs
- background-check date/status columns
- `dbo.PeopleExtra` columns, target field names, data types, and aggregate
  migration coverage
- `dbo.OrganizationExtra` columns and all qualifying Involvements with
  `EvaluateBackgroundCheckThroughDate`
- the `Approved for Role` definition in `StandardExtraValues2`, including its
  Code type and all six required options
- aggregate stored `Approved for Role` types/values and duplicate-row counts

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
Also confirm that `Approved for Role` is a standard Code Extra Value containing
the six exact updater options, that `Ineligible Volunteer` is stored as a
Boolean Extra Value, and that the duplicate-row check returns zero.

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
12. A person does not require a background check before their actual 18th
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

## Phase 3: Volunteer Status Updater

Install `VolunteerStatusUpdater.py` as a TouchPoint Python Script named
`VolunteerStatusUpdater`. Do not add it to Morning Batch yet.

Install `VolunteerStatusUpdaterAdmin.py` as a separate TouchPoint Python
Script named `VolunteerStatusUpdaterAdmin`. Restrict both its first-line role
directive and any Custom Report menu entry to `Admin`. Open it through
`/PyScript/VolunteerStatusUpdaterAdmin`; its saves use
`/PyScriptForm/VolunteerStatusUpdaterAdmin` and previews open in a new tab.

In the Updater Admin app, leave **Enable updates to Approved for Role** off,
review and save the updater-owned validity, age, training-exclusion, regular
service-code allowlist, and delivery settings, and run **Preview status
updates**. Preview uses saved
configuration and never writes person Extra Values, queues updater email, or
changes `VolunteerStatusUpdaterState`.

Validate the preview against representative live records for every rule:

1. Complete application with current, expired, and no Approved background
   check, plus current Approved MVR-only checks.
2. Incomplete application with and without an Approved check.
3. Latest background-check Not Approved, MVR Not Approved, Ineligible
   Volunteer, and newer Pending results.
4. A person below the minimum age and a person with no birthdate.
5. Existing output values that need a change and values already correct.
6. People included by each candidate-population branch, including Ineligible
   Volunteer and latest Not Approved background check.
7. A current, non-pending member of the selected Volunteer Application
   Involvement receives Application on File, while candidates who are pending,
   inactive, or not members have that checkbox cleared.

After the live preview is correct, enable updater writes only after checking
the Admin confirmation. If updater email is wanted, select authorized staff
recipients and enable its separate default-off switch. Conduct a controlled
staff-only production run before adding this call after the evaluator in the
existing `MorningBatch` script:

```python
print(model.CallScript("BackgroundCheckEvaluator"))
print(model.CallScript("VolunteerStatusUpdater"))
```

The updater emails only when a production run changes a status or encounters
a person-level write failure. A run with no changes and no failures sends no
updater email.

## Background Check Evaluator Admin

Install `BackgroundCheckEvaluatorAdmin.py` as a TouchPoint Python Script named
`BackgroundCheckEvaluatorAdmin`. It requires the `Admin` role and manages only
the Background Check Evaluator configuration.

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
- `BCE.BackgroundCheckServiceCodes` (required comma-separated positive
  allowlist; no tenant-specific default)

The coordinator and recipient controls use live TouchPoint person search.
Administrators search by name, email address, or People ID and select the
matching person by displayed name. The configurator stores People IDs
internally because they remain stable if a person's name or email changes.

## Volunteer Status Updater Admin

`VolunteerStatusUpdaterAdmin` is independent of
`BackgroundCheckEvaluatorAdmin`. The updater reads only these updater-owned
settings:

- `VSU.ConfigurationSaved`
- `VSU.UpdatesEnabled` and `VSU.EmailEnabled` (both default to `false`)
- `VSU.RecipientPeopleIds`
- `VSU.QueuedByPeopleId`, `VSU.FromAddress`, and `VSU.FromName`
- `VSU.BackgroundCheckValidMonths`
- `VSU.MinimumBackgroundCheckAge`
- `VSU.TrainingReportTypeId`
- `VSU.BackgroundCheckServiceCodes` (required comma-separated positive
  allowlist; initially suggested from the matching `BCE.*` setting)
- `VSU.MVRServiceCodes` (required comma-separated positive MVR allowlist)
- `VSU.MVRCheckValidMonths` (defaults to `12`)
- `VSU.VolunteerApplicationInvolvementId`

If earlier `VSU.ProgramId` or `VSU.DivisionId` settings exist, they are ignored.
The Admin app does not delete them, and the updater never reads them.

On first use, when a corresponding `VSU.*` value does not exist, the Admin app
shows the matching `BCE.*` value as a suggested starting point, including the
evaluator report recipients as suggested updater recipients. An Admin must
review and save the form to create the independent updater configuration.
Later evaluator changes are not copied or synchronized automatically.

The Updater Admin includes:

- a searchable, stable-ID selector for the active Volunteer Application
  Involvement;
- a read-only readiness check for the `Approved for Role` definition and all
  six required Code options in `StandardExtraValues2`;
- the status decision table and candidate-scope explanation;
- separate default-off write and email controls;
- a first-enable confirmation requiring live preview review;
- an Admin-managed recipient picker and complete-report privacy disclosure;
- a preview that opens in a new tab and never writes, emails, or changes state;
  and
- the latest aggregate `VolunteerStatusUpdaterState` production summary.

The readiness check does not create or modify Standard Extra Values. Correct
the definition through TouchPoint administration, rerun the aggregate
diagnostic, and confirm that duplicate stored rows are zero before enabling
writes. The Admin app rejects write activation while its readiness check is
failing; disabling writes remains available. The updater repeats the same
definition check before every preview or production evaluation so a missing or
changed standard definition cannot result in an unintended ad-hoc write.

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

### Volunteer Status Updater state

Production updater runs store a minimal versioned JSON summary in Text Content
named `VolunteerStatusUpdaterState`. It contains the timestamp and aggregate
evaluated, changed, unchanged, failed, and email-queued values. It contains no
names, contact information, People IDs, or person-level history. Preview never
creates or changes this state.

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
The updater maintains `Approved for Role` as a person Extra Value; it does not
add, delete, or change Volunteer Code assignments.

## Privacy behavior

The evaluator report contains volunteer names, required-through dates,
Involvement names, eligibility status, coverage status, and exception or error
reasons. It does not include email addresses or phone numbers. Every configured
report recipient receives the complete report. Recipient selection is
therefore limited to the Admin-only configurator and should contain only
authorized staff.

Updater email likewise contains the complete old/new status and reason list,
with volunteer names and People IDs but no email addresses or phone numbers.
It has its own Admin-only recipient list and is disabled by default.

## Local validation

Run:

```bash
python3 -m unittest discover -s "Development Resources/tests" -v
python3 -m py_compile "Installation Files/BackgroundCheckEvaluator.py" \
  "Installation Files/BackgroundCheckEvaluatorAdmin.py" \
  "Installation Files/BackgroundCheckEvalDiagnostic.py" \
  "Installation Files/VolunteerStatusUpdater.py" \
  "Installation Files/VolunteerStatusUpdaterAdmin.py"
```

Local tests cannot establish production success. The remaining live checks are
the current diagnostic, both Admin apps rendering, evaluator and updater
previews, representative decision-rule comparisons, a controlled staff-only
email test, a controlled production updater run, the following Morning Batch
execution, and review of both Text Content state summaries.

## Disable and rollback

To stop updater writes immediately, clear **Enable Morning Batch updates to
Approved for Role** and save. Clear updater email separately if necessary.
Remove the `VolunteerStatusUpdater` call from Morning Batch to stop evaluation
entirely. These actions do not revert values already written. To roll back the
software, remove the Updater Admin and updater script/call after disabling
writes; restore the prior Diagnostic only if that component must also be
rolled back. The existing evaluator and its Admin remain independently
deployable.
