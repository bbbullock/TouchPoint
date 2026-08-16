#Roles=Access
# -*- coding: utf-8 -*-
# Application: Volunteer Schedule Report
# Version: 1.0.0
# Released: 2026-08-15
# Written by: Brian Bullock with Codex assistance
# Email: bbbullock@mac.com
# GitHub: https://github.com/bbbullock/TouchPoint
#
# Version history
# 1.0.0 (2026-08-15)
# - Reports one or more Scheduler Involvements with vacancies and substitutes.
# - Supports reusable standalone and Monday Batch profiles, print, and email.
# - Minimizes contact details by default and requires privacy confirmation.
# - Uses #Roles=Access as the sole interactive authorization authority.

"""
Weekly Volunteer Schedule Report v1.0.0 for TouchPoint Scheduler Involvements.

Read-only with respect to people, Involvements, meetings, assignments, and
commitments. The only writes are successful automated-send state in Text
Content and this extension's saved-profile configuration. Email is disabled by
default.

Scheduler table relationships were informed by TPxi Scheduler Report v2.2:
https://github.com/bswaby/Touchpoint/tree/main/TPxi/Scheduler%20Report
"""

import cgi
import datetime
import json


APP_VERSION = "1.0.0"
SETTING_PREFIX = "VSR."
PROFILES_CONTENT = "VolunteerScheduleReportProfiles"
STATE_CONTENT = "VolunteerScheduleReportState"
PROFILE_VERSION = 1
STATE_VERSION = 1
WINDOWS_TIME_ZONE_ID = "Central Standard Time"


def html_escape(value):
    return cgi.escape(str(value if value is not None else ""), True)


def parse_ids(raw):
    values = []
    if isinstance(raw, (list, tuple)):
        parts = raw
    else:
        parts = str(raw or "").replace(";", ",").split(",")
    for part in parts:
        try:
            value = int(str(part).strip())
        except Exception:
            continue
        if value > 0 and value not in values:
            values.append(value)
    return values


def parse_iso_date(raw):
    return datetime.datetime.strptime(str(raw), "%Y-%m-%d").date()


def iso_date(value):
    return value.strftime("%Y-%m-%d")


def sql_datetime(value):
    """Return a SQL-parameter-safe midnight DateTime in TouchPoint."""
    year = int(value.year)
    month = int(value.month)
    day = int(value.day)
    try:
        from System import DateTime
        return DateTime(year, month, day, 0, 0, 0)
    except Exception:
        return datetime.datetime(year, month, day, 0, 0, 0)


def central_today():
    try:
        from System import DateTime, TimeZoneInfo
        zone = TimeZoneInfo.FindSystemTimeZoneById(WINDOWS_TIME_ZONE_ID)
        local_now = TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, zone)
        return datetime.date(local_now.Year, local_now.Month, local_now.Day)
    except Exception:
        return datetime.datetime.now().date()


def current_or_next_weekend(today):
    weekday = today.weekday()
    if weekday <= 4:
        friday = today + datetime.timedelta(days=4 - weekday)
    else:
        friday = today - datetime.timedelta(days=weekday - 4)
    return friday, friday + datetime.timedelta(days=2)


def next_weekend_from_monday(run_date):
    friday = run_date + datetime.timedelta(days=(4 - run_date.weekday()) % 7)
    return friday, friday + datetime.timedelta(days=2)


def commitment_details(raw):
    try:
        code = 99 if raw is None else int(raw)
    except Exception:
        code = 99
    mapping = {
        0: ("Regrets", False, False, True),
        1: ("Committed", True, True, True),
        2: ("Find Sub", False, False, True),
        3: ("Sub Found", False, False, True),
        4: ("Substitute", True, True, True),
        99: ("Scheduled", True, True, True),
    }
    return mapping.get(code, ("Status {0}".format(code), False, False, True))


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def truthy(raw):
    return str(raw or "").strip().lower() in ("true", "1", "yes", "y", "on")


def format_datetime(value):
    if value is None:
        return ""
    try:
        return value.strftime("%A, %B %d, %Y at %-I:%M %p")
    except Exception:
        try:
            return value.ToString("dddd, MMMM dd, yyyy 'at' h:mm tt")
        except Exception:
            return str(value)


def datetime_sort_value(value):
    try:
        return value.strftime("%Y%m%d%H%M%S")
    except Exception:
        try:
            return value.ToString("yyyyMMddHHmmss")
        except Exception:
            return str(value)


def build_slots(rows):
    slots = {}
    for row in rows:
        org_id = safe_int(getattr(row, "OrganizationId", 0))
        meeting_team_id = safe_int(getattr(row, "TimeSlotMeetingTeamId", 0))
        subgroup_id = safe_int(getattr(row, "TimeSlotMeetingTeamSubGroupId", 0))
        service_date = getattr(row, "MeetingDateTime", None)
        key = (org_id, datetime_sort_value(service_date), meeting_team_id, subgroup_id)
        if key not in slots:
            needed_raw = getattr(row, "NumberNeeded", None)
            needed = None if needed_raw is None else max(0, safe_int(needed_raw))
            slots[key] = {
                "organization_id": org_id,
                "organization_name": str(getattr(row, "OrganizationName", "") or ""),
                "meeting_id": safe_int(getattr(row, "MeetingId", 0)),
                "meeting_datetime": service_date,
                "team": str(getattr(row, "TeamName", "") or "Unspecified Team"),
                "subgroup": str(getattr(row, "SubGroupName", "") or ""),
                "needed": needed,
                "required": bool(getattr(row, "IsRequired", False)),
                "location": str(getattr(row, "Location", "") or ""),
                "volunteers": {},
                "warnings": [],
            }
        slot = slots[key]
        people_id = safe_int(getattr(row, "PeopleId", 0))
        if not people_id:
            continue
        meeting_volunteer_active = getattr(row, "MeetingVolunteerActive", None)
        if meeting_volunteer_active is not None and not bool(meeting_volunteer_active):
            continue
        label, counts_as_filled, is_recipient, display = commitment_details(
            getattr(row, "Commitment", None)
        )
        if bool(getattr(row, "IsSub", False)) and label not in ("Regrets", "Find Sub", "Sub Found"):
            label, counts_as_filled, is_recipient, display = commitment_details(4)
        if not display or label in ("Regrets", "Sub Found"):
            continue
        volunteer = {
            "people_id": people_id,
            "name": str(getattr(row, "VolunteerName", "") or "Person {0}".format(people_id)),
            "email": str(getattr(row, "EmailAddress", "") or ""),
            "phone": str(getattr(row, "CellPhone", "") or ""),
            "status": label,
            "filled": counts_as_filled,
            "recipient": is_recipient,
        }
        existing = slot["volunteers"].get(people_id)
        priority = {"Substitute": 4, "Committed": 3, "Scheduled": 2, "Find Sub": 1}
        if existing is None or priority.get(label, 0) >= priority.get(existing["status"], 0):
            slot["volunteers"][people_id] = volunteer
        if label == "Find Sub":
            warning = "{0} has an unresolved Find Sub request.".format(volunteer["name"])
            if warning not in slot["warnings"]:
                slot["warnings"].append(warning)

    results = []
    for key in sorted(slots):
        slot = slots[key]
        volunteers = list(slot["volunteers"].values())
        volunteers.sort(key=lambda item: item["name"].lower())
        slot["volunteers"] = volunteers
        filled = len([item for item in volunteers if item["filled"]])
        slot["filled"] = filled
        slot["open"] = None if slot["needed"] is None else max(slot["needed"] - filled, 0)
        results.append(slot)
    return results


