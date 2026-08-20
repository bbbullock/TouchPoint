#Roles=Admin

# Volunteer Status Updater Admin
# Version: 1.12.0
# 2026-08-20 1.12.0 - Added MVR service-code and 12-month validity settings,
# PrimaryVolunteerMVR readiness, and background-check/MVR terminology.
# 2026-08-20 1.11.0 - Added independent background-check ServiceCode allowlist
# configuration and documented the MVR-only MissingInfo rule.
# 2026-08-19 1.10.0 - Removed NotApproved from output readiness and documented
# exclusion of deceased and archived people.
# 2026-08-19 1.9.0 - Changed incomplete applications to MissingInfo and
# removed the obsolete denied/adverse rule from the decision table.
# 2026-08-19 1.8.0 - Added Denied readiness and rule guidance for Not Approved
# background checks and the Ineligible Volunteer Extra Value.
# 2026-08-18 1.7.0 - Removed SystemExit from live-search responses because
# TouchPoint renders it as a traceback after the JSON response.
# 2026-08-18 1.6.0 - Replaced generic live-search failures with bounded,
# Admin-visible HTTP and response details for live tenant diagnosis.
# 2026-08-18 1.5.0 - Aligned person and Involvement live-search routing and
# fetch requests with the live-proven BackgroundCheckEvaluatorAdmin pattern.
# 2026-08-18 1.4.0 - Repaired all live-search controls by isolating the
# Involvement picker from person-picker initialization and routing explicit
# lookup actions independently of form-save method detection.
# 2026-08-18 1.3.0 - Made Volunteer Application Involvement membership the
# authority for both setting and clearing Application on File.
# 2026-08-18 1.2.0 - Added Volunteer Application Involvement selection and
# documented membership-driven Application on File updates.
# 2026-08-18 1.1.0 - Removed Involvement Program and Division settings and
# documented the person-level candidate population.
# 2026-08-18 1.0.0 - Added independent VSU configuration, first-use BCE
# suggestions, readiness checks, preview, activation safeguards, and run state.
# Written by: Brian Bullock with Codex assistance
# Email: bbbullock@mac.com
# GitHub: https://github.com/bbbullock/TouchPoint

"""Admin-only configuration UI for VolunteerStatusUpdater."""

import cgi
import json


APP_VERSION = "1.12.0"
SETTING_PREFIX = "VSU."
BCE_SETTING_PREFIX = "BCE."
STATE_CONTENT_NAME = "VolunteerStatusUpdaterState"
STANDARD_EV_CONTENT_NAME = "StandardExtraValues2"
APPROVED_ROLE_EV_FIELD = "Approved for Role"
APPROVED_ROLE_CODES = (
    "PrimaryVolunteer",
    "PrimaryVolunteerMVR",
    "SecondaryVolunteer",
    "SecondaryVolunteerExpiredBackground",
    "Denied",
    "MissingInfo",
)

DEFAULTS = {
    "ConfigurationSaved": "false",
    "UpdatesEnabled": "false",
    "EmailEnabled": "false",
    "RecipientPeopleIds": "",
    "QueuedByPeopleId": "0",
    "FromAddress": "",
    "FromName": "",
    "BackgroundCheckValidMonths": "33",
    "MinimumBackgroundCheckAge": "18",
    "TrainingReportTypeId": "0",
    "BackgroundCheckServiceCodes": "",
    "MVRServiceCodes": "",
    "MVRCheckValidMonths": "12",
    "VolunteerApplicationInvolvementId": "0",
}

# These values are shown from the evaluator only when the corresponding VSU
# setting does not exist. Saving creates an independent VSU configuration.
BCE_SUGGESTIONS = {
    "RecipientPeopleIds": "ReportRecipientPeopleIds",
    "QueuedByPeopleId": "QueuedByPeopleId",
    "FromAddress": "FromAddress",
    "FromName": "FromName",
    "BackgroundCheckValidMonths": "BackgroundCheckValidMonths",
    "MinimumBackgroundCheckAge": "MinimumBackgroundCheckAge",
    "TrainingReportTypeId": "TrainingReportTypeId",
    "BackgroundCheckServiceCodes": (
        "BackgroundCheckServiceCodes"
    ),
}

for setting_name in DEFAULTS:
    if len(SETTING_PREFIX + setting_name) > 50:
        raise ValueError(
            "TouchPoint setting key exceeds 50 characters: {0}".format(
                SETTING_PREFIX + setting_name
            )
        )

model.Header = "Volunteer Status Updater Configuration"
model.Transactional = True


def escape(value):
    return cgi.escape(str(value if value is not None else ""), True)


def posted(name, default=""):
    try:
        value = getattr(Data, name)
        return str(value if value is not None else default).strip()
    except Exception:
        return default


def json_escape(value):
    text = unicode(value if value is not None else "")
    parts = ['"']
    for char in text:
        code = ord(char)
        if char == '"':
            parts.append('\\"')
        elif char == "\\":
            parts.append("\\\\")
        elif char == "\n":
            parts.append("\\n")
        elif char == "\r":
            parts.append("\\r")
        elif char == "\t":
            parts.append("\\t")
        elif code < 32 or code >= 127:
            parts.append("\\u{0:04x}".format(code))
        else:
            parts.append(char)
    parts.append('"')
    return "".join(parts)


