#Roles=Admin

# Background Check Evaluator Admin
# Version: 3.1.2
# 2026-08-18 3.1.2 - Replaced tenant-specific installation defaults with
# safe empty values for public distribution; saved BCE settings still prevail.
# 2026-08-18 3.1.1 - Added a default-off church-wide switch for displaying
# Process Builder reminder steps in evaluator reports and email.
# 2026-08-18 3.1.0 - Documented the two Process Builder reminder statuses
# displayed inline in the evaluator report.
# 2026-08-18 3.0.4 - Kept Admin version aligned with Process Builder
# diagnostic discovery.
# 2026-08-18 3.0.3 - Show only evaluate-through dates that have not expired.
# 2026-08-18 3.0.2 - Kept Admin version aligned with report presentation.
# 2026-08-18 3.0.1 - List only Involvements with a populated
# EvaluateBackgroundCheckThroughDate DateValue; blank EVs are meeting-based.
# 2026-08-18 3.0.0 - Replaced editable program-year dates with a read-only
# display of each Involvement's EvaluateBackgroundCheckThroughDate EV.
# 2026-08-17 2.0.3 - Replaced the reserved generic action form field with
# BCEAdminAction and surfaced HTTP status for failed in-frame requests.
# 2026-08-17 2.0.2 - Reset comparison history with a valid versioned state
# document because TouchPoint does not reliably persist empty Text Content.
# 2026-08-17 2.0.1 - Clarified the exact tenant-confirmed AppStatus EV fields.
# 2026-08-17 2.0.0 - Removed all deprecated Volunteer Code configuration;
# volunteer eligibility is now evaluated exclusively from People EVs.
# 2026-08-17 1.2.4 - Added the standard alert-success and alert-danger
# semantics to Admin toasts and simplified successful-save text to Saved.
# 2026-08-17 1.2.3 - Kept saves and comparison-history actions inside the
# TouchPoint frame by replacing only the Admin app container in place.
# 2026-08-17 1.2.2 - Matched the established TouchPoint bottom-center toast
# presentation, accessibility markup, dismissal, and timing.
# 2026-08-17 1.2.1 - Restored the Admin page after form posts so successful
# saves display the standard bottom Saved toast; clarified EV precedence.
# 2026-08-17 1.2.0 - Added End of Program Year date configuration for
# flagged Involvements and partial-run operational guidance.
# 2026-08-16 1.1.0 - Added Extra Value migration controls and legacy
# Volunteer Code transition mode.
# 2026-07-28 1.0.0 - Added church-wide configuration and comparison controls.
# Written by: Brian Bullock with Codex assistance
# Email: bbbullock@mac.com
# GitHub: https://github.com/bbbullock/TouchPoint

"""
Church-wide configuration UI for BackgroundCheckEvaluator.

Install as a TouchPoint Python Script named BackgroundCheckEvaluatorAdmin.
Only users with the Admin role may view or change these settings.
"""

import cgi
import datetime
import json


# TouchPoint's Setting.Id column is nvarchar(50). Keep the namespace short.
# Do not lengthen individual setting names without checking the combined size.
SETTING_PREFIX = "BCE."
APP_VERSION = "3.1.2"
STATE_CONTENT_NAME = "BackgroundCheckEvaluatorState"
EVALUATE_THROUGH_DATE_EV_FIELD = "EvaluateBackgroundCheckThroughDate"
EVALUATOR_SCRIPT_NAME = "BackgroundCheckEvaluator"

DEFAULTS = {
    "EmailEnabled": "false",
    "ShowProcessReminderSteps": "false",
    "QueuedByPeopleId": "0",
    "ReportRecipientPeopleIds": "",
    "FailureRecipientPeopleIds": "",
    "FromAddress": "",
    "FromName": "",
    "ProgramId": "0",
    "DivisionId": "0",
    "LookaheadDays": "30",
    "BackgroundCheckValidMonths": "33",
    "MinimumBackgroundCheckAge": "18",
    "TrainingReportTypeId": "0",
}

for setting_name in DEFAULTS:
    if len(SETTING_PREFIX + setting_name) > 50:
        raise ValueError(
            "TouchPoint setting key exceeds 50 characters: {0}".format(
                SETTING_PREFIX + setting_name
            )
        )

model.Header = "Background Check Evaluator Configuration"
model.Transactional = True


def escape(value):
    return cgi.escape(str(value if value is not None else ""), True)


def current(name):
    return str(
        model.Setting(
            SETTING_PREFIX + name,
            DEFAULTS[name],
        )
        or DEFAULTS[name]
    )


def posted(name, default=""):
    try:
        value = getattr(Data, name)
        return str(value if value is not None else default).strip()
    except Exception:
        return default


