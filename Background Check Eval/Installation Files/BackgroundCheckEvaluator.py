#Roles=Admin

# Background Check Evaluator
# Version: 3.1.3
# 2026-08-18 3.1.3 - Replaced tenant-specific installation defaults with
# safe empty values for public distribution; saved BCE settings still prevail.
# 2026-08-18 3.1.2 - Clarified Involvement coverage reporting by renaming
# Status to Processing result and using explicit evaluation-result labels.
# 2026-08-18 3.1.1 - Added a default-off Admin switch that suppresses
# Process Builder reminder lookups and report/email text during testing.
# 2026-08-18 3.1.0 - Added inline Process Builder reminder status for the
# Volunteer App and Background Check processes.
# 2026-08-18 3.0.4 - Kept evaluator version aligned with Process Builder
# diagnostic discovery; report integration awaits tenant schema results.
# 2026-08-18 3.0.3 - Ignore expired evaluate-through dates; fall back to
# future meetings when present and drop Involvements with neither.
# 2026-08-18 3.0.2 - Simplified report exception columns, added red failure
# cells, and show N/A for approved checks when background checks are age-exempt.
# 2026-08-18 3.0.1 - Use EvaluateBackgroundCheckThroughDate only when its
# DateValue is populated; blank standard EVs remain meeting-based.
# 2026-08-18 3.0.0 - Replaced the deprecated program-year flag and separate
# date configuration with the EvaluateBackgroundCheckThroughDate date EV.
# 2026-08-17 2.0.3 - Kept evaluator version aligned with Admin action routing.
# 2026-08-17 2.0.2 - Recognized the Admin's versioned reset-state marker as
# empty comparison history.
# 2026-08-17 2.0.1 - Finalized application evaluation against the tenant's
# confirmed AppStatus-qualified PeopleExtra field names.
# 2026-08-17 2.0.0 - Removed deprecated Volunteer Code evaluation and added
# support for both code-only and AppStatus-qualified application EV fields.
# 2026-08-17 1.2.4 - Kept evaluator version aligned with Admin toast semantics.
# 2026-08-17 1.2.3 - Kept evaluator version aligned with the Admin in-frame fix.
# 2026-08-17 1.2.2 - Kept evaluator version aligned with the Admin toast fix.
# 2026-08-17 1.2.1 - Made Volunteer Extra Values take precedence over
# corresponding legacy Volunteer Codes when an EV record exists.
# 2026-08-17 1.2.0 - Added Involvement program-year dates, current-age
# qualification, complete nightly coverage reporting, partial failure
# isolation, and Involvement-aware comparison history.
# 2026-08-16 1.1.0 - Added People Extra Value migration support and a
# configurable legacy Volunteer Code transition mode.
# 2026-07-28 1.0.0 - Added nightly comparison history and Admin configuration.
# Written by: Brian Bullock with Codex assistance
# Email: bbbullock@mac.com
# GitHub: https://github.com/bbbullock/TouchPoint

"""Nightly Background Check Evaluator for TouchPoint."""

import cgi
import datetime
import json

try:
    from System import DateTime as DotNetDateTime
except ImportError:
    DotNetDateTime = None


SETTING_PREFIX = "BCE."
APP_VERSION = "3.1.3"
STATE_CONTENT_NAME = "BackgroundCheckEvaluatorState"
EVALUATE_THROUGH_DATE_EV_FIELD = "EvaluateBackgroundCheckThroughDate"


def setting(name, default):
    return str(model.Setting(SETTING_PREFIX + name, str(default)) or default)


def int_setting(name, default):
    try:
        return int(setting(name, default))
    except Exception:
        return int(default)


def bool_setting(name, default):
    value = setting(name, "true" if default else "false").strip().lower()
    return value in ("true", "1", "yes", "y", "on")


EMAIL_ENABLED = bool_setting("EmailEnabled", False)
SHOW_PROCESS_REMINDER_STEPS = bool_setting(
    "ShowProcessReminderSteps", False
)
QUEUED_BY_PEOPLE_ID = int_setting("QueuedByPeopleId", 0)
REPORT_RECIPIENT_PEOPLE_IDS = setting(
    "ReportRecipientPeopleIds", ""
)
FAILURE_RECIPIENT_PEOPLE_IDS = setting(
    "FailureRecipientPeopleIds", REPORT_RECIPIENT_PEOPLE_IDS
)
FROM_ADDRESS = setting("FromAddress", "")
FROM_NAME = setting("FromName", "")

