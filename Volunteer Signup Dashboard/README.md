# Volunteer Signup Dashboard v1.0 beta

`VolunteerSignupDashboard.py` is one independently deployable TouchPoint
Python script for reusable volunteer-signup dashboards.

The Registration Form is the source of truth for shifts. The script reads every
option from the selected `RegQuestion.Options` JSON and then joins existing
`MemberTags` / `OrgMemMemTags` records to those options. A shift therefore
appears with zero volunteers even when TouchPoint has not created its subgroup
MemberTag yet.

## Beta behavior

- Administrators can inspect an Involvement's Registration Form questions,
  preview dashboards, and create, update, or delete saved configurations.
- The Involvement lookup searches active Involvements by name or ID and only
  returns those with an option-based Registration Form question.
- **Inspect Registration Form** appears directly beneath the selected
  Involvement. Selecting or removing an Involvement immediately clears the
  previously displayed subgroup-question list.
- One report can combine shifts from multiple Registration Form questions.
- The question selector includes only questions with dated subgroup Values and
  orders those questions by their earliest shift date. After inspection, all
  eligible subgroup questions are selected by default.
- Dashboard rows are visually grouped under date headers. Date groups and
  recognizable shift times are displayed chronologically.
- Dashboard setup and report output use the shared TouchPoint readability font
  stack: **Helvetica Neue**, Helvetica, Arial, then the device sans-serif.
- If none of the displayed Registration Form shifts has a configured limit,
  the report omits the **Limit** and **Remaining** columns. Mixed reports keep
  both columns and display a dash for shifts without an individual limit.
- Volunteer names are collapsed by default behind a per-shift **View
  volunteers** button, keeping shifts compact even when 8–10 people sign up.
  Expanded names appear in a smaller type size within a full-width list beneath
  the selected shift. Names are alphabetized by last name and flow down the
  first of two balanced columns before continuing at the top of the second.
- Users with `Admin`, `OrgLeadersOnly`, or `Staff` can load, preview, and save
  configurations. Configuration deletion remains restricted to Administrators.
- Saved configurations use stable profile IDs and are stored as versioned JSON
  in Text Content named `VolunteerSignupDashboardProfiles`.
- Saving a loaded configuration with its existing name updates that
  configuration. Changing the name before saving creates a new configuration
  and leaves the previously loaded configuration intact.
- Configuration deletion requires the stable profile ID plus an explicit
  browser confirmation.
- The script never adds, updates, or deletes people, Involvement membership,
  registration responses, subgroups, or attendance.
- Volunteer email display is off by default.
- Enabling volunteer email display reveals a Contact Information Notice and
  requires affirmative authorization before previewing or saving.
- Preview opens in a separate tab and renders only the submitted report. It
  does not save the configuration.
- The report-only preview provides a primary **Print Report** action and print
  CSS that hides TouchPoint navigation and other surrounding page content.
  Printing automatically includes every volunteer list, whether or not it was
  expanded on screen. If JavaScript is unavailable, names remain visible and
  the disclosure buttons are hidden.

## Saved configuration fields

Each profile stores:

- stable profile ID and configuration name;
- stable Involvement ID;
- one or more stable Registration Form question identifiers;
- report title;
- exact subgroup values to exclude;
- member-name, email-address, and technical subgroup/question display choices;
- last-saved People ID and timestamp.

The complete shift list and current limits are reread from the Registration
Form each time the report runs. Editing the Form therefore updates the report
without rewriting the saved configuration.

Existing beta profiles remain loadable. A profile saved before the Contact
Information Notice was introduced must be reviewed and confirmed before it can
again display volunteer email addresses.

## Installation

1. In TouchPoint, open **Admin > Advanced > Special Content > Python Scripts**.
2. Create a script named exactly `VolunteerSignupDashboard`.
3. Paste the complete contents of `VolunteerSignupDashboard.py` and save it.
4. Open `/PyScript/VolunteerSignupDashboard` as an Administrator.
5. Search for and choose an active Involvement, then select **Inspect
   Registration Form**.
6. Choose one or more questions whose options create the volunteer-shift
   subgroups.
7. Preview the dashboard before saving a configuration.

Optionally add the app to **Special Content > Text > CustomReports**:

```xml
<Report name="VolunteerSignupDashboard" type="PyScript" role="OrgLeadersOnly,Staff" />
```

Administrators can also open the direct URL even if they do not have an
operational role assigned for the menu link.

All form submissions use `/PyScriptForm/VolunteerSignupDashboard`; do not
change the installed script name without changing those form actions.

Option `Value` must match the resulting `MemberTags.Name`. Option `Text` is the
human-readable shift label. Option `Limit`, when supplied, produces capacity
and remaining-position totals.

