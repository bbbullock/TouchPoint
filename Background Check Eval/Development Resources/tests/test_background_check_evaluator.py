import pathlib
import re
import contextlib
import datetime
import html
import io
import json
import sys
import types
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
INSTALLATION_ROOT = PROJECT_ROOT / "Installation Files"


def read_source(name):
    return (INSTALLATION_ROOT / name).read_text(encoding="utf-8")


class EvaluatorMigrationTests(unittest.TestCase):
    def setUp(self):
        self.evaluator = read_source("BackgroundCheckEvaluator.py")
        self.admin = read_source("BackgroundCheckEvaluatorAdmin.py")
        self.diagnostic = read_source("BackgroundCheckEvalDiagnostic.py")

    def test_deployed_scripts_keep_admin_directive_first(self):
        for name in (
            "BackgroundCheckEvaluator.py",
            "BackgroundCheckEvaluatorAdmin.py",
            "BackgroundCheckEvalDiagnostic.py",
            "VolunteerStatusUpdater.py",
            "VolunteerStatusUpdaterAdmin.py",
        ):
            self.assertEqual(read_source(name).splitlines()[0], "#Roles=Admin")

    def test_component_versions_and_admin_display(self):
        versions = []
        for source in (self.evaluator, self.admin, self.diagnostic):
            match = re.search(r'^APP_VERSION = "([^"]+)"$', source, re.M)
            self.assertIsNotNone(match)
            versions.append(match.group(1))
        self.assertEqual(versions, ["3.3.0", "3.3.0", "3.7.0"])
        self.assertIn("Version {app_version}", self.admin)
        self.assertIn(
            "Each TouchPoint script is independently deployable",
            read_source("README.md"),
        )

    def test_email_defaults_off_and_legacy_codes_are_removed(self):
        self.assertIn('"EmailEnabled": "false"', self.admin)
        self.assertIn('"ShowProcessReminderSteps": "false"', self.admin)
        self.assertIn('"QueuedByPeopleId": "0"', self.admin)
        self.assertIn('"ReportRecipientPeopleIds": ""', self.admin)
        self.assertIn('"FailureRecipientPeopleIds": ""', self.admin)
        self.assertIn('"FromAddress": ""', self.admin)
        self.assertIn('"FromName": ""', self.admin)
        self.assertIn('"ProgramId": "0"', self.admin)
        self.assertNotIn("UseLegacyVolCodes", self.admin)
        self.assertNotIn("UseLegacyVolunteerCodes", self.evaluator)
        self.assertNotIn("dbo.VoluteerApprovalIds", self.evaluator)

    def test_both_application_extra_values_are_required(self):
        self.assertIn("HasApplicationApprovedEV = 1", self.evaluator)
        self.assertIn("AND HasApplicationOnFileEV = 1", self.evaluator)
        self.assertIn(
            'APPLICATION_APPROVED_EV_FIELD = "AppStatus:Application Approved"',
            self.evaluator,
        )
        self.assertIn(
            'APPLICATION_ON_FILE_EV_FIELD = "AppStatus:Application on File"',
            self.evaluator,
        )
        self.assertNotIn("ApplicationApprovedQualifiedEV", self.evaluator)

    def test_new_exclusion_extra_values_are_always_enforced(self):
        self.assertIn("pe.Field = @RefusesEV", self.evaluator)
        self.assertIn("pe.Field = @CollegeEV", self.evaluator)
        self.assertIn("OR HasRefusesFlag = 1", self.evaluator)
        self.assertIn("OR HasCollegeFlag = 1", self.evaluator)

    def test_only_configured_background_check_service_codes_qualify(self):
        self.assertIn(
            'setting("BackgroundCheckServiceCodes", "")',
            self.evaluator,
        )
        self.assertIn("@BackgroundCheckServiceCodes", self.evaluator)
        self.assertIn(
            "UPPER(LTRIM(RTRIM(ISNULL(bc.ServiceCode, ''))))",
            self.evaluator,
        )
        self.assertIn(
            '"BackgroundCheckServiceCodes": ""', self.admin
        )
        self.assertIn(
            "Qualifying background-check service codes", self.admin
        )

    def test_evaluator_fails_safe_without_regular_service_codes(self):
        with self.assertRaisesRegex(
            ValueError, "background-check service codes"
        ):
            execute_evaluator(email_enabled=False, service_codes="")

    def test_admin_declares_ev_only_evaluation(self):
        self.assertIn("uses only these People Extra Values", self.admin)
        self.assertIn("Legacy Volunteer Codes are deprecated", self.admin)
        self.assertNotIn('id="legacyCodesBox"', self.admin)

    def test_complete_report_recipient_disclosure_is_visible(self):
        self.assertIn(
            "Every report recipient receives a nightly report",
            self.admin,
        )

    def test_admin_save_feedback_has_accessible_toasts(self):
        self.assertIn(
            'class="bce-toast alert-success" id="bceToast"', self.admin
        )
        self.assertIn("<span><strong>Saved</strong></span>", self.admin)
        self.assertIn('aria-live="polite" aria-atomic="true"', self.admin)
        self.assertIn(
            'class="bce-toast bce-toast-error alert-danger"', self.admin
        )
        self.assertIn("left:50%; bottom:24px; transform:translateX(-50%)", self.admin)
        self.assertIn("background:#287a45", self.admin)
        self.assertIn("window.setTimeout(dismissToast, 5000)", self.admin)
        self.assertIn("toast.parentNode.removeChild(toast)", self.admin)
        self.assertIn("model.Form = html\nif is_post:\n    print(html)", self.admin)

    def test_admin_actions_remain_inside_touchpoint_frame(self):
        self.assertIn("function postInPlace(sourceForm, errorMessage)", self.admin)
        self.assertIn("function replaceAdmin(markup)", self.admin)
        self.assertIn("current.innerHTML = next.innerHTML", self.admin)
        self.assertIn("initializeBackgroundCheckEvaluator()", self.admin)
        self.assertIn("event.preventDefault()", self.admin)
        self.assertIn("'X-Requested-With':'XMLHttpRequest'", self.admin)
        self.assertIn('target="_self"', self.admin)
        self.assertIn(
            "JavaScript is required to save without leaving the TouchPoint page.",
            self.admin,
        )

    def test_diagnostic_is_aggregate_and_contains_no_person_identity_columns(self):
        section = self.diagnostic.split(
            '"Target Volunteer Extra Value Summary"', 1
        )[1].split("sections.append", 1)[0]
        self.assertIn("COUNT(DISTINCT PeopleId)", section)
        self.assertNotIn("Name2", section)
        self.assertNotIn("EmailAddress", section)
        self.assertIn("Application and AppStatus Extra Value Storage", self.diagnostic)
        self.assertIn("Field LIKE 'AppStatus%'", self.diagnostic)
        self.assertIn(
            "Field = 'AppStatus:Application Approved'", self.diagnostic
        )
        self.assertIn(
            "Field = 'AppStatus:Application on File'", self.diagnostic
        )
        self.assertIn("Process Builder Database Objects", self.diagnostic)
        self.assertIn("Process Builder Object Columns", self.diagnostic)
        self.assertIn("Process Builder Foreign Keys", self.diagnostic)

    def test_diagnostic_has_privacy_safe_background_check_classification(self):
        self.assertIn("BackgroundCheckLabels Columns", self.diagnostic)
        self.assertIn("Background Check Label Definitions", self.diagnostic)
        self.assertIn(
            "Background Check Classification Detail Summary", self.diagnostic
        )
        self.assertIn("bc.SubmitType", self.diagnostic)
        self.assertIn("bc.[Level]", self.diagnostic)
        self.assertIn("bc.UserType", self.diagnostic)
        self.assertIn("bc.ChildServing", self.diagnostic)
        self.assertIn("bc.OverThirteen", self.diagnostic)

        correlation = self.diagnostic.split(
            '"Background Check Legacy MVR and Training Date Correlation"', 1
        )[1].split("page =", 1)[0]
        self.assertIn("v.MVRProcessedDate", correlation)
        self.assertIn("v.TrainingDate", correlation)
        self.assertIn("COUNT(DISTINCT", correlation)
        self.assertNotIn("p.Name", correlation)
        self.assertNotIn("EmailAddress", correlation)
        self.assertNotIn("SELECT bc.PeopleID", correlation)

    def test_comparison_state_is_json_with_legacy_read_compatibility(self):
        self.assertIn('"version": 3', self.evaluator)
        self.assertIn('document.get("people_ids", [])', self.evaluator)
        self.assertIn('if "=" in line:', self.evaluator)

    def test_reset_history_writes_versioned_nonempty_state(self):
        self.assertIn('"reset": True', self.admin)
        self.assertIn("json.dumps(reset_state, sort_keys=True)", self.admin)
        self.assertNotIn(
            'model.WriteContentText(STATE_CONTENT_NAME, "", "")', self.admin
        )
        self.assertIn('document.get("reset", False)', self.evaluator)
        self.assertIn('state.get("reset", False)', self.admin)

    def test_admin_uses_namespaced_action_field(self):
        self.assertIn('posted("BCEAdminAction")', self.admin)
        self.assertIn('name="BCEAdminAction" value="reset_history"', self.admin)
        self.assertIn("BCEAdminAction=search_people", self.admin)
        self.assertNotIn('posted("action")', self.admin)
        self.assertNotIn('name="action"', self.admin)
        self.assertIn("HTTP status: ' + response.status", self.admin)

    def test_date_ev_involvements_do_not_require_upcoming_meetings(self):
        self.assertIn("meetings.UpcomingMeetingCount > 0", self.evaluator)
        self.assertIn(
            "OR date_ev.EvaluateThroughDate >= @Today", self.evaluator
        )
        self.assertIn(
            "CASE WHEN date_ev.EvaluateThroughDate >= @Today", self.evaluator
        )
        self.assertIn(
            "oe.Field = @EvaluateThroughDateEVField", self.evaluator
        )
        self.assertIn("MAX(oe.DateValue) AS EvaluateThroughDate", self.evaluator)
        self.assertNotIn("EVRecordCount", self.evaluator)
        self.assertNotIn(
            "EvaluateBackgroundCheckThroughEndOfProgramYear", self.evaluator
        )

    def test_age_requirement_uses_evaluation_date_not_future_target(self):
        self.assertIn(
            "DATEADD(year, @MinimumBackgroundCheckAge, p.BDate) <= @Today",
            self.evaluator,
        )
        self.assertIn("WHEN p.BDate IS NULL", self.evaluator)
        self.assertNotIn(
            "DATEADD(year, @MinimumBackgroundCheckAge, p.BDate) <= @TargetDate",
            self.evaluator,
        )

    def test_admin_displays_date_ev_without_editing_source_records(self):
        self.assertIn("load_flagged_involvements", self.admin)
        self.assertIn("Involvement evaluate-through dates", self.admin)
        self.assertIn("Involvement's Extra Values tab", self.admin)
        self.assertIn("oe.DateValue", self.admin)
        self.assertIn(
            "HAVING MAX(oe.DateValue) >= CAST(GETDATE() AS date)", self.admin
        )
        self.assertIn("Blank or expired dates are ignored", self.admin)
        self.assertNotIn("ProgramYearDate_", self.admin)
        self.assertNotIn("PROGRAM_YEAR_CONTENT_NAME", self.admin)

    def test_nightly_report_contains_coverage_and_error_sections(self):
        self.assertIn("Involvements included in this evaluation", self.evaluator)
        self.assertIn("<th>Processing result</th>", self.evaluator)
        self.assertIn("Evaluated successfully", self.evaluator)
        self.assertIn("Evaluation failed", self.evaluator)
        self.assertNotIn("<th>Status</th>", self.evaluator)
        self.assertIn("Evaluation errors requiring corrective action", self.evaluator)
        self.assertIn("send_email(REPORT_RECIPIENT_PEOPLE_IDS", self.evaluator)
        self.assertIn("send_email(\n                        FAILURE_RECIPIENT_PEOPLE_IDS", self.evaluator)
        self.assertNotIn("if rows and EMAIL_ENABLED", self.evaluator)

    def test_people_report_uses_requested_columns_and_failure_styles(self):
        namespace, model = execute_evaluator(email_enabled=False)
        underage = {
            "PeopleId": 300,
            "VolunteerName": "Underage Example",
            "LatestApprovedCheck": None,
            "HasApplicationRequirements": False,
            "Involvements": [(20, "Example", "09/01/2026", "Meeting")],
            "BackgroundRequiredValues": [False],
            "Reasons": ["Volunteer application requirements are incomplete"],
            "BackgroundCheckProcessStatus": "Not in process",
            "VolunteerAppProcessStatus": "Application reminder sent",
        }
        adult = {
            "PeopleId": 301,
            "VolunteerName": "Adult Example",
            "LatestApprovedCheck": None,
            "HasApplicationRequirements": True,
            "Involvements": [(20, "Example", "09/01/2026", "Meeting")],
            "BackgroundRequiredValues": [True],
            "Reasons": ["No approved background check on file"],
            "BackgroundCheckProcessStatus": "Background reminder sent",
            "VolunteerAppProcessStatus": "Completed",
        }
        rendered = namespace["render_people_table"]([underage, adult], False)
        self.assertIn("<th>Meets Application Requirements</th>", rendered)
        self.assertNotIn("<th>Exception</th>", rendered)
        self.assertIn(">N/A</td>", rendered)
        self.assertIn("background:#f2dede;color:#a94442", rendered)
        self.assertNotIn("Reminder step:", rendered)
        namespace["SHOW_PROCESS_REMINDER_STEPS"] = True
        rendered = namespace["render_people_table"]([underage, adult], False)
        self.assertIn("Reminder step: Background reminder sent", rendered)
        self.assertIn("Reminder step: Application reminder sent", rendered)

    def test_process_builder_reminder_switch_is_default_off(self):
        self.assertIn(
            'Show Process Builder reminder steps in reports and email',
            self.admin,
        )
        self.assertIn(
            'SHOW_PROCESS_REMINDER_STEPS = bool_setting(\n'
            '    "ShowProcessReminderSteps", False',
            self.evaluator,
        )
        self.assertIn("WHERE @ShowProcessReminderSteps = 1", self.evaluator)

    def test_process_builder_status_uses_confirmed_schema_and_names(self):
        self.assertIn("dbo.ProcessBuilder", self.evaluator)
        self.assertIn("dbo.ProcessPeople", self.evaluator)
        self.assertIn("dbo.ProcessProgression", self.evaluator)
        self.assertIn("dbo.ProcessStep", self.evaluator)
        self.assertIn("progression.IsCurrent = 1", self.evaluator)
        self.assertIn(
            'BACKGROUND_CHECK_PROCESS_NAME = "Evaluate for Background Check status"',
            self.evaluator,
        )
        self.assertIn(
            'VOLUNTEER_APP_PROCESS_NAME = "Evaluate for Volunteer App"',
            self.evaluator,
        )

    def test_partial_state_preserves_failed_involvement(self):
        namespace, model = execute_evaluator(email_enabled=False)
        previous = namespace["empty_state"]()
        previous["involvements"]["10"] = {
            "required_through": "2027-06-30",
            "evaluation_basis": "Configured through date",
            "exception_people_ids": [100],
        }
        previous["involvements"]["20"] = {
            "required_through": "2026-09-01",
            "evaluation_basis": "Latest upcoming meeting",
            "exception_people_ids": [200],
        }
        coverage = [
            coverage_record(10, "Failed"),
            coverage_record(20, "Completed"),
        ]
        row = exception_row(20, 201)
        errors = [
            {"OrganizationId": 10, "Involvement": "Flagged", "Message": "Missing"}
        ]
        updated = namespace["build_updated_state"](
            previous, coverage, [row], errors
        )
        self.assertEqual(
            updated["involvements"]["10"]["exception_people_ids"], [100]
        )
        self.assertEqual(
            updated["involvements"]["20"]["exception_people_ids"], [201]
        )
        self.assertTrue(updated["incomplete"])

    def test_completed_scope_queues_nightly_email_and_updates_state(self):
        namespace, model = execute_evaluator(email_enabled=True)
        self.assertEqual(len(model.emails), 1)
        nightly_body = model.emails[0][5]
        self.assertIn("Meeting Based", nightly_body)
        self.assertEqual(len(model.writes), 1)
        state = json.loads(model.writes[0][1])
        self.assertFalse(state["incomplete"])
        self.assertEqual(state["failed_involvement_ids"], [])
        self.assertIn("20", state["involvements"])