PROGRAM_ID = int_setting("ProgramId", 0)
DIVISION_ID = int_setting("DivisionId", 0)
APPLICATION_APPROVED_EV_FIELD = "AppStatus:Application Approved"
APPLICATION_ON_FILE_EV_FIELD = "AppStatus:Application on File"
COLLEGE_NO_BACKGROUND_CHECK_EV_FIELD = (
    "College Student (no background check)"
)
REFUSES_BACKGROUND_CHECK_EV_FIELD = "Individual Refuses Background Check"
VOLUNTEER_APP_PROCESS_NAME = "Evaluate for Volunteer App"
BACKGROUND_CHECK_PROCESS_NAME = "Evaluate for Background Check status"

LOOKAHEAD_DAYS = int_setting("LookaheadDays", 30)
BACKGROUND_CHECK_VALID_MONTHS = int_setting(
    "BackgroundCheckValidMonths", 33
)
MINIMUM_BACKGROUND_CHECK_AGE = int_setting("MinimumBackgroundCheckAge", 18)
TRAINING_REPORT_TYPE_ID = int_setting("TrainingReportTypeId", 0)

REPORT_SUBJECT = "Nightly Volunteer Background Check Evaluation"
FAILURE_SUBJECT = "TouchPoint Background Check Evaluator - Action Required"

model.Header = "Volunteer Background Check Evaluation"
model.Transactional = True


def html_escape(value):
    if value is None:
        return ""
    return cgi.escape(str(value), True)


def format_date(value):
    if not value:
        return ""
    try:
        return value.ToString("MM/dd/yyyy")
    except AttributeError:
        try:
            return value.strftime("%m/%d/%Y")
        except Exception:
            return str(value)[:10]


def iso_date(value):
    if not value:
        return ""
    try:
        return value.ToString("yyyy-MM-dd")
    except AttributeError:
        try:
            return value.strftime("%Y-%m-%d")
        except Exception:
            return str(value)[:10]


def parse_iso_date(value):
    parts = str(value or "").split("-")
    if len(parts) != 3:
        raise ValueError("Date must use YYYY-MM-DD format.")
    year, month, day = [int(part) for part in parts]
    if DotNetDateTime is not None:
        return DotNetDateTime(year, month, day)
    return datetime.datetime(year, month, day)


def today_midnight():
    try:
        now = model.DateTime
        year = int(now.Year)
        month = int(now.Month)
        day = int(now.Day)
    except Exception:
        now = datetime.datetime.now()
        year = now.year
        month = now.month
        day = now.day
    if DotNetDateTime is not None:
        return DotNetDateTime(year, month, day)
    return datetime.datetime(year, month, day)


def current_timestamp():
    try:
        return model.DateTime.ToString("yyyy-MM-dd HH:mm:ss")
    except Exception:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def people_query(people_ids):
    return "peopleids='{0}'".format(people_ids)


def send_email(recipient_ids, subject, body):
    model.Email(
        people_query(recipient_ids),
        QUEUED_BY_PEOPLE_ID,
        FROM_ADDRESS,
        FROM_NAME,
        subject,
        body,
    )


def requested_action():
    try:
        return str(getattr(Data, "BCEAction") or "").strip().lower()
    except Exception:
        return ""


def empty_state():
    return {
        "version": 3,
        "updated": "",
        "incomplete": False,
        "failed_involvement_ids": [],
        "involvements": {},
        "legacy_people_ids": [],
    }


def normalize_ids(values):
    results = []
    for value in values or []:
        try:
            item_id = int(value)
            if item_id > 0 and item_id not in results:
                results.append(item_id)
        except Exception:
            pass
    return sorted(results)


def load_comparison_state():
    raw = str(model.TextContent(STATE_CONTENT_NAME) or "").strip()
    if not raw:
        return False, empty_state()

    state = empty_state()
    if raw.startswith("{"):
        try:
            document = json.loads(raw)
            if bool(document.get("reset", False)):
                return False, empty_state()
            version = int(document.get("version", 0) or 0)
            state["updated"] = str(document.get("updated", "") or "")
            if version >= 3:
                state["incomplete"] = bool(document.get("incomplete", False))
                state["failed_involvement_ids"] = normalize_ids(
                    document.get("failed_involvement_ids", [])
                )
                for organization_id, item in document.get(
                    "involvements", {}
                ).items():
                    state["involvements"][str(organization_id)] = {
                        "required_through": str(
                            item.get("required_through", "") or ""
                        ),
                        "evaluation_basis": str(
                            item.get("evaluation_basis", "") or ""
                        ),
                        "exception_people_ids": normalize_ids(
                            item.get("exception_people_ids", [])
                        ),
                    }
                state["legacy_people_ids"] = normalize_ids(
                    document.get("legacy_people_ids", [])
                )
                return True, state
            state["legacy_people_ids"] = normalize_ids(
                document.get("people_ids", [])
            )
            return True, state
        except Exception:
            return False, empty_state()

    values = {}
    for line in raw.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip().lower()] = value.strip()
    state["updated"] = values.get("updated", "")
    state["legacy_people_ids"] = normalize_ids(
        values.get("people", "").split(",")
    )
    return True, state


