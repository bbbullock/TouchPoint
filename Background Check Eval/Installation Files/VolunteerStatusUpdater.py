#Roles=Admin

# Volunteer Status Updater
# Version: 1.9.0
# 2026-08-20 1.9.0 - Added 12-month, latest-result MVR qualification and the
# PrimaryVolunteerMVR status; standardized background-check/MVR wording.
# 2026-08-20 1.8.0 - Restricted background-check qualification and denial
# results to configured ServiceCode values; current approved MVR-only checks
# produce MissingInfo.
# 2026-08-19 1.7.0 - Removed NotApproved as an output option and excluded
# deceased and archived people from evaluation.
# 2026-08-19 1.6.0 - Changed incomplete applications to MissingInfo and
# removed the obsolete newer denied/adverse override.
# 2026-08-19 1.5.0 - Added Denied when the latest qualifying background
# check is Not Approved or Ineligible Volunteer is checked.
# 2026-08-18 1.4.0 - Made Volunteer Application Involvement membership the
# sole authority for both setting and clearing Application on File.
# 2026-08-18 1.3.0 - Added configured Volunteer Application Involvement
# membership as a candidate source and authoritative Application on File input.
# 2026-08-18 1.2.0 - Replaced Involvement Program/Division scope with the
# person-level union of Approved for Role, checked application EVs, and a
# current approved background check.
# 2026-08-18 1.1.0 - Made runtime configuration fully independent under the
# VSU namespace for management by VolunteerStatusUpdaterAdmin.
# 2026-08-18 1.0.0 - Added preview-first person Extra Value evaluation,
# default-off Morning Batch writes, changed-only updates, minimal run state,
# and optional change/failure email with Admin-managed recipients.
# Written by: Brian Bullock with Codex assistance
# Email: bbbullock@mac.com
# GitHub: https://github.com/bbbullock/TouchPoint

"""Maintain the person-level Approved for Role Extra Value in TouchPoint."""

import cgi
import datetime
import json

try:
    from System import DateTime as DotNetDateTime
except ImportError:
    DotNetDateTime = None


APP_VERSION = "1.9.0"
SETTING_PREFIX = "VSU."
STATE_CONTENT_NAME = "VolunteerStatusUpdaterState"

APPROVED_ROLE_EV_FIELD = "Approved for Role"
APPLICATION_APPROVED_EV_FIELD = "AppStatus:Application Approved"
APPLICATION_ON_FILE_EV_FIELD = "AppStatus:Application on File"
INELIGIBLE_VOLUNTEER_EV_FIELD = "Ineligible Volunteer"

STATUS_PRIMARY = "PrimaryVolunteer"
STATUS_PRIMARY_MVR = "PrimaryVolunteerMVR"
STATUS_SECONDARY = "SecondaryVolunteer"
STATUS_SECONDARY_EXPIRED = "SecondaryVolunteerExpiredBackground"
STATUS_DENIED = "Denied"
STATUS_MISSING_INFO = "MissingInfo"
ALLOWED_STATUSES = (
    STATUS_PRIMARY,
    STATUS_PRIMARY_MVR,
    STATUS_SECONDARY,
    STATUS_SECONDARY_EXPIRED,
    STATUS_DENIED,
    STATUS_MISSING_INFO,
)
STANDARD_EV_CONTENT_NAME = "StandardExtraValues2"

REPORT_SUBJECT = "Volunteer Status Updater - Changes"

model.Header = "Volunteer Status Updater"
model.Transactional = True


def setting(prefix, name, default):
    return str(model.Setting(prefix + name, str(default)) or default)


def int_setting(prefix, name, default):
    try:
        return int(setting(prefix, name, default))
    except Exception:
        return int(default)


def bool_setting(prefix, name, default):
    value = setting(prefix, name, "true" if default else "false")
    return value.strip().lower() in ("true", "1", "yes", "y", "on")