def was_posted(name):
    try:
        getattr(Data, name)
        return True
    except Exception:
        return False


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


def person_json(row):
    return (
        '{"id":%s,"name":%s,"email":%s}'
        % (
            int(row.PeopleId),
            json_escape(row.Name2 or row.Name or ""),
            json_escape(row.EmailAddress or ""),
        )
    )


def normalize_id_list(raw):
    values = []
    if isinstance(raw, (list, tuple)):
        parts = raw
    else:
        parts = str(raw or "").split(",")
    for part in parts:
        part = str(part)
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


def load_comparison_state_summary():
    raw = str(model.TextContent(STATE_CONTENT_NAME) or "").strip()
    if not raw:
        return False, "", 0, False

    if raw.startswith("{"):
        try:
            state = json.loads(raw)
            if bool(state.get("reset", False)):
                return False, "", 0, False
            people_ids = []
            if int(state.get("version", 0) or 0) >= 3:
                people_ids.extend(state.get("legacy_people_ids", []))
                for item in state.get("involvements", {}).values():
                    people_ids.extend(item.get("exception_people_ids", []))
            else:
                people_ids.extend(state.get("people_ids", []))
            return (
                True,
                str(state.get("updated", "") or ""),
                len(normalize_id_list(people_ids)),
                bool(state.get("incomplete", False)),
            )
        except Exception:
            return False, "", 0, False

    # Backward compatibility for the original line-based state document.
    values = {}
    for line in raw.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip().lower()] = value.strip()

    people_ids = normalize_id_list(values.get("people", ""))
    return True, values.get("updated", ""), len(people_ids), False


def load_flagged_involvements(program_id, division_id):
    return list(
        q.QuerySql(
            """
            SELECT
                o.OrganizationId,
                o.OrganizationName AS Involvement,
                ev.EvaluateThroughDate,
                ev.ExtraValueType
            FROM dbo.Organizations o
            JOIN dbo.Division d ON d.Id = o.DivisionId
            CROSS APPLY (
                SELECT
                    MAX(oe.DateValue) AS EvaluateThroughDate,
                    MAX(oe.Type) AS ExtraValueType
                FROM dbo.OrganizationExtra oe
                WHERE oe.OrganizationId = o.OrganizationId
                  AND oe.Field = @EvaluateThroughDateEVField
                HAVING MAX(oe.DateValue) >= CAST(GETDATE() AS date)
            ) ev
            WHERE d.ProgId = @ProgramId
              AND d.Id = @DivisionId
              AND o.OrganizationStatusId = 30
            ORDER BY o.OrganizationName, o.OrganizationId
            """,
            {
                "ProgramId": int(program_id),
                "DivisionId": int(division_id),
                "EvaluateThroughDateEVField": EVALUATE_THROUGH_DATE_EV_FIELD,
            },
        )
    )


def handle_people_search():
    term = posted("term")
    exact_id = 0
    try:
        exact_id = int(term)
    except Exception:
        exact_id = 0

    if len(term) < 2 and exact_id == 0:
        print('{"success":true,"people":[]}')
        raise SystemExit()

    rows = list(
        q.QuerySql(
            """
            SELECT TOP 12
                PeopleId,
                Name,
                Name2,
                EmailAddress
            FROM dbo.People
            WHERE PeopleId = @ExactPeopleId
               OR (
                    (Name LIKE @LikeTerm
                     OR Name2 LIKE @LikeTerm
                     OR EmailAddress LIKE @LikeTerm)
                    AND ISNULL(IsDeceased, 0) = 0
                    AND ISNULL(ArchivedFlag, 0) = 0
               )
            ORDER BY
                CASE WHEN PeopleId = @ExactPeopleId THEN 0 ELSE 1 END,
                Name2
            """,
            {
                "ExactPeopleId": exact_id,
                "LikeTerm": "%" + term + "%",
            },
        )
    )
    print(
        '{"success":true,"people":[%s]}'
        % ",".join(person_json(row) for row in rows)
    )
    raise SystemExit()


def require_int(name, minimum, maximum):
    raw = posted(name)
    try:
        value = int(raw)
    except Exception:
        raise ValueError("{0} must be a whole number.".format(name))
    if value < minimum or value > maximum:
        raise ValueError(
            "{0} must be between {1} and {2}.".format(
                name, minimum, maximum
            )
        )
    return str(value)


def require_people_ids(name):
    raw = posted(name)
    ids = []
    for part in raw.split(","):
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
            raise ValueError(
                "{0} contains an invalid People ID.".format(name)
            )
        ids.append(str(value))
    if not ids:
        raise ValueError("{0} requires at least one People ID.".format(name))
    return ",".join(ids)