def state_people_ids(state):
    people_ids = set(state.get("legacy_people_ids", []))
    for item in state.get("involvements", {}).values():
        people_ids.update(item.get("exception_people_ids", []))
    return people_ids


def build_updated_state(previous_state, coverage, rows, errors):
    by_organization = {}
    for row in rows:
        key = str(int(row.OrganizationId))
        by_organization.setdefault(key, set()).add(int(row.PeopleId))

    next_state = empty_state()
    next_state["updated"] = current_timestamp()
    next_state["incomplete"] = bool(errors)
    next_state["failed_involvement_ids"] = sorted(
        int(error["OrganizationId"]) for error in errors
    )
    for item in coverage:
        key = str(item["OrganizationId"])
        if item["Status"] == "Completed":
            next_state["involvements"][key] = {
                "required_through": item["RequiredThroughIso"],
                "evaluation_basis": item["EvaluationBasis"],
                "exception_people_ids": sorted(by_organization.get(key, set())),
            }
        elif key in previous_state.get("involvements", {}):
            next_state["involvements"][key] = previous_state[
                "involvements"
            ][key]
    if errors:
        next_state["legacy_people_ids"] = previous_state.get(
            "legacy_people_ids", []
        )
    return next_state


def save_comparison_state(state):
    model.WriteContentText(
        STATE_CONTENT_NAME,
        json.dumps(state, sort_keys=True),
        "",
    )


INVOLVEMENT_SCOPE_SQL = """
DECLARE @Today date = CAST(@EvaluationDate AS date);

SELECT
    o.OrganizationId,
    o.OrganizationName AS Involvement,
    CASE WHEN date_ev.EvaluateThroughDate >= @Today
         THEN 1 ELSE 0 END AS HasThroughDateEV,
    date_ev.EvaluateThroughDate,
    meetings.LatestMeetingDate,
    ISNULL(meetings.UpcomingMeetingCount, 0) AS UpcomingMeetingCount,
    ISNULL(members.CurrentMemberCount, 0) AS CurrentMemberCount
FROM dbo.Organizations o WITH (NOLOCK)
JOIN dbo.Division d WITH (NOLOCK)
  ON d.Id = o.DivisionId
OUTER APPLY (
    SELECT
        MAX(CAST(m.MeetingDate AS date)) AS LatestMeetingDate,
        COUNT(*) AS UpcomingMeetingCount
    FROM dbo.Meetings m WITH (NOLOCK)
    WHERE m.OrganizationId = o.OrganizationId
      AND ISNULL(m.DidNotMeet, 0) = 0
      AND m.MeetingDate >= @Today
      AND m.MeetingDate < DATEADD(day, @LookaheadDays + 1, @Today)
) meetings
OUTER APPLY (
    SELECT
        MAX(oe.DateValue) AS EvaluateThroughDate
    FROM dbo.OrganizationExtra oe WITH (NOLOCK)
    WHERE oe.OrganizationId = o.OrganizationId
      AND oe.Field = @EvaluateThroughDateEVField
) date_ev
OUTER APPLY (
    SELECT COUNT(*) AS CurrentMemberCount
    FROM dbo.OrganizationMembers om WITH (NOLOCK)
    WHERE om.OrganizationId = o.OrganizationId
      AND om.InactiveDate IS NULL
      AND ISNULL(om.Pending, 0) = 0
) members
WHERE d.ProgId = @ProgramId
  AND d.Id = @DivisionId
  AND o.OrganizationStatusId = 30
  AND (
      meetings.UpcomingMeetingCount > 0
      OR date_ev.EvaluateThroughDate >= @Today
  )
ORDER BY o.OrganizationName, o.OrganizationId;
"""


