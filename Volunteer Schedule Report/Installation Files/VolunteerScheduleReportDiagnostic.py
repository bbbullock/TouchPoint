#Roles=Admin
# -*- coding: utf-8 -*-
# Application: Volunteer Schedule Report Diagnostic
# Version: 1.0.0
# Released: 2026-08-15
# Written by: Brian Bullock with Codex assistance
# Email: bbbullock@mac.com
# GitHub: https://github.com/bbbullock/TouchPoint
#
# Version history
# 1.0.0 (2026-08-15)
# - Provides a read-only Scheduler schema and sample-data diagnostic.
# - Accepts an on-screen or hard-coded Scheduler Involvement ID.
# - Performs no email delivery and no TouchPoint data writes.

# Read-only schema and sample-data diagnostic for VolunteerScheduleReport.
# This deliberately uses no triple-quoted strings because some TouchPoint
# editors corrupt them during paste. It sends no email and performs no writes.

import cgi
import datetime


APP_VERSION = "1.0.0"

# Optional: replace 0 with a Scheduler Involvement ID. An ID entered in the
# on-screen form takes precedence over this value.
DEFAULT_INVOLVEMENT_ID = 0

TABLE_NAMES = ["TimeSlots", "TimeSlotTeams", "TimeSlotMeetings", "TimeSlotMeetingTeams", "TimeSlotTeamSubGroups", "TimeSlotMeetingTeamSubGroups", "TimeSlotMeetingTeamSubGroupVolunteers", "TimeSlotMeetingVolunteers", "Attend", "Meetings"]
ORG_SQL = "SELECT OrganizationId, OrganizationName, OrganizationStatusId, RegistrationTypeId FROM dbo.Organizations WHERE OrganizationId = @OrganizationId"
SCHEMA_SQL = "SELECT TABLE_NAME AS TableName, COLUMN_NAME AS ColumnName, DATA_TYPE AS DataType, IS_NULLABLE AS IsNullable FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME IN ({0}) ORDER BY TABLE_NAME, ORDINAL_POSITION"
COUNTS_SQL = "SELECT (SELECT COUNT(*) FROM TimeSlotMeetings tsm JOIN Meetings m ON m.MeetingId = tsm.MeetingId WHERE m.OrganizationId = @OrganizationId) AS TimeSlotMeetings, (SELECT COUNT(*) FROM TimeSlotMeetingTeams tsmt JOIN TimeSlotMeetings tsm ON tsm.TimeSlotMeetingId = tsmt.TimeSlotMeetingId JOIN Meetings m ON m.MeetingId = tsm.MeetingId WHERE m.OrganizationId = @OrganizationId) AS MeetingTeams, (SELECT COUNT(*) FROM TimeSlotMeetingTeamSubGroupVolunteers v JOIN TimeSlotMeetingTeams t ON t.TimeSlotMeetingTeamId = v.TimeSlotMeetingTeamId JOIN TimeSlotMeetings tsm ON tsm.TimeSlotMeetingId = t.TimeSlotMeetingId JOIN Meetings m ON m.MeetingId = tsm.MeetingId WHERE m.OrganizationId = @OrganizationId) AS AssignmentRows"
SAMPLE_SQL = ";WITH LatestAttend AS (SELECT MeetingId, PeopleId, MAX(AttendId) AS AttendId FROM Attend GROUP BY MeetingId, PeopleId) SELECT TOP 100 m.OrganizationId, o.OrganizationName, tsm.MeetingDateTime, tsmt.TeamName, CASE WHEN mt.Name IS NULL THEN '' ELSE mt.Name END AS SubGroupName, CASE WHEN tsmt.UseSubGroup = 0 THEN tst.NumberVolunteersNeeded ELSE tssg.NumberVolunteersNeeded END AS NumberNeeded, v.IsActive, p.PeopleId, p.Name2, p.EmailAddress, p.CellPhone, a.Commitment FROM TimeSlotMeetingTeams tsmt JOIN TimeSlotMeetings tsm ON tsm.TimeSlotMeetingId = tsmt.TimeSlotMeetingId JOIN Meetings m ON m.MeetingId = tsm.MeetingId JOIN Organizations o ON o.OrganizationId = m.OrganizationId LEFT JOIN TimeSlotTeams tst ON tst.TimeSlotId = tsm.TimeSlotId AND tst.TeamName = tsmt.TeamName LEFT JOIN TimeSlotMeetingTeamSubGroups tssg ON tssg.TimeSlotMeetingTeamId = tsmt.TimeSlotMeetingTeamId AND ISNULL(tssg.IsDeleted, 0) = 0 LEFT JOIN MemberTags mt ON mt.Id = tssg.MemberTagId AND mt.OrgId = m.OrganizationId LEFT JOIN TimeSlotMeetingTeamSubGroupVolunteers v ON v.IsActive <> 0 AND v.TimeSlotMeetingTeamId = tsmt.TimeSlotMeetingTeamId AND ((v.TimeSlotMeetingTeamSubGroupId IS NULL AND tssg.TimeSlotMeetingTeamSubGroupId IS NULL) OR v.TimeSlotMeetingTeamSubGroupId = tssg.TimeSlotMeetingTeamSubGroupId) LEFT JOIN People p ON p.PeopleId = v.PeopleId LEFT JOIN LatestAttend la ON la.MeetingId = m.MeetingId AND la.PeopleId = p.PeopleId LEFT JOIN Attend a ON a.AttendId = la.AttendId WHERE m.OrganizationId = @OrganizationId AND tsm.MeetingDateTime >= @StartDate AND tsm.MeetingDateTime < @EndDate ORDER BY tsm.MeetingDateTime, tsmt.TeamName, SubGroupName, p.Name2"


