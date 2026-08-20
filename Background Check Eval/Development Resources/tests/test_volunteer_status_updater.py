import contextlib
import html
import io
import json
import pathlib
import sys
import types
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
INSTALLATION_ROOT = PROJECT_ROOT / "Installation Files"


def read_source(name):
    return (INSTALLATION_ROOT / name).read_text(encoding="utf-8")


def candidate(
    people_id,
    current="",
    app_approved=True,
    app_on_file=True,
    underage=False,
    current_check=False,
    expired_check=False,
    ineligible=False,
    latest_status=None,
    application_membership=True,
    current_mvr=False,
    current_unknown_check=False,
):
    return types.SimpleNamespace(
        PeopleId=people_id,
        VolunteerName="Volunteer {0}".format(people_id),
        ExistingApprovedRole=current,
        HasApplicationApproved=app_approved,
        HasApplicationOnFile=application_membership,
        HasStoredApplicationOnFile=app_on_file,
        HasVolunteerApplicationMembership=application_membership,
        IsUnderMinimumAge=underage,
        HasCurrentApprovedCheck=current_check,
        HasExpiredApprovedCheck=expired_check,
        HasIneligibleVolunteer=ineligible,
        LatestBackgroundStatus=latest_status,
        HasCurrentApprovedMVR=current_mvr,
        HasCurrentApprovedUnknownCheck=current_unknown_check,
    )


class FakeModel:
    CmsHost = "https://example.test"

    def __init__(
        self,
        updates_enabled=False,
        email_enabled=False,
        fail_ids=None,
        configuration_saved=True,
        output_ready=True,
        background_codes="BG100,BG200",
        mvr_codes="MVR100",
        mvr_valid_months="12",
    ):
        self.settings = {
            "VSU.BackgroundCheckValidMonths": "33",
            "VSU.MinimumBackgroundCheckAge": "18",
            "VSU.TrainingReportTypeId": "9",
            "VSU.BackgroundCheckServiceCodes": background_codes,
            "VSU.MVRServiceCodes": mvr_codes,
            "VSU.MVRCheckValidMonths": mvr_valid_months,
            "VSU.VolunteerApplicationInvolvementId": "700",
            "VSU.QueuedByPeopleId": "50",
            "VSU.FromAddress": "sender@example.test",
            "VSU.FromName": "Example Sender",
            "VSU.UpdatesEnabled": "true" if updates_enabled else "false",
            "VSU.ConfigurationSaved": (
                "true" if configuration_saved else "false"
            ),
            "VSU.EmailEnabled": "true" if email_enabled else "false",
            "VSU.RecipientPeopleIds": "60,61",
        }
        self.fail_ids = set(fail_ids or [])
        self.extra_value_writes = []
        self.bool_writes = []
        self.content_writes = []
        self.emails = []
        self.output_ready = output_ready

    def Setting(self, key, default):
        return self.settings.get(key, default)

    def TextContent(self, name):
        if not self.output_ready:
            return ""
        return (
            "Approved for Role Code PrimaryVolunteer SecondaryVolunteer "
            "PrimaryVolunteerMVR SecondaryVolunteerExpiredBackground Denied "
            "MissingInfo"
        )

    def AddExtraValueCode(self, people_id, field, value):
        if people_id in self.fail_ids:
            raise RuntimeError("simulated write failure")
        self.extra_value_writes.append((people_id, field, value))

    def AddExtraValueBool(self, people_id, field, value):
        if people_id in self.fail_ids:
            raise RuntimeError("simulated write failure")
        self.bool_writes.append((people_id, field, value))

    def WriteContentText(self, name, content, keyword=""):
        self.content_writes.append((name, content, keyword))

    def Email(self, *args):
        self.emails.append(args)