def normalize_service_codes(raw):
    codes = []
    allowed = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
    for part in str(raw or "").split(","):
        code = part.strip().upper()
        if not code:
            continue
        if len(code) > 50 or any(char not in allowed for char in code):
            raise ValueError(
                "Background-check or MVR service codes contain an invalid "
                "value. Use comma-separated letters, numbers, periods, "
                "underscores, or hyphens."
            )
        if code not in codes:
            codes.append(code)
    return ",".join(codes)


UPDATES_ENABLED = bool_setting(SETTING_PREFIX, "UpdatesEnabled", False)
CONFIGURATION_SAVED = bool_setting(
    SETTING_PREFIX, "ConfigurationSaved", False
)
EMAIL_ENABLED = bool_setting(SETTING_PREFIX, "EmailEnabled", False)
RECIPIENT_PEOPLE_IDS = setting(
    SETTING_PREFIX, "RecipientPeopleIds", ""
)

QUEUED_BY_PEOPLE_ID = int_setting(SETTING_PREFIX, "QueuedByPeopleId", 0)
FROM_ADDRESS = setting(SETTING_PREFIX, "FromAddress", "")
FROM_NAME = setting(SETTING_PREFIX, "FromName", "")
BACKGROUND_CHECK_VALID_MONTHS = int_setting(
    SETTING_PREFIX, "BackgroundCheckValidMonths", 33
)
MINIMUM_BACKGROUND_CHECK_AGE = int_setting(
    SETTING_PREFIX, "MinimumBackgroundCheckAge", 18
)
TRAINING_REPORT_TYPE_ID = int_setting(
    SETTING_PREFIX, "TrainingReportTypeId", 0
)
BACKGROUND_CHECK_SERVICE_CODES = normalize_service_codes(
    setting(SETTING_PREFIX, "BackgroundCheckServiceCodes", "")
)
MVR_SERVICE_CODES = normalize_service_codes(
    setting(SETTING_PREFIX, "MVRServiceCodes", "")
)
MVR_CHECK_VALID_MONTHS = int_setting(
    SETTING_PREFIX, "MVRCheckValidMonths", 12
)
VOLUNTEER_APPLICATION_INVOLVEMENT_ID = int_setting(
    SETTING_PREFIX, "VolunteerApplicationInvolvementId", 0
)


def html_escape(value):
    if value is None:
        return ""
    return cgi.escape(str(value), True)


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


def requested_action():
    try:
        return str(getattr(Data, "VSUAction") or "").strip().lower()
    except Exception:
        return ""


def people_query(people_ids):
    return "peopleids='{0}'".format(people_ids)


def send_email(subject, body):
    model.Email(
        people_query(RECIPIENT_PEOPLE_IDS),
        QUEUED_BY_PEOPLE_ID,
        FROM_ADDRESS,
        FROM_NAME,
        subject,
        body,
    )


def validate_output_definition():
    content = str(model.TextContent(STANDARD_EV_CONTENT_NAME) or "")
    field_index = content.find(APPROVED_ROLE_EV_FIELD)
    if field_index < 0:
        raise ValueError(
            "Approved for Role is not defined in StandardExtraValues2."
        )
    window = content[max(0, field_index - 1000):field_index + 6000]
    if "Code" not in window:
        raise ValueError(
            "Approved for Role was found, but its Code type was not confirmed."
        )
    missing = [status for status in ALLOWED_STATUSES if status not in window]
    if missing:
        raise ValueError(
            "Approved for Role is missing configured option(s): {0}.".format(
                ", ".join(missing)
            )
        )