def recipient_people_ids(slots, include_serving, staff_ids):
    values = []
    if include_serving:
        for slot in slots:
            for volunteer in slot["volunteers"]:
                if volunteer["recipient"] and volunteer["people_id"] not in values:
                    values.append(volunteer["people_id"])
    for people_id in staff_ids:
        if people_id not in values:
            values.append(people_id)
    return values


def report_summary(slots):
    volunteers = set()
    confirmed = set()
    awaiting_confirmation = set()
    substitute_warnings = set()
    vacancies = 0
    for slot in slots:
        if slot["open"] is not None:
            vacancies += slot["open"]
        for volunteer in slot["volunteers"]:
            people_id = volunteer["people_id"]
            volunteers.add(people_id)
            if volunteer["status"] in ("Committed", "Substitute"):
                confirmed.add(people_id)
            elif volunteer["status"] == "Scheduled":
                awaiting_confirmation.add(people_id)
            elif volunteer["status"] == "Find Sub":
                substitute_warnings.add(people_id)
    return (len(volunteers), len(confirmed), len(awaiting_confirmation),
            vacancies, len(substitute_warnings))


def load_json_text(raw, default):
    try:
        value = json.loads(str(raw or ""))
        return value
    except Exception:
        return default


def json_for_script(value):
    return json.dumps(value).replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def valid_profile(profile):
    if not isinstance(profile, dict):
        return False
    if not str(profile.get("id", "")).strip():
        return False
    if not str(profile.get("name", "")).strip():
        return False
    if not parse_ids(profile.get("scheduler_ids", [])):
        return False
    return True


def profiles_from_document(document):
    if not isinstance(document, dict) or safe_int(document.get("version"), 0) != PROFILE_VERSION:
        return []
    return [profile for profile in document.get("profiles", []) if valid_profile(profile)]


def profile_kind(profile):
    value = str(profile.get("profile_type", "") or "").strip().lower()
    if value == "manual":
        return "manual"
    return "monday"


def selected_profile(profiles, profile_id):
    wanted = str(profile_id or "")
    for profile in profiles:
        if str(profile.get("id", "")) == wanted:
            return profile
    return None


SCHEDULE_SQL = """
;WITH LatestVolunteers AS (
    SELECT TimeSlotMeetingId, PeopleId,
           MAX(TimeSlotMeetingVolunteerId) AS TimeSlotMeetingVolunteerId
    FROM TimeSlotMeetingVolunteers
    GROUP BY TimeSlotMeetingId, PeopleId
),
LatestAttend AS (
    SELECT MeetingId, PeopleId, MAX(AttendId) AS AttendId
    FROM Attend
    GROUP BY MeetingId, PeopleId
)
SELECT
    m.OrganizationId,
    o.OrganizationName,
    m.MeetingId,
    tsm.MeetingDateTime,
    m.Location,
    tsmt.TimeSlotMeetingTeamId,
    tssg.TimeSlotMeetingTeamSubGroupId,
    tsmt.TeamName,
    CASE WHEN mt.Name IS NULL THEN '' ELSE mt.Name END AS SubGroupName,
    CASE WHEN tsmt.UseSubGroup = 0
         THEN tst.NumberVolunteersNeeded
         ELSE tssg.NumberVolunteersNeeded END AS NumberNeeded,
    CASE WHEN tstsg.Require IS NULL THEN 0 ELSE tstsg.Require END AS IsRequired,
    v.PeopleId,
    p.Name2 AS VolunteerName,
    p.EmailAddress,
    p.CellPhone,
    a.Commitment,
    tsmv.VolunteerOption,
    tsmv.IsActive AS MeetingVolunteerActive,
    tsmv.IsSub
FROM TimeSlotMeetingTeams tsmt
JOIN TimeSlotMeetings tsm
  ON tsm.TimeSlotMeetingId = tsmt.TimeSlotMeetingId
JOIN Meetings m
  ON m.MeetingId = tsm.MeetingId
JOIN Organizations o
  ON o.OrganizationId = m.OrganizationId
LEFT JOIN TimeSlotTeams tst
  ON tst.TimeSlotId = tsm.TimeSlotId
 AND tst.TeamName = tsmt.TeamName
 AND ISNULL(tst.IsDeleted, 0) = 0
LEFT JOIN TimeSlotMeetingTeamSubGroups tssg
  ON tssg.TimeSlotMeetingTeamId = tsmt.TimeSlotMeetingTeamId
 AND ISNULL(tssg.IsDeleted, 0) = 0
LEFT JOIN TimeSlotTeamSubGroups tstsg
  ON tstsg.TimeSlotTeamSubGroupId = tssg.TimeSlotTeamSubGroupId
 AND ISNULL(tstsg.IsDeleted, 0) = 0
LEFT JOIN MemberTags mt
  ON mt.Id = tssg.MemberTagId
 AND mt.OrgId = m.OrganizationId
LEFT JOIN TimeSlotMeetingTeamSubGroupVolunteers v
  ON v.IsActive <> 0
 AND v.TimeSlotMeetingTeamId = tsmt.TimeSlotMeetingTeamId
 AND (v.DateServiceEnded IS NULL OR v.DateServiceEnded >= tsm.MeetingDateTime)
 AND ((v.TimeSlotMeetingTeamSubGroupId IS NULL
       AND tssg.TimeSlotMeetingTeamSubGroupId IS NULL)
   OR v.TimeSlotMeetingTeamSubGroupId = tssg.TimeSlotMeetingTeamSubGroupId)
LEFT JOIN People p
  ON p.PeopleId = v.PeopleId
LEFT JOIN LatestVolunteers lv
  ON lv.TimeSlotMeetingId = tsm.TimeSlotMeetingId
 AND lv.PeopleId = v.PeopleId
LEFT JOIN TimeSlotMeetingVolunteers tsmv
  ON tsmv.TimeSlotMeetingVolunteerId = lv.TimeSlotMeetingVolunteerId
LEFT JOIN LatestAttend la
  ON la.MeetingId = m.MeetingId
 AND la.PeopleId = v.PeopleId
LEFT JOIN Attend a
  ON a.AttendId = la.AttendId
WHERE m.OrganizationId IN ({organization_ids})
  AND tsm.MeetingDateTime >= @StartDate
  AND tsm.MeetingDateTime < @EndDateExclusive
  AND ISNULL(tsm.IsDeleted, 0) = 0
  AND ISNULL(tsmt.IsDeleted, 0) = 0
  AND ISNULL(m.DidNotMeet, 0) = 0
  AND ISNULL(m.Canceled, 0) = 0
  AND o.OrganizationStatusId = 30
  AND o.RegistrationTypeId = 22
ORDER BY o.OrganizationName, tsm.MeetingDateTime, tsmt.TeamName,
         SubGroupName, p.Name2
"""