def validate_lookup_id(table_name, value):
    sql = "SELECT COUNT(*) FROM {0} WHERE Id = {1}".format(
        table_name, int(value)
    )
    if q.QuerySqlInt(sql) != 1:
        raise ValueError(
            "ID {0} was not found in {1}.".format(value, table_name)
        )


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
    values = {}
    values["EmailEnabled"] = (
        "true" if posted("EmailEnabled").lower() == "true" else "false"
    )
    values["ShowProcessReminderSteps"] = (
        "true"
        if posted("ShowProcessReminderSteps").lower() == "true"
        else "false"
    )
    values["QueuedByPeopleId"] = require_int(
        "QueuedByPeopleId", 1, 2147483647
    )
    values["ReportRecipientPeopleIds"] = require_people_ids(
        "ReportRecipientPeopleIds"
    )
    values["FailureRecipientPeopleIds"] = require_people_ids(
        "FailureRecipientPeopleIds"
    )

    values["FromAddress"] = posted("FromAddress")
    values["FromName"] = posted("FromName")
    if "@" not in values["FromAddress"]:
        raise ValueError("FromAddress must be a valid email address.")
    if not values["FromName"]:
        raise ValueError("FromName is required.")

    values["ProgramId"] = require_int("ProgramId", 1, 2147483647)
    values["DivisionId"] = require_int("DivisionId", 1, 2147483647)
    values["LookaheadDays"] = require_int("LookaheadDays", 1, 365)
    values["BackgroundCheckValidMonths"] = require_int(
        "BackgroundCheckValidMonths", 1, 120
    )
    values["MinimumBackgroundCheckAge"] = require_int(
        "MinimumBackgroundCheckAge", 0, 100
    )
    values["TrainingReportTypeId"] = require_int(
        "TrainingReportTypeId", 0, 100
    )

    hierarchy_count = q.QuerySqlInt(
        """
        SELECT COUNT(*)
        FROM dbo.Division d
        WHERE d.Id = {0}
          AND d.ProgId = {1}
        """.format(values["DivisionId"], values["ProgramId"])
    )
    if hierarchy_count != 1:
        raise ValueError(
            "The selected Division does not belong to the selected Program."
        )

    validate_person(values["QueuedByPeopleId"], "Queued-by")

    all_recipient_ids = set(
        values["ReportRecipientPeopleIds"].split(",")
        + values["FailureRecipientPeopleIds"].split(",")
    )
    for people_id in all_recipient_ids:
        validate_person(people_id, "Recipient")

    for name, value in values.items():
        model.SetSetting(SETTING_PREFIX + name, value)


def select_options(rows, value_field, label_builder, selected):
    options = []
    for row in rows:
        value = str(getattr(row, value_field))
        options.append(
            '<option value="{0}"{1}>{2}</option>'.format(
                escape(value),
                " selected" if value == str(selected) else "",
                escape(label_builder(row)),
            )
        )
    return "".join(options)


is_post = str(getattr(model, "HttpMethod", "")).lower() == "post"
action = posted("BCEAdminAction").lower()
if is_post and action == "search_people":
    handle_people_search()

message = ""
toast = ""
if is_post and action == "initialize_baseline":
    try:
        Data.BCEAction = "initialize_baseline"
        result = model.CallScript(EVALUATOR_SCRIPT_NAME)
        message = (
            '<div class="alert alert-success"><strong>Baseline initialized.'
            "</strong> The current evaluator results are now the comparison "
            "baseline. No report email was sent.</div>{0}".format(result or "")
        )
    except Exception as exc:
        message = (
            '<div class="alert alert-danger"><strong>Baseline not '
            "initialized:</strong> {0}</div>".format(escape(exc))
        )
    finally:
        try:
            Data.BCEAction = ""
        except Exception:
            pass
elif is_post and action == "reset_history":
    try:
        reset_state = {
            "version": 3,
            "updated": datetime.datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "incomplete": False,
            "failed_involvement_ids": [],
            "legacy_people_ids": [],
            "involvements": {},
            "reset": True,
        }
        model.WriteContentText(
            STATE_CONTENT_NAME,
            json.dumps(reset_state, sort_keys=True),
            "",
        )
        message = (
            '<div class="alert alert-success"><strong>Comparison history '
            "reset.</strong> The next successful production run will show all "
            "current exceptions as new.</div>"
        )
    except Exception as exc:
        message = (
            '<div class="alert alert-danger"><strong>History not reset:'
            "</strong> {0}</div>".format(escape(exc))
        )