def validate_configuration(for_writes):
    errors = []
    try:
        validate_output_definition()
    except Exception as exc:
        errors.append(str(exc))
    if for_writes and not CONFIGURATION_SAVED:
        errors.append(
            "The independent updater configuration has not been reviewed "
            "and saved."
        )
    if BACKGROUND_CHECK_VALID_MONTHS <= 0:
        errors.append("Background-check valid months must be greater than zero.")
    if MINIMUM_BACKGROUND_CHECK_AGE < 0:
        errors.append("Minimum background-check age cannot be negative.")
    if not BACKGROUND_CHECK_SERVICE_CODES:
        errors.append(
            "Qualifying background-check service codes are not "
            "configured in the updater Admin app."
        )
    if not MVR_SERVICE_CODES:
        errors.append(
            "MVR service codes are not configured in the updater Admin app."
        )
    if MVR_CHECK_VALID_MONTHS <= 0:
        errors.append("MVR Check Valid Months must be greater than zero.")
    overlap = sorted(
        set(BACKGROUND_CHECK_SERVICE_CODES.split(","))
        & set(MVR_SERVICE_CODES.split(","))
    )
    if overlap:
        errors.append(
            "Background-check and MVR service codes cannot overlap: {0}."
            .format(", ".join(overlap))
        )
    if VOLUNTEER_APPLICATION_INVOLVEMENT_ID <= 0:
        errors.append(
            "Volunteer Application Involvement is not configured in the "
            "updater Admin app."
        )
    else:
        involvement_count = q.QuerySqlInt(
            """
            SELECT COUNT(*)
            FROM dbo.Organizations
            WHERE OrganizationId = {0}
              AND OrganizationStatusId = 30
            """.format(int(VOLUNTEER_APPLICATION_INVOLVEMENT_ID))
        )
        if involvement_count != 1:
            errors.append(
                "The configured Volunteer Application Involvement was not "
                "found or is not active."
            )
    if for_writes and EMAIL_ENABLED:
        if QUEUED_BY_PEOPLE_ID <= 0:
            errors.append("The updater queued-by person is not configured.")
        if not FROM_NAME:
            errors.append("The updater sender name is not configured.")
        if "@" not in FROM_ADDRESS:
            errors.append("The updater sender address is not configured.")
        if not RECIPIENT_PEOPLE_IDS:
            errors.append("Updater email recipients are not configured.")
    if errors:
        raise ValueError(" ".join(errors))