def execute_updater(
    rows,
    updates_enabled=False,
    email_enabled=False,
    action="",
    fail_ids=None,
    query_error=None,
    capture_error=False,
    configuration_saved=True,
    output_ready=True,
    background_codes="BG100,BG200",
    mvr_codes="MVR100",
    mvr_valid_months="12",
):
    fake_cgi = types.ModuleType("cgi")
    fake_cgi.escape = html.escape
    previous_cgi = sys.modules.get("cgi")
    sys.modules["cgi"] = fake_cgi

    class Query:
        def __init__(self):
            self.calls = []

        def QuerySql(self, sql, parameters=None):
            self.calls.append((sql, parameters))
            if query_error is not None:
                raise query_error
            return rows

        def QuerySqlInt(self, sql):
            return 1

    model = FakeModel(
        updates_enabled,
        email_enabled,
        fail_ids,
        configuration_saved,
        output_ready,
        background_codes,
        mvr_codes,
        mvr_valid_months,
    )
    query = Query()
    namespace = {
        "model": model,
        "q": query,
        "Data": types.SimpleNamespace(VSUAction=action),
    }
    output = io.StringIO()
    captured_error = None
    try:
        with contextlib.redirect_stdout(output):
            try:
                exec(
                    compile(
                        read_source("VolunteerStatusUpdater.py"),
                        "VolunteerStatusUpdater.py",
                        "exec",
                    ),
                    namespace,
                )
            except Exception as exc:
                if not capture_error:
                    raise
                captured_error = exc
    finally:
        if previous_cgi is None:
            del sys.modules["cgi"]
        else:
            sys.modules["cgi"] = previous_cgi
    result = (namespace, model, query, output.getvalue())
    if capture_error:
        return result + (captured_error,)
    return result


def execute_admin_get():
    fake_cgi = types.ModuleType("cgi")
    fake_cgi.escape = html.escape
    previous_cgi = sys.modules.get("cgi")
    sys.modules["cgi"] = fake_cgi

    class Model:
        CmsHost = "https://example.test"
        HttpMethod = "GET"

        def Setting(self, key, default):
            return default

        def TextContent(self, name):
            return (
                "Approved for Role Code PrimaryVolunteer SecondaryVolunteer "
                "PrimaryVolunteerMVR SecondaryVolunteerExpiredBackground Denied "
                "MissingInfo"
            )

    class Query:
        def QuerySql(self, sql, parameters=None):
            return []

    model = Model()
    namespace = {
        "model": model,
        "q": Query(),
        "Data": types.SimpleNamespace(),
    }
    try:
        exec(
            compile(
                read_source("VolunteerStatusUpdaterAdmin.py"),
                "VolunteerStatusUpdaterAdmin.py",
                "exec",
            ),
            namespace,
        )
    finally:
        if previous_cgi is None:
            del sys.modules["cgi"]
        else:
            sys.modules["cgi"] = previous_cgi
    return model.Form


def execute_admin_post(
    confirm_enable,
    ready=True,
    background_codes="BG100,BG200",
    mvr_codes="MVR100",
    mvr_valid_months="12",
):
    fake_cgi = types.ModuleType("cgi")
    fake_cgi.escape = html.escape
    previous_cgi = sys.modules.get("cgi")
    sys.modules["cgi"] = fake_cgi

    class Model:
        CmsHost = "https://example.test"
        HttpMethod = "POST"

        def __init__(self):
            self.setting_writes = []

        def Setting(self, key, default):
            return default

        def SetSetting(self, key, value):
            self.setting_writes.append((key, value))

        def TextContent(self, name):
            if not ready:
                return ""
            return (
                "Approved for Role Code PrimaryVolunteer SecondaryVolunteer "
                "PrimaryVolunteerMVR SecondaryVolunteerExpiredBackground Denied "
                "MissingInfo"
            )

    class Query:
        def QuerySql(self, sql, parameters=None):
            return []

        def QuerySqlInt(self, sql):
            return 1

    data = types.SimpleNamespace(
        QueuedByPeopleId="50",
        RecipientPeopleIds="",
        EmailEnabled="false",
        FromAddress="sender@example.test",
        FromName="Example Sender",
        BackgroundCheckValidMonths="33",
        MinimumBackgroundCheckAge="18",
        TrainingReportTypeId="9",
        BackgroundCheckServiceCodes=background_codes,
        MVRServiceCodes=mvr_codes,
        MVRCheckValidMonths=mvr_valid_months,
        VolunteerApplicationInvolvementId="700",
        UpdatesEnabled="true",
        ConfirmEnable="true" if confirm_enable else "false",
    )
    model = Model()
    namespace = {"model": model, "q": Query(), "Data": data}
    output = io.StringIO()
    try:
        with contextlib.redirect_stdout(output):
            exec(
                compile(
                    read_source("VolunteerStatusUpdaterAdmin.py"),
                    "VolunteerStatusUpdaterAdmin.py",
                    "exec",
                ),
                namespace,
            )
    finally:
        if previous_cgi is None:
            del sys.modules["cgi"]
        else:
            sys.modules["cgi"] = previous_cgi
    return model, output.getvalue()