elif is_post:
    try:
        save_configuration()
        toast = (
            '<div class="bce-toast alert-success" id="bceToast" '
            'role="status" aria-live="polite" aria-atomic="true">'
            "<span><strong>Saved</strong></span>"
            '<button type="button" class="bce-toast-close" '
            'id="bceToastClose" aria-label="Dismiss notification">'
            "&times;</button></div>"
        )
    except Exception as exc:
        message = (
            '<div class="alert alert-danger"><strong>Not saved:</strong> '
            "{0}</div>".format(escape(exc))
        )
        toast = (
            '<div class="bce-toast bce-toast-error alert-danger" '
            'id="bceToast" '
            'role="alert" aria-live="assertive" aria-atomic="true"><span>'
            "Configuration was not saved. Correct the displayed problem and "
            "try again.</span>"
            '<button type="button" class="bce-toast-close" '
            'id="bceToastClose" aria-label="Dismiss notification">'
            "&times;</button></div>"
        )


programs = list(
    q.QuerySql(
        """
        SELECT Id, Name
        FROM dbo.Program
        ORDER BY Name
        """
    )
)
divisions = list(
    q.QuerySql(
        """
        SELECT d.Id, d.Name, d.ProgId, p.Name AS ProgramName
        FROM dbo.Division d
        JOIN dbo.Program p ON p.Id = d.ProgId
        ORDER BY p.Name, d.Name
        """
    )
)
program_options = select_options(
    programs, "Id", lambda row: row.Name, current("ProgramId")
)
division_options = select_options(
    divisions,
    "Id",
    lambda row: "{0} : {1}".format(row.ProgramName, row.Name),
    current("DivisionId"),
)


try:
    through_date_involvements = load_flagged_involvements(
        current("ProgramId"), current("DivisionId")
    )
except Exception as exc:
    through_date_involvements = []
    message += (
        '<div class="alert alert-danger"><strong>Evaluate-through dates '
        "could not be loaded:</strong> {0}</div>".format(
            escape(exc)
        )
    )

through_date_rows = []
for involvement in through_date_involvements:
    organization_id = int(involvement.OrganizationId)
    through_date = involvement.EvaluateThroughDate
    try:
        display_date = through_date.ToString("MM/dd/yyyy")
    except Exception:
        display_date = through_date.strftime("%m/%d/%Y")
    organization_url = "{0}/Org/{1}".format(model.CmsHost, organization_id)
    through_date_rows.append(
        """
        <tr>
          <td><a href="{url}">{name}</a><br>
            <small>Organization ID {organization_id}</small></td>
          <td>{date}</td>
          <td>{ev_type}</td>
          <td>{status}</td>
        </tr>
        """.format(
            url=escape(organization_url),
            name=escape(involvement.Involvement),
            organization_id=organization_id,
            date=escape(display_date or "Missing"),
            ev_type=escape(involvement.ExtraValueType or "Unknown"),
            status=(
                '<span class="text-success"><strong>Configured</strong></span>'
                if display_date else ""
            ),
        )
    )

if through_date_rows:
    through_date_table = """
    <table class="table table-striped table-bordered">
      <thead><tr><th>Involvement</th><th>Evaluate through</th>
        <th>EV type</th><th>Status</th></tr></thead>
      <tbody>{0}</tbody>
    </table>
    """.format("".join(through_date_rows))
else:
    through_date_table = (
        '<div class="alert alert-info">No active Involvements in the selected '
        "Program and Division currently have the <code>{0}</code> Extra "
        "Value.</div>".format(
            escape(EVALUATE_THROUGH_DATE_EV_FIELD)
        )
    )

through_date_warning = ""


email_enabled = current("EmailEnabled").lower() == "true"
show_process_reminder_steps = (
    current("ShowProcessReminderSteps").lower() == "true"
)
state_exists, state_updated, state_people_count, state_incomplete = (
    load_comparison_state_summary()
)
if state_exists:
    state_summary = (
        "<strong>Baseline saved:</strong> {0} &mdash; {1} volunteer(s) in "
        "the saved comparison state.{2}"
    ).format(
        escape(state_updated or "timestamp unavailable"),
        state_people_count,
        (
            " <strong>The most recent production run was partial.</strong>"
            if state_incomplete
            else ""
        ),
    )
else:
    state_summary = (
        "<strong>No comparison baseline is saved.</strong> Until one is "
        "initialized, all current exceptions will appear as new."
    )

configured_people_ids = normalize_id_list(
    ",".join(
        [
            current("QueuedByPeopleId"),
            current("ReportRecipientPeopleIds"),
            current("FailureRecipientPeopleIds"),
        ]
    )
)
configured_people = load_people(configured_people_ids)
configured_people_json = (
    "{"
    + ",".join(
        json_escape(str(row.PeopleId)) + ":" + person_json(row)
        for row in configured_people
    )
    + "}"
)