CANDIDATE_SQL = """
/* VOLUNTEER_STATUS_UPDATER_CANDIDATES */
DECLARE @Today date = CAST(@EvaluationDate AS date);

;WITH CandidatePeople AS (
    SELECT DISTINCT pe.PeopleId
    FROM dbo.PeopleExtra pe WITH (NOLOCK)
    WHERE LTRIM(RTRIM(pe.Field)) = @ApprovedRoleEV
      AND NULLIF(LTRIM(RTRIM(pe.StrValue)), '') IS NOT NULL

    UNION

    SELECT DISTINCT pe.PeopleId
    FROM dbo.PeopleExtra pe WITH (NOLOCK)
    WHERE pe.BitValue = 1
      AND LTRIM(RTRIM(pe.Field)) IN (
        @ApplicationApprovedEV,
        @ApplicationOnFileEV,
        @IneligibleVolunteerEV
    )

    UNION

    SELECT DISTINCT bc.PeopleId
    FROM dbo.BackgroundChecks bc WITH (NOLOCK)
    WHERE LOWER(LTRIM(RTRIM(bc.ApprovalStatus))) = 'approved'
      AND ISNULL(bc.ReportTypeId, 0) <> @TrainingReportTypeId
      AND CHARINDEX(
          ',' + UPPER(LTRIM(RTRIM(ISNULL(bc.ServiceCode, '')))) + ',',
          ',' + @BackgroundCheckServiceCodes + ','
      ) > 0
      AND bc.Updated >= DATEADD(month, -@ValidMonths, @Today)
      AND bc.Updated < DATEADD(day, 1, @Today)

    UNION

    SELECT DISTINCT bc.PeopleId
    FROM dbo.BackgroundChecks bc WITH (NOLOCK)
    WHERE LOWER(LTRIM(RTRIM(bc.ApprovalStatus))) = 'approved'
      AND ISNULL(bc.ReportTypeId, 0) <> @TrainingReportTypeId
      AND CHARINDEX(
          ',' + UPPER(LTRIM(RTRIM(ISNULL(bc.ServiceCode, '')))) + ',',
          ',' + @MVRServiceCodes + ','
      ) > 0
      AND CAST(bc.Updated AS date) >
          DATEADD(month, -@MVRValidMonths, @Today)
      AND bc.Updated < DATEADD(day, 1, @Today)

    UNION

    SELECT DISTINCT bc.PeopleId
    FROM dbo.BackgroundChecks bc WITH (NOLOCK)
    WHERE LOWER(LTRIM(RTRIM(bc.ApprovalStatus))) = 'not approved'
      AND ISNULL(bc.ReportTypeId, 0) <> @TrainingReportTypeId
      AND CHARINDEX(
          ',' + UPPER(LTRIM(RTRIM(ISNULL(bc.ServiceCode, '')))) + ',',
          ',' + @BackgroundCheckServiceCodes + ','
      ) > 0
      AND bc.Updated < DATEADD(day, 1, @Today)

    UNION

    SELECT DISTINCT om.PeopleId
    FROM dbo.OrganizationMembers om WITH (NOLOCK)
    WHERE om.OrganizationId = @VolunteerApplicationInvolvementId
      AND om.InactiveDate IS NULL
      AND ISNULL(om.Pending, 0) = 0
)
SELECT
    cp.PeopleId,
    p.Name2 AS VolunteerName,
    CASE
        WHEN p.BDate IS NOT NULL
         AND DATEADD(year, @MinimumBackgroundCheckAge, p.BDate) > @Today
            THEN 1 ELSE 0
    END AS IsUnderMinimumAge,
    ISNULL(application_flags.HasApplicationApproved, 0)
        AS HasApplicationApproved,
    ISNULL(application_flags.HasApplicationOnFile, 0)
        AS HasStoredApplicationOnFile,
    ISNULL(application_flags.HasIneligibleVolunteer, 0)
        AS HasIneligibleVolunteer,
    ISNULL(application_membership.HasMembership, 0)
        AS HasApplicationOnFile,
    ISNULL(application_membership.HasMembership, 0)
        AS HasVolunteerApplicationMembership,
    approved_role.ExistingApprovedRole,
    background.LatestApprovedCheck,
    latest_result.LatestBackgroundStatus,
    latest_result.LatestBackgroundDate,
    ISNULL(mvr.HasCurrentApprovedMVR, 0) AS HasCurrentApprovedMVR,
    ISNULL(unknown_check.HasCurrentApprovedUnknownCheck, 0)
        AS HasCurrentApprovedUnknownCheck,
    CASE
        WHEN background.LatestApprovedCheck IS NOT NULL
         AND background.LatestApprovedCheck >=
             DATEADD(month, -@ValidMonths, @Today)
            THEN 1 ELSE 0
    END AS HasCurrentApprovedCheck,
    CASE
        WHEN background.LatestApprovedCheck IS NOT NULL
         AND background.LatestApprovedCheck <
             DATEADD(month, -@ValidMonths, @Today)
            THEN 1 ELSE 0
    END AS HasExpiredApprovedCheck
FROM CandidatePeople cp
JOIN dbo.People p WITH (NOLOCK)
  ON p.PeopleId = cp.PeopleId
OUTER APPLY (
    SELECT
        MAX(CASE
            WHEN LTRIM(RTRIM(pe.Field)) = @ApplicationApprovedEV
             AND pe.BitValue = 1 THEN 1 ELSE 0 END)
            AS HasApplicationApproved,
        MAX(CASE
            WHEN LTRIM(RTRIM(pe.Field)) = @ApplicationOnFileEV
             AND pe.BitValue = 1 THEN 1 ELSE 0 END)
            AS HasApplicationOnFile,
        MAX(CASE
            WHEN LTRIM(RTRIM(pe.Field)) = @IneligibleVolunteerEV
             AND pe.BitValue = 1 THEN 1 ELSE 0 END)
            AS HasIneligibleVolunteer
    FROM dbo.PeopleExtra pe WITH (NOLOCK)
    WHERE pe.PeopleId = cp.PeopleId
      AND LTRIM(RTRIM(pe.Field)) IN (
          @ApplicationApprovedEV,
          @ApplicationOnFileEV,
          @IneligibleVolunteerEV
      )
) application_flags
OUTER APPLY (
    SELECT TOP 1 1 AS HasMembership
    FROM dbo.OrganizationMembers om WITH (NOLOCK)
    WHERE om.PeopleId = cp.PeopleId
      AND om.OrganizationId = @VolunteerApplicationInvolvementId
      AND om.InactiveDate IS NULL
      AND ISNULL(om.Pending, 0) = 0
) application_membership
OUTER APPLY (
    SELECT MAX(pe.StrValue) AS ExistingApprovedRole
    FROM dbo.PeopleExtra pe WITH (NOLOCK)
    WHERE pe.PeopleId = cp.PeopleId
      AND LTRIM(RTRIM(pe.Field)) = @ApprovedRoleEV
) approved_role
OUTER APPLY (
    SELECT
        MAX(CASE WHEN LOWER(LTRIM(RTRIM(bc.ApprovalStatus))) = 'approved'
                 THEN bc.Updated END) AS LatestApprovedCheck
    FROM dbo.BackgroundChecks bc WITH (NOLOCK)
    WHERE bc.PeopleId = cp.PeopleId
      AND ISNULL(bc.ReportTypeId, 0) <> @TrainingReportTypeId
      AND CHARINDEX(
          ',' + UPPER(LTRIM(RTRIM(ISNULL(bc.ServiceCode, '')))) + ',',
          ',' + @BackgroundCheckServiceCodes + ','
      ) > 0
      AND bc.Updated < DATEADD(day, 1, @Today)
) background
OUTER APPLY (
    SELECT TOP 1
        LTRIM(RTRIM(bc.ApprovalStatus)) AS LatestBackgroundStatus,
        bc.Updated AS LatestBackgroundDate
    FROM dbo.BackgroundChecks bc WITH (NOLOCK)
    WHERE bc.PeopleId = cp.PeopleId
      AND ISNULL(bc.ReportTypeId, 0) <> @TrainingReportTypeId
      AND CHARINDEX(
          ',' + UPPER(LTRIM(RTRIM(ISNULL(bc.ServiceCode, '')))) + ',',
          ',' + @BackgroundCheckServiceCodes + ','
      ) > 0
      AND bc.Updated < DATEADD(day, 1, @Today)
    ORDER BY bc.Updated DESC, bc.ID DESC
) latest_result
OUTER APPLY (
    SELECT TOP 1
        CASE
            WHEN LOWER(LTRIM(RTRIM(bc.ApprovalStatus))) = 'approved'
             AND CAST(bc.Updated AS date) >
                 DATEADD(month, -@MVRValidMonths, @Today)
                THEN 1 ELSE 0
        END AS HasCurrentApprovedMVR
    FROM dbo.BackgroundChecks bc WITH (NOLOCK)
    WHERE bc.PeopleId = cp.PeopleId
      AND ISNULL(bc.ReportTypeId, 0) <> @TrainingReportTypeId
      AND CHARINDEX(
          ',' + UPPER(LTRIM(RTRIM(ISNULL(bc.ServiceCode, '')))) + ',',
          ',' + @MVRServiceCodes + ','
      ) > 0
      AND bc.Updated < DATEADD(day, 1, @Today)
    ORDER BY bc.Updated DESC, bc.ID DESC
) mvr
OUTER APPLY (
    SELECT TOP 1 1 AS HasCurrentApprovedUnknownCheck
    FROM dbo.BackgroundChecks bc WITH (NOLOCK)
    WHERE bc.PeopleId = cp.PeopleId
      AND LOWER(LTRIM(RTRIM(bc.ApprovalStatus))) = 'approved'
      AND ISNULL(bc.ReportTypeId, 0) <> @TrainingReportTypeId
      AND CHARINDEX(
          ',' + UPPER(LTRIM(RTRIM(ISNULL(bc.ServiceCode, '')))) + ',',
          ',' + @BackgroundCheckServiceCodes + ','
      ) = 0
      AND CHARINDEX(
          ',' + UPPER(LTRIM(RTRIM(ISNULL(bc.ServiceCode, '')))) + ',',
          ',' + @MVRServiceCodes + ','
      ) = 0
      AND bc.Updated >= DATEADD(month, -@ValidMonths, @Today)
      AND bc.Updated < DATEADD(day, 1, @Today)
) unknown_check
WHERE ISNULL(p.IsDeceased, 0) = 0
  AND ISNULL(p.ArchivedFlag, 0) = 0
ORDER BY p.Name2, cp.PeopleId;
"""


