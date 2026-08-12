# TouchPoint Weekly Volunteer Schedule Report

This extension produces a staff-friendly weekly report from TouchPoint
Scheduler Involvements. A report may contain one Scheduler or several selected
Schedulers, defaults to Friday through Sunday, supports custom manual date
ranges, prints cleanly, and can be emailed manually or from saved Monday
profiles.

The report is read-only. It never changes people, Involvements, meetings,
assignments, commitments, or attendance. It writes only its own configuration
and successful automated-send state in TouchPoint.

## Files

- `VolunteerScheduleReportDiagnostic.sql` — primary temporary, read-only
  tenant schema and sample-data check. Using a SQL Script avoids Python editor
  parsing differences between TouchPoint installations.
- `VolunteerScheduleAssignmentDiagnostic.sql` — focused second-stage check of
  assignments, commitments, substitutes, vacancies, staffing targets, and
  contact fields for the confirmed Scheduler.
- `VolunteerScheduleReportDiagnostic.py` — retained as an optional Python
  version; do not use it when the TouchPoint editor changes pasted source.
- `VolunteerScheduleReport.py` — report UI, report renderer, email delivery,
  and Morning Batch profile runner.
- `VolunteerScheduleReportAdmin.py` — Admin-only delivery settings and saved
  report profiles.
- `tests/test_volunteer_schedule_report.py` — local behavior and safety tests.

## Report behavior

- The on-demand default is the current weekend when run Friday–Sunday and the
  upcoming weekend when run Monday–Thursday.
- Weekend calculations explicitly use the Windows `Central Standard Time`
  zone, which provides `America/Chicago` daylight-saving behavior in TouchPoint.
- Manual reports may use any inclusive range up to 93 days.
- Manual date inputs are converted from IronPython `date` values to .NET
  `DateTime` values before they are passed to parameterized SQL.
- Results are grouped by Scheduler Involvement, meeting date/time, Team, and
  optional Sub-Group. The job label is `Team — Sub-Group` when a Sub-Group is
  present.
- Scheduler selection is restricted to active Involvements with TouchPoint
  Scheduler registration type `22` and generated Time Slot data.
- Committed, Scheduled/Uncommitted, and Substitute volunteers count as filled.
  `Find Sub` is shown as an unresolved warning and does not count as filled.
  Regrets and replaced originals marked `Sub Found` do not appear as coverage.
- Empty slots remain visible with filled/needed counts and open-position flags.
- Email recipients are deduplicated TouchPoint People IDs. Serving recipients
  include people counted as filled; unresolved `Find Sub` people are not
  automatically treated as serving recipients.

## Phase 1 — run the diagnostic

1. Install `VolunteerScheduleReportDiagnostic.sql` at **Admin > Advanced >
   Special Content > SQL Scripts** with the name
   `VolunteerScheduleReportDiagnosticSql`. Use this new name so it cannot be
   confused with the earlier Python diagnostic.
2. Edit `DECLARE @InvolvementId INT = 0` near the top of the SQL Script and
   replace `0` with the known Scheduler Involvement ID. Save, then run it.
3. Confirm that the result includes the selected Involvement, Scheduler table
   columns, relationship counts, and upcoming teams. Save or screenshot the
   complete grid; those columns are used to finalize the tenant-specific
   assignment, Sub-Group, commitment, and staffing-target query.
4. Install `VolunteerScheduleAssignmentDiagnostic.sql` as a SQL Script named
   `VolunteerScheduleAssignmentDiagnostic`. Set its `@InvolvementId`, save,
   and run it. It defaults to the next 46 days and includes empty slots as well
   as active and inactive assignment records so status handling can be checked.
5. Compare the returned information with the Scheduler screen. Confirm:
   - Team and Sub-Group names;
   - required volunteer counts, including an empty slot;
   - committed, scheduled, Find Sub, Sub Found, and substitute examples when
     available;
   - email and mobile-phone fields;
   - one Scheduler with no Sub-Groups and one that uses Sub-Groups.