INVOLVEMENT_EVALUATION_SQL = """
DECLARE @Today date = CAST(@EvaluationDate AS date);
DECLARE @TargetDate date = CAST(@RequiredThroughDate AS date);

;WITH Evaluation AS (
    SELECT
        o.OrganizationId,
        o.OrganizationName,
        om.PeopleId,
        p.Name2,
        CASE
            WHEN p.BDate IS NULL
                THEN 1
            WHEN DATEADD(year, @MinimumBackgroundCheckAge, p.BDate) <= @Today
                THEN 1
            ELSE 0
        END AS BackgroundCheckRequired,
        bg.LatestApprovedCheck,
        ISNULL(background_process.ProcessStatus, 'Not in process')
            AS BackgroundCheckProcessStatus,
        ISNULL(application_process.ProcessStatus, 'Not in process')
            AS VolunteerAppProcessStatus,
        CASE WHEN EXISTS (
            SELECT 1 FROM dbo.PeopleExtra pe WITH (NOLOCK)
            WHERE pe.PeopleId = om.PeopleId
              AND LTRIM(RTRIM(pe.Field)) = @ApplicationApprovedEV
              AND pe.BitValue = 1
        ) THEN 1 ELSE 0 END AS HasApplicationApprovedEV,
        CASE WHEN EXISTS (
            SELECT 1 FROM dbo.PeopleExtra pe WITH (NOLOCK)
            WHERE pe.PeopleId = om.PeopleId
              AND LTRIM(RTRIM(pe.Field)) = @ApplicationOnFileEV
              AND pe.BitValue = 1
        ) THEN 1 ELSE 0 END AS HasApplicationOnFileEV,
        CASE WHEN EXISTS (
            SELECT 1 FROM dbo.PeopleExtra pe WITH (NOLOCK)
            WHERE pe.PeopleId = om.PeopleId
              AND pe.Field = @RefusesEV AND pe.BitValue = 1
        ) THEN 1 ELSE 0 END AS HasRefusesFlag,
        CASE WHEN EXISTS (
            SELECT 1 FROM dbo.PeopleExtra pe WITH (NOLOCK)
            WHERE pe.PeopleId = om.PeopleId
              AND pe.Field = @CollegeEV AND pe.BitValue = 1
        ) THEN 1 ELSE 0 END AS HasCollegeFlag
    FROM dbo.Organizations o WITH (NOLOCK)
    JOIN dbo.OrganizationMembers om WITH (NOLOCK)
      ON om.OrganizationId = o.OrganizationId
     AND om.InactiveDate IS NULL
     AND ISNULL(om.Pending, 0) = 0
    JOIN dbo.People p WITH (NOLOCK) ON p.PeopleId = om.PeopleId
    OUTER APPLY (
        SELECT MAX(bc.Updated) AS LatestApprovedCheck
        FROM dbo.BackgroundChecks bc WITH (NOLOCK)
        WHERE bc.PeopleId = om.PeopleId
          AND bc.ApprovalStatus = 'Approved'
          AND ISNULL(bc.ReportTypeId, 0) <> @TrainingReportTypeId
          AND bc.Updated < DATEADD(day, 1, @TargetDate)
    ) bg
    OUTER APPLY (
        SELECT TOP 1
            CASE
                WHEN pp.IsAbandoned = 1 THEN 'Abandoned'
                WHEN pp.IsComplete = 1 THEN 'Completed'
                WHEN pp.IsActive = 1 AND current_step.StepName IS NOT NULL
                    THEN current_step.StepName
                WHEN pp.IsActive = 1 THEN 'Added to Process'
                ELSE 'Inactive'
            END AS ProcessStatus
        FROM dbo.ProcessBuilder pb WITH (NOLOCK)
        JOIN dbo.ProcessPeople pp WITH (NOLOCK)
          ON pp.ProcessId = pb.ProcessId
         AND pp.PeopleId = om.PeopleId
        OUTER APPLY (
            SELECT TOP 1 ps.StepName
            FROM dbo.ProcessProgression progression WITH (NOLOCK)
            JOIN dbo.ProcessStep ps WITH (NOLOCK)
              ON ps.ProcessStepId = progression.ProcessStepId
            WHERE progression.ProcessPeopleId = pp.ProcessPeopleId
              AND progression.IsCurrent = 1
            ORDER BY
                ISNULL(progression.ModifiedDate, progression.StartDate) DESC,
                progression.ProcessProgressionId DESC
        ) current_step
        WHERE @ShowProcessReminderSteps = 1
          AND pb.ProcessName = @BackgroundCheckProcessName
          AND pb.IsArchived = 0
        ORDER BY
            CASE WHEN pp.IsActive = 1 THEN 0 ELSE 1 END,
            ISNULL(pp.ModifiedDate, pp.CreatedDate) DESC,
            pp.ProcessPeopleId DESC
    ) background_process
    OUTER APPLY (
        SELECT TOP 1
            CASE
                WHEN pp.IsAbandoned = 1 THEN 'Abandoned'
                WHEN pp.IsComplete = 1 THEN 'Completed'
                WHEN pp.IsActive = 1 AND current_step.StepName IS NOT NULL
                    THEN current_step.StepName
                WHEN pp.IsActive = 1 THEN 'Added to Process'
                ELSE 'Inactive'
            END AS ProcessStatus
        FROM dbo.ProcessBuilder pb WITH (NOLOCK)
        JOIN dbo.ProcessPeople pp WITH (NOLOCK)
          ON pp.ProcessId = pb.ProcessId
         AND pp.PeopleId = om.PeopleId
        OUTER APPLY (
            SELECT TOP 1 ps.StepName
            FROM dbo.ProcessProgression progression WITH (NOLOCK)
            JOIN dbo.ProcessStep ps WITH (NOLOCK)
              ON ps.ProcessStepId = progression.ProcessStepId
            WHERE progression.ProcessPeopleId = pp.ProcessPeopleId
              AND progression.IsCurrent = 1
            ORDER BY
                ISNULL(progression.ModifiedDate, progression.StartDate) DESC,
                progression.ProcessProgressionId DESC
        ) current_step
        WHERE @ShowProcessReminderSteps = 1
          AND pb.ProcessName = @VolunteerAppProcessName
          AND pb.IsArchived = 0
        ORDER BY
            CASE WHEN pp.IsActive = 1 THEN 0 ELSE 1 END,
            ISNULL(pp.ModifiedDate, pp.CreatedDate) DESC,
            pp.ProcessPeopleId DESC
    ) application_process
    WHERE o.OrganizationId = @OrganizationId
      AND ISNULL(p.IsDeceased, 0) = 0
      AND ISNULL(p.ArchivedFlag, 0) = 0
), FinalEvaluation AS (
    SELECT *,
        CASE WHEN (HasApplicationApprovedEV = 1
                   AND HasApplicationOnFileEV = 1)
        THEN 1 ELSE 0 END AS HasApplicationRequirements
    FROM Evaluation
)
SELECT
    OrganizationId,
    OrganizationName AS Involvement,
    @TargetDate AS RequiredThroughDate,
    @EvaluationBasis AS EvaluationBasis,
    PeopleId,
    Name2 AS VolunteerName,
    BackgroundCheckRequired,
    LatestApprovedCheck,
    BackgroundCheckProcessStatus,
    VolunteerAppProcessStatus,
    HasApplicationRequirements,
    STUFF(
        CASE
            WHEN BackgroundCheckRequired = 1 AND LatestApprovedCheck IS NULL
                THEN '; No approved background check on file'
            WHEN BackgroundCheckRequired = 1
             AND LatestApprovedCheck < DATEADD(month, -@ValidMonths, @TargetDate)
                THEN '; Approved background check expires before required-through date'
            ELSE ''
        END
        + CASE WHEN HasApplicationRequirements = 0
            THEN '; Volunteer application requirements are incomplete'
            ELSE '' END
        + CASE WHEN HasRefusesFlag = 1
            THEN '; Individual refuses background check'
            ELSE '' END
        + CASE WHEN HasCollegeFlag = 1
            THEN '; College Student (no background check) is selected'
            ELSE '' END,
        1, 2, ''
    ) AS ExceptionReason
FROM FinalEvaluation
WHERE (BackgroundCheckRequired = 1 AND LatestApprovedCheck IS NULL)
   OR (BackgroundCheckRequired = 1
       AND LatestApprovedCheck < DATEADD(month, -@ValidMonths, @TargetDate))
   OR HasApplicationRequirements = 0
   OR HasRefusesFlag = 1
   OR HasCollegeFlag = 1
ORDER BY Name2, PeopleId;
"""