def candidate_parameters():
    return {
        "EvaluationDate": today_midnight(),
        "ValidMonths": BACKGROUND_CHECK_VALID_MONTHS,
        "MinimumBackgroundCheckAge": MINIMUM_BACKGROUND_CHECK_AGE,
        "TrainingReportTypeId": TRAINING_REPORT_TYPE_ID,
        "BackgroundCheckServiceCodes": (
            BACKGROUND_CHECK_SERVICE_CODES
        ),
        "MVRServiceCodes": MVR_SERVICE_CODES,
        "MVRValidMonths": MVR_CHECK_VALID_MONTHS,
        "ApprovedRoleEV": APPROVED_ROLE_EV_FIELD,
        "ApplicationApprovedEV": APPLICATION_APPROVED_EV_FIELD,
        "ApplicationOnFileEV": APPLICATION_ON_FILE_EV_FIELD,
        "IneligibleVolunteerEV": INELIGIBLE_VOLUNTEER_EV_FIELD,
        "VolunteerApplicationInvolvementId": (
            VOLUNTEER_APPLICATION_INVOLVEMENT_ID
        ),
    }


def calculate_status(row):
    latest_status = str(row.LatestBackgroundStatus or "").strip()
    if bool(row.HasIneligibleVolunteer):
        return STATUS_DENIED, "Ineligible Volunteer is checked"
    if latest_status.lower() == "not approved":
        return STATUS_DENIED, "Latest background check is Not Approved"
    if not bool(row.HasApplicationApproved) or not bool(
        row.HasApplicationOnFile
    ):
        return (
            STATUS_MISSING_INFO,
            "Application on File and Application Approved are both required",
        )
    if bool(row.IsUnderMinimumAge):
        return STATUS_SECONDARY, "Below the minimum background-check age"
    if bool(row.HasCurrentApprovedCheck):
        if bool(row.HasCurrentApprovedMVR):
            return (
                STATUS_PRIMARY_MVR,
                "Current approved background check and MVR",
            )
        return STATUS_PRIMARY, "Current approved background check"
    if bool(row.HasExpiredApprovedCheck):
        return (
            STATUS_SECONDARY_EXPIRED,
            "Latest approved background check is expired",
        )
    if bool(row.HasCurrentApprovedMVR):
        return (
            STATUS_MISSING_INFO,
            "Current approved MVR does not satisfy the background-check "
            "requirement",
        )
    if bool(row.HasCurrentApprovedUnknownCheck):
        return (
            STATUS_MISSING_INFO,
            "Current approved check uses an unrecognized service code",
        )
    if latest_status:
        return (
            STATUS_SECONDARY,
            "No approved background check; latest result is {0}".format(
                latest_status
            ),
        )
    return STATUS_SECONDARY, "No background-check record"