def render_report(slots, start_date, end_date, title, include_controls,
                  include_email=True, include_phone=True):
    volunteer_count, confirmed_count, awaiting_count, vacancy_count, warning_count = report_summary(slots)
    parts = [
        '<div class="vsr-report">',
        '<div class="vsr-report-head"><div><h2>{0}</h2><p>{1} through {2}</p></div>'.format(
            html_escape(title), html_escape(start_date.strftime("%B %d, %Y")),
            html_escape(end_date.strftime("%B %d, %Y"))),
        '</div>',
        '<table class="vsr-summary" role="presentation"><tr>',
        '<td><strong>{0}</strong><span>Volunteers</span></td>'.format(volunteer_count),
        '<td class="vsr-summary-confirmed"><strong>{0}</strong><span>Committed / Confirmed</span></td>'.format(
            confirmed_count),
        '<td class="vsr-summary-awaiting"><strong>{0}</strong><span>Awaiting Confirmation</span></td>'.format(
            awaiting_count),
        '<td class="vsr-summary-vacancy"><strong>{0}</strong><span>{1}</span></td>'.format(
            vacancy_count, "Vacancy" if vacancy_count == 1 else "Vacancies"),
        '<td class="vsr-summary-warning"><strong>{0}</strong><span>Substitute {1}</span></td>'.format(
            warning_count, "Warning" if warning_count == 1 else "Warnings"),
        '</tr></table>',
    ]
    if include_controls:
        parts.append('''<div class="vsr-actions no-print"><button type="button" class="btn btn-primary btn-lg vsr-print-button" onclick="printVolunteerScheduleReport()">Print Report</button></div>
<script>
function printVolunteerScheduleReport() {
  var report = document.querySelector('.vsr-report');
  var styles = document.getElementById('vsrReportStyles');
  if (!report || !styles) {
    window.print();
    return;
  }
  var frame = document.createElement('iframe');
  frame.setAttribute('title', 'Print Volunteer Schedule Report');
  frame.style.position = 'fixed';
  frame.style.left = '-10000px';
  frame.style.top = '0';
  frame.style.width = '1200px';
  frame.style.height = '800px';
  frame.style.border = '0';
  document.body.appendChild(frame);
  var printDocument = frame.contentWindow.document;
  printDocument.open();
  printDocument.write('<!doctype html><html><head><meta charset="utf-8">' + styles.outerHTML + '<style>body{margin:0;padding:18px;background:#fff}.no-print{display:none!important}</style></head><body>' + report.outerHTML + '</body></html>');
  printDocument.close();
  frame.contentWindow.onafterprint = function() {
    if (frame.parentNode) frame.parentNode.removeChild(frame);
  };
  window.setTimeout(function() {
    frame.contentWindow.focus();
    frame.contentWindow.print();
  }, 250);
}
</script>''')
    if not slots:
        parts.append('<div class="alert alert-info">No Scheduler slots were found for the selected Involvements and dates.</div>')
    current_org = None
    current_service = None
    for slot in slots:
        if current_org != slot["organization_id"]:
            if current_org is not None:
                parts.append("</div>")
            current_org = slot["organization_id"]
            current_service = None
            parts.append('<div class="vsr-org"><h3>{0}</h3>'.format(html_escape(slot["organization_name"])))
        service_key = datetime_sort_value(slot["meeting_datetime"])
        if current_service != service_key:
            current_service = service_key
            location = ""
            if slot["location"]:
                location = " &middot; {0}".format(html_escape(slot["location"]))
            parts.append('<h4>{0}{1}</h4>'.format(html_escape(format_datetime(slot["meeting_datetime"])), location))
        job = slot["team"]
        if slot["subgroup"]:
            job += " — " + slot["subgroup"]
        if slot["needed"] is None:
            count_text = "{0} assigned; target not set".format(slot["filled"])
        else:
            count_text = "{0} of {1} filled".format(slot["filled"], slot["needed"])
        status_class = "vsr-slot-open" if slot["open"] else "vsr-slot-full"
        parts.append('<section class="vsr-slot {0}"><div class="vsr-slot-title"><strong>{1}</strong><span>{2}</span></div>'.format(
            status_class, html_escape(job), html_escape(count_text)))
        headings = ["Volunteer", "Status"]
        if include_email:
            headings.append("Email")
        if include_phone:
            headings.append("Mobile phone")
        parts.append('<table><thead><tr>{0}</tr></thead><tbody>'.format(
            "".join('<th scope="col">{0}</th>'.format(html_escape(value)) for value in headings)
        ))
        for volunteer in slot["volunteers"]:
            status_css = "vsr-status-" + volunteer["status"].lower().replace(" ", "-")
            cells = ['<td>{0}</td>'.format(html_escape(volunteer["name"])),
                     '<td><span class="vsr-badge {0}">{1}</span></td>'.format(
                         status_css, html_escape(volunteer["status"]))]
            if include_email:
                cells.append('<td>{0}</td>'.format(html_escape(volunteer["email"])))
            if include_phone:
                cells.append('<td>{0}</td>'.format(html_escape(volunteer["phone"])))
            parts.append('<tr>{0}</tr>'.format("".join(cells)))
        if not slot["volunteers"]:
            parts.append('<tr><td colspan="{0}"><em>No active volunteers assigned.</em></td></tr>'.format(
                len(headings)))
        parts.append("</tbody></table>")
        if slot["open"]:
            parts.append('<div class="vsr-gap"><strong>{0} open {1}</strong></div>'.format(
                slot["open"], "position" if slot["open"] == 1 else "positions"))
        for warning in slot["warnings"]:
            parts.append('<div class="vsr-find-sub">{0}</div>'.format(html_escape(warning)))
        parts.append("</section>")
    if current_org is not None:
        parts.append("</div>")
    parts.append('''
<div class="vsr-definitions">
  <strong class="vsr-definitions-title">Understanding the report totals</strong>
  <div><strong>Volunteers</strong><span>Unique people listed with a role for the selected weekend.</span></div>
  <div><strong>Committed / Confirmed</strong><span>People who confirmed their assignment, including confirmed substitutes serving for someone else.</span></div>
  <div><strong>Awaiting Confirmation</strong><span>People assigned to a role who have not yet confirmed their availability.</span></div>
  <div><strong>Vacancies</strong><span>Total unfilled positions across all Team and Sub-Group staffing targets in the report.</span></div>
  <div><strong>Substitute Warnings</strong><span>People with an unresolved Find Sub request where no replacement has filled the role.</span></div>
</div>
''')
    parts.append("</div>")
    return "".join(parts)