def scope_parameters():
    return {
        "EvaluationDate": today_midnight(),
        "ProgramId": PROGRAM_ID,
        "DivisionId": DIVISION_ID,
        "LookaheadDays": LOOKAHEAD_DAYS,
        "EvaluateThroughDateEVField": EVALUATE_THROUGH_DATE_EV_FIELD,
    }


def evaluation_parameters(organization_id, target_date, basis):
    return {
        "EvaluationDate": today_midnight(),
        "RequiredThroughDate": target_date,
        "EvaluationBasis": basis,
        "OrganizationId": int(organization_id),
        "ValidMonths": BACKGROUND_CHECK_VALID_MONTHS,
        "MinimumBackgroundCheckAge": MINIMUM_BACKGROUND_CHECK_AGE,
        "ApplicationApprovedEV": APPLICATION_APPROVED_EV_FIELD,
        "ApplicationOnFileEV": APPLICATION_ON_FILE_EV_FIELD,
        "CollegeEV": COLLEGE_NO_BACKGROUND_CHECK_EV_FIELD,
        "RefusesEV": REFUSES_BACKGROUND_CHECK_EV_FIELD,
        "TrainingReportTypeId": TRAINING_REPORT_TYPE_ID,
        "VolunteerAppProcessName": VOLUNTEER_APP_PROCESS_NAME,
        "BackgroundCheckProcessName": BACKGROUND_CHECK_PROCESS_NAME,
        "ShowProcessReminderSteps": SHOW_PROCESS_REMINDER_STEPS,
    }