def evaluate_candidates():
    rows = list(q.QuerySql(CANDIDATE_SQL, candidate_parameters()))
    results = []
    for row in rows:
        desired_status, reason = calculate_status(row)
        if desired_status not in ALLOWED_STATUSES:
            raise ValueError("Calculated an unsupported Approved for Role value.")
        current_status = str(row.ExistingApprovedRole or "").strip()
        desired_application_on_file = bool(
            row.HasVolunteerApplicationMembership
        )
        needs_application_update = (
            bool(row.HasStoredApplicationOnFile)
            != desired_application_on_file
        )
        needs_role_update = current_status != desired_status
        results.append(
            {
                "PeopleId": int(row.PeopleId),
                "VolunteerName": str(row.VolunteerName or ""),
                "CurrentStatus": current_status,
                "DesiredStatus": desired_status,
                "Reason": reason,
                "DesiredApplicationOnFile": desired_application_on_file,
                "NeedsApplicationOnFileUpdate": needs_application_update,
                "NeedsApprovedRoleUpdate": needs_role_update,
                "NeedsChange": needs_application_update or needs_role_update,
            }
        )
    return results


def apply_changes(results):
    changed = []
    unchanged = []
    failed = []
    for item in results:
        if not item["NeedsChange"]:
            unchanged.append(item)
            continue
        application_updated = False
        try:
            if item["NeedsApplicationOnFileUpdate"]:
                model.AddExtraValueBool(
                    int(item["PeopleId"]),
                    APPLICATION_ON_FILE_EV_FIELD,
                    item["DesiredApplicationOnFile"],
                )
                application_updated = True
            if item["NeedsApprovedRoleUpdate"]:
                model.AddExtraValueCode(
                    int(item["PeopleId"]),
                    APPROVED_ROLE_EV_FIELD,
                    item["DesiredStatus"],
                )
            changed_item = dict(item)
            changed_item["ApplicationOnFileUpdated"] = application_updated
            changed.append(changed_item)
        except Exception as exc:
            failed_item = dict(item)
            failed_item["Error"] = str(exc)
            failed_item["ApplicationOnFileUpdated"] = application_updated
            failed.append(failed_item)
    return changed, unchanged, failed