def raw_vsu(name):
    sentinel = "__VSU_SETTING_NOT_SAVED__"
    value = str(model.Setting(SETTING_PREFIX + name, sentinel) or sentinel)
    if value == sentinel:
        return None
    return value


def current(name):
    value = raw_vsu(name)
    if value is not None:
        return value
    if name in BCE_SUGGESTIONS and not configuration_saved():
        return str(
            model.Setting(
                BCE_SETTING_PREFIX + BCE_SUGGESTIONS[name],
                DEFAULTS[name],
            )
            or DEFAULTS[name]
        )
    return DEFAULTS[name]


def configuration_saved():
    value = raw_vsu("ConfigurationSaved")
    return str(value or DEFAULTS["ConfigurationSaved"]).lower() == "true"


def normalize_id_list(raw):
    values = []
    for part in str(raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            value = int(part)
        except Exception:
            continue
        if value > 0 and value not in values:
            values.append(value)
    return values


def person_json(row):
    return (
        '{"id":%s,"name":%s,"email":%s}'
        % (
            int(row.PeopleId),
            json_escape(row.Name2 or row.Name or ""),
            json_escape(row.EmailAddress or ""),
        )
    )


def load_people(people_ids):
    if not people_ids:
        return []
    sql = """
        SELECT PeopleId, Name, Name2, EmailAddress
        FROM dbo.People
        WHERE PeopleId IN ({0})
        ORDER BY Name2
    """.format(",".join(str(int(value)) for value in people_ids))
    return list(q.QuerySql(sql))


def handle_people_search():
    term = posted("term")
    exact_id = 0
    try:
        exact_id = int(term)
    except Exception:
        exact_id = 0
    if len(term) < 2 and exact_id == 0:
        return '{"success":true,"people":[]}'
    rows = list(
        q.QuerySql(
            """
            SELECT TOP 12 PeopleId, Name, Name2, EmailAddress
            FROM dbo.People
            WHERE PeopleId = @ExactPeopleId
               OR (
                    (Name LIKE @LikeTerm OR Name2 LIKE @LikeTerm
                     OR EmailAddress LIKE @LikeTerm)
                    AND ISNULL(IsDeceased, 0) = 0
                    AND ISNULL(ArchivedFlag, 0) = 0
               )
            ORDER BY CASE WHEN PeopleId = @ExactPeopleId THEN 0 ELSE 1 END,
                     Name2
            """,
            {"ExactPeopleId": exact_id, "LikeTerm": "%" + term + "%"},
        )
    )
    return (
        '{"success":true,"people":[%s]}'
        % ",".join(person_json(row) for row in rows)
    )


def involvement_json(row):
    label = "{0} : {1} : {2}".format(
        row.ProgramName or "Program unavailable",
        row.DivisionName or "Division unavailable",
        row.OrganizationName or "Unnamed Involvement",
    )
    return '{"id":%s,"label":%s}' % (
        int(row.OrganizationId),
        json_escape(label),
    )


def handle_involvement_search():
    term = posted("term")
    exact_id = 0
    try:
        exact_id = int(term)
    except Exception:
        exact_id = 0
    if len(term) < 2 and exact_id == 0:
        return '{"success":true,"involvements":[]}'
    rows = list(
        q.QuerySql(
            """
            SELECT TOP 15
                o.OrganizationId,
                o.OrganizationName,
                d.Name AS DivisionName,
                p.Name AS ProgramName
            FROM dbo.Organizations o
            JOIN dbo.Division d ON d.Id = o.DivisionId
            JOIN dbo.Program p ON p.Id = d.ProgId
            WHERE o.OrganizationStatusId = 30
              AND (
                    o.OrganizationId = @ExactOrganizationId
                    OR o.OrganizationName LIKE @LikeTerm
                    OR d.Name LIKE @LikeTerm
                    OR p.Name LIKE @LikeTerm
              )
            ORDER BY
                CASE WHEN o.OrganizationId = @ExactOrganizationId
                     THEN 0 ELSE 1 END,
                p.Name, d.Name, o.OrganizationName
            """,
            {
                "ExactOrganizationId": exact_id,
                "LikeTerm": "%" + term + "%",
            },
        )
    )
    return (
        '{"success":true,"involvements":[%s]}'
        % ",".join(involvement_json(row) for row in rows)
    )


def require_int(name, minimum, maximum):
    raw = posted(name)
    try:
        value = int(raw)
    except Exception:
        raise ValueError("{0} must be a whole number.".format(name))
    if value < minimum or value > maximum:
        raise ValueError(
            "{0} must be between {1} and {2}.".format(name, minimum, maximum)
        )
    return str(value)


def require_service_codes(name):
    codes = []
    allowed = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
    for part in posted(name).split(","):
        code = part.strip().upper()
        if not code:
            continue
        if len(code) > 50 or any(char not in allowed for char in code):
            raise ValueError(
                "Service codes must use "
                "comma-separated letters, numbers, periods, underscores, "
                "or hyphens."
            )
        if code not in codes:
            codes.append(code)
    if not codes:
        raise ValueError(
            "At least one service code "
            "is required."
        )
    return ",".join(codes)


def require_people_ids(name, allow_empty):
    ids = []
    for part in posted(name).split(","):
        part = part.strip()
        if not part:
            continue
        try:
            value = int(part)
        except Exception:
            raise ValueError(
                "{0} must contain comma-separated People IDs.".format(name)
            )
        if value <= 0:
            raise ValueError("{0} contains an invalid People ID.".format(name))
        if value not in ids:
            ids.append(value)
    if not ids and not allow_empty:
        raise ValueError("{0} requires at least one person.".format(name))
    return ",".join(str(value) for value in ids)


def validate_person(people_id, label):
    count = q.QuerySqlInt(
        "SELECT COUNT(*) FROM dbo.People WHERE PeopleId = {0}".format(
            int(people_id)
        )
    )
    if count != 1:
        raise ValueError(
            "{0} People ID {1} was not found.".format(label, people_id)
        )


def save_configuration():
    values = {
        "ConfigurationSaved": "true",
        "UpdatesEnabled": (
            "true" if posted("UpdatesEnabled").lower() == "true" else "false"
        ),
        "EmailEnabled": (
            "true" if posted("EmailEnabled").lower() == "true" else "false"
        ),
        "BackgroundCheckValidMonths": require_int(
            "BackgroundCheckValidMonths", 1, 120
        ),
        "MinimumBackgroundCheckAge": require_int(
            "MinimumBackgroundCheckAge", 0, 100
        ),
        "TrainingReportTypeId": require_int("TrainingReportTypeId", 0, 100),
        "BackgroundCheckServiceCodes": require_service_codes(
            "BackgroundCheckServiceCodes"
        ),
        "MVRServiceCodes": require_service_codes("MVRServiceCodes"),
        "MVRCheckValidMonths": require_int(
            "MVRCheckValidMonths", 1, 120
        ),
        "VolunteerApplicationInvolvementId": require_int(
            "VolunteerApplicationInvolvementId", 1, 2147483647
        ),
    }
    values["RecipientPeopleIds"] = require_people_ids(
        "RecipientPeopleIds", values["EmailEnabled"] != "true"
    )
    values["QueuedByPeopleId"] = posted("QueuedByPeopleId") or "0"
    values["FromAddress"] = posted("FromAddress")
    values["FromName"] = posted("FromName")

    background_codes = set(values["BackgroundCheckServiceCodes"].split(","))
    mvr_codes = set(values["MVRServiceCodes"].split(","))
    overlap = sorted(background_codes & mvr_codes)
    if overlap:
        raise ValueError(
            "Background-check and MVR service codes cannot overlap: {0}."
            .format(", ".join(overlap))
        )

    involvement_count = q.QuerySqlInt(
        """
        SELECT COUNT(*)
        FROM dbo.Organizations
        WHERE OrganizationId = {0}
          AND OrganizationStatusId = 30
        """.format(values["VolunteerApplicationInvolvementId"])
    )
    if involvement_count != 1:
        raise ValueError(
            "The Volunteer Application Involvement was not found or is not "
            "active."
        )

    enabling_updates = (
        (
            not configuration_saved()
            or current("UpdatesEnabled").lower() != "true"
        )
        and values["UpdatesEnabled"] == "true"
    )
    if enabling_updates and posted("ConfirmEnable").lower() != "true":
        raise ValueError(
            "Confirm that the live updater preview was reviewed before "
            "enabling Morning Batch writes."
        )
    if values["UpdatesEnabled"] == "true":
        ready, detail = readiness_summary()
        if not ready:
            raise ValueError(
                "Approved for Role readiness must pass before writes can be "
                "enabled. {0}".format(detail)
            )

    try:
        queued_by = int(values["QueuedByPeopleId"])
    except Exception:
        raise ValueError("Queued-by People ID must be a whole number.")
    if queued_by > 0:
        validate_person(queued_by, "Queued-by")
    for people_id in values["RecipientPeopleIds"].split(","):
        if people_id:
            validate_person(people_id, "Recipient")

    if values["EmailEnabled"] == "true":
        if queued_by <= 0:
            raise ValueError("Queued-by person is required when email is enabled.")
        if not values["FromName"]:
            raise ValueError("From name is required when email is enabled.")
        if "@" not in values["FromAddress"]:
            raise ValueError(
                "A valid From address is required when email is enabled."
            )

    for name, value in values.items():
        model.SetSetting(SETTING_PREFIX + name, value)


def readiness_summary():
    try:
        content = str(model.TextContent(STANDARD_EV_CONTENT_NAME) or "")
        field_index = content.find(APPROVED_ROLE_EV_FIELD)
        if field_index < 0:
            return False, "Approved for Role is not defined in StandardExtraValues2."
        window = content[max(0, field_index - 1000):field_index + 6000]
        missing = [code for code in APPROVED_ROLE_CODES if code not in window]
        if "Code" not in window:
            return False, "Approved for Role was found, but its Code type was not confirmed."
        if missing:
            return False, "Missing configured option(s): {0}.".format(
                ", ".join(missing)
            )
        return True, "Approved for Role and all six configured options were found."
    except Exception as exc:
        return False, "Readiness check failed: {0}".format(exc)


def load_state_summary():
    raw = str(model.TextContent(STATE_CONTENT_NAME) or "").strip()
    if not raw:
        return None
    try:
        state = json.loads(raw)
        if int(state.get("version", 0) or 0) < 1:
            return None
        return state
    except Exception:
        return None


is_post = str(getattr(model, "HttpMethod", "")).lower() == "post"
action = posted("VSUAdminAction").lower()
lookup_response = None
if is_post and action == "search_people":
    lookup_response = handle_people_search()
if is_post and action == "search_involvements":
    lookup_response = handle_involvement_search()

message = ""
toast = ""
if is_post and lookup_response is None:
    try:
        save_configuration()
        toast = (
            '<div class="vsu-toast alert-success" id="vsuToast" role="status" '
            'aria-live="polite" aria-atomic="true"><span><strong>Saved</strong>'
            '</span><button type="button" class="vsu-toast-close" '
            'id="vsuToastClose" aria-label="Dismiss notification">&times;'
            "</button></div>"
        )
    except Exception as exc:
        message = (
            '<div class="alert alert-danger" role="alert"><strong>Not saved:'
            "</strong> {0}</div>".format(escape(exc))
        )
        toast = (
            '<div class="vsu-toast vsu-toast-error alert-danger" id="vsuToast" '
            'role="alert" aria-live="assertive" aria-atomic="true"><span>'
            "Configuration was not saved. Correct the displayed problem and "
            'try again.</span><button type="button" class="vsu-toast-close" '
            'id="vsuToastClose" aria-label="Dismiss notification">&times;'
            "</button></div>"
        )

try:
    configured_involvement_id = int(
        current("VolunteerApplicationInvolvementId") or "0"
    )
except Exception:
    configured_involvement_id = 0
configured_involvements = []
if configured_involvement_id > 0:
    configured_involvements = list(
        q.QuerySql(
            """
            SELECT
                o.OrganizationId,
                o.OrganizationName,
                d.Name AS DivisionName,
                p.Name AS ProgramName
            FROM dbo.Organizations o
            JOIN dbo.Division d ON d.Id = o.DivisionId
            JOIN dbo.Program p ON p.Id = d.ProgId
            WHERE o.OrganizationId = @OrganizationId
            """,
            {"OrganizationId": configured_involvement_id},
        )
    )
configured_involvement_json = (
    involvement_json(configured_involvements[0])
    if configured_involvements
    else "null"
)

configured_ids = normalize_id_list(
    ",".join([current("QueuedByPeopleId"), current("RecipientPeopleIds")])
)
configured_people = load_people(configured_ids)
configured_people_json = (
    "{"
    + ",".join(
        json_escape(str(row.PeopleId)) + ":" + person_json(row)
        for row in configured_people
    )
    + "}"
)

ready, readiness_detail = readiness_summary()
readiness_html = (
    '<div class="alert alert-success"><strong>Ready:</strong> {0}</div>'
    if ready
    else '<div class="alert alert-danger"><strong>Not ready:</strong> {0}</div>'
).format(escape(readiness_detail))

state = load_state_summary()
if state is None:
    state_html = (
        "<strong>No production updater run has been recorded.</strong> "
        "Previews do not create or change this summary."
    )
else:
    state_html = (
        "<strong>Last production run:</strong> {0} &mdash; {1} evaluated, "
        "{2} changed, {3} unchanged, {4} failed; email {5}."
    ).format(
        escape(state.get("updated", "timestamp unavailable")),
        int(state.get("evaluated", 0) or 0),
        int(state.get("changed", 0) or 0),
        int(state.get("unchanged", 0) or 0),
        int(state.get("failed", 0) or 0),
        "queued" if bool(state.get("email_queued", False)) else "not queued",
    )

suggestion_notice = ""
if not configuration_saved():
    suggestion_notice = (
        '<div class="alert alert-warning"><strong>Review required.</strong> '
        "Where matching updater settings do not yet exist, values shown below "
        "are suggestions from Background Check Evaluator. Saving creates an "
        "independent VSU configuration; later evaluator changes will not "
        "synchronize automatically.</div>"
    )

updates_enabled = current("UpdatesEnabled").lower() == "true"
email_enabled = current("EmailEnabled").lower() == "true"

html = """
<style>
.vsu-wrap {{max-width:1080px;margin:0 auto;font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;}}
.vsu-wrap h1,.vsu-wrap h2 {{font-weight:300;}}
.vsu-version {{color:#667;margin-bottom:18px;}}
.vsu-card {{border:1px solid #d9dfe5;border-radius:5px;padding:18px;margin-bottom:18px;background:#fff;}}
.vsu-grid {{display:grid;grid-template-columns:repeat(2,minmax(260px,1fr));gap:16px 22px;}}
.vsu-field label {{display:block;font-weight:600;margin-bottom:5px;}}
.vsu-field input,.vsu-field select {{width:100%;min-height:38px;padding:7px 9px;border:1px solid #b8c2cc;border-radius:4px;}}
.vsu-help {{color:#667;font-size:12px;margin-top:4px;}}
.vsu-danger {{border-left:5px solid #d9534f;}}
.vsu-person-picker {{position:relative;}}
.vsu-person-results {{display:none;position:absolute;z-index:1000;left:0;right:0;max-height:260px;overflow:auto;background:#fff;border:1px solid #aeb8c2;border-radius:4px;box-shadow:0 5px 15px rgba(0,0,0,.18);}}
.vsu-person-result {{padding:9px 11px;cursor:pointer;border-bottom:1px solid #eee;}}
.vsu-person-result:hover {{background:#eef6fc;}}
.vsu-person-result small {{display:block;color:#667;}}
.vsu-chips {{display:flex;flex-wrap:wrap;gap:6px;margin:7px 0;}}
.vsu-chip {{display:inline-flex;align-items:center;gap:7px;padding:5px 8px;background:#eaf3f9;border:1px solid #b8d5e6;border-radius:16px;}}
.vsu-chip button {{border:0;background:transparent;color:#a33;padding:0;}}
.vsu-toast {{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);z-index:2000;display:flex;align-items:center;gap:18px;min-width:280px;max-width:calc(100% - 32px);padding:12px 16px;background:#287a45;border:1px solid #1f6237;border-radius:6px;box-shadow:0 4px 14px rgba(0,0,0,.24);color:#fff;}}
.vsu-toast-error {{background:#b42318;border-color:#8f1c13;}}
.vsu-toast-close {{border:0;background:transparent;color:#fff;font-size:1.4em;line-height:1;padding:0;cursor:pointer;}}
@media (max-width:760px) {{.vsu-grid {{grid-template-columns:1fr;}}}}
</style>
<div class="vsu-wrap">
  <h1>Volunteer Status Updater Configuration</h1>
  <div class="vsu-version">Version {version}</div>
  {message}{toast}{suggestion_notice}
  <div class="alert alert-info">
    These settings belong only to Volunteer Status Updater. Saving does not
    evaluate volunteers, write Extra Values, or send email.
  </div>
  <form id="vsuConfigForm" method="post" target="_self">
    <input type="hidden" name="UpdatesEnabled" value="{updates_value}">
    <input type="hidden" name="EmailEnabled" value="{email_value}">
    <input type="hidden" name="ConfirmEnable" value="false">

    <div class="vsu-card">
      <h2>Readiness</h2>
      {readiness_html}
      <p class="vsu-help">
        This check reads StandardExtraValues2 only. The Admin app does not
        create or modify the Approved for Role definition.
      </p>
    </div>

    <div class="vsu-card">
      <h2>Candidate population</h2>
      <p>An individual is evaluated when at least one of these is true:</p>
      <ul>
        <li>Approved for Role currently has any stored value;</li>
        <li>Application on File is checked;</li>
        <li>Application Approved is checked;</li>
        <li>Ineligible Volunteer is checked;</li>
        <li>a current Approved background check or MVR, or latest Not Approved
          background check, is on file; or</li>
        <li>the person is a current, non-pending member of the configured
          Volunteer Application Involvement.</li>
      </ul>
      <p class="vsu-help">
        Deceased and archived people are excluded from evaluation.
        Program, Division, and all other Involvement memberships are ignored.
        Membership in the one Volunteer Application Involvement selected below
        is the authority for Application on File. A current, non-pending member
        is checked; a pending, inactive, or absent person is cleared. The
        complete status decision table is then applied to every candidate.
      </p>
      <div class="vsu-field" style="margin-top:16px;">
        <label>Volunteer Application Involvement</label>
        <div id="applicationInvolvementPicker" class="vsu-person-picker">
          <input type="hidden" name="VolunteerApplicationInvolvementId"
            value="{application_involvement_id}">
          <div class="vsu-chips" id="applicationInvolvementSelection"></div>
          <input id="applicationInvolvementSearch" autocomplete="off"
            placeholder="Search active Involvements by name or ID">
          <div class="vsu-person-results"
            id="applicationInvolvementResults"></div>
        </div>
        <div class="vsu-help">
          Choose the Involvement that receives completed volunteer
          applications. The saved reference is its stable Organization ID.
        </div>
      </div>
    </div>

    <div class="vsu-card">
      <h2>Evaluation settings</h2>
      <div class="vsu-grid">
        <div class="vsu-field"><label>Background check valid months</label>
          <input name="BackgroundCheckValidMonths" type="number" min="1"
            max="120" value="{valid_months}"></div>
        <div class="vsu-field"><label>Minimum background-check age</label>
          <input name="MinimumBackgroundCheckAge" type="number" min="0"
            max="100" value="{minimum_age}"></div>
        <div class="vsu-field"><label>Training Report Type ID</label>
          <input name="TrainingReportTypeId" type="number" min="0" max="100"
            value="{training_type}">
          <div class="vsu-help">This type is excluded from status evaluation.</div>
        </div>
        <div class="vsu-field">
          <label>Qualifying background-check service codes</label>
          <input name="BackgroundCheckServiceCodes"
            value="{background_service_codes}"
            placeholder="Example: 12345,67890">
          <div class="vsu-help">
            Enter the comma-separated provider ServiceCode values confirmed
            by the diagnostic as background checks. MVR, training, and unknown
            codes remain nonqualifying.
          </div>
        </div>
        <div class="vsu-field">
          <label>MVR service codes</label>
          <input name="MVRServiceCodes" value="{mvr_service_codes}"
            placeholder="Example: 12345">
          <div class="vsu-help">
            Enter the comma-separated provider ServiceCode values that
            positively identify MVR checks. A code cannot appear in both
            service-code fields.
          </div>
        </div>
        <div class="vsu-field">
          <label>MVR Check Valid Months</label>
          <input name="MVRCheckValidMonths" type="number" min="1" max="120"
            value="{mvr_valid_months}">
          <div class="vsu-help">
            The latest MVR must be Approved and newer than this many calendar
            months. It expires on the anniversary date.
          </div>
        </div>
      </div>
    </div>

    <div class="vsu-card">
      <h2>Status rules</h2>
      <div class="table-responsive">
        <table class="table table-striped table-bordered">
          <thead><tr><th scope="col">Condition</th>
            <th scope="col">Approved for Role</th></tr></thead>
          <tbody>
            <tr><td>Latest background check is Not Approved, or Ineligible
              Volunteer is checked</td><td><code>Denied</code></td></tr>
            <tr><td>Complete application, current approved background check,
              and current approved MVR</td><td><code>PrimaryVolunteerMVR</code></td></tr>
            <tr><td>Complete application and current approved background check
              without a current approved MVR</td><td><code>PrimaryVolunteer</code></td></tr>
            <tr><td>Complete application and no approved check of any type</td><td><code>SecondaryVolunteer</code></td></tr>
            <tr><td>Complete application and expired approved background check</td><td><code>SecondaryVolunteerExpiredBackground</code></td></tr>
            <tr><td>Complete application and only a current approved MVR</td><td><code>MissingInfo</code></td></tr>
            <tr><td>Incomplete application</td><td><code>MissingInfo</code></td></tr>
          </tbody>
        </table>
      </div>
      <p class="vsu-help">
        Denied takes precedence over every other status rule.
        Below-minimum-age volunteers with complete applications are Secondary.
        A newer Pending background-check result does not invalidate current
        background-check approval. The latest MVR must itself be Approved and
        in date. College and refusal flags do not override these rules.
      </p>
    </div>

    <div class="vsu-card">
      <h2>Change and failure email</h2>
      <div class="alert alert-info">
        Every recipient receives the complete list, including names, People
        IDs, old and new status, and reasons. Email addresses and phone numbers
        are not included. Email is sent only for changes or failures.
      </div>
      <div class="vsu-grid">
        <div class="vsu-field"><label>Queued-by person</label>
          <div class="vsu-person-picker" data-picker="single" data-fill-sender="true">
            <input type="hidden" name="QueuedByPeopleId" value="{queued_by}">
            <div class="vsu-chips"></div>
            <input class="vsu-person-search" autocomplete="off" placeholder="Search by name, email, or People ID">
            <div class="vsu-person-results"></div>
          </div>
        </div>
        <div class="vsu-field"><label>From name</label>
          <input name="FromName" value="{from_name}"></div>
        <div class="vsu-field"><label>From address</label>
          <input name="FromAddress" type="email" value="{from_address}"></div>
        <div class="vsu-field"><label>Recipients</label>
          <div class="vsu-person-picker" data-picker="multi">
            <input type="hidden" name="RecipientPeopleIds" value="{recipients}">
            <div class="vsu-chips"></div>
            <input class="vsu-person-search" autocomplete="off" placeholder="Search and add people">
            <div class="vsu-person-results"></div>
          </div>
        </div>
      </div>
      <label style="margin-top:14px;display:block;">
        <input id="emailEnabledBox" type="checkbox"{email_checked}>
        Enable updater change and failure email
      </label>
    </div>

    <div class="vsu-card vsu-danger">
      <h2>Morning Batch writes</h2>
      <label><input id="updatesEnabledBox" type="checkbox"{updates_checked}>
        Enable updates to Approved for Role</label>
      <div class="vsu-help">Leave disabled until the live preview is reviewed.</div>
      <div id="enableConfirmation" class="alert alert-warning" style="margin-top:12px;display:none;">
        <label><input id="confirmEnableBox" type="checkbox">
          I reviewed the live preview and authorize Morning Batch writes.</label>
      </div>
    </div>

    <button type="submit" class="btn btn-primary">Save updater configuration</button>
    <noscript><div class="alert alert-danger" style="margin-top:12px;">
      JavaScript is required to save without leaving the TouchPoint page.
    </div></noscript>
  </form>

  <div class="vsu-card" style="margin-top:18px;">
    <h2>Preview status updates</h2>
    <p>Preview uses saved VSU settings and opens in a new tab. It never writes
      Extra Values, sends email, or changes the last-run summary.</p>
    <form id="vsuPreviewForm" method="post" target="_blank">
      <input type="hidden" name="VSUAction" value="preview">
      <button type="submit" class="btn btn-default">Preview status updates</button>
    </form>
  </div>

  <div class="vsu-card"><h2>Last production run</h2><p>{state_html}</p></div>
</div>
<script>
function initializeVolunteerStatusUpdaterAdmin() {{
  var form = document.getElementById('vsuConfigForm');
  if (!form) return;
  form.action = window.location.pathname.replace('/PyScript/', '/PyScriptForm/');
  var previewForm = document.getElementById('vsuPreviewForm');
  previewForm.action = form.action.replace('/VolunteerStatusUpdaterAdmin', '/VolunteerStatusUpdater');
  var lookupUrl = form.action;
  function summarizeLookupResponse(text) {{
    var holder = document.createElement('div');
    holder.innerHTML = String(text || '');
    var plain = (holder.textContent || holder.innerText || '')
      .replace(/\\s+/g, ' ').trim();
    return plain.substring(0, 240) || 'empty response';
  }}
  function requestLookup(body) {{
    return fetch(lookupUrl, {{
      method:'POST',
      headers:{{'Content-Type':'application/x-www-form-urlencoded'}},
      body:body,
      credentials:'same-origin'
    }}).then(function(response) {{
      return response.text().then(function(text) {{
        if (!response.ok) {{
          throw new Error(
            'HTTP ' + response.status + ': ' + summarizeLookupResponse(text)
          );
        }}
        try {{
          return JSON.parse(text);
        }} catch (error) {{
          throw new Error(
            'Expected JSON but received: ' + summarizeLookupResponse(text)
          );
        }}
      }});
    }});
  }}
  function lookupFailureMarkup(error) {{
    return '<strong>Lookup failed.</strong><small>' +
      esc(error && error.message ? error.message : 'Unknown response error') +
      '</small>';
  }}
  var toast = document.getElementById('vsuToast');
  if (toast) {{
    var dismiss = function() {{if (toast && toast.parentNode) toast.parentNode.removeChild(toast);}};
    var close = document.getElementById('vsuToastClose');
    if (close) close.addEventListener('click', dismiss);
    if (toast.className.indexOf('vsu-toast-error') < 0) window.setTimeout(dismiss, 5000);
  }}
  function showError(text) {{
    var old = document.getElementById('vsuSaveError');
    if (old && old.parentNode) old.parentNode.removeChild(old);
    var error = document.createElement('div');
    error.id = 'vsuSaveError'; error.className = 'alert alert-danger';
    error.setAttribute('role', 'alert'); error.textContent = text;
    form.parentNode.insertBefore(error, form); form.removeAttribute('aria-busy');
  }}
  function replaceAdmin(markup) {{
    var holder = document.createElement('div'); holder.innerHTML = markup;
    var next = holder.querySelector('.vsu-wrap');
    var current = document.querySelector('.vsu-wrap');
    if (!next || !current) throw new Error('Admin response was incomplete');
    current.innerHTML = next.innerHTML;
    initializeVolunteerStatusUpdaterAdmin(); current.scrollIntoView({{block:'start'}});
  }}
  form.addEventListener('submit', function(event) {{
    event.preventDefault(); if (!form.reportValidity()) return;
    var fields = new FormData(form); var body = new URLSearchParams();
    fields.forEach(function(value,key) {{body.append(key,value);}});
    form.setAttribute('aria-busy','true');
    fetch(form.action, {{method:'POST',credentials:'same-origin',headers:{{
      'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
      'X-Requested-With':'XMLHttpRequest'}},body:body.toString()}})
      .then(function(response) {{if (!response.ok) throw new Error('HTTP status: '+response.status+'.'); return response.text();}})
      .then(replaceAdmin).catch(function(error) {{showError('The configuration could not be saved. '+(error.message||''));}});
  }});
  var emailBox = document.getElementById('emailEnabledBox');
  var emailHidden = form.querySelector('input[name="EmailEnabled"]');
  var updatesBox = document.getElementById('updatesEnabledBox');
  var updatesHidden = form.querySelector('input[name="UpdatesEnabled"]');
  var confirmBox = document.getElementById('confirmEnableBox');
  var confirmHidden = form.querySelector('input[name="ConfirmEnable"]');
  var confirmation = document.getElementById('enableConfirmation');
  var wasEnabled = {was_enabled};
  function syncControls() {{
    emailHidden.value = emailBox.checked ? 'true' : 'false';
    updatesHidden.value = updatesBox.checked ? 'true' : 'false';
    var needed = !wasEnabled && updatesBox.checked;
    confirmation.style.display = needed ? 'block' : 'none';
    confirmHidden.value = needed && confirmBox.checked ? 'true' : 'false';
  }}
  emailBox.addEventListener('change',syncControls);
  updatesBox.addEventListener('change',syncControls);
  confirmBox.addEventListener('change',syncControls); syncControls();
  var applicationPicker = document.getElementById(
    'applicationInvolvementPicker'
  );
  var applicationHidden = applicationPicker.querySelector(
    'input[name="VolunteerApplicationInvolvementId"]'
  );
  var applicationSearch = document.getElementById(
    'applicationInvolvementSearch'
  );
  var applicationResults = document.getElementById(
    'applicationInvolvementResults'
  );
  var applicationSelection = document.getElementById(
    'applicationInvolvementSelection'
  );
  var selectedInvolvement = {configured_involvement_json};
  var involvementTimer = null;
  var knownPeople = {configured_people_json};
  function esc(s) {{return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}}
  function idsFrom(input) {{return (input.value||'').split(',').map(function(x) {{return parseInt(x,10);}}).filter(function(x,i,a) {{return x>0&&a.indexOf(x)===i;}});}}
  function renderInvolvementSelection() {{
    applicationSelection.innerHTML = '';
    if (!selectedInvolvement) return;
    var chip = document.createElement('span');
    chip.className = 'vsu-chip';
    chip.innerHTML = '<span>' + esc(selectedInvolvement.label) +
      ' <small>(ID ' + selectedInvolvement.id + ')</small></span>' +
      '<button type="button" title="Clear">&times;</button>';
    chip.querySelector('button').addEventListener('click', function() {{
      selectedInvolvement = null;
      applicationHidden.value = '0';
      renderInvolvementSelection();
    }});
    applicationSelection.appendChild(chip);
  }}
  function chooseInvolvement(item) {{
    selectedInvolvement = item;
    applicationHidden.value = String(item.id);
    applicationSearch.value = '';
    applicationResults.style.display = 'none';
    renderInvolvementSelection();
  }}
  function showInvolvementResults(items) {{
    applicationResults.innerHTML = '';
    if (!items.length) {{
      applicationResults.innerHTML =
        '<div class="vsu-person-result">No active Involvements found</div>';
    }} else {{
      items.forEach(function(item) {{
        var row = document.createElement('div');
        row.className = 'vsu-person-result';
        row.innerHTML = '<strong>' + esc(item.label) + '</strong>' +
          '<small>Organization ID ' + item.id + '</small>';
        row.addEventListener('click', function() {{
          chooseInvolvement(item);
        }});
        applicationResults.appendChild(row);
      }});
    }}
    applicationResults.style.display = 'block';
  }}
  applicationSearch.addEventListener('input', function() {{
    clearTimeout(involvementTimer);
    var term = applicationSearch.value.trim();
    if (term.length < 2 && !/^\\d+$/.test(term)) {{
      applicationResults.style.display = 'none';
      return;
    }}
    involvementTimer = setTimeout(function() {{
      requestLookup(
        'VSUAdminAction=search_involvements&term=' + encodeURIComponent(term)
      )
        .then(function(data) {{
          showInvolvementResults(data.involvements || []);
        }}).catch(function(error) {{
          applicationResults.innerHTML = '<div class="vsu-person-result">' +
            lookupFailureMarkup(error) + '</div>';
          applicationResults.style.display = 'block';
        }});
    }}, 250);
  }});
  document.addEventListener('click', function(event) {{
    if (!applicationPicker.contains(event.target)) {{
      applicationResults.style.display = 'none';
    }}
  }});
  renderInvolvementSelection();
  function setupPicker(root) {{
    var hidden=root.querySelector('input[type="hidden"]'), search=root.querySelector('.vsu-person-search'), results=root.querySelector('.vsu-person-results'), chips=root.querySelector('.vsu-chips'), single=root.getAttribute('data-picker')==='single', timer=null;
    function render() {{chips.innerHTML=''; idsFrom(hidden).forEach(function(id) {{var person=knownPeople[String(id)]||{{id:id,name:'People ID '+id,email:''}}, chip=document.createElement('span'); chip.className='vsu-chip'; chip.innerHTML='<span>'+esc(person.name)+' <small>(PID '+id+')</small></span><button type="button" title="Remove">&times;</button>'; chip.querySelector('button').addEventListener('click',function() {{hidden.value=idsFrom(hidden).filter(function(x) {{return x!==id;}}).join(',');render();}});chips.appendChild(chip);}});}}
    function choose(person) {{knownPeople[String(person.id)]=person;var ids=idsFrom(hidden);if(single)ids=[person.id];else if(ids.indexOf(person.id)<0)ids.push(person.id);hidden.value=ids.join(',');if(root.getAttribute('data-fill-sender')==='true'){{form.querySelector('input[name="FromName"]').value=person.name||'';if(person.email)form.querySelector('input[name="FromAddress"]').value=person.email;}}search.value='';results.style.display='none';render();}}
    function show(people) {{results.innerHTML='';if(!people.length)results.innerHTML='<div class="vsu-person-result">No people found</div>';else people.forEach(function(person) {{var row=document.createElement('div');row.className='vsu-person-result';row.innerHTML='<strong>'+esc(person.name)+'</strong><small>PID '+person.id+(person.email?' &middot; '+esc(person.email):'')+'</small>';row.addEventListener('click',function() {{choose(person);}});results.appendChild(row);}});results.style.display='block';}}
    search.addEventListener('input',function() {{clearTimeout(timer);var term=search.value.trim();if(term.length<2&&!/^\\d+$/.test(term)){{results.style.display='none';return;}}timer=setTimeout(function() {{requestLookup('VSUAdminAction=search_people&term='+encodeURIComponent(term)).then(function(data){{show(data.people||[]);}}).catch(function(error){{results.innerHTML='<div class="vsu-person-result">'+lookupFailureMarkup(error)+'</div>';results.style.display='block';}});}},250);}});
    document.addEventListener('click',function(event){{if(!root.contains(event.target))results.style.display='none';}});render();
  }}
  Array.prototype.forEach.call(
    document.querySelectorAll('.vsu-person-picker[data-picker]'), setupPicker
  );
}}
initializeVolunteerStatusUpdaterAdmin();
</script>
""".format(
    version=APP_VERSION,
    message=message,
    toast=toast,
    suggestion_notice=suggestion_notice,
    readiness_html=readiness_html,
    application_involvement_id=escape(
        current("VolunteerApplicationInvolvementId")
    ),
    configured_involvement_json=configured_involvement_json,
    valid_months=escape(current("BackgroundCheckValidMonths")),
    minimum_age=escape(current("MinimumBackgroundCheckAge")),
    training_type=escape(current("TrainingReportTypeId")),
    background_service_codes=escape(
        current("BackgroundCheckServiceCodes")
    ),
    mvr_service_codes=escape(current("MVRServiceCodes")),
    mvr_valid_months=escape(current("MVRCheckValidMonths")),
    queued_by=escape(current("QueuedByPeopleId")),
    from_name=escape(current("FromName")),
    from_address=escape(current("FromAddress")),
    recipients=escape(current("RecipientPeopleIds")),
    updates_value="true" if updates_enabled else "false",
    updates_checked=" checked" if updates_enabled else "",
    email_value="true" if email_enabled else "false",
    email_checked=" checked" if email_enabled else "",
    was_enabled=(
        "true" if configuration_saved() and updates_enabled else "false"
    ),
    configured_people_json=configured_people_json,
    state_html=state_html,
)

if lookup_response is not None:
    print(lookup_response)
else:
    model.Form = html
    if is_post:
        print(html)