def evaluate_involvements():
    scope_rows = list(q.QuerySql(INVOLVEMENT_SCOPE_SQL, scope_parameters()))
    coverage = []
    exception_rows = []
    errors = []
    for involvement in scope_rows:
        organization_id = int(involvement.OrganizationId)
        has_through_date_ev = bool(involvement.HasThroughDateEV)
        basis = (
            "Configured through date"
            if has_through_date_ev
            else "Latest upcoming meeting"
        )
        target_date = involvement.EvaluateThroughDate
        if not has_through_date_ev:
            target_date = involvement.LatestMeetingDate

        try:
            rows = list(
                q.QuerySql(
                    INVOLVEMENT_EVALUATION_SQL,
                    evaluation_parameters(organization_id, target_date, basis),
                )
            )
            exception_rows.extend(rows)
            coverage.append(
                coverage_item(involvement, basis, target_date, "Completed", "")
            )
        except Exception as exc:
            message = "Evaluation query failed: {0}".format(exc)
            errors.append(
                {
                    "OrganizationId": organization_id,
                    "Involvement": str(involvement.Involvement),
                    "Message": message,
                }
            )
            coverage.append(
                coverage_item(involvement, basis, target_date, "Failed", message)
            )
    return coverage, exception_rows, errors


def coverage_item(involvement, basis, target_date, status, message):
    return {
        "OrganizationId": int(involvement.OrganizationId),
        "Involvement": str(involvement.Involvement),
        "EvaluationBasis": basis,
        "RequiredThrough": (
            format_date(target_date) if target_date else "Not configured"
        ),
        "RequiredThroughIso": iso_date(target_date),
        "UpcomingMeetingCount": int(involvement.UpcomingMeetingCount),
        "CurrentMemberCount": int(involvement.CurrentMemberCount),
        "Status": status,
        "Message": message,
    }


def group_rows_by_person(rows):
    groups = []
    by_people_id = {}
    for row in rows:
        people_id = int(row.PeopleId)
        if people_id not in by_people_id:
            group = {
                "PeopleId": people_id,
                "VolunteerName": row.VolunteerName,
                "LatestApprovedCheck": row.LatestApprovedCheck,
                "HasApplicationRequirements": bool(
                    row.HasApplicationRequirements
                ),
                "BackgroundCheckProcessStatus": str(
                    row.BackgroundCheckProcessStatus or "Not in process"
                ),
                "VolunteerAppProcessStatus": str(
                    row.VolunteerAppProcessStatus or "Not in process"
                ),
                "Involvements": [],
                "BackgroundRequiredValues": [],
                "Reasons": [],
            }
            by_people_id[people_id] = group
            groups.append(group)
        group = by_people_id[people_id]
        involvement_key = (
            int(row.OrganizationId),
            str(row.Involvement),
            format_date(row.RequiredThroughDate),
            str(row.EvaluationBasis),
        )
        if involvement_key not in group["Involvements"]:
            group["Involvements"].append(involvement_key)
        required = bool(row.BackgroundCheckRequired)
        if required not in group["BackgroundRequiredValues"]:
            group["BackgroundRequiredValues"].append(required)
        for reason in str(row.ExceptionReason or "").split("; "):
            reason = reason.strip()
            if reason and reason not in group["Reasons"]:
                group["Reasons"].append(reason)
    return groups


def render_coverage_table(coverage):
    parts = [
        "<h2>Involvements included in this evaluation</h2>",
        '<table class="table table-striped table-bordered" '
        'style="border-collapse:collapse;width:100%;">',
        "<thead><tr><th>Involvement</th><th>Evaluation method</th>",
        "<th>Required through</th><th>Upcoming meetings</th>",
        "<th>Current members</th><th>Processing result</th></tr></thead><tbody>",
    ]
    if not coverage:
        parts.append(
            '<tr><td colspan="6"><em>No qualifying Involvements were found.'
            "</em></td></tr>"
        )
    for item in coverage:
        organization_url = "{0}/Org/{1}".format(
            model.CmsHost, item["OrganizationId"]
        )
        status_text = (
            '<span style="color:#3c763d;"><strong>Evaluated successfully</strong></span>'
            if item["Status"] == "Completed"
            else '<span style="color:#a94442;"><strong>Evaluation failed</strong></span>'
        )
        parts.extend(
            [
                "<tr>",
                '<td><a href="{0}">{1}</a></td>'.format(
                    html_escape(organization_url),
                    html_escape(item["Involvement"]),
                ),
                "<td>{0}</td>".format(
                    html_escape(item["EvaluationBasis"])
                ),
                "<td>{0}</td>".format(
                    html_escape(item["RequiredThrough"])
                ),
                "<td>{0}</td>".format(item["UpcomingMeetingCount"]),
                "<td>{0}</td>".format(item["CurrentMemberCount"]),
                "<td>{0}</td>".format(status_text),
                "</tr>",
            ]
        )
    parts.append("</tbody></table>")
    return "".join(parts)