6. Do not proceed if the query fails or the sample disagrees with TouchPoint.
   Save the diagnostic output so the tenant-specific join can be corrected
   without guessing.

The diagnostic performs no writes and sends no email. Remove or archive it
after validation.

### Confirmed tenant evidence

The August 2, 2026 diagnostic for Scheduler Involvement `315` (Media Ministry
Schedule) confirmed active Scheduler registration type `22`, 277 Time Slot
meetings, and 419 meeting-team rows. The focused 46-day assignment export
confirmed:

- Team and Sub-Group labels and both staffing-target paths;
- active and inactive roster links;
- committed and scheduled/uncommitted assignments;
- an active empty slot that must remain visible; and
- deleted Time Slot meetings that must not appear in the report.

The report query therefore filters canceled/deleted meeting structures,
inactive or ended roster assignments, and inactive meeting-volunteer records.
It retains an empty active slot and treats either commitment code `4` or an
active `IsSub` flag as substitute coverage. Find Sub, Sub Found, and regret
behavior must still be checked against a weekend containing those statuses.

## Phase 2 — preview installation

1. Install `VolunteerScheduleReport.py` as a Python Script named exactly
   `VolunteerScheduleReport`.
2. Install `VolunteerScheduleReportAdmin.py` as a Python Script named exactly
   `VolunteerScheduleReportAdmin`.
3. Leave `VSR.EmailEnabled` off. This is the default.
4. Optionally add the report to **Special Content > Text > CustomReports**:

   ```xml
   <Report name="VolunteerScheduleReport" type="PyScript" role="ManageGroups" />
   ```

   TouchPoint may cache Custom Report changes. The report script uses the base
   `Access` directive and explicitly permits only users with `Admin` or
   `ManageGroups`; the administration script enforces `Admin`.
5. Open the report, select a known Scheduler, and compare Friday–Sunday results
   with the Scheduler screen. Repeat with multiple Schedulers and a custom
   date range.
6. Verify the printed result before enabling email.

TouchPoint displays Custom Report links through `/PyScript/`, but interactive
POST requests must use `/PyScriptForm/`. The report and administration forms
explicitly post to their `/PyScriptForm/` routes and set `model.Form` so preview,
search, save, edit, and delete actions render correctly.

The standalone report includes a **Saved Profile Preset** selector. It includes
both standalone saved profiles and Monday Batch profiles, with the profile type
shown in each option. A selected preset fills its Scheduler Involvements, Staff
Recipients, serving-volunteer delivery choice, and contact-column choices. The
date range remains independently editable and is never stored in the profile.
New custom reports exclude volunteer email addresses and mobile phones by
default. The Contact Information Notice remains hidden unless at least one of
those contact columns is selected. **Preview report** opens a report-only
preview in a separate browser tab, without repeating the setup form, so the
report parameters remain available in the original tab. The preview includes a
prominent **Print Report** button that creates an isolated printable copy of
the report, preventing TouchPoint's surrounding page layout from interfering
with browser print preview. The button is omitted from the printed output.

Users with `Admin` or `ManageGroups` can create, update, and delete shared
standalone profiles from this page. Profile names must be unique regardless of
capitalization. Monday Batch profiles are read-only on the standalone page and
can only be changed in Administration. Loading or previewing any preset does
not enable automation, send email, or update duplicate-send state; the user
must still click **Email current report** to send manually.

## Administration and saved profiles

Open `/PyScript/VolunteerScheduleReportAdmin` as an Administrator. The visible
administration page loads through `/PyScript/`; its forms and live searches
submit to `/PyScriptForm/`.

Delivery settings use compact `VSR.` TouchPoint Settings:

- `VSR.EmailEnabled`
- `VSR.QueuedByPeopleId`
- `VSR.FromAddress`
- `VSR.FromName`
- `VSR.FailureRecipientPeopleIds`