REPORT_STYLE = """
<style id="vsrReportStyles">
.vsr-shell,.vsr-report{max-width:1180px;margin:20px auto;color:#24313d;font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;font-weight:400;line-height:1.42857143}
.vsr-shell button,.vsr-shell input,.vsr-shell select,.vsr-report button{font-family:inherit}
.vsr-shell h2,.vsr-report h2{font-weight:300}.vsr-shell h3,.vsr-shell h4,.vsr-report h3,.vsr-report h4{font-weight:400}.vsr-shell label,.vsr-slot th{font-weight:600}.vsr-shell .help-block{font-size:.9em}
.vsr-panel{border:1px solid #d8e0e7;border-radius:8px;padding:18px;background:#fff;margin-bottom:18px}
.vsr-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.vsr-grid .wide{grid-column:1/-1}
.vsr-privacy{border-left:5px solid #b43535;background:#fff3f3;padding:12px}.vsr-privacy p{margin:4px 0 8px}
.vsr-selected{display:flex;gap:6px;flex-wrap:wrap;margin-top:7px}.vsr-pill{background:#e8f1f8;border-radius:14px;padding:4px 9px}
.vsr-results{position:relative}.vsr-results-list{position:absolute;z-index:4;background:#fff;border:1px solid #ccd6df;width:100%;box-shadow:0 3px 10px #999;max-height:220px;overflow:auto}
.vsr-result{display:block;width:100%;text-align:left;border:0;border-bottom:1px solid #eee;background:#fff;padding:8px}.vsr-result:hover{background:#f3f7fa}
.vsr-report-head{margin-bottom:12px}.vsr-summary{border-collapse:separate;border-spacing:0;margin:0 0 20px;table-layout:fixed;width:100%}.vsr-summary td{background:#eef3f6;border:1px solid #d8e0e7;border-right:0;overflow-wrap:anywhere;padding:12px;vertical-align:top;width:20%}.vsr-summary td:first-child{border-radius:7px 0 0 7px}.vsr-summary td:last-child{border-radius:0 7px 7px 0;border-right:1px solid #d8e0e7}.vsr-summary strong{display:block;font-size:26px;font-weight:600;margin-bottom:4px}.vsr-summary span{display:block;font-weight:600}.vsr-summary-confirmed{background:#dff2e4!important}.vsr-summary-awaiting{background:#fff0c7!important}.vsr-summary-vacancy,.vsr-summary-warning{background:#fde2e2!important}.vsr-actions{margin:10px 0 18px;text-align:right}.vsr-print-button{font-weight:600;min-width:160px;padding:10px 20px}
.vsr-org{page-break-inside:avoid}.vsr-org h3{border-bottom:3px solid #2b6f98;padding-bottom:5px}.vsr-org h4{margin:18px 0 8px}
.vsr-slot{border:1px solid #d7dee5;border-left:5px solid #37845a;margin:8px 0 14px;padding:10px;page-break-inside:avoid}.vsr-slot-open{border-left-color:#b43535}.vsr-slot-title{display:flex;justify-content:space-between;gap:12px;margin-bottom:7px}
.vsr-slot table{border-collapse:collapse;width:100%;font-size:13px}.vsr-slot th,.vsr-slot td{border-top:1px solid #e1e6ea;padding:6px;text-align:left}.vsr-badge{display:inline-block;padding:2px 7px;border-radius:10px;background:#edf1f4}.vsr-status-committed,.vsr-status-substitute{background:#dff2e4;color:#245c36}.vsr-status-scheduled{background:#fff0c7;color:#735100}.vsr-status-find-sub{background:#fde2e2;color:#8b1f1f}.vsr-gap{background:#fde2e2;border:1px solid #d99b9b;border-radius:5px;color:#8b1f1f;display:inline-block;margin-top:9px;padding:6px 10px}.vsr-find-sub{margin-top:7px;color:#8b1f1f}
.vsr-definitions{background:#f7f9fb;border-top:3px solid #2b6f98;font-size:11px;margin-top:22px;padding:12px}.vsr-definitions-title{display:block;margin-bottom:4px}.vsr-definitions div{display:table;width:100%;padding:4px 0}.vsr-definitions div+div{border-top:1px solid #e1e6ea}.vsr-definitions div strong,.vsr-definitions div span{display:table-cell}.vsr-definitions div strong{width:185px}
@media(max-width:700px){.vsr-grid{grid-template-columns:1fr}.vsr-report-head,.vsr-slot-title{display:block}.vsr-slot table{font-size:11px}.vsr-summary td{padding:8px 4px}.vsr-summary strong{font-size:22px}.vsr-summary span{font-size:11px}.vsr-definitions div strong,.vsr-definitions div span{display:block}.vsr-definitions div strong{width:auto}}
@media print{.no-print,.vsr-shell{display:none!important}.vsr-report{margin:0;max-width:none}.vsr-slot{break-inside:avoid}.vsr-org{break-before:auto}}
</style>
"""


# TouchPoint runtime helpers and entry point

def setting(name, default):
    return str(model.Setting(SETTING_PREFIX + name, str(default)) or default)


def bool_setting(name, default):
    value = setting(name, "true" if default else "false").strip().lower()
    return value in ("true", "1", "yes", "y", "on")


def int_setting(name, default):
    return safe_int(setting(name, default), default)


def data_value(name, default=""):
    try:
        value = getattr(Data, name)
        return value if value is not None else default
    except Exception:
        try:
            value = getattr(model.Data, name)
            return value if value is not None else default
        except Exception:
            return default


def requested_action():
    return str(data_value("VSRAction", data_value("action", "")) or "").strip().lower()


def query_schedule(organization_ids, start_date, end_date):
    ids = parse_ids(organization_ids)
    if not ids:
        raise ValueError("Select at least one Scheduler Involvement.")
    if end_date < start_date:
        raise ValueError("End date must be on or after start date.")
    if (end_date - start_date).days > 92:
        raise ValueError("Date range cannot exceed 93 days.")
    sql = SCHEDULE_SQL.format(organization_ids=",".join(str(value) for value in ids))
    rows = list(q.QuerySql(sql, {
        "StartDate": sql_datetime(start_date),
        "EndDateExclusive": sql_datetime(end_date + datetime.timedelta(days=1)),
    }))
    return build_slots(rows)


def people_details(people_ids):
    ids = parse_ids(people_ids)
    if not ids:
        return []
    return list(q.QuerySql("""
        SELECT PeopleId, Name2, EmailAddress, CellPhone, IsDeceased, ArchivedFlag
        FROM People
        WHERE PeopleId IN ({0})
        ORDER BY Name2
    """.format(",".join(str(value) for value in ids))))


def people_query(people_ids):
    return "peopleids='{0}'".format(",".join(str(value) for value in parse_ids(people_ids)))


def email_configuration():
    return {
        "enabled": bool_setting("EmailEnabled", False),
        "queued_by": int_setting("QueuedByPeopleId", 0),
        "from_address": setting("FromAddress", ""),
        "from_name": setting("FromName", "Volunteer Scheduler"),
        "failure_ids": parse_ids(setting("FailureRecipientPeopleIds", "")),
    }


def validate_email_configuration(config):
    if not config["enabled"]:
        raise ValueError("Email is disabled in Volunteer Schedule Report Administration.")
    if config["queued_by"] <= 0:
        raise ValueError("Queued-by person is not configured.")
    if not config["from_address"] or "@" not in config["from_address"]:
        raise ValueError("A valid from address is required.")


def send_report_email(recipient_ids, subject, body):
    ids = parse_ids(recipient_ids)
    if not ids:
        raise ValueError("No recipients with TouchPoint People IDs were selected.")
    config = email_configuration()
    validate_email_configuration(config)
    model.Email(
        people_query(ids), config["queued_by"], config["from_address"],
        config["from_name"], subject, REPORT_STYLE + body,
    )


def search_involvements():
    term = str(data_value("term", "")).strip()
    exact_id = safe_int(term, 0)
    if len(term) < 2 and not exact_id:
        return '{"success":true,"items":[]}'
    rows = list(q.QuerySql("""
        SELECT TOP 15 o.OrganizationId, o.OrganizationName
        FROM Organizations o
        WHERE o.OrganizationStatusId = 30
          AND o.RegistrationTypeId = 22
          AND (o.OrganizationId = @ExactId OR o.OrganizationName LIKE @LikeTerm)
          AND EXISTS (
              SELECT 1
              FROM TimeSlotMeetings tsm
              JOIN Meetings m ON m.MeetingId = tsm.MeetingId
              WHERE m.OrganizationId = o.OrganizationId
          )
        ORDER BY CASE WHEN o.OrganizationId = @ExactId THEN 0 ELSE 1 END,
                 o.OrganizationName
    """, {"ExactId": exact_id, "LikeTerm": "%" + term + "%"}))
    items = []
    for row in rows:
        items.append({"id": safe_int(row.OrganizationId), "name": str(row.OrganizationName or "")})
    return json.dumps({"success": True, "items": items})