### Hide specific shifts (optional)

This control was previously labeled **Excluded Subgroup Values**. It removes an
exact Registration Form option `Value` from the report. Normally, leave it
blank. It is intended for non-shift placeholders such as `? 99` that live in
the same question as real shifts. Enter one exact stored option Value/member-tag
name per line; entering the visible option label will not hide the shift.

If two selected questions contain the same subgroup Value, the report stops
with an explanation. TouchPoint would store both selections under the same
MemberTag name, so the dashboard cannot safely determine which question owns
that signup.

### Date grouping and sorting

The date must be at the beginning of the subgroup Value, before its first
colon. The beta recognizes these forms:

- `509:900am` for May 9 at 9:00 AM;
- `0509:9am` for May 9 at 9:00 AM;
- `5/9:9am` or `5/9/2026:9am`;
- `2026-05-09:9am`.

For three- or four-digit month/day values, the year is taken from a four-digit
year in the Involvement name. If the name has no year, the current year is
used. Shifts whose Values do not begin with a recognized date appear last in
an **Other shifts** group. Within a date, times containing `am` or `pm` are
sorted chronologically; other shifts retain Registration Form order.

Only questions containing at least one subgroup Value with a recognized date
prefix are offered for selection. This prevents ordinary registration-answer
questions from appearing in a shift report and supplies the date used to sort
the question selector. Questions without a dated shift subgroup remain in the
Registration Form but are not selectable in this dashboard.

### Show stored subgroup values and questions

This display option is enabled by default for beta troubleshooting. When it is
cleared, the report hides both the stored subgroup Value and the Registration
Form question name, including question names in the report footnote. Shift
labels, dates, counts, limits, and volunteer information are unaffected.

## Required live beta checks

Local tests cannot confirm tenant-specific Registration Form schema or data.
Before general use, an Administrator should verify the following in TouchPoint:

1. The Involvement lookup finds the intended Involvement by name.
2. All intended questions appear after inspecting the Involvement.
3. Questions appear in date order, and a question without a dated subgroup is
   not offered for selection.
4. The report's shift count equals the combined number of options in the
   selected questions, including at least one shift with no signups.
5. A zero-signup shift appears in yellow with a count of zero.
6. An existing signup appears under the option whose `Value` matches the
   created subgroup name.
7. Limits and remaining positions match the Form.
   When no displayed shift has a limit, both capacity columns are absent.
8. A specifically hidden shift is omitted exactly as configured.
9. Date headers appear in chronological order and shifts within a date are
   ordered by time.
10. Clearing **Show stored subgroup values and questions** hides both technical
    subgroup Values and question names from the report.
11. A shift with 8–10 signups initially shows a compact **View volunteers**
    button; opening and closing it reveals and hides the complete name list.
12. Print preview contains every volunteer name, including shifts that were
    collapsed on screen.
13. An `OrgLeadersOnly` or `Staff` user can preview and save but cannot delete.
14. An Administrator can save, reload, update, and delete a disposable beta
    configuration.
15. Email addresses remain hidden unless deliberately enabled.
16. Preview opens in a separate tab containing no setup form.
17. **Print Report** opens a print preview containing only the report; inspect
    the browser's print-preview thumbnails at both portrait and landscape
    widths before production use.

## User interface standards

This beta follows `/Users/brianbullock/TouchPoint/TOUCHPOINT_UI_STANDARDS.md`:

- one centered 1,180-pixel shell, bordered panels, and a responsive two-column
  grid;
- TouchPoint/Bootstrap-compatible controls and feedback alerts;
- human-friendly Involvement search backed by a stable hidden ID and a
  removable selected-record chip;
- safe privacy defaults and conditional contact-information disclosure;
- unsaved-change confirmation before loading another configuration;
- report-only preview, isolated printing, chronological date groups, and
  visible red vacancy styling.

No project-specific UI exception is currently documented. Actual desktop,
narrow-screen, and browser print-preview appearance must still be verified in
the live TouchPoint tenant; local source and rendering tests cannot validate
the tenant theme or surrounding navigation markup.

The beta intentionally filters deceased and archived people but does not apply
an Organization MemberType filter. Confirm the tenant's desired membership
status rules during beta testing before production release.

## Text Content and rollback

The script creates or updates only this extension-owned Text Content:

- `VolunteerSignupDashboardProfiles`

There are no Settings keys, Morning Batch hooks, email-delivery actions, or
separate processing-state records in v1.0 beta.

To disable the app, remove its Custom Report link or remove/rename the Python
script. To roll back saved configuration changes, restore an earlier version of
the Text Content through TouchPoint's content history. Deleting the Python
script does not alter signup data.

## Local validation

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile VolunteerSignupDashboard.py
git diff --check
```