def render_change_table(items, preview):
    if not items:
        return '<div class="alert alert-success">No Extra Value changes.</div>'
    parts = [
        '<div class="table-responsive">',
        '<table class="table table-striped table-bordered">',
        "<thead><tr>",
        '<th scope="col">Volunteer</th>',
        '<th scope="col">Application on File</th>',
        '<th scope="col">Previous status</th>',
        '<th scope="col">New status</th>',
        '<th scope="col">Reason</th><th scope="col">Result</th>',
        "</tr></thead><tbody>",
    ]
    for item in items:
        person_url = "{0}/Person2/{1}#tab-volunteer".format(
            model.CmsHost, item["PeopleId"]
        )
        parts.extend(
            [
                "<tr>",
                '<td><a href="{0}" target="_blank" rel="noopener">{1}</a>'
                '<br><small>People ID {2}</small></td>'.format(
                    html_escape(person_url),
                    html_escape(item["VolunteerName"]),
                    item["PeopleId"],
                ),
                "<td>{0}</td>".format(
                    (
                        (
                            "Would set from Involvement membership"
                            if preview
                            else "Set from Involvement membership"
                        )
                        if item["DesiredApplicationOnFile"]
                        else (
                            "Would clear; not a current member"
                            if preview
                            else "Cleared; not a current member"
                        )
                    )
                    if item["NeedsApplicationOnFileUpdate"]
                    else (
                        "Already checked"
                        if item["DesiredApplicationOnFile"]
                        else "Already cleared"
                    )
                ),
                "<td>{0}</td>".format(
                    html_escape(item["CurrentStatus"] or "Not set")
                ),
                "<td><strong>{0}</strong></td>".format(
                    html_escape(item["DesiredStatus"])
                ),
                "<td>{0}</td>".format(html_escape(item["Reason"])),
                "<td>{0}</td>".format(
                    "Would change" if preview else "Updated"
                ),
                "</tr>",
            ]
        )
    parts.append("</tbody></table></div>")
    return "".join(parts)


def render_failures(failed):
    if not failed:
        return ""
    parts = [
        '<div class="alert alert-danger"><strong>Update failures:</strong>',
        "<ul>",
    ]
    for item in failed:
        partial = ""
        if item.get("ApplicationOnFileUpdated", False):
            partial = " Application on File was set before this failure."
        parts.append(
            "<li>{0} (People ID {1}): {2}{3}</li>".format(
                html_escape(item["VolunteerName"]),
                item["PeopleId"],
                html_escape(item.get("Error", "Unknown error")),
                html_escape(partial),
            )
        )
    parts.extend(["</ul>", "</div>"])
    return "".join(parts)