html = """
<style>
.bce-wrap {{
  max-width: 1180px; margin:0 auto;
  font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;
}}
.bce-title {{ font-weight:300; margin-bottom:4px; }}
.bce-version {{ color:#667; margin-bottom:18px; }}
.bce-card {{
  border: 1px solid #d9dfe5; border-radius: 5px; padding: 18px;
  margin-bottom: 18px; background: #fff;
}}
.bce-grid {{
  display: grid; grid-template-columns: repeat(2, minmax(260px, 1fr));
  gap: 16px 22px;
}}
.bce-field label {{ display:block; font-weight:600; margin-bottom:5px; }}
.bce-field input, .bce-field select {{
  width:100%; min-height:38px; padding:7px 9px; border:1px solid #b8c2cc;
  border-radius:4px;
}}
.bce-help {{ color:#667; font-size:12px; margin-top:4px; }}
.bce-danger {{ border-left:5px solid #d9534f; }}
.bce-person-picker {{ position:relative; }}
.bce-person-results {{
  display:none; position:absolute; z-index:1000; left:0; right:0;
  max-height:260px; overflow:auto; background:#fff; border:1px solid #aeb8c2;
  border-radius:4px; box-shadow:0 5px 15px rgba(0,0,0,.18);
}}
.bce-person-result {{ padding:9px 11px; cursor:pointer; border-bottom:1px solid #eee; }}
.bce-person-result:hover {{ background:#eef6fc; }}
.bce-person-result small {{ display:block; color:#667; }}
.bce-chips {{ display:flex; flex-wrap:wrap; gap:6px; margin:7px 0; }}
.bce-chip {{
  display:inline-flex; align-items:center; gap:7px; padding:5px 8px;
  background:#eaf3f9; border:1px solid #b8d5e6; border-radius:16px;
}}
.bce-chip button {{ border:0; background:transparent; color:#a33; padding:0; }}
.bce-toast {{
  position:fixed; left:50%; bottom:24px; transform:translateX(-50%);
  z-index:2000; display:flex; align-items:center; gap:18px;
  min-width:280px; max-width:calc(100% - 32px); margin:0;
  padding:12px 16px; background:#287a45; border:1px solid #1f6237;
  border-radius:6px; box-shadow:0 4px 14px rgba(0,0,0,.24); color:#fff;
}}
.bce-toast-error {{ background:#b42318; border-color:#8f1c13; }}
.bce-toast-close {{
  border:0; background:transparent; color:#fff; font-size:1.4em;
  line-height:1; padding:0; cursor:pointer;
}}
@media (max-width: 760px) {{ .bce-grid {{ grid-template-columns:1fr; }} }}
</style>
<div class="bce-wrap">
<h1 class="bce-title">Background Check Evaluator Configuration</h1>
<div class="bce-version">Version {app_version}</div>
{message}
{toast}
<div class="alert alert-info">
  These are church-wide settings. Changes affect the next manual or Morning
  Batch run. Saving settings does not evaluate volunteers or send email.
</div>
<form id="bceConfigForm" method="post" target="_self">
  <input type="hidden" name="EmailEnabled" value="{email_value}">
  <input type="hidden" name="ShowProcessReminderSteps"
    value="{process_steps_value}">

  <div class="bce-card">
    <h2>Evaluation scope</h2>
    <div class="bce-grid">
      <div class="bce-field"><label>Program</label>
        <select name="ProgramId">{program_options}</select></div>
      <div class="bce-field"><label>Division</label>
        <select name="DivisionId">{division_options}</select></div>
      <div class="bce-field"><label>Lookahead days</label>
        <input name="LookaheadDays" type="number" min="1" max="365"
          value="{lookahead}"></div>
      <div class="bce-field"><label>Background check valid months</label>
        <input name="BackgroundCheckValidMonths" type="number" min="1" max="120"
          value="{valid_months}"></div>
      <div class="bce-field"><label>Minimum background-check age</label>
        <input name="MinimumBackgroundCheckAge" type="number" min="0" max="100"
          value="{minimum_age}">
        <div class="bce-help">
          The requirement begins on the first nightly run on or after the
          person's 18th birthday. Future birthdays are not anticipated.
        </div>
      </div>
      <div class="bce-field"><label>Training Report Type ID</label>
        <input name="TrainingReportTypeId" type="number" min="0" max="100"
          value="{training_type}">
        <div class="bce-help">This type is excluded from background checks.</div>
      </div>
    </div>
  </div>

  <div class="bce-card">
    <h2>Involvement evaluate-through dates</h2>
    <p>
      Only active Involvements with a populated
      <code>{evaluate_through_date_ev_field}</code> date appear here and are
      evaluated through that date, inclusive, even without an upcoming
      meeting. Blank or expired dates are ignored. An Involvement with future
      meetings then uses its latest meeting in the lookahead window; one with
      no future meetings drops from the evaluation. Change the date on the
      Involvement's Extra Values tab.
    </p>
    {through_date_warning}
    {through_date_table}
  </div>

  <div class="bce-card">
    <h2>Volunteer eligibility records</h2>
    <p>The evaluator uses only these People Extra Values:</p>
    <ul>
      <li><strong>AppStatus:Application Approved</strong> and
        <strong>AppStatus:Application on File</strong> &mdash; both are
        required.</li>
      <li><strong>College Student (no background check)</strong> &mdash;
        must not be selected.</li>
      <li><strong>Individual Refuses Background Check</strong> &mdash;
        must not be selected.</li>
    </ul>
    <label>
      <input id="processStepsBox" type="checkbox"{process_steps_checked}>
      Show Process Builder reminder steps in reports and email
    </label>
    <div class="bce-help">
      Leave disabled during testing to omit reminder-process information from
      the evaluator report and nightly email. When enabled, the current
      background-check and volunteer-application reminder steps appear beneath
      their related evaluation results.
    </div>
    <div class="help-block">
      Legacy Volunteer Codes are deprecated and are not read by the evaluator.
    </div>
  </div>

  <div class="bce-card">
    <h2>Email delivery</h2>
    <div class="alert alert-info">
      Every report recipient receives a nightly report showing all included
      Involvements, evaluation status, listed volunteer names, assignments,
      exception reasons, and recoverable processing errors. Missing program
      year dates also trigger the separate failure notification.
    </div>
    <div class="bce-grid">
      <div class="bce-field"><label>Sender / email coordinator</label>
        <div class="bce-person-picker" data-picker="single"
          data-target="QueuedByPeopleId" data-fill-sender="true">
          <input type="hidden" name="QueuedByPeopleId" value="{queued_by}">
          <div class="bce-chips"></div>
          <input class="bce-person-search" autocomplete="off"
            placeholder="Search by name, email, or People ID">
          <div class="bce-person-results"></div>
        </div>
      </div>
      <div class="bce-field"><label>From name</label>
        <input name="FromName" value="{from_name}"></div>
      <div class="bce-field"><label>From address</label>
        <input name="FromAddress" type="email" value="{from_address}"></div>
      <div class="bce-field"><label>Report recipients</label>
        <div class="bce-person-picker" data-picker="multi"
          data-target="ReportRecipientPeopleIds">
          <input type="hidden" name="ReportRecipientPeopleIds"
            value="{report_recipients}">
          <div class="bce-chips"></div>
          <input class="bce-person-search" autocomplete="off"
            placeholder="Search and add people">
          <div class="bce-person-results"></div>
        </div>
      </div>
      <div class="bce-field"><label>Failure recipients</label>
        <div class="bce-person-picker" data-picker="multi"
          data-target="FailureRecipientPeopleIds">
          <input type="hidden" name="FailureRecipientPeopleIds"
            value="{failure_recipients}">
          <div class="bce-chips"></div>
          <input class="bce-person-search" autocomplete="off"
            placeholder="Search and add people">
          <div class="bce-person-results"></div>
        </div>
      </div>
    </div>
  </div>

  <div class="bce-card bce-danger">
    <h2>Email activation</h2>
    <label>
      <input id="emailEnabledBox" type="checkbox"{email_checked}>
      Enable nightly evaluation and failure email
    </label>
    <div class="bce-help">
      Leave disabled until the evaluator preview has been manually verified.
    </div>
  </div>

  <button type="submit" class="btn btn-primary">
    Save church-wide configuration
  </button>
  <noscript><div class="alert alert-danger" style="margin-top:12px;">
    JavaScript is required to save without leaving the TouchPoint page.
  </div></noscript>
</form>

<div class="bce-card" style="margin-top:18px;">
  <h2>Nightly comparison history</h2>
  <p>{state_summary}</p>
  <p class="bce-help">
    History is stored by Involvement. Partial production runs update completed
    Involvements and retain prior history for failed Involvements. Preview mode
    never changes history.
  </p>
  <form class="bceActionForm" method="post" style="display:inline-block;">
    <input type="hidden" name="BCEAdminAction"
      value="initialize_baseline">
    <button type="submit" class="btn btn-default"
      onclick="return confirm('Use the evaluator results right now as the baseline? No report email will be sent.');">
      Initialize current results as baseline
    </button>
  </form>
  <form class="bceActionForm" method="post"
    style="display:inline-block;margin-left:8px;">
    <input type="hidden" name="BCEAdminAction" value="reset_history">
    <button type="submit" class="btn btn-danger"
      onclick="return confirm('Reset comparison history? The next successful production run will show every current exception as new.');">
      Reset comparison history
    </button>
  </form>
</div>
</div>
<script>
function initializeBackgroundCheckEvaluator() {{
  var form = document.getElementById('bceConfigForm');
  if (!form) return;
  form.action = window.location.pathname.replace('/PyScript/', '/PyScriptForm/');
  Array.prototype.forEach.call(
    document.querySelectorAll('.bceActionForm'),
    function(actionForm) {{ actionForm.action = form.action; }}
  );
  var lookupUrl = form.action;
  var toast = document.getElementById('bceToast');
  if (toast) {{
    var toastClose = document.getElementById('bceToastClose');
    var dismissToast = function() {{
      if (toast && toast.parentNode) toast.parentNode.removeChild(toast);
    }};
    if (toastClose) toastClose.addEventListener('click', dismissToast);
    if (toast.className.indexOf('bce-toast-error') < 0) {{
      window.setTimeout(dismissToast, 5000);
    }}
  }}
  function showInFrameError(message) {{
    var old = document.getElementById('bceActionError');
    if (old && old.parentNode) old.parentNode.removeChild(old);
    var error = document.createElement('div');
    error.id = 'bceActionError';
    error.className = 'alert alert-danger';
    error.setAttribute('role', 'alert');
    error.textContent = message;
    form.parentNode.insertBefore(error, form);
    form.removeAttribute('aria-busy');
  }}
  function replaceAdmin(markup) {{
    var holder = document.createElement('div');
    holder.innerHTML = markup;
    var next = holder.querySelector('.bce-wrap');
    var current = document.querySelector('.bce-wrap');
    if (!next || !current) throw new Error('Admin response was incomplete');
    current.innerHTML = next.innerHTML;
    initializeBackgroundCheckEvaluator();
    current.scrollIntoView({{block:'start'}});
  }}
  function postInPlace(sourceForm, errorMessage) {{
    var fields = new FormData(sourceForm);
    var body = new URLSearchParams();
    fields.forEach(function(value, key) {{ body.append(key, value); }});
    form.setAttribute('aria-busy', 'true');
    return fetch(sourceForm.action, {{
      method:'POST',
      credentials:'same-origin',
      headers:{{
        'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With':'XMLHttpRequest'
      }},
      body:body.toString()
    }}).then(function(response) {{
      if (!response.ok) {{
        throw new Error(errorMessage + ' HTTP status: ' + response.status + '.');
      }}
      return response.text();
    }}).then(replaceAdmin).catch(function(error) {{
      var detail = error && error.message ? ' ' + error.message : '';
      showInFrameError(errorMessage + detail);
    }});
  }}
  form.addEventListener('submit', function(event) {{
    event.preventDefault();
    if (!form.reportValidity()) return;
    postInPlace(form, 'The configuration could not be saved. Please try again.');
  }});
  Array.prototype.forEach.call(
    document.querySelectorAll('.bceActionForm'),
    function(actionForm) {{
      actionForm.addEventListener('submit', function(event) {{
        event.preventDefault();
        postInPlace(
          actionForm,
          'The comparison-history action could not be completed. Please try again.'
        );
      }});
    }}
  );
  var knownPeople = {configured_people_json};
  var box = document.getElementById('emailEnabledBox');
  var hidden = document.querySelector('input[name="EmailEnabled"]');
  function sync() {{ hidden.value = box.checked ? 'true' : 'false'; }}
  box.addEventListener('change', sync);
  sync();
  var processStepsBox = document.getElementById('processStepsBox');
  var processStepsHidden = document.querySelector(
    'input[name="ShowProcessReminderSteps"]'
  );
  function syncProcessSteps() {{
    processStepsHidden.value = processStepsBox.checked ? 'true' : 'false';
  }}
  processStepsBox.addEventListener('change', syncProcessSteps);
  syncProcessSteps();

  function esc(s) {{
    return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }}

  function idsFrom(input) {{
    return (input.value || '').split(',').map(function(x) {{
      return parseInt(x, 10);
    }}).filter(function(x, i, a) {{ return x > 0 && a.indexOf(x) === i; }});
  }}

  function setupPicker(root) {{
    var hiddenInput = root.querySelector('input[type="hidden"]');
    var search = root.querySelector('.bce-person-search');
    var results = root.querySelector('.bce-person-results');
    var chips = root.querySelector('.bce-chips');
    var isSingle = root.getAttribute('data-picker') === 'single';
    var timer = null;

    function renderChips() {{
      var ids = idsFrom(hiddenInput);
      chips.innerHTML = '';
      ids.forEach(function(id) {{
        var person = knownPeople[String(id)] || {{
          id:id, name:'People ID ' + id, email:''
        }};
        var chip = document.createElement('span');
        chip.className = 'bce-chip';
        chip.innerHTML = '<span>' + esc(person.name) + ' <small>(PID ' +
          id + ')</small></span><button type="button" title="Remove">&times;</button>';
        chip.querySelector('button').addEventListener('click', function() {{
          hiddenInput.value = idsFrom(hiddenInput).filter(function(x) {{
            return x !== id;
          }}).join(',');
          renderChips();
        }});
        chips.appendChild(chip);
      }});
    }}

    function choose(person) {{
      knownPeople[String(person.id)] = person;
      var ids = idsFrom(hiddenInput);
      if (isSingle) ids = [person.id];
      else if (ids.indexOf(person.id) < 0) ids.push(person.id);
      hiddenInput.value = ids.join(',');
      if (root.getAttribute('data-fill-sender') === 'true') {{
        var fromName = form.querySelector('input[name="FromName"]');
        var fromAddress = form.querySelector('input[name="FromAddress"]');
        if (fromName) fromName.value = person.name || '';
        if (fromAddress && person.email) fromAddress.value = person.email;
      }}
      search.value = '';
      results.style.display = 'none';
      renderChips();
    }}

    function showResults(people) {{
      results.innerHTML = '';
      if (!people.length) {{
        results.innerHTML = '<div class="bce-person-result">No people found</div>';
      }} else {{
        people.forEach(function(person) {{
          var row = document.createElement('div');
          row.className = 'bce-person-result';
          row.innerHTML = '<strong>' + esc(person.name) + '</strong><small>PID ' +
            person.id + (person.email ? ' &middot; ' + esc(person.email) : '') +
            '</small>';
          row.addEventListener('click', function() {{ choose(person); }});
          results.appendChild(row);
        }});
      }}
      results.style.display = 'block';
    }}

    search.addEventListener('input', function() {{
      clearTimeout(timer);
      var term = search.value.trim();
      if (term.length < 2 && !/^\\d+$/.test(term)) {{
        results.style.display = 'none';
        return;
      }}
      timer = setTimeout(function() {{
        var body = 'BCEAdminAction=search_people&term=' +
          encodeURIComponent(term);
        fetch(lookupUrl, {{
          method:'POST',
          headers:{{'Content-Type':'application/x-www-form-urlencoded'}},
          body:body,
          credentials:'same-origin'
        }}).then(function(response) {{ return response.json(); }})
          .then(function(data) {{ showResults(data.people || []); }})
          .catch(function() {{
            results.innerHTML =
              '<div class="bce-person-result">Lookup failed</div>';
            results.style.display = 'block';
          }});
      }}, 250);
    }});

    document.addEventListener('click', function(event) {{
      if (!root.contains(event.target)) results.style.display = 'none';
    }});
    renderChips();
  }}

  Array.prototype.forEach.call(
    document.querySelectorAll('.bce-person-picker'), setupPicker
  );
}}
initializeBackgroundCheckEvaluator();
</script>
""".format(
    message=message,
    toast=toast,
    app_version=APP_VERSION,
    email_value="true" if email_enabled else "false",
    email_checked=" checked" if email_enabled else "",
    process_steps_value=(
        "true" if show_process_reminder_steps else "false"
    ),
    process_steps_checked=(
        " checked" if show_process_reminder_steps else ""
    ),
    program_options=program_options,
    division_options=division_options,
    lookahead=escape(current("LookaheadDays")),
    valid_months=escape(current("BackgroundCheckValidMonths")),
    minimum_age=escape(current("MinimumBackgroundCheckAge")),
    training_type=escape(current("TrainingReportTypeId")),
    queued_by=escape(current("QueuedByPeopleId")),
    from_name=escape(current("FromName")),
    from_address=escape(current("FromAddress")),
    report_recipients=escape(current("ReportRecipientPeopleIds")),
    failure_recipients=escape(current("FailureRecipientPeopleIds")),
    configured_people_json=configured_people_json,
    state_summary=state_summary,
    evaluate_through_date_ev_field=escape(EVALUATE_THROUGH_DATE_EV_FIELD),
    through_date_warning=through_date_warning,
    through_date_table=through_date_table,
)

model.Form = html
if is_post:
    print(html)
