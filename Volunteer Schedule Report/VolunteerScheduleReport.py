#Roles=Access

"""
Weekly Volunteer Schedule Report for TouchPoint Scheduler Involvements.

Read-only with respect to people, Involvements, meetings, assignments, and
commitments. The only writes are successful automated-send state in Text
Content. Email is disabled by default.

Scheduler table relationships were informed by TPxi Scheduler Report v2.2:
https://github.com/bswaby/Touchpoint/tree/main/TPxi/Scheduler%20Report
"""

import cgi
import datetime
import json


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
        parts.append('<div class="vsr-actions no-print"><button type="button" class="btn btn-default" onclick="window.print()">Print report</button></div>')
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
            "".join("<th>{0}</th>".format(html_escape(value)) for value in headings)
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
<style>
.vsr-shell,.vsr-report{max-width:1180px;margin:20px auto;color:#24313d}
.vsr-panel{border:1px solid #d8e0e7;border-radius:8px;padding:18px;background:#fff;margin-bottom:18px}
.vsr-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.vsr-grid .wide{grid-column:1/-1}
.vsr-selected{display:flex;gap:6px;flex-wrap:wrap;margin-top:7px}.vsr-pill{background:#e8f1f8;border-radius:14px;padding:4px 9px}
.vsr-results{position:relative}.vsr-results-list{position:absolute;z-index:4;background:#fff;border:1px solid #ccd6df;width:100%;box-shadow:0 3px 10px #999;max-height:220px;overflow:auto}
.vsr-result{display:block;width:100%;text-align:left;border:0;border-bottom:1px solid #eee;background:#fff;padding:8px}.vsr-result:hover{background:#f3f7fa}
.vsr-report-head{margin-bottom:12px}.vsr-summary{border-collapse:separate;border-spacing:0;margin:0 0 20px;table-layout:fixed;width:100%}.vsr-summary td{background:#eef3f6;border:1px solid #d8e0e7;border-right:0;overflow-wrap:anywhere;padding:12px;vertical-align:top;width:20%}.vsr-summary td:first-child{border-radius:7px 0 0 7px}.vsr-summary td:last-child{border-radius:0 7px 7px 0;border-right:1px solid #d8e0e7}.vsr-summary strong{display:block;font-size:26px;margin-bottom:4px}.vsr-summary span{display:block;font-weight:bold}.vsr-summary-confirmed{background:#dff2e4!important}.vsr-summary-awaiting{background:#fff0c7!important}.vsr-summary-vacancy,.vsr-summary-warning{background:#fde2e2!important}.vsr-actions{margin:10px 0}
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
    document = load_json_text(model.TextContent(PROFILES_CONTENT), {"version": PROFILE_VERSION, "profiles": []})
    return profiles_from_document(document)


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
        if not bool(profile.get("enabled", False)) or safe_int(profile.get("send_weekday", 0), 0) != today.weekday():
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
        })
    return presets


def render_runner(selected_org_ids, staff_ids, start_date, end_date, include_serving,
                  include_email, include_phone, selected_profile_id, profiles,
                  report_html, message):
    selected_orgs = load_selected_involvements(selected_org_ids)
    selected_staff = people_details(staff_ids)
    org_json = json_for_script([{"id": safe_int(r.OrganizationId), "name": str(r.OrganizationName or "")} for r in selected_orgs])
    staff_json = json_for_script([{"id": safe_int(r.PeopleId), "name": str(r.Name2 or ""), "email": str(r.EmailAddress or "")} for r in selected_staff])
    presets = profile_presets(profiles)
    presets_json = json_for_script(presets)
    preset_options = ['<option value="">Custom report</option>']
    for preset in presets:
        selected = " selected" if preset["id"] == str(selected_profile_id or "") else ""
        label = preset["name"] if preset["enabled"] else preset["name"] + " (disabled)"
        preset_options.append('<option value="{0}"{1}>{2}</option>'.format(
            html_escape(preset["id"]), selected, html_escape(label)))
    checked = " checked" if include_serving else ""
    checked_email = " checked" if include_email else ""
    checked_phone = " checked" if include_phone else ""
    email_is_enabled = bool_setting("EmailEnabled", False)
    email_disabled = "" if email_is_enabled else " disabled"
    email_note = "Email is enabled. Select serving volunteers and/or a staff recipient." if email_is_enabled else "Email is disabled. Configure and save Delivery settings in VolunteerScheduleReportAdmin."
    parts = [REPORT_STYLE]
    parts.append('<div class="vsr-shell"><div class="vsr-panel"><h2>Volunteer Schedule Report</h2>')
    if message:
        parts.append(message)
    parts.append("""
<form action="/PyScriptForm/VolunteerScheduleReport" method="post" id="vsrForm">
  <div class="vsr-grid">
    <div class="wide"><label>Saved Monday profile preset</label>
      <select class="form-control" name="presetId" id="vsrProfilePreset">{12}</select>
      <span class="help-block">Selecting a preset fills this form only. It does not send email or change the saved profile.</span></div>
    <div class="wide"><label>Scheduler Involvements</label><div class="vsr-results">
      <input type="search" class="form-control" id="vsrOrgSearch" placeholder="Search by Scheduler name or ID" autocomplete="off">
      <div id="vsrOrgResults"></div></div><div class="vsr-selected" id="vsrSelectedOrgs"></div>
      <input type="hidden" name="schedulerIds" id="vsrSchedulerIds" value="{0}"></div>
    <div><label>Start date</label><input class="form-control" type="date" name="startDate" value="{1}" required></div>
    <div><label>End date</label><input class="form-control" type="date" name="endDate" value="{2}" required></div>
    <div><label><input type="checkbox" name="includeVolunteerEmail" value="true"{10}> Include volunteer email addresses</label></div>
    <div><label><input type="checkbox" name="includeVolunteerPhone" value="true"{11}> Include volunteer mobile phones</label></div>
    <div class="wide"><label><input type="checkbox" name="includeServingVolunteers" value="true"{3}> Email all volunteers serving in this range</label></div>
    <div class="wide"><label>Additional staff recipients</label><div class="vsr-results">
      <input type="search" class="form-control" id="vsrPersonSearch" placeholder="Search staff by name, email, or People ID" autocomplete="off">
      <div id="vsrPersonResults"></div></div><div class="vsr-selected" id="vsrSelectedStaff"></div>
      <input type="hidden" name="staffPeopleIds" id="vsrStaffIds" value="{4}"></div>
  </div>
  <div style="margin-top:15px"><button class="btn btn-primary" name="VSRAction" value="preview">Preview report</button>
  <button class="btn btn-default" id="vsrEmailButton" name="VSRAction" value="email"{7}>Email current report</button>
  <span class="help-block" id="vsrEmailNote">{8}</span></div>
</form></div></div>
<script>
(function(){{
  var orgs={5}, people={6}, presets={13};
  function esc(v){{return String(v||'').replace(/[&<>"']/g,function(c){{return {{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c];}});}}
  var emailEnabled={9};
  function updateEmailButton(){{var button=document.getElementById('vsrEmailButton'),serving=document.querySelector('input[name="includeServingVolunteers"]'),staff=document.getElementById('vsrStaffIds');if(button)button.disabled=!emailEnabled||!(serving.checked||staff.value);}}
  function draw(items, box, hidden){{box.innerHTML='';items.forEach(function(x,i){{var s=document.createElement('span');s.className='vsr-pill';s.innerHTML=esc(x.name)+' <button type="button" aria-label="Remove">&times;</button>';s.querySelector('button').onclick=function(){{items.splice(i,1);draw(items,box,hidden);}};box.appendChild(s);}});hidden.value=items.map(function(x){{return x.id;}}).join(',');updateEmailButton();}}
  function search(input, resultBox, action, selected, selectedBox, hidden){{var timer;input.oninput=function(){{clearTimeout(timer);var term=input.value.trim();if(term.length<2){{resultBox.innerHTML='';return;}}timer=setTimeout(function(){{var body='VSRAction='+encodeURIComponent(action)+'&term='+encodeURIComponent(term);fetch('/PyScriptForm/VolunteerScheduleReport',{{method:'POST',headers:{{'Content-Type':'application/x-www-form-urlencoded'}},body:body}}).then(function(r){{return r.json();}}).then(function(d){{resultBox.className='vsr-results-list';resultBox.innerHTML='';(d.items||[]).forEach(function(x){{var b=document.createElement('button');b.type='button';b.className='vsr-result';b.textContent=x.name+' ('+x.id+')'+(x.email?' — '+x.email:'');b.onclick=function(){{if(!selected.some(function(y){{return y.id===x.id;}}))selected.push(x);draw(selected,selectedBox,hidden);resultBox.innerHTML='';input.value='';}};resultBox.appendChild(b);}});}});}},250);}};}}
  var orgBox=document.getElementById('vsrSelectedOrgs'),orgHidden=document.getElementById('vsrSchedulerIds');
  var staffBox=document.getElementById('vsrSelectedStaff'),staffHidden=document.getElementById('vsrStaffIds');
  draw(orgs,orgBox,orgHidden);draw(people,staffBox,staffHidden);
  document.getElementById('vsrProfilePreset').onchange=function(){{var id=this.value,preset=null,i;for(i=0;i<presets.length;i++){{if(presets[i].id===id){{preset=presets[i];break;}}}}if(!preset)return;orgs=preset.orgs.slice(0);people=preset.staff.slice(0);draw(orgs,orgBox,orgHidden);draw(people,staffBox,staffHidden);document.querySelector('input[name="includeServingVolunteers"]').checked=preset.include_serving_volunteers;document.querySelector('input[name="includeVolunteerEmail"]').checked=preset.include_volunteer_email;document.querySelector('input[name="includeVolunteerPhone"]').checked=preset.include_volunteer_phone;updateEmailButton();}};
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
        "".join(preset_options), presets_json,
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
    profiles = load_profiles()
    selected_profile_id = str(data_value("presetId", "") or "").strip()
    preset = selected_profile(profiles, selected_profile_id)
    include_serving = str(data_value("includeServingVolunteers", "")).lower() in ("true", "1", "yes", "on")
    include_email = True if not action else str(data_value("includeVolunteerEmail", "")).lower() in ("true", "1", "yes", "on")
    include_phone = True if not action else str(data_value("includeVolunteerPhone", "")).lower() in ("true", "1", "yes", "on")
    start_date = default_start
    end_date = default_end
    message = ""
    report_html = ""
    if action in ("preview", "email"):
        try:
            start_date = parse_iso_date(data_value("startDate"))
            end_date = parse_iso_date(data_value("endDate"))
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
    return render_runner(
        selected_org_ids, staff_ids, start_date, end_date, include_serving,
        include_email, include_phone, selected_profile_id, profiles,
        report_html, message,
    )


def emit_form(content):
    model.Form = content
    print(content)


if "model" in globals():
    model.Header = "Volunteer Schedule Report"
    model.Transactional = True
    runtime_action = requested_action()
    is_admin = model.UserIsInRole("Admin")
    is_manager = model.UserIsInRole("ManageGroups")
    if runtime_action == "run_profiles" and not is_admin:
        emit_form('<div class="alert alert-danger">Administrator access is required to run saved profiles.</div>')
    elif runtime_action != "run_profiles" and not (is_admin or is_manager):
        emit_form('<div class="alert alert-danger">Admin or Manage Groups access is required.</div>')
    elif runtime_action == "run_profiles":
        run_profiles()
    else:
        emit_form(run_interactive())