def search_people():
    term = str(data_value("term", "")).strip()
    exact_id = safe_int(term, 0)
    if len(term) < 2 and not exact_id:
        return '{"success":true,"items":[]}'
    rows = list(q.QuerySql("""
        SELECT TOP 15 PeopleId, Name2, EmailAddress, CellPhone
        FROM People
        WHERE PeopleId = @ExactId
           OR ((Name LIKE @LikeTerm OR Name2 LIKE @LikeTerm OR EmailAddress LIKE @LikeTerm)
               AND ISNULL(IsDeceased, 0) = 0 AND ISNULL(ArchivedFlag, 0) = 0)
        ORDER BY CASE WHEN PeopleId = @ExactId THEN 0 ELSE 1 END, Name2
    """, {"ExactId": exact_id, "LikeTerm": "%" + term + "%"}))
    items = []
    for row in rows:
        items.append({
            "id": safe_int(row.PeopleId), "name": str(row.Name2 or ""),
            "email": str(row.EmailAddress or ""), "phone": str(row.CellPhone or ""),
        })
    return json.dumps({"success": True, "items": items})


def load_profiles():
    document = load_profile_document()
    return profiles_from_document(document)


def load_profile_document():
    raw = str(model.TextContent(PROFILES_CONTENT) or "").strip()
    if not raw:
        return {"version": PROFILE_VERSION, "profiles": []}
    try:
        document = json.loads(raw)
    except Exception:
        raise ValueError("Saved profile content is not valid JSON. Correct or archive the Text Content before saving.")
    if not isinstance(document, dict) or safe_int(document.get("version"), 0) != PROFILE_VERSION:
        raise ValueError("Saved profile content has an unsupported version.")
    if not isinstance(document.get("profiles"), list):
        document["profiles"] = []
    return document


def save_profile_document(document):
    model.WriteContentText(PROFILES_CONTENT, json.dumps(document, sort_keys=True), "")


def validate_people_ids(ids):
    values = parse_ids(ids)
    if not values:
        return []
    rows = list(q.QuerySql("""
        SELECT PeopleId FROM People
        WHERE PeopleId IN ({0})
          AND ISNULL(IsDeceased, 0) = 0 AND ISNULL(ArchivedFlag, 0) = 0
    """.format(",".join(str(value) for value in values))))
    found = sorted(safe_int(row.PeopleId) for row in rows)
    if found != sorted(values):
        raise ValueError("One or more selected staff People IDs are invalid or inactive.")
    return values


def validate_scheduler_ids(ids):
    values = parse_ids(ids)
    if not values:
        raise ValueError("Select at least one Scheduler Involvement.")
    rows = list(q.QuerySql("""
        SELECT o.OrganizationId
        FROM Organizations o
        WHERE o.OrganizationId IN ({0})
          AND o.OrganizationStatusId = 30
          AND o.RegistrationTypeId = 22
          AND EXISTS (
              SELECT 1 FROM TimeSlotMeetings tsm
              JOIN Meetings m ON m.MeetingId = tsm.MeetingId
              WHERE m.OrganizationId = o.OrganizationId
          )
    """.format(",".join(str(value) for value in values))))
    found = sorted(safe_int(row.OrganizationId) for row in rows)
    if found != sorted(values):
        raise ValueError("One or more selected Involvements are not active Schedulers.")
    return values


def new_profile_id(name):
    base = "".join(char.lower() if char.isalnum() else "-" for char in str(name)).strip("-")
    while "--" in base:
        base = base.replace("--", "-")
    if not base:
        base = "profile"
    return "{0}-{1}".format(base[:28], datetime.datetime.now().strftime("%Y%m%d%H%M%S%f"))


def validate_unique_profile_name(profiles, name, current_id):
    wanted = str(name or "").strip().lower()
    for profile in profiles:
        if (str(profile.get("id", "")) != str(current_id or "") and
                str(profile.get("name", "")).strip().lower() == wanted):
            raise ValueError("A saved profile with this name already exists.")