def escape(value):
    return cgi.escape(str(value if value is not None else ""), True)


def posted(name, default=""):
    try:
        value = getattr(Data, name)
        return str(value if value is not None else default).strip()
    except Exception:
        return default


def positive_id(raw):
    try:
        value = int(raw)
        if value > 0:
            return value
    except Exception:
        pass
    return 0


def requested_org_id():
    entered_id = positive_id(posted("OrganizationId"))
    configured_id = positive_id(DEFAULT_INVOLVEMENT_ID)
    context_id = positive_id(posted("CurrentOrgId"))
    return entered_id or configured_id or context_id


def render_rows(title, rows, columns):
    parts = ["<h3>" + escape(title) + "</h3>"]
    if not rows:
        return "".join(parts) + '<div class="alert alert-warning">No rows returned.</div>'
    parts.append('<div class="table-responsive"><table class="table table-striped table-condensed"><thead><tr>')
    for key, label in columns:
        parts.append("<th>" + escape(label) + "</th>")
    parts.append("</tr></thead><tbody>")
    for row in rows:
        parts.append("<tr>")
        for key, label in columns:
            parts.append("<td>" + escape(getattr(row, key, "")) + "</td>")
        parts.append("</tr>")
    parts.append("</tbody></table></div>")
    return "".join(parts)


def run_diagnostic(org_id):
    try:
        parameters = {"OrganizationId": org_id}
        org_rows = list(q.QuerySql(ORG_SQL, parameters))
        print(render_rows("Selected Involvement", org_rows, [("OrganizationId", "ID"), ("OrganizationName", "Name"), ("OrganizationStatusId", "Status ID"), ("RegistrationTypeId", "Registration Type ID")]))
        quoted_tables = ",".join("'" + name + "'" for name in TABLE_NAMES)
        schema_rows = list(q.QuerySql(SCHEMA_SQL.format(quoted_tables)))
        print(render_rows("Scheduler Table Columns", schema_rows, [("TableName", "Table"), ("ColumnName", "Column"), ("DataType", "Type"), ("IsNullable", "Nullable")]))
        count_rows = list(q.QuerySql(COUNTS_SQL, parameters))
        print(render_rows("Relationship Counts", count_rows, [("TimeSlotMeetings", "Time Slot Meetings"), ("MeetingTeams", "Meeting Teams"), ("AssignmentRows", "Assignment Rows")]))
        today = datetime.datetime.now().date()
        sample_parameters = {"OrganizationId": org_id, "StartDate": today, "EndDate": today + datetime.timedelta(days=60)}
        sample_rows = list(q.QuerySql(SAMPLE_SQL, sample_parameters))
        sample_columns = [("MeetingDateTime", "Date/Time"), ("TeamName", "Team"), ("SubGroupName", "Sub-Group"), ("NumberNeeded", "Needed"), ("IsActive", "Assignment Active"), ("PeopleId", "People ID"), ("Name2", "Volunteer"), ("Commitment", "Commitment"), ("EmailAddress", "Email"), ("CellPhone", "Cell Phone")]
        print(render_rows("Upcoming Sample (60 days)", sample_rows, sample_columns))
        print('<div class="alert alert-success">Diagnostic completed. Review the sample against the Scheduler screen before deploying the report.</div>')
    except Exception as error:
        print('<div class="alert alert-danger"><strong>Diagnostic failed:</strong> ' + escape(error) + "</div>")


def prompt_html(org_id):
    parts = []
    parts.append("<style>.vsr-diag{max-width:1180px;margin:20px auto}.vsr-diag .table{font-size:12px}.vsr-diag h3{margin-top:28px}</style>")
    parts.append('<div class="vsr-diag"><div class="alert alert-info"><strong>Read-only:</strong> this diagnostic queries schema and sample Scheduler data only.</div>')
    parts.append('<form method="post" class="form-inline"><label for="OrganizationId">Known Scheduler Involvement ID</label> ')
    parts.append('<input class="form-control" id="OrganizationId" name="OrganizationId" value="' + escape(org_id or "") + '" required> ')
    parts.append('<button class="btn btn-primary" type="submit">Run diagnostic</button></form>')
    parts.append('<p class="help-block">Enter an ID here, or set <code>DEFAULT_INVOLVEMENT_ID</code> near the top of the script. The entered value takes precedence.</p>')
    return "".join(parts)


def main():
    model.Header = "Volunteer Schedule Report Diagnostic v{0}".format(APP_VERSION)
    org_id = requested_org_id()
    print(prompt_html(org_id))
    if org_id:
        run_diagnostic(org_id)
    else:
        print('<div class="alert alert-warning">Enter the ID of a Scheduler Involvement, then click <strong>Run diagnostic</strong>.</div>')
    print("</div>")


main()