def coverage_record(organization_id, status):
    return {
        "OrganizationId": organization_id,
        "Involvement": "Involvement {0}".format(organization_id),
        "EvaluationBasis": (
            "Configured through date"
            if organization_id == 10
            else "Latest upcoming meeting"
        ),
        "RequiredThrough": (
            "Not configured" if status == "Failed" else "09/01/2026"
        ),
        "RequiredThroughIso": (
            "" if status == "Failed" else "2026-09-01"
        ),
        "UpcomingMeetingCount": 0 if organization_id == 10 else 1,
        "CurrentMemberCount": 1,
        "Status": status,
        "Message": "Missing" if status == "Failed" else "",
    }


def exception_row(organization_id, people_id):
    return types.SimpleNamespace(
        OrganizationId=organization_id,
        Involvement="Involvement {0}".format(organization_id),
        RequiredThroughDate=datetime.datetime(2026, 9, 1),
        EvaluationBasis="Latest upcoming meeting",
        PeopleId=people_id,
        VolunteerName="Example Person",
        BackgroundCheckRequired=True,
        LatestApprovedCheck=None,
        HasApplicationRequirements=True,
        BackgroundCheckProcessStatus="Background reminder sent",
        VolunteerAppProcessStatus="Application reminder sent",
        ExceptionReason="No approved background check on file",
    )