def render_errors(errors):
    if not errors:
        return ""
    parts = [
        '<div class="alert alert-danger">',
        "<h2>Evaluation errors requiring corrective action</h2><ul>",
    ]
    for error in errors:
        parts.append(
            "<li><strong>{0}:</strong> {1}</li>".format(
                html_escape(error["Involvement"]),
                html_escape(error["Message"]),
            )
        )
    parts.append("</ul></div>")
    return "".join(parts)


def render_people_table(people, show_new_badge):
    parts = [
        '<table class="table table-striped table-bordered" '
        'style="border-collapse:collapse;width:100%;">',
        "<thead><tr><th>Volunteer</th><th>Affected Involvements</th>",
        "<th>Background Check Required</th><th>Latest Approved Check</th>",
        "<th>Meets Application Requirements</th>",
        "</tr></thead><tbody>",
    ]
    for person in people:
        person_url = "{0}/Person2/{1}#tab-volunteer".format(
            model.CmsHost, person["PeopleId"]
        )
        involvement_items = []
        for organization_id, name, required_through, basis in person[
            "Involvements"
        ]:
            organization_url = "{0}/Org/{1}".format(
                model.CmsHost, organization_id
            )
            involvement_items.append(
                '<li><a href="{0}">{1}</a> &mdash; required through {2} '
                "({3})</li>".format(
                    html_escape(organization_url),
                    html_escape(name),
                    html_escape(required_through),
                    html_escape(basis),
                )
            )
        required_values = person["BackgroundRequiredValues"]
        if required_values == [True]:
            required_text = "Yes"
        elif required_values == [False]:
            required_text = "No - currently under {0}".format(
                MINIMUM_BACKGROUND_CHECK_AGE
            )
        else:
            required_text = "Varies"
        background_check_problem = any(
            reason in (
                "No approved background check on file",
                "Approved background check expires before required-through date",
            )
            for reason in person["Reasons"]
        )
        if required_values == [False]:
            latest_check_text = "N/A"
            latest_check_style = ""
        else:
            latest_check_text = (
                format_date(person["LatestApprovedCheck"])
                if person["LatestApprovedCheck"]
                else "None"
            )
            latest_check_style = (
                ' style="background:#f2dede;color:#a94442;font-weight:bold;"'
                if background_check_problem
                else ""
            )
        application_met = bool(person["HasApplicationRequirements"])
        application_style = (
            ""
            if application_met
            else ' style="background:#f2dede;color:#a94442;font-weight:bold;"'
        )
        background_process_html = ""
        application_process_html = ""
        if SHOW_PROCESS_REMINDER_STEPS:
            background_process_html = (
                '<div style="font-size:85%;color:#667;margin-top:4px;">'
                "Reminder step: {0}</div>"
            ).format(html_escape(person["BackgroundCheckProcessStatus"]))
            application_process_html = (
                '<div style="font-size:85%;color:#667;margin-top:4px;">'
                "Reminder step: {0}</div>"
            ).format(html_escape(person["VolunteerAppProcessStatus"]))
        parts.extend(
            [
                "<tr>",
                '<td>{0}<a href="{1}">{2}</a></td>'.format(
                    (
                        '<span class="label label-danger" '
                        'style="margin-right:6px;">NEW</span>'
                        if show_new_badge
                        else ""
                    ),
                    html_escape(person_url),
                    html_escape(person["VolunteerName"]),
                ),
                "<td><ul>{0}</ul></td>".format("".join(involvement_items)),
                "<td>{0}{1}</td>".format(
                    html_escape(required_text), background_process_html
                ),
                "<td{0}>{1}</td>".format(
                    latest_check_style,
                    html_escape(latest_check_text),
                ),
                "<td{0}>{1}{2}</td>".format(
                    application_style,
                    "Yes" if application_met else "No",
                    application_process_html,
                ),
                "</tr>",
            ]
        )
    parts.append("</tbody></table>")
    return "".join(parts)