def build_report(results, changed, unchanged, failed, preview):
    proposed = [item for item in results if item["NeedsChange"]]
    detail_items = proposed if preview else changed
    title = "Volunteer Status Updater Preview" if preview else "Volunteer Status Updater"
    parts = [
        '<div style="font-family:\'Helvetica Neue\',Helvetica,Arial,sans-serif;">',
        '<h1 style="font-weight:300;">{0}</h1>'.format(title),
        "<p>Run date: <strong>{0}</strong></p>".format(
            html_escape(current_timestamp())
        ),
        (
            "<p><strong>{0}</strong> evaluated; <strong>{1}</strong> {2}; "
            "<strong>{3}</strong> unchanged; <strong>{4}</strong> failed.</p>"
        ).format(
            len(results),
            len(proposed) if preview else len(changed),
            "would change" if preview else "changed",
            len(unchanged),
            len(failed),
        ),
    ]
    if preview:
        parts.append(
            '<div class="alert alert-info"><strong>Preview only.</strong> '
            "No Extra Values were updated and no email was sent.</div>"
        )
    parts.append(render_change_table(detail_items, preview))
    parts.append(render_failures(failed))
    parts.append("</div>")
    return "".join(parts)


def save_last_run_summary(results, changed, unchanged, failed, email_queued):
    state = {
        "version": 1,
        "updated": current_timestamp(),
        "evaluated": len(results),
        "changed": len(changed),
        "unchanged": len(unchanged),
        "skipped": 0,
        "failed": len(failed),
        "email_queued": bool(email_queued),
    }
    model.WriteContentText(
        STATE_CONTENT_NAME,
        json.dumps(state, sort_keys=True),
        "",
    )


def main():
    preview = requested_action() == "preview" or not UPDATES_ENABLED
    validate_configuration(not preview)
    results = evaluate_candidates()
    if preview:
        changed = []
        unchanged = [item for item in results if not item["NeedsChange"]]
        failed = []
        if not UPDATES_ENABLED and requested_action() != "preview":
            print(
                '<div class="alert alert-warning"><strong>Updates are '
                "disabled.</strong> This Morning Batch run was preview-only."
                "</div>"
            )
        print(build_report(results, changed, unchanged, failed, True))
        return

    changed, unchanged, failed = apply_changes(results)
    report = build_report(results, changed, unchanged, failed, False)
    email_queued = False
    email_error = None
    if EMAIL_ENABLED and (changed or failed):
        try:
            send_email(REPORT_SUBJECT, report)
            email_queued = True
        except Exception as exc:
            email_error = exc
    save_last_run_summary(
        results, changed, unchanged, failed, email_queued
    )
    if changed:
        print(
            '<div class="alert alert-success">Updated {0} volunteer status'
            " value(s).</div>".format(len(changed))
        )
    else:
        print(
            '<div class="alert alert-success">No volunteer status changes '
            "were required.</div>"
        )
    if email_error is not None:
        print(
            '<div class="alert alert-danger"><strong>Updater email was not '
            "queued:</strong> {0}</div>".format(html_escape(email_error))
        )
    print(report)


try:
    main()
except Exception as exc:
    print(
        '<div class="alert alert-danger"><strong>Volunteer Status Updater '
        "failed:</strong> {0}</div>".format(html_escape(exc))
    )
    if EMAIL_ENABLED and UPDATES_ENABLED and requested_action() != "preview":
        try:
            send_email(
                REPORT_SUBJECT + " - Failure",
                '<div style="font-family:\'Helvetica Neue\',Helvetica,Arial,'
                'sans-serif;"><h1 style="font-weight:300;">Volunteer Status '
                "Updater Failure</h1><p>The production run failed before it "
                "could complete.</p><div class=\"alert alert-danger\">{0}"
                "</div></div>".format(html_escape(exc)),
            )
        except Exception as email_exc:
            print(
                '<div class="alert alert-danger"><strong>Failure email was '
                "not queued:</strong> {0}</div>".format(
                    html_escape(email_exc)
                )
            )
    raise