def execute_admin_lookup(action, term, rows, http_method="POST"):
    fake_cgi = types.ModuleType("cgi")
    fake_cgi.escape = html.escape
    previous_cgi = sys.modules.get("cgi")
    sys.modules["cgi"] = fake_cgi

    class Model:
        CmsHost = "https://example.test"
        HttpMethod = http_method

        def Setting(self, key, default):
            return default

        def TextContent(self, name):
            return ""

    class Query:
        def __init__(self):
            self.calls = []

        def QuerySql(self, sql, parameters=None):
            self.calls.append((sql, parameters))
            return rows

    model = Model()
    query = Query()
    namespace = {
        "model": model,
        "q": query,
        "Data": types.SimpleNamespace(VSUAdminAction=action, term=term),
        "unicode": str,
    }
    output = io.StringIO()
    try:
        with contextlib.redirect_stdout(output):
            exec(
                compile(
                    read_source("VolunteerStatusUpdaterAdmin.py"),
                    "VolunteerStatusUpdaterAdmin.py",
                    "exec",
                ),
                namespace,
            )
    finally:
        if previous_cgi is None:
            del sys.modules["cgi"]
        else:
            sys.modules["cgi"] = previous_cgi
    return json.loads(output.getvalue()), query


class VolunteerStatusUpdaterTests(unittest.TestCase):
    def setUp(self):
        self.source = read_source("VolunteerStatusUpdater.py")
        self.admin = read_source("VolunteerStatusUpdaterAdmin.py")
        self.evaluator_admin = read_source("BackgroundCheckEvaluatorAdmin.py")
        self.diagnostic = read_source("BackgroundCheckEvalDiagnostic.py")

    def test_script_is_independently_deployable_and_default_off(self):
        self.assertEqual(self.source.splitlines()[0], "#Roles=Admin")
        self.assertIn('APP_VERSION = "1.9.0"', self.source)
        self.assertIn(
            'bool_setting(SETTING_PREFIX, "UpdatesEnabled", False)',
            self.source,
        )
        self.assertIn(
            'bool_setting(SETTING_PREFIX, "EmailEnabled", False)',
            self.source,
        )
        self.assertNotIn("BCE_SETTING_PREFIX", self.source)
        self.assertNotIn("STATUS_NOT_APPROVED", self.source)
        self.assertNotIn('SETTING_PREFIX, "ProgramId"', self.source)
        self.assertNotIn('SETTING_PREFIX, "DivisionId"', self.source)

    def test_candidate_query_uses_union_and_parameters(self):
        _, _, query, _ = execute_updater([], action="preview")
        sql, parameters = query.calls[0]
        self.assertIn("CandidatePeople AS", sql)
        self.assertIn("UNION", sql)
        self.assertIn("dbo.PeopleExtra", sql)
        self.assertIn("dbo.BackgroundChecks", sql)
        self.assertIn("dbo.OrganizationMembers", sql)
        self.assertNotIn("dbo.Organizations", sql)
        self.assertNotIn("dbo.Division", sql)
        self.assertIn("@ApprovedRoleEV", sql)
        self.assertIn(
            "NULLIF(LTRIM(RTRIM(pe.StrValue)), '') IS NOT NULL", sql
        )
        self.assertIn("@ApplicationApprovedEV", sql)
        self.assertIn("@ApplicationOnFileEV", sql)
        self.assertIn("@IneligibleVolunteerEV", sql)
        self.assertIn(
            "LOWER(LTRIM(RTRIM(bc.ApprovalStatus))) = 'not approved'",
            sql,
        )
        self.assertNotIn("LatestAdverseCheck", sql)
        self.assertNotIn("HasNewerAdverseResult", sql)
        self.assertIn("WHERE ISNULL(p.IsDeceased, 0) = 0", sql)
        self.assertIn("AND ISNULL(p.ArchivedFlag, 0) = 0", sql)
        self.assertIn("WHERE pe.BitValue = 1", sql)
        self.assertIn(
            "bc.Updated >= DATEADD(month, -@ValidMonths, @Today)", sql
        )
        self.assertIn("bc.Updated < DATEADD(day, 1, @Today)", sql)
        self.assertIn("@BackgroundCheckServiceCodes", sql)
        self.assertIn("@MVRServiceCodes", sql)
        self.assertIn("@MVRValidMonths", sql)
        self.assertIn("UPPER(LTRIM(RTRIM(ISNULL(bc.ServiceCode, ''))))", sql)
        self.assertIn("HasCurrentApprovedMVR", sql)
        self.assertIn("HasCurrentApprovedUnknownCheck", sql)
        self.assertIn(
            "om.OrganizationId = @VolunteerApplicationInvolvementId", sql
        )
        self.assertIn("om.InactiveDate IS NULL", sql)
        self.assertIn("ISNULL(om.Pending, 0) = 0", sql)
        self.assertEqual(parameters["VolunteerApplicationInvolvementId"], 700)
        self.assertEqual(
            parameters["IneligibleVolunteerEV"], "Ineligible Volunteer"
        )
        self.assertEqual(
            parameters["BackgroundCheckServiceCodes"],
            "BG100,BG200",
        )
        self.assertEqual(parameters["MVRServiceCodes"], "MVR100")
        self.assertEqual(parameters["MVRValidMonths"], 12)
        self.assertIn(
            "CAST(bc.Updated AS date) >\n"
            "          DATEADD(month, -@MVRValidMonths, @Today)",
            sql,
        )
        mvr_section = sql.split(") latest_result", 1)[1].split(") mvr", 1)[0]
        self.assertIn(
            "LOWER(LTRIM(RTRIM(bc.ApprovalStatus))) = 'approved'",
            mvr_section,
        )
        self.assertIn("ORDER BY bc.Updated DESC, bc.ID DESC", mvr_section)
        self.assertNotIn("ProgramId", parameters)
        self.assertNotIn("DivisionId", parameters)
        self.assertNotIn("UPDATE dbo.PeopleExtra", self.source)
        self.assertNotIn("INSERT INTO dbo.PeopleExtra", self.source)

    def test_decision_table(self):
        namespace, _, _, _ = execute_updater([], action="preview")
        calculate = namespace["calculate_status"]
        cases = [
            (candidate(1, current_check=True), "PrimaryVolunteer"),
            (candidate(2), "SecondaryVolunteer"),
            (
                candidate(3, expired_check=True),
                "SecondaryVolunteerExpiredBackground",
            ),
            (candidate(4, app_approved=False), "MissingInfo"),
            (
                candidate(
                    5,
                    app_on_file=False,
                    application_membership=False,
                ),
                "MissingInfo",
            ),
            (
                candidate(6, latest_status="Adverse"),
                "SecondaryVolunteer",
            ),
            (candidate(7, underage=True, expired_check=True), "SecondaryVolunteer"),
            (
                candidate(8, current_check=True, latest_status="Pending"),
                "PrimaryVolunteer",
            ),
            (candidate(9, latest_status="Pending"), "SecondaryVolunteer"),
            (candidate(10, latest_status="Error"), "SecondaryVolunteer"),
            (candidate(11, latest_status="Cancelled"), "SecondaryVolunteer"),
            (
                candidate(14, current_check=True, latest_status="Not Approved"),
                "Denied",
            ),
            (
                candidate(15, current_check=True, ineligible=True),
                "Denied",
            ),
            (candidate(16, current_mvr=True), "MissingInfo"),
            (
                candidate(
                    17,
                    expired_check=True,
                    current_mvr=True,
                ),
                "SecondaryVolunteerExpiredBackground",
            ),
            (
                candidate(
                    18,
                    current_check=True,
                    current_mvr=True,
                ),
                "PrimaryVolunteerMVR",
            ),
            (candidate(19, current_unknown_check=True), "MissingInfo"),
        ]
        for row, expected in cases:
            self.assertEqual(calculate(row)[0], expected)

    def test_preview_never_writes_emails_or_state(self):
        rows = [candidate(1, current="MissingInfo", current_check=True)]
        _, model, _, output = execute_updater(
            rows, updates_enabled=True, email_enabled=True, action="preview"
        )
        self.assertEqual(model.extra_value_writes, [])
        self.assertEqual(model.bool_writes, [])
        self.assertEqual(model.content_writes, [])
        self.assertEqual(model.emails, [])
        self.assertIn("Preview only", output)
        self.assertIn("Would change", output)

    def test_denied_rule_writes_approved_for_role(self):
        rows = [
            candidate(
                1,
                current="PrimaryVolunteer",
                current_check=True,
                latest_status="Not Approved",
            )
        ]
        _, model, _, output = execute_updater(rows, updates_enabled=True)
        self.assertEqual(
            model.extra_value_writes,
            [(1, "Approved for Role", "Denied")],
        )
        self.assertIn("Latest background check is Not Approved", output)

    def test_legacy_not_approved_value_is_replaced_for_active_candidate(self):
        rows = [candidate(1, current="NotApproved", current_check=True)]
        _, model, _, _ = execute_updater(rows, updates_enabled=True)
        self.assertEqual(
            model.extra_value_writes,
            [(1, "Approved for Role", "PrimaryVolunteer")],
        )

    def test_expired_or_invalid_mvr_downgrades_primary_mvr(self):
        rows = [
            candidate(
                1,
                current="PrimaryVolunteerMVR",
                current_check=True,
                current_mvr=False,
            )
        ]
        _, model, _, output = execute_updater(rows, updates_enabled=True)
        self.assertEqual(
            model.extra_value_writes,
            [(1, "Approved for Role", "PrimaryVolunteer")],
        )
        self.assertIn("Current approved background check", output)

    def test_membership_sets_application_on_file_before_role_status(self):
        rows = [
            candidate(
                1,
                current="MissingInfo",
                app_approved=True,
                app_on_file=False,
                current_check=True,
                application_membership=True,
            )
        ]
        _, model, _, output = execute_updater(rows, updates_enabled=True)
        self.assertEqual(
            model.bool_writes,
            [(1, "AppStatus:Application on File", True)],
        )
        self.assertEqual(
            model.extra_value_writes,
            [(1, "Approved for Role", "PrimaryVolunteer")],
        )
        self.assertIn("Set from Involvement membership", output)

    def test_membership_preview_proposes_application_update_without_writing(self):
        rows = [
            candidate(
                1,
                current="MissingInfo",
                app_approved=False,
                app_on_file=False,
                application_membership=True,
            )
        ]
        _, model, _, output = execute_updater(
            rows, updates_enabled=True, action="preview"
        )
        self.assertEqual(model.bool_writes, [])
        self.assertEqual(model.extra_value_writes, [])
        self.assertIn("Would set from Involvement membership", output)

    def test_absent_membership_clears_application_on_file(self):
        rows = [
            candidate(
                1,
                current="SecondaryVolunteer",
                app_on_file=True,
                application_membership=False,
            )
        ]
        _, model, _, output = execute_updater(rows, updates_enabled=True)
        self.assertEqual(
            model.bool_writes,
            [(1, "AppStatus:Application on File", False)],
        )
        self.assertEqual(
            model.extra_value_writes,
            [(1, "Approved for Role", "MissingInfo")],
        )
        self.assertIn("Cleared; not a current member", output)

    def test_absent_membership_preview_proposes_clear_without_writing(self):
        rows = [
            candidate(
                1,
                current="SecondaryVolunteer",
                app_on_file=True,
                application_membership=False,
            )
        ]
        _, model, _, output = execute_updater(
            rows, updates_enabled=True, action="preview"
        )
        self.assertEqual(model.bool_writes, [])
        self.assertEqual(model.extra_value_writes, [])
        self.assertIn("Would clear; not a current member", output)

    def test_disabled_morning_batch_is_preview_only(self):
        rows = [candidate(1, current="MissingInfo", current_check=True)]
        _, model, _, output = execute_updater(rows, updates_enabled=False)
        self.assertEqual(model.extra_value_writes, [])
        self.assertEqual(model.content_writes, [])
        self.assertIn("Updates are disabled", output)

    def test_unsaved_independent_configuration_blocks_writes(self):
        _, model, _, output, error = execute_updater(
            [candidate(1, current="MissingInfo", current_check=True)],
            updates_enabled=True,
            configuration_saved=False,
            capture_error=True,
        )
        self.assertIsInstance(error, ValueError)
        self.assertEqual(model.extra_value_writes, [])
        self.assertIn("has not been reviewed and saved", output)

    def test_missing_background_check_service_codes_blocks_evaluation(self):
        _, model, query, output, error = execute_updater(
            [],
            action="preview",
            background_codes="",
            capture_error=True,
        )
        self.assertIsInstance(error, ValueError)
        self.assertEqual(query.calls, [])
        self.assertEqual(model.extra_value_writes, [])
        self.assertIn(
            "background-check service codes are not configured",
            output,
        )

    def test_missing_standard_extra_value_definition_blocks_writes(self):
        _, model, _, output, error = execute_updater(
            [candidate(1, current="MissingInfo", current_check=True)],
            updates_enabled=True,
            output_ready=False,
            capture_error=True,
        )
        self.assertIsInstance(error, ValueError)
        self.assertEqual(model.extra_value_writes, [])
        self.assertIn("not defined in StandardExtraValues2", output)

    def test_denied_must_be_configured_as_approved_for_role_option(self):
        namespace, model, _, _ = execute_updater([], action="preview")
        model.TextContent = lambda name: (
            "Approved for Role Code PrimaryVolunteer SecondaryVolunteer "
            "PrimaryVolunteerMVR SecondaryVolunteerExpiredBackground MissingInfo"
        )
        with self.assertRaisesRegex(ValueError, "Denied"):
            namespace["validate_output_definition"]()

    def test_missing_info_must_be_configured_as_approved_for_role_option(self):
        namespace, model, _, _ = execute_updater([], action="preview")
        model.TextContent = lambda name: (
            "Approved for Role Code PrimaryVolunteer SecondaryVolunteer "
            "PrimaryVolunteerMVR SecondaryVolunteerExpiredBackground Denied"
        )
        with self.assertRaisesRegex(ValueError, "MissingInfo"):
            namespace["validate_output_definition"]()

    def test_primary_mvr_must_be_configured_as_approved_for_role_option(self):
        namespace, model, _, _ = execute_updater([], action="preview")
        model.TextContent = lambda name: (
            "Approved for Role Code PrimaryVolunteer SecondaryVolunteer "
            "SecondaryVolunteerExpiredBackground Denied MissingInfo"
        )
        with self.assertRaisesRegex(ValueError, "PrimaryVolunteerMVR"):
            namespace["validate_output_definition"]()

    def test_production_changes_only_differences_and_saves_minimal_state(self):
        rows = [
            candidate(1, current="MissingInfo", current_check=True),
            candidate(2, current="SecondaryVolunteer"),
        ]
        _, model, _, _ = execute_updater(rows, updates_enabled=True)
        self.assertEqual(
            model.extra_value_writes,
            [(1, "Approved for Role", "PrimaryVolunteer")],
        )
        self.assertEqual(len(model.content_writes), 1)
        state = json.loads(model.content_writes[0][1])
        self.assertEqual(state["evaluated"], 2)
        self.assertEqual(state["changed"], 1)
        self.assertEqual(state["unchanged"], 1)
        self.assertEqual(state["failed"], 0)
        self.assertNotIn("people", state)

    def test_email_is_queued_only_for_changes_or_failures(self):
        unchanged = [candidate(1, current="SecondaryVolunteer")]
        _, model, _, _ = execute_updater(
            unchanged, updates_enabled=True, email_enabled=True
        )
        self.assertEqual(model.emails, [])

        changed = [candidate(2, current="MissingInfo", current_check=True)]
        _, model, _, _ = execute_updater(
            changed, updates_enabled=True, email_enabled=True
        )
        self.assertEqual(len(model.emails), 1)
        body = model.emails[0][5]
        self.assertIn("Volunteer 2", body)
        self.assertIn("MissingInfo", body)
        self.assertIn("PrimaryVolunteer", body)
        self.assertIn("Current approved background check", body)
        self.assertNotIn("EmailAddress", body)
        self.assertNotIn("Phone", body)

    def test_person_failure_isolated_and_reported(self):
        rows = [
            candidate(1, current="MissingInfo", current_check=True),
            candidate(2, current="MissingInfo", current_check=True),
        ]
        _, model, _, output = execute_updater(
            rows,
            updates_enabled=True,
            email_enabled=True,
            fail_ids=[1],
        )
        self.assertEqual(
            model.extra_value_writes,
            [(2, "Approved for Role", "PrimaryVolunteer")],
        )
        state = json.loads(model.content_writes[0][1])
        self.assertEqual(state["changed"], 1)
        self.assertEqual(state["failed"], 1)
        self.assertIn("simulated write failure", output)
        self.assertEqual(len(model.emails), 1)

    def test_fatal_production_failure_attempts_failure_email(self):
        _, model, _, output, error = execute_updater(
            [],
            updates_enabled=True,
            email_enabled=True,
            query_error=RuntimeError("simulated query failure"),
            capture_error=True,
        )
        self.assertIsInstance(error, RuntimeError)
        self.assertEqual(model.extra_value_writes, [])
        self.assertEqual(model.content_writes, [])
        self.assertEqual(len(model.emails), 1)
        self.assertIn("Failure", model.emails[0][4])
        self.assertIn("simulated query failure", model.emails[0][5])
        self.assertIn("failed", output)

    def test_admin_has_preview_safeguards_and_privacy_disclosure(self):
        self.assertIn('APP_VERSION = "1.12.0"', self.admin)
        self.assertNotIn('"NotApproved"', self.admin)
        self.assertIn('"Denied"', self.admin)
        self.assertIn('"MissingInfo"', self.admin)
        self.assertIn('SETTING_PREFIX = "VSU."', self.admin)
        self.assertIn('BCE_SETTING_PREFIX = "BCE."', self.admin)
        self.assertIn("BCE_SUGGESTIONS", self.admin)
        self.assertIn(
            "if name in BCE_SUGGESTIONS and not configuration_saved()",
            self.admin,
        )
        self.assertIn("synchronize automatically", self.admin)
        self.assertNotIn('"ProgramId"', self.admin)
        self.assertNotIn('"DivisionId"', self.admin)
        self.assertIn('"UpdatesEnabled": "false"', self.admin)
        self.assertIn('"EmailEnabled": "false"', self.admin)
        self.assertIn(
            '"BackgroundCheckServiceCodes": ""', self.admin
        )
        self.assertIn(
            '"BackgroundCheckServiceCodes": (', self.admin
        )
        self.assertIn('"MVRServiceCodes": ""', self.admin)
        self.assertIn('"MVRCheckValidMonths": "12"', self.admin)
        self.assertIn(
            '"VolunteerApplicationInvolvementId": "0"', self.admin
        )
        self.assertIn('value="{application_involvement_id}"', self.admin)
        self.assertIn("search_involvements", self.admin)
        self.assertIn("@ExactOrganizationId", self.admin)
        self.assertIn("o.OrganizationStatusId = 30", self.admin)
        self.assertIn("Organization ID", self.admin)
        self.assertIn("pending, inactive, or absent person is cleared", self.admin)
        self.assertIn('id="vsuPreviewForm"', self.admin)
        self.assertIn('target="_blank"', self.admin)
        self.assertIn('name="VSUAction" value="preview"', self.admin)
        self.assertIn("'/VolunteerStatusUpdater'", self.admin)
        self.assertIn("never writes", self.admin)
        self.assertIn("I reviewed the live preview", self.admin)
        self.assertIn("including names, People", self.admin)
        self.assertIn("Email addresses and phone numbers", self.admin)
        self.assertIn("if lookup_response is not None", self.admin)
        self.assertNotIn("raise SystemExit", self.admin)
        self.assertIn("/PyScriptForm/", self.admin)
        self.assertNotIn("VolunteerStatusUpdater", self.evaluator_admin)
        self.assertNotIn("Approved for Role updater", self.evaluator_admin)

    def test_admin_get_renders_updater_controls(self):
        rendered = execute_admin_get()
        self.assertIn("Volunteer Status Updater Configuration", rendered)
        self.assertIn("Preview status updates", rendered)
        self.assertIn("Version 1.12.0", rendered)
        self.assertIn("Deceased and archived people are excluded", rendered)
        self.assertIn("Ineligible Volunteer is checked", rendered)
        self.assertIn("Incomplete application", rendered)
        self.assertIn("MissingInfo", rendered)
        self.assertIn(
            "Qualifying background-check service codes", rendered
        )
        self.assertIn("MVR service codes", rendered)
        self.assertIn("MVR Check Valid Months", rendered)
        self.assertIn("PrimaryVolunteerMVR", rendered)
        self.assertIn("Candidate population", rendered)
        self.assertIn("Volunteer Application Involvement", rendered)
        self.assertIn('font-family:"Helvetica Neue"', rendered)
        self.assertIn('scope="col"', rendered)

    def test_admin_person_lookup_routes_and_returns_json(self):
        rows = [
            types.SimpleNamespace(
                PeopleId=42,
                Name="Volunteer, Taylor",
                Name2="Taylor Volunteer",
                EmailAddress="taylor@example.test",
            )
        ]
        payload, query = execute_admin_lookup(
            "search_people", "Taylor", rows
        )
        self.assertTrue(payload["success"])
        self.assertEqual(payload["people"][0]["id"], 42)
        self.assertEqual(query.calls[0][1]["LikeTerm"], "%Taylor%")

    def test_admin_involvement_lookup_routes_and_returns_json(self):
        rows = [
            types.SimpleNamespace(
                OrganizationId=700,
                OrganizationName="Volunteer Application",
                DivisionName="Volunteer Ministry",
                ProgramName="Administration",
            )
        ]
        payload, query = execute_admin_lookup(
            "search_involvements", "Volunteer", rows
        )
        self.assertTrue(payload["success"])
        self.assertEqual(payload["involvements"][0]["id"], 700)
        self.assertEqual(query.calls[0][1]["LikeTerm"], "%Volunteer%")

    def test_admin_initializes_only_actual_person_pickers(self):
        self.assertIn(
            "'.vsu-person-picker[data-picker]'", self.admin
        )

    def test_admin_lookup_failures_expose_bounded_response_detail(self):
        self.assertIn("summarizeLookupResponse", self.admin)
        self.assertIn("response.status", self.admin)
        self.assertIn("Expected JSON but received", self.admin)
        self.assertIn("substring(0, 240)", self.admin)

    def test_admin_requires_confirmation_for_first_write_enable(self):
        model, output = execute_admin_post(confirm_enable=False)
        self.assertEqual(model.setting_writes, [])
        self.assertIn("Confirm that the live updater preview", output)

        model, output = execute_admin_post(confirm_enable=True)
        self.assertIn(("VSU.ConfigurationSaved", "true"), model.setting_writes)
        self.assertIn(("VSU.UpdatesEnabled", "true"), model.setting_writes)
        self.assertIn(("VSU.EmailEnabled", "false"), model.setting_writes)
        self.assertIn(
            ("VSU.VolunteerApplicationInvolvementId", "700"),
            model.setting_writes,
        )
        self.assertIn(
            (
                "VSU.BackgroundCheckServiceCodes",
                "BG100,BG200",
            ),
            model.setting_writes,
        )
        self.assertIn(
            ("VSU.MVRServiceCodes", "MVR100"), model.setting_writes
        )
        self.assertIn(
            ("VSU.MVRCheckValidMonths", "12"), model.setting_writes
        )
        self.assertIn("<strong>Saved</strong>", output)

    def test_admin_blocks_write_enable_until_extra_value_is_ready(self):
        model, output = execute_admin_post(confirm_enable=True, ready=False)
        self.assertEqual(model.setting_writes, [])
        self.assertIn("readiness must pass", output)

    def test_admin_requires_background_check_service_codes(self):
        model, output = execute_admin_post(
            confirm_enable=True, background_codes=""
        )
        self.assertEqual(model.setting_writes, [])
        self.assertIn(
            "At least one service code",
            output,
        )

    def test_admin_requires_mvr_service_codes_and_rejects_overlap(self):
        model, output = execute_admin_post(
            confirm_enable=True, mvr_codes=""
        )
        self.assertEqual(model.setting_writes, [])
        self.assertIn("At least one service code", output)

        model, output = execute_admin_post(
            confirm_enable=True,
            background_codes="BG100,MVR100",
            mvr_codes="MVR100",
        )
        self.assertEqual(model.setting_writes, [])
        self.assertIn("cannot overlap: MVR100", output)

    def test_diagnostic_checks_definition_and_storage_without_people(self):
        self.assertIn('model.TextContent("StandardExtraValues2")', self.diagnostic)
        self.assertIn("Approved for Role Stored Values", self.diagnostic)
        self.assertIn("Approved for Role Duplicate Record Check", self.diagnostic)
        self.assertIn("Ineligible Volunteer", self.diagnostic)
        self.assertIn('"Denied"', self.diagnostic)
        self.assertIn('"MissingInfo"', self.diagnostic)
        self.assertIn('"PrimaryVolunteerMVR"', self.diagnostic)
        expected_options = self.diagnostic.split("expected = [", 1)[1].split(
            "]", 1
        )[0]
        self.assertNotIn("NotApproved", expected_options)
        section = self.diagnostic.split(
            '"Approved for Role Stored Values"', 1
        )[1].split("sections.append", 1)[0]
        self.assertIn("COUNT(DISTINCT PeopleId)", section)
        self.assertNotIn("Name2", section)
        self.assertNotIn("EmailAddress", section)


if __name__ == "__main__":
    unittest.main()