def build_report(
    coverage,
    rows,
    errors,
    previous_state_exists,
    previous_state,
    next_state,
):
    people = group_rows_by_person(rows)
    previous_ids = state_people_ids(previous_state)
    merged_ids = state_people_ids(next_state)
    new_people = [
        person
        for person in people
        if not previous_state_exists or person["PeopleId"] not in previous_ids
    ]
    ongoing_people = [
        person
        for person in people
        if previous_state_exists and person["PeopleId"] in previous_ids
    ]
    resolved_count = len(previous_ids.difference(merged_ids))
    completed_count = len(
        [item for item in coverage if item["Status"] == "Completed"]
    )

    parts = [
        '<div style="font-family:\'Helvetica Neue\',Helvetica,Arial,sans-serif;">',
        "<h1>Nightly Volunteer Background Check Evaluation</h1>",
        "<p>Evaluation date: <strong>{0}</strong></p>".format(
            format_date(today_midnight())
        ),
        (
            "<p><strong>{0}</strong> Involvement(s) completed; "
            "<strong>{1}</strong> failed. <strong>{2}</strong> volunteer(s) "
            "have exceptions: <strong>{3}</strong> new and "
            "<strong>{4}</strong> ongoing. <strong>{5}</strong> are no "
            "longer listed after successfully evaluated work.</p>"
        ).format(
            completed_count,
            len(errors),
            len(people),
            len(new_people),
            len(ongoing_people),
            resolved_count,
        ),
        render_coverage_table(coverage),
        render_errors(errors),
        "<h2>Volunteer exceptions</h2>",
    ]
    if new_people:
        parts.extend(
            [
                '<h3 style="color:#a94442;">New exceptions ({0})</h3>'.format(
                    len(new_people)
                ),
                render_people_table(new_people, True),
            ]
        )
    else:
        parts.append(
            '<div class="alert alert-success"><strong>No new volunteer '
            "exceptions.</strong></div>"
        )
    if ongoing_people:
        parts.extend(
            [
                "<h3>Ongoing exceptions ({0})</h3>".format(
                    len(ongoing_people)
                ),
                render_people_table(ongoing_people, False),
            ]
        )
    if not people:
        parts.append(
            '<div class="alert alert-success">No volunteer eligibility '
            "exceptions were found in the successfully evaluated "
            "Involvements.</div>"
        )
    if errors:
        parts.append(
            '<p><small>This was a partial run. Comparison history was updated '
            "for completed Involvements; prior history was retained for "
            "failed Involvements.</small></p>"
        )
    elif previous_state_exists:
        parts.append(
            "<p><small>Compared with state saved {0}.</small></p>".format(
                html_escape(previous_state.get("updated", "") or "previously")
            )
        )
    else:
        parts.append(
            '<p><small>No prior comparison baseline existed. Current '
            "exceptions are shown as new.</small></p>"
        )
    parts.append("</div>")
    return "".join(parts)


def involvement_failure_body(errors):
    return "".join(
        [
            "<h1>Background Check Evaluation Requires Action</h1>",
            "<p>The nightly run completed only partially. The regular nightly "
            "report was also queued with successful results and these errors."
            "</p>",
            render_errors(errors),
        ]
    )


def fatal_failure_body(exc):
    return (
        "<h1>TouchPoint Background Check Evaluator Failed</h1>"
        "<p>The evaluator could not build a reliable nightly report. "
        "Comparison history was not changed.</p>"
        "<p><strong>Error:</strong> {0}</p>"
    ).format(html_escape(exc))


def main():
    try:
        previous_exists, previous_state = load_comparison_state()
        coverage, rows, errors = evaluate_involvements()
        next_state = build_updated_state(
            previous_state, coverage, rows, errors
        )
        report = build_report(
            coverage,
            rows,
            errors,
            previous_exists,
            previous_state,
            next_state,
        )

        if requested_action() == "initialize_baseline":
            save_comparison_state(next_state)
            print(
                '<div class="alert alert-success">Initialized comparison '
                "history for completed Involvements. No email was queued."
                "</div>"
            )
            print(report)
            return

        if EMAIL_ENABLED:
            send_email(REPORT_RECIPIENT_PEOPLE_IDS, REPORT_SUBJECT, report)
            failure_email_error = None
            if errors:
                try:
                    send_email(
                        FAILURE_RECIPIENT_PEOPLE_IDS,
                        FAILURE_SUBJECT,
                        involvement_failure_body(errors),
                    )
                except Exception as exc:
                    failure_email_error = exc
            save_comparison_state(next_state)
            print(
                '<div class="alert alert-success">Queued the nightly report '
                "and updated comparison history for completed "
                "Involvements.</div>"
            )
            if failure_email_error is not None:
                print(
                    '<div class="alert alert-danger">The nightly report was '
                    "queued, but the failure notification could not be "
                    "queued: {0}</div>".format(
                        html_escape(failure_email_error)
                    )
                )
        else:
            print(
                '<div class="alert alert-warning"><strong>Preview mode:'
                "</strong> No email was queued and comparison history was "
                "not changed.</div>"
            )
        print(report)
    except Exception as exc:
        body = fatal_failure_body(exc)
        if EMAIL_ENABLED:
            try:
                send_email(
                    FAILURE_RECIPIENT_PEOPLE_IDS,
                    FAILURE_SUBJECT,
                    body,
                )
            except Exception as email_exc:
                body += (
                    "<p><strong>Failure notification could not be queued:"
                    "</strong> {0}</p>"
                ).format(html_escape(email_exc))
        print('<div class="alert alert-danger">{0}</div>'.format(body))
        raise


main()