def save_manual_profile(document):
    profiles = document["profiles"]
    profile_id = str(data_value("presetId", "") or "").strip()
    existing = selected_profile(profiles, profile_id)
    if profile_id and existing is None:
        raise ValueError("The selected saved profile was not found. Refresh the report and try again.")
    if existing is not None and profile_kind(existing) != "manual":
        raise ValueError("Monday Batch profiles can only be edited in Volunteer Schedule Report Administration.")
    name = str(data_value("profileName", "") or "").strip()
    if not name:
        raise ValueError("Profile name is required.")
    validate_unique_profile_name(profiles, name, profile_id)
    scheduler_ids = validate_scheduler_ids(data_value("schedulerIds", ""))
    staff_ids = validate_people_ids(data_value("staffPeopleIds", ""))
    include_volunteers = truthy(data_value("includeServingVolunteers", ""))
    include_email = truthy(data_value("includeVolunteerEmail", ""))
    include_phone = truthy(data_value("includeVolunteerPhone", ""))
    acknowledged = truthy(data_value("privacyAcknowledged", ""))
    if not include_email and not include_phone:
        acknowledged = False
    if include_volunteers and (include_email or include_phone) and not acknowledged:
        raise ValueError("Confirm the contact-information notice before saving volunteer delivery with contact details.")
    value = {
        "id": str(existing.get("id")) if existing else new_profile_id(name),
        "name": name,
        "profile_type": "manual",
        "scheduler_ids": scheduler_ids,
        "include_serving_volunteers": include_volunteers,
        "include_volunteer_email": include_email,
        "include_volunteer_phone": include_phone,
        "staff_people_ids": staff_ids,
        "enabled": False,
        "send_weekday": 0,
        "privacy_acknowledged": acknowledged,
        "last_saved_people_id": safe_int(getattr(model, "UserPeopleId", 0)),
        "last_saved_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }
    if existing:
        profiles[profiles.index(existing)] = value
    else:
        profiles.append(value)
    profiles.sort(key=lambda item: str(item.get("name", "")).lower())
    save_profile_document(document)
    return value


def delete_manual_profile(document):
    profile_id = str(data_value("presetId", "") or "").strip()
    existing = selected_profile(document["profiles"], profile_id)
    if existing is None:
        raise ValueError("Select a saved standalone profile to delete.")
    if profile_kind(existing) != "manual":
        raise ValueError("Monday Batch profiles can only be deleted in Volunteer Schedule Report Administration.")
    document["profiles"].remove(existing)
    save_profile_document(document)


def load_send_state():
    document = load_json_text(model.TextContent(STATE_CONTENT), {"version": STATE_VERSION, "sent": {}})
    if not isinstance(document, dict) or safe_int(document.get("version"), 0) != STATE_VERSION:
        return {"version": STATE_VERSION, "sent": {}}
    if not isinstance(document.get("sent"), dict):
        document["sent"] = {}
    return document


def save_send_state(state):
    model.WriteContentText(STATE_CONTENT, json.dumps(state, sort_keys=True), "")


def resolve_email_recipients(recipient_ids):
    deliverable = []
    missing = []
    for row in people_details(recipient_ids):
        if bool(row.IsDeceased) or bool(row.ArchivedFlag):
            missing.append("{0} (inactive)".format(str(row.Name2 or "Person {0}".format(row.PeopleId))))
        elif str(row.EmailAddress or "").strip():
            deliverable.append(safe_int(row.PeopleId))
        else:
            missing.append(str(row.Name2 or "Person {0}".format(row.PeopleId)))
    return deliverable, missing


def run_profiles():
    today = central_today()
    profiles = load_profiles()
    state = load_send_state()
    results = []
    errors = []
    if today.weekday() != 0:
        print("Volunteer Schedule Report: no profiles due; today is not Monday.")
        return
    start_date, end_date = next_weekend_from_monday(today)
    window_key = "{0}|{1}".format(iso_date(start_date), iso_date(end_date))
    for profile in profiles:
        if (profile_kind(profile) != "monday" or
                not bool(profile.get("enabled", False)) or
                safe_int(profile.get("send_weekday", 0), 0) != today.weekday()):
            continue
        profile_id = str(profile.get("id"))
        name = str(profile.get("name") or profile_id)
        if state["sent"].get(profile_id) == window_key:
            results.append("{0}: already sent for {1}".format(name, window_key))
            continue
        try:
            slots = query_schedule(profile.get("scheduler_ids", []), start_date, end_date)
            recipients = recipient_people_ids(
                slots, bool(profile.get("include_serving_volunteers", False)),
                parse_ids(profile.get("staff_people_ids", [])),
            )
            if not recipients:
                raise ValueError("profile has no recipients for this date range")
            title = str(profile.get("name") or "Volunteer Schedule")
            body = render_report(
                slots, start_date, end_date, title, False,
                bool(profile.get("include_volunteer_email", True)),
                bool(profile.get("include_volunteer_phone", True)),
            )
            subject = "{0} - {1} through {2}".format(title, start_date.strftime("%b %d"), end_date.strftime("%b %d, %Y"))
            deliverable, missing = resolve_email_recipients(recipients)
            send_report_email(deliverable, subject, body)
            state["sent"][profile_id] = window_key
            save_send_state(state)
            note = "{0}: queued to {1} people".format(name, len(deliverable))
            if missing:
                note += "; no email for " + ", ".join(missing)
            results.append(note)
        except Exception as error:
            message = "{0}: {1}".format(name, error)
            errors.append(message)
            results.append(message)
    if errors:
        config = email_configuration()
        if config["enabled"] and config["failure_ids"]:
            try:
                model.Email(
                    people_query(config["failure_ids"]), config["queued_by"],
                    config["from_address"], config["from_name"],
                    "Volunteer Schedule Report profile failure",
                    "<p>{0}</p>".format("<br>".join(html_escape(value) for value in errors)),
                )
            except Exception as notify_error:
                results.append("Failure notification could not be queued: {0}".format(notify_error))
    print("<h3>Volunteer Schedule Report batch</h3><ul>{0}</ul>".format(
        "".join("<li>{0}</li>".format(html_escape(value)) for value in results)
        if results else "<li>No enabled profiles were due.</li>"
    ))


def load_selected_involvements(ids):
    values = parse_ids(ids)
    if not values:
        return []
    return list(q.QuerySql("""
        SELECT OrganizationId, OrganizationName
        FROM Organizations
        WHERE OrganizationId IN ({0})
        ORDER BY OrganizationName
    """.format(",".join(str(value) for value in values))))


def profile_presets(profiles):
    presets = []
    for profile in sorted(profiles, key=lambda item: str(item.get("name", "")).lower()):
        orgs = load_selected_involvements(profile.get("scheduler_ids", []))
        staff = people_details(profile.get("staff_people_ids", []))
        presets.append({
            "id": str(profile.get("id", "")),
            "name": str(profile.get("name", "")),
            "profile_type": profile_kind(profile),
            "read_only": profile_kind(profile) == "monday",
            "enabled": bool(profile.get("enabled", False)),
            "orgs": [{"id": safe_int(row.OrganizationId),
                      "name": str(row.OrganizationName or "")} for row in orgs],
            "staff": [{"id": safe_int(row.PeopleId), "name": str(row.Name2 or ""),
                       "email": str(row.EmailAddress or "")} for row in staff],
            "include_serving_volunteers": bool(
                profile.get("include_serving_volunteers", False)),
            "include_volunteer_email": bool(
                profile.get("include_volunteer_email", True)),
            "include_volunteer_phone": bool(
                profile.get("include_volunteer_phone", True)),
            "privacy_acknowledged": bool(
                profile.get("privacy_acknowledged", False)),
        })
    return presets


def render_runner(selected_org_ids, staff_ids, start_date, end_date, include_serving,
                  include_email, include_phone, selected_profile_id, profiles,
                  profile_name, privacy_acknowledged, report_html, message):
    selected_orgs = load_selected_involvements(selected_org_ids)
    selected_staff = people_details(staff_ids)
    org_json = json_for_script([{"id": safe_int(r.OrganizationId), "name": str(r.OrganizationName or "")} for r in selected_orgs])
    staff_json = json_for_script([{"id": safe_int(r.PeopleId), "name": str(r.Name2 or ""), "email": str(r.EmailAddress or "")} for r in selected_staff])
    presets = profile_presets(profiles)
    presets_json = json_for_script(presets)
    preset_options = ['<option value="">Custom report</option>']
    for preset in presets:
        selected = " selected" if preset["id"] == str(selected_profile_id or "") else ""
        if preset["profile_type"] == "monday":
            label = preset["name"] + " — Monday Batch"
            if not preset["enabled"]:
                label += " (disabled)"
        else:
            label = preset["name"] + " — Saved Profile"
        preset_options.append('<option value="{0}"{1}>{2}</option>'.format(
            html_escape(preset["id"]), selected, html_escape(label)))
    checked = " checked" if include_serving else ""
    checked_email = " checked" if include_email else ""
    checked_phone = " checked" if include_phone else ""
    checked_privacy = " checked" if privacy_acknowledged else ""
    contact_notice_style = "" if include_email or include_phone else ' style="display:none"'
    selected_value = selected_profile(profiles, selected_profile_id)
    profile_read_only = selected_value is not None and profile_kind(selected_value) == "monday"
    profile_read_only_note = ""
    if profile_read_only:
        profile_read_only_note = '<div class="alert alert-info">This is a Monday Batch profile. You may use or adjust it for this report, but it can only be edited or deleted in Volunteer Schedule Report Administration.</div>'
    save_disabled = " disabled" if profile_read_only else ""
    delete_disabled = "" if selected_value is not None and not profile_read_only else " disabled"
    save_label = "Update profile" if selected_value is not None and not profile_read_only else "Save as new profile"
    email_is_enabled = bool_setting("EmailEnabled", False)
    email_disabled = "" if email_is_enabled else " disabled"
    email_note = "Email is enabled. Select serving volunteers and/or a staff recipient." if email_is_enabled else "Email is disabled. Configure and save Delivery settings in VolunteerScheduleReportAdmin."
    parts = [REPORT_STYLE]
    parts.append('<div class="vsr-shell"><div class="vsr-panel"><h2>Volunteer Schedule Report <small>v{0}</small></h2>'.format(APP_VERSION))
    if message:
        parts.append(message)
    parts.append("""
<form action="/PyScriptForm/VolunteerScheduleReport" method="post" id="vsrForm">
  <div class="vsr-grid">
    <div class="wide"><label for="vsrProfilePreset">Saved Profile Preset</label>
      <select class="form-control" name="presetId" id="vsrProfilePreset">{12}</select>
      <span class="help-block" id="vsrPresetHelp">Selecting a preset fills this form only. It does not send email or change the saved profile.</span></div>
    <div class="wide" id="vsrProfileNotice" aria-live="polite">{14}</div>
    <div class="wide"><label for="vsrProfileName">Profile name</label><input class="form-control" name="profileName" id="vsrProfileName" value="{15}" maxlength="100"></div>
    <div class="wide"><label for="vsrOrgSearch">Scheduler Involvements</label><div class="vsr-results">
      <input type="search" class="form-control" id="vsrOrgSearch" placeholder="Search by Scheduler name or ID" autocomplete="off">
      <div id="vsrOrgResults" aria-live="polite"></div></div><div class="vsr-selected" id="vsrSelectedOrgs" aria-live="polite"></div>
      <input type="hidden" name="schedulerIds" id="vsrSchedulerIds" value="{0}"></div>
    <div><label for="vsrStartDate">Start date</label><input class="form-control" id="vsrStartDate" type="date" name="startDate" value="{1}" required></div>
    <div><label for="vsrEndDate">End date</label><input class="form-control" id="vsrEndDate" type="date" name="endDate" value="{2}" required></div>
    <div><label><input type="checkbox" name="includeVolunteerEmail" id="vsrIncludeEmail" value="true"{10}> Include volunteer email addresses</label></div>
    <div><label><input type="checkbox" name="includeVolunteerPhone" id="vsrIncludePhone" value="true"{11}> Include volunteer mobile phones</label></div>
    <div class="wide"><label><input type="checkbox" name="includeServingVolunteers" value="true"{3}> Email all volunteers serving in this range</label></div>
    <div class="wide"><label for="vsrPersonSearch">Staff Recipients</label><div class="vsr-results">
      <input type="search" class="form-control" id="vsrPersonSearch" placeholder="Search staff by name, email, or People ID" autocomplete="off">
      <div id="vsrPersonResults" aria-live="polite"></div></div><div class="vsr-selected" id="vsrSelectedStaff" aria-live="polite"></div>
      <input type="hidden" name="staffPeopleIds" id="vsrStaffIds" value="{4}"></div>
    <div class="wide vsr-privacy" id="vsrContactNotice"{20}><strong>Contact Information Notice</strong><p>Each recipient receives the same complete report. Any selected contact fields are visible for every listed volunteer.</p><label><input type="checkbox" name="privacyAcknowledged" id="vsrPrivacyAcknowledged" value="true"{16}> I confirm this profile is authorized to distribute the selected contact details.</label></div>
  </div>
  <div style="margin-top:15px"><button class="btn btn-default" id="vsrSaveProfileButton" name="VSRAction" value="save_profile"{17}>{18}</button>
  <button class="btn btn-danger" id="vsrDeleteProfileButton" name="VSRAction" value="delete_profile" onclick="return confirm('Delete this saved standalone profile?')"{19}>Delete profile</button></div>
  <div style="margin-top:15px"><button class="btn btn-primary" name="VSRAction" value="preview" formtarget="_blank">Preview report</button>
  <button class="btn btn-default" id="vsrEmailButton" name="VSRAction" value="email"{7}>Email current report</button>
  <span class="help-block" id="vsrEmailNote">{8}</span></div>
</form></div></div>
<script>
(function(){{
  var orgs={5}, people={6}, presets={13};
  var form=document.getElementById('vsrForm'),dirty=false,activePresetId=document.getElementById('vsrProfilePreset').value;
  function esc(v){{return String(v||'').replace(/[&<>"']/g,function(c){{return {{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c];}});}}
  var emailEnabled={9};
  function updateEmailButton(){{var button=document.getElementById('vsrEmailButton'),serving=document.querySelector('input[name="includeServingVolunteers"]'),staff=document.getElementById('vsrStaffIds');if(button)button.disabled=!emailEnabled||!(serving.checked||staff.value);}}
  function updateContactNotice(){{var email=document.getElementById('vsrIncludeEmail'),phone=document.getElementById('vsrIncludePhone'),notice=document.getElementById('vsrContactNotice'),ack=document.getElementById('vsrPrivacyAcknowledged'),show=email.checked||phone.checked;notice.style.display=show?'':'none';if(!show)ack.checked=false;}}
  function profileById(id){{var i;for(i=0;i<presets.length;i++)if(presets[i].id===id)return presets[i];return null;}}
  function updateProfileControls(preset){{var readOnly=preset&&preset.read_only,save=document.getElementById('vsrSaveProfileButton'),del=document.getElementById('vsrDeleteProfileButton'),notice=document.getElementById('vsrProfileNotice');save.disabled=!!readOnly;save.textContent=preset&&!readOnly?'Update profile':'Save as new profile';del.disabled=!preset||!!readOnly;notice.innerHTML=readOnly?'<div class="alert alert-info">This is a Monday Batch profile. You may use or adjust it for this report, but it can only be edited or deleted in Volunteer Schedule Report Administration.</div>':'';}}
  function draw(items, box, hidden){{box.innerHTML='';items.forEach(function(x,i){{var s=document.createElement('span');s.className='vsr-pill';s.innerHTML=esc(x.name)+' <button type="button" aria-label="Remove">&times;</button>';s.querySelector('button').onclick=function(){{items.splice(i,1);draw(items,box,hidden);}};box.appendChild(s);}});hidden.value=items.map(function(x){{return x.id;}}).join(',');updateEmailButton();}}
  function search(input, resultBox, action, selected, selectedBox, hidden){{var timer;input.oninput=function(){{clearTimeout(timer);var term=input.value.trim();if(term.length<2){{resultBox.innerHTML='';return;}}timer=setTimeout(function(){{var body='VSRAction='+encodeURIComponent(action)+'&term='+encodeURIComponent(term);fetch('/PyScriptForm/VolunteerScheduleReport',{{method:'POST',headers:{{'Content-Type':'application/x-www-form-urlencoded'}},body:body}}).then(function(r){{return r.json();}}).then(function(d){{resultBox.className='vsr-results-list';resultBox.innerHTML='';(d.items||[]).forEach(function(x){{var b=document.createElement('button');b.type='button';b.className='vsr-result';b.textContent=x.name+' ('+x.id+')'+(x.email?' — '+x.email:'');b.onclick=function(){{if(!selected.some(function(y){{return y.id===x.id;}}))selected.push(x);draw(selected,selectedBox,hidden);resultBox.innerHTML='';input.value='';}};resultBox.appendChild(b);}});}});}},250);}};}}
  var orgBox=document.getElementById('vsrSelectedOrgs'),orgHidden=document.getElementById('vsrSchedulerIds');
  var staffBox=document.getElementById('vsrSelectedStaff'),staffHidden=document.getElementById('vsrStaffIds');
  draw(orgs,orgBox,orgHidden);draw(people,staffBox,staffHidden);
  form.oninput=function(e){{if(e.target.id!=='vsrProfilePreset')dirty=true;}};
  form.onchange=function(e){{if(e.target.id!=='vsrProfilePreset')dirty=true;if(e.target.id==='vsrIncludeEmail'||e.target.id==='vsrIncludePhone')updateContactNotice();}};
  form.onsubmit=function(){{dirty=false;}};
  document.getElementById('vsrProfilePreset').onchange=function(){{if(dirty&&!confirm('Discard unsaved changes and load another profile?')){{this.value=activePresetId;return;}}activePresetId=this.value;dirty=false;var preset=profileById(this.value);if(!preset){{orgs=[];people=[];draw(orgs,orgBox,orgHidden);draw(people,staffBox,staffHidden);document.getElementById('vsrProfileName').value='';document.querySelector('input[name="includeServingVolunteers"]').checked=false;document.querySelector('input[name="includeVolunteerEmail"]').checked=false;document.querySelector('input[name="includeVolunteerPhone"]').checked=false;document.getElementById('vsrPrivacyAcknowledged').checked=false;updateProfileControls(null);updateContactNotice();updateEmailButton();return;}}orgs=preset.orgs.slice(0);people=preset.staff.slice(0);draw(orgs,orgBox,orgHidden);draw(people,staffBox,staffHidden);document.getElementById('vsrProfileName').value=preset.name;document.querySelector('input[name="includeServingVolunteers"]').checked=preset.include_serving_volunteers;document.querySelector('input[name="includeVolunteerEmail"]').checked=preset.include_volunteer_email;document.querySelector('input[name="includeVolunteerPhone"]').checked=preset.include_volunteer_phone;document.getElementById('vsrPrivacyAcknowledged').checked=preset.privacy_acknowledged;updateProfileControls(preset);updateContactNotice();updateEmailButton();}};
  updateProfileControls(profileById(document.getElementById('vsrProfilePreset').value));
  updateContactNotice();
  document.querySelector('input[name="includeServingVolunteers"]').onchange=updateEmailButton;
  search(document.getElementById('vsrOrgSearch'),document.getElementById('vsrOrgResults'),'search_involvements',orgs,orgBox,orgHidden);
  search(document.getElementById('vsrPersonSearch'),document.getElementById('vsrPersonResults'),'search_people',people,staffBox,staffHidden);
}})();
</script>
""".format(
        html_escape(",".join(str(value) for value in parse_ids(selected_org_ids))),
        html_escape(iso_date(start_date)), html_escape(iso_date(end_date)), checked,
        html_escape(",".join(str(value) for value in parse_ids(staff_ids))),
        org_json, staff_json, email_disabled, html_escape(email_note),
        "true" if email_is_enabled else "false", checked_email, checked_phone,
        "".join(preset_options), presets_json, profile_read_only_note,
        html_escape(profile_name), checked_privacy, save_disabled, save_label,
        delete_disabled, contact_notice_style,
    ))
    if report_html:
        parts.append(REPORT_STYLE + report_html)
    return "".join(parts)


def run_interactive():
    action = requested_action()
    if action == "search_involvements":
        return search_involvements()
    if action == "search_people":
        return search_people()
    today = central_today()
    default_start, default_end = current_or_next_weekend(today)
    selected_org_ids = parse_ids(data_value("schedulerIds", data_value("CurrentOrgId", "")))
    staff_ids = parse_ids(data_value("staffPeopleIds", ""))
    document = {"version": PROFILE_VERSION, "profiles": []}
    profiles = []
    message = ""
    profile_load_error = None
    try:
        document = load_profile_document()
        profiles = profiles_from_document(document)
    except Exception as error:
        profile_load_error = error
        message = '<div class="alert alert-danger">{0}</div>'.format(html_escape(error))
    selected_profile_id = str(data_value("presetId", "") or "").strip()
    preset = selected_profile(profiles, selected_profile_id)
    profile_name = str(data_value("profileName", "") or "").strip()
    include_serving = truthy(data_value("includeServingVolunteers", ""))
    include_email = truthy(data_value("includeVolunteerEmail", ""))
    include_phone = truthy(data_value("includeVolunteerPhone", ""))
    privacy_acknowledged = truthy(data_value("privacyAcknowledged", ""))
    start_date = default_start
    end_date = default_end
    report_html = ""
    if action:
        try:
            start_date = parse_iso_date(data_value("startDate"))
            end_date = parse_iso_date(data_value("endDate"))
        except Exception as error:
            message = '<div class="alert alert-danger">{0}</div>'.format(html_escape(error))
    if action == "save_profile":
        try:
            if profile_load_error is not None:
                raise profile_load_error
            saved = save_manual_profile(document)
            profiles = profiles_from_document(document)
            selected_profile_id = str(saved["id"])
            preset = saved
            profile_name = str(saved["name"])
            privacy_acknowledged = bool(saved.get("privacy_acknowledged", False))
            message = '<div class="alert alert-success">Profile saved: {0}</div>'.format(
                html_escape(saved["name"]))
        except Exception as error:
            message = '<div class="alert alert-danger">{0}</div>'.format(html_escape(error))
    elif action == "delete_profile":
        try:
            if profile_load_error is not None:
                raise profile_load_error
            delete_manual_profile(document)
            profiles = profiles_from_document(document)
            selected_profile_id = ""
            preset = None
            profile_name = ""
            selected_org_ids = []
            staff_ids = []
            include_serving = False
            include_email = False
            include_phone = False
            privacy_acknowledged = False
            message = '<div class="alert alert-success">Saved profile deleted.</div>'
        except Exception as error:
            message = '<div class="alert alert-danger">{0}</div>'.format(html_escape(error))
    elif action in ("preview", "email"):
        try:
            slots = query_schedule(selected_org_ids, start_date, end_date)
            title = str(preset.get("name")) if preset else "Volunteer Schedule"
            report_html = render_report(
                slots, start_date, end_date, title, True,
                include_email, include_phone,
            )
            if action == "email":
                recipients = recipient_people_ids(slots, include_serving, staff_ids)
                deliverable, missing = resolve_email_recipients(recipients)
                subject = "Volunteer Schedule - {0} through {1}".format(start_date.strftime("%b %d"), end_date.strftime("%b %d, %Y"))
                send_report_email(
                    deliverable, subject,
                    render_report(slots, start_date, end_date, title, False,
                                  include_email, include_phone),
                )
                message = '<div class="alert alert-success">Report queued to {0} people.{1}</div>'.format(
                    len(deliverable),
                    " People without email: " + html_escape(", ".join(missing)) if missing else "",
                )
        except Exception as error:
            message = '<div class="alert alert-danger">{0}</div>'.format(html_escape(error))
    if action == "preview":
        model.Header = ""
        if report_html:
            return REPORT_STYLE + report_html
        return REPORT_STYLE + '<div class="vsr-report">{0}</div>'.format(message)
    return render_runner(
        selected_org_ids, staff_ids, start_date, end_date, include_serving,
        include_email, include_phone, selected_profile_id, profiles,
        profile_name, privacy_acknowledged, report_html, message,
    )


def emit_form(content):
    model.Form = content
    print(content)


if "model" in globals():
    model.Header = "Volunteer Schedule Report v{0}".format(APP_VERSION)
    model.Transactional = True
    runtime_action = requested_action()
    is_admin = model.UserIsInRole("Admin")
    if runtime_action == "run_profiles" and not is_admin:
        emit_form('<div class="alert alert-danger">Administrator access is required to run saved profiles.</div>')
    elif runtime_action == "run_profiles":
        run_profiles()
    else:
        emit_form(run_interactive())