Profiles are versioned JSON in Text Content named
`VolunteerScheduleReportProfiles`. Each profile retains its type, selected
Scheduler IDs, selected staff People IDs, the serving-volunteer delivery option,
Monday send day, enabled state, independently selected volunteer email/mobile
display options, contact-distribution acknowledgement, and last-saved metadata.
Existing profiles without a profile type are treated as Monday Batch profiles
for backward compatibility. Current names and email addresses are resolved from
stable People IDs when a report runs.

Administrators can edit standalone profiles in Administration and convert them
to Monday Batch profiles. Conversion requires confirmation and does not enable
the profile automatically. Once converted, the profile remains editable only
in Administration. Standalone profiles are ignored by Morning Batch even if
their stored data is edited outside the extension.

New profiles created in Administration are identified as Monday Batch profiles;
their volunteer email and mobile-phone columns are unchecked by default. An
existing standalone profile instead displays a permanent conversion option.
The separate **Send this profile automatically during Monday Morning Batch**
checkbox is the weekly-delivery on/off switch. Contact-information confirmation
appears only when email or mobile-phone columns are selected.

Automated-send history is stored in Text Content named
`VolunteerScheduleReportState`. It records only each profile's last successful
Friday–Sunday window. Preview and manual email do not update it.

### Privacy behavior

The manual report and each saved profile can independently include or exclude
the volunteer email and mobile-phone columns. Recipient email resolution still
occurs privately at send time even when the email column is excluded. If
**Email all volunteers serving** is enabled, each volunteer receives the same
complete report with only the selected contact columns. A profile that exposes
either contact field cannot be enabled for volunteer delivery until an
Administrator confirms this distribution explicitly.

The report summary counts unique listed people. **Committed / Confirmed**
includes committed volunteers and active substitutes; **Awaiting Confirmation**
includes scheduled assignments without confirmation; **Vacancies** totals the
unfilled positions across all Team/Sub-Group staffing targets; and **Substitute
Warnings** counts people with unresolved Find Sub requests. All five metrics
remain in one summary row, while each staffing gap also remains visible in its
Team/Sub-Group section as a red alert badge. A compact definition key appears at
the bottom of every preview, printout, and email.

## Controlled email activation

1. Configure queued-by person, sender, and failure recipients, but leave email
   disabled.
2. Create a disabled profile with serving-volunteer delivery off and only the
   intended test staff recipients.
3. Enable email globally and use **Email current report** for a controlled staff
   test.
4. Verify sender, subject, dates, assignments, contacts, gaps, and print layout.
5. Only then acknowledge contact distribution and enable the intended Monday
   profile.

If a selected person has no email address, TouchPoint cannot deliver to that
person. The extension removes that person from the email query and identifies
the name in the manual or batch result. A send with no deliverable recipients
fails and does not advance automated-send history.

## Morning Batch

Add this call to the existing Morning Batch script. The report itself exits
without sending unless the day is Monday, the profile is enabled, email is
enabled globally, and that profile/window has not already succeeded.

The account configured by TouchPoint's `MorningBatchUsername` setting must have
the `Admin` role because automated profile execution is Admin-only.

```python
try:
    Data.VSRAction = "run_profiles"
    print(model.CallScript("VolunteerScheduleReport"))
finally:
    Data.VSRAction = ""
```

On Monday, each enabled profile reports the upcoming Friday–Sunday. A profile
failure does not stop later profiles. After a successful queue operation, its
window is saved to prevent duplicate automated sends. Manual sends never alter
that state.

## Rollback and disable

- Turn off `Enable manual and automated email` in the Admin script for an
  immediate delivery stop.
- Disable an individual profile to stop only that Monday report.
- Remove the Morning Batch call to stop automation while preserving profiles.
- Remove the CustomReports entry and archive the Python Scripts to remove the
  extension. Existing Scheduler records are unaffected.

## Local verification

Run from this directory:

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile VolunteerScheduleReport.py VolunteerScheduleReportAdmin.py VolunteerScheduleReportDiagnostic.py
git diff --check
```

Local tests mock the pure report logic. They do not replace the live diagnostic,
Scheduler comparison, print review, and controlled staff email test.