def execute_evaluator(email_enabled, service_codes="BG100,BG200"):
    fake_cgi = types.ModuleType("cgi")
    fake_cgi.escape = html.escape
    previous_cgi = sys.modules.get("cgi")
    sys.modules["cgi"] = fake_cgi

    class Model:
        CmsHost = "https://example.test"

        def __init__(self):
            self.emails = []
            self.writes = []

        def Setting(self, key, default):
            if key == "BCE.EmailEnabled":
                return "true" if email_enabled else "false"
            if key == "BCE.BackgroundCheckServiceCodes":
                return service_codes
            return default

        def TextContent(self, name):
            return ""

        def WriteContentText(self, name, content, keyword=""):
            self.writes.append((name, content, keyword))

        def Email(self, *args):
            self.emails.append(args)

    class Query:
        def QuerySql(self, sql, parameters=None):
            if "INVOLVEMENT_SCOPE_MARKER" in sql:
                return []
            if "SELECT\n    o.OrganizationId" in sql:
                return [
                    types.SimpleNamespace(
                        OrganizationId=20,
                        Involvement="Meeting Based",
                        HasThroughDateEV=False,
                        EvaluateThroughDate=None,
                        LatestMeetingDate=datetime.datetime(2026, 9, 1),
                        UpcomingMeetingCount=1,
                        CurrentMemberCount=1,
                    ),
                ]
            return [exception_row(20, 201)]

    model = Model()
    namespace = {
        "model": model,
        "q": Query(),
        "Data": types.SimpleNamespace(BCEAction=""),
    }
    output = io.StringIO()
    try:
        with contextlib.redirect_stdout(output):
            exec(
                compile(
                    read_source("BackgroundCheckEvaluator.py"),
                    "BackgroundCheckEvaluator.py",
                    "exec",
                ),
                namespace,
            )
    finally:
        if previous_cgi is None:
            del sys.modules["cgi"]
        else:
            sys.modules["cgi"] = previous_cgi
    return namespace, model


if __name__ == "__main__":
    unittest.main()
