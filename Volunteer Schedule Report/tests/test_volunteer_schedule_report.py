import datetime
import contextlib
import html
import io
import pathlib
import sys
import types
import unittest


PROJECT = pathlib.Path(__file__).resolve().parents[1]
REPORT_PATH = PROJECT / "VolunteerScheduleReport.py"
ADMIN_PATH = PROJECT / "VolunteerScheduleReportAdmin.py"
DIAGNOSTIC_PATH = PROJECT / "VolunteerScheduleReportDiagnostic.py"
SQL_DIAGNOSTIC_PATH = PROJECT / "VolunteerScheduleReportDiagnostic.sql"
ASSIGNMENT_DIAGNOSTIC_PATH = PROJECT / "VolunteerScheduleAssignmentDiagnostic.sql"


def load_report_functions():
    source = REPORT_PATH.read_text(encoding="utf-8")
    source = source.split("# TouchPoint runtime helpers and entry point")[0]
    if "cgi" not in sys.modules:
        module = types.ModuleType("cgi")
        import html
        module.escape = html.escape
        sys.modules["cgi"] = module
    namespace = {}
    exec(compile(source, str(REPORT_PATH), "exec"), namespace)
    return namespace


class Row:
    def __init__(self, **values):
        self.__dict__.update(values)


class VolunteerScheduleCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ns = load_report_functions()

    def row(self, people_id, status, name, org_id=10, team_id=100,
            subgroup_id=0, needed=4, subgroup=""):
        return Row(
            OrganizationId=org_id,
            OrganizationName="Worship Volunteers" if org_id == 10 else "Welcome Team",
            MeetingId=500 + org_id,
            MeetingDateTime=datetime.datetime(2026, 8, 7, 18, 0),
            Location="Sanctuary",
            TimeSlotMeetingTeamId=team_id,
            TimeSlotMeetingTeamSubGroupId=subgroup_id,
            TeamName="Production",
            SubGroupName=subgroup,
            NumberNeeded=needed,
            IsRequired=True,
            PeopleId=people_id,
            VolunteerName=name,
            EmailAddress=(name.lower().replace(" ", ".") + "@example.org") if people_id else "",
            CellPhone="555-0100" if people_id else "",
            Commitment=status,
        )

    def test_current_or_next_weekend(self):
        fn = self.ns["current_or_next_weekend"]
        self.assertEqual(fn(datetime.date(2026, 8, 3)),
                         (datetime.date(2026, 8, 7), datetime.date(2026, 8, 9)))
        self.assertEqual(fn(datetime.date(2026, 8, 7)),
                         (datetime.date(2026, 8, 7), datetime.date(2026, 8, 9)))
        self.assertEqual(fn(datetime.date(2026, 8, 9)),
                         (datetime.date(2026, 8, 7), datetime.date(2026, 8, 9)))

    def test_monday_batch_targets_upcoming_weekend(self):
        fn = self.ns["next_weekend_from_monday"]
        self.assertEqual(fn(datetime.date(2026, 8, 3)),
                         (datetime.date(2026, 8, 7), datetime.date(2026, 8, 9)))

    def test_central_timezone_is_explicit(self):
        self.assertEqual(self.ns["WINDOWS_TIME_ZONE_ID"], "Central Standard Time")

    def test_sql_datetime_converts_date_to_midnight_datetime(self):
        value = self.ns["sql_datetime"](datetime.date(2026, 8, 7))
        self.assertEqual(value, datetime.datetime(2026, 8, 7, 0, 0, 0))

    def test_parse_ids_accepts_csv_and_profile_lists(self):
        parse_ids = self.ns["parse_ids"]
        self.assertEqual(parse_ids("3, 2;3,bad"), [3, 2])
        self.assertEqual(parse_ids([8, "9", 8]), [8, 9])

    def test_commitment_mapping(self):
        details = self.ns["commitment_details"]
        self.assertEqual(details(1)[:3], ("Committed", True, True))
        self.assertEqual(details(None)[:3], ("Scheduled", True, True))
        self.assertEqual(details(4)[:3], ("Substitute", True, True))
        self.assertEqual(details(2)[:3], ("Find Sub", False, False))
        self.assertEqual(details(3)[:3], ("Sub Found", False, False))
        self.assertEqual(details(0)[:3], ("Regrets", False, False))

    def test_slots_count_coverage_and_substitute_warning(self):
        rows = [
            self.row(1, 1, "Alex Able"),
            self.row(2, 99, "Bailey Baker"),
            self.row(3, 4, "Casey Cover"),
            self.row(4, 2, "Devon Needs Sub"),
            self.row(5, 3, "Evan Replaced"),
            self.row(6, 0, "Frank Regrets"),
        ]
        slots = self.ns["build_slots"](rows)
        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0]["filled"], 3)
        self.assertEqual(slots[0]["open"], 1)
        self.assertEqual([v["status"] for v in slots[0]["volunteers"]],
                         ["Committed", "Scheduled", "Substitute", "Find Sub"])
        self.assertEqual(len(slots[0]["warnings"]), 1)

    def test_report_summary_counts_unique_people_by_commitment_state(self):
        rows = [
            self.row(1, 1, "Alex Able"),
            self.row(2, 4, "Bailey Baker"),
            self.row(3, 99, "Casey Current"),
            self.row(4, 2, "Devon Needs Sub"),
            self.row(5, 0, "Evan Regrets"),
        ]
        slots = self.ns["build_slots"](rows)
        self.assertEqual(self.ns["report_summary"](slots), (4, 2, 1, 1, 1))

    def test_report_summary_deduplicates_people_across_roles(self):
        rows = [
            self.row(1, 1, "Alex Able", subgroup_id=70, subgroup="Camera"),
            self.row(1, 1, "Alex Able", subgroup_id=71, subgroup="Audio"),
        ]
        self.assertEqual(self.ns["report_summary"](self.ns["build_slots"](rows)),
                         (1, 1, 0, 6, 0))

    def test_report_summary_sums_vacancies_across_slots(self):
        rows = [
            self.row(1, 1, "Alex Able", needed=2, subgroup_id=70, subgroup="Camera"),
            self.row(2, 1, "Bailey Baker", needed=3, subgroup_id=71, subgroup="Audio"),
        ]
        self.assertEqual(self.ns["report_summary"](self.ns["build_slots"](rows)),
                         (2, 2, 0, 3, 0))

    def test_latest_priority_deduplicates_person(self):
        rows = [self.row(1, 99, "Alex Able"), self.row(1, 1, "Alex Able")]
        slot = self.ns["build_slots"](rows)[0]
        self.assertEqual(len(slot["volunteers"]), 1)
        self.assertEqual(slot["volunteers"][0]["status"], "Committed")

    def test_inactive_meeting_assignment_is_not_counted(self):
        inactive = self.row(1, 1, "Alex Able", needed=1)
        inactive.MeetingVolunteerActive = False
        slot = self.ns["build_slots"]([inactive])[0]
        self.assertEqual(slot["filled"], 0)
        self.assertEqual(slot["open"], 1)
        self.assertEqual(slot["volunteers"], [])

    def test_is_sub_marks_active_coverage_as_substitute(self):
        substitute = self.row(1, 99, "Alex Able", needed=1)
        substitute.MeetingVolunteerActive = True
        substitute.IsSub = True
        slot = self.ns["build_slots"]([substitute])[0]
        self.assertEqual(slot["filled"], 1)
        self.assertEqual(slot["open"], 0)
        self.assertEqual(slot["volunteers"][0]["status"], "Substitute")

    def test_empty_slot_is_retained(self):
        slot = self.ns["build_slots"]([self.row(0, None, "", needed=2)])[0]
        self.assertEqual(slot["filled"], 0)
        self.assertEqual(slot["open"], 2)
        self.assertEqual(slot["volunteers"], [])

    def test_team_and_subgroup_make_distinct_jobs(self):
        rows = [
            self.row(1, 1, "Alex Able", subgroup_id=70, subgroup="Camera"),
            self.row(2, 1, "Bailey Baker", subgroup_id=71, subgroup="Audio"),
            self.row(3, 1, "Casey Cover", org_id=11, team_id=110),
        ]
        slots = self.ns["build_slots"](rows)
        self.assertEqual(len(slots), 3)
        self.assertEqual({slot["subgroup"] for slot in slots}, {"", "Audio", "Camera"})

    def test_recipient_list_excludes_find_sub_and_deduplicates_staff(self):
        rows = [self.row(1, 1, "Alex Able"), self.row(2, 2, "Bailey Baker")]
        slots = self.ns["build_slots"](rows)
        recipients = self.ns["recipient_people_ids"](slots, True, [1, 9])
        self.assertEqual(recipients, [1, 9])

    def test_report_escapes_contact_information(self):
        row = self.row(1, 1, "<Alex>")
        row.EmailAddress = 'alex+"test"@example.org'
        html = self.ns["render_report"](
            self.ns["build_slots"]([row]), datetime.date(2026, 8, 7),
            datetime.date(2026, 8, 9), "Weekend <Schedule>", False,
        )
        self.assertIn("&lt;Alex&gt;", html)
        self.assertIn("Weekend &lt;Schedule&gt;", html)
        self.assertNotIn('alex+"test"', html)

    def test_report_renders_updated_metrics_and_definitions(self):
        rows = [
            self.row(1, 1, "Alex Able"),
            self.row(2, 99, "Bailey Baker"),
            self.row(3, 2, "Casey Needs Sub"),
        ]
        report = self.ns["render_report"](
            self.ns["build_slots"](rows), datetime.date(2026, 8, 7),
            datetime.date(2026, 8, 9), "Weekend Schedule", False,
        )
        self.assertIn("Committed / Confirmed", report)
        self.assertIn("Awaiting Confirmation", report)
        self.assertIn("Vacancies", report)
        self.assertIn("Substitute Warning", report)
        self.assertIn("Understanding the report totals", report)
        summary = report.split('<div class="vsr-org">')[0]
        self.assertEqual(summary.count('<td'), 5)
        self.assertNotIn("open positions", summary)
        self.assertIn('<div class="vsr-gap"><strong>2 open positions</strong></div>',
                      report)

    def test_report_can_exclude_contact_columns(self):
        row = self.row(1, 1, "Alex Able")
        report = self.ns["render_report"](
            self.ns["build_slots"]([row]), datetime.date(2026, 8, 7),
            datetime.date(2026, 8, 9), "Weekend Schedule", False,
            False, False,
        )
        self.assertIn("Alex Able", report)
        self.assertNotIn("alex.able@example.org", report)
        self.assertNotIn("555-0100", report)
        self.assertNotIn("<th>Email</th>", report)
        self.assertNotIn("<th>Mobile phone</th>", report)

    def test_report_contact_columns_are_independent(self):
        row = self.row(1, 1, "Alex Able")
        report = self.ns["render_report"](
            self.ns["build_slots"]([row]), datetime.date(2026, 8, 7),
            datetime.date(2026, 8, 9), "Weekend Schedule", False,
            True, False,
        )
        self.assertIn("alex.able@example.org", report)
        self.assertNotIn("555-0100", report)
        self.assertIn("<th>Email</th>", report)
        self.assertNotIn("<th>Mobile phone</th>", report)

    def test_embedded_json_cannot_close_script_tag(self):
        encoded = self.ns["json_for_script"]([{"name": "</script><script>bad()</script>"}])
        self.assertNotIn("</script>", encoded.lower())

    def test_profile_document_requires_supported_version_and_scheduler(self):
        profiles = self.ns["profiles_from_document"]
        good = {"version": 1, "profiles": [{"id": "one", "name": "One", "scheduler_ids": [10]}]}
        bad = {"version": 2, "profiles": good["profiles"]}
        self.assertEqual(len(profiles(good)), 1)
        self.assertEqual(profiles(bad), [])

    def test_selected_profile_matches_stable_profile_id(self):
        profiles = [
            {"id": "one", "name": "First"},
            {"id": "two", "name": "Second"},
        ]
        self.assertEqual(self.ns["selected_profile"](profiles, "two")["name"],
                         "Second")
        self.assertIsNone(self.ns["selected_profile"](profiles, "missing"))

    def test_sql_uses_half_open_parameterized_window(self):
        sql = self.ns["SCHEDULE_SQL"]
        self.assertIn("tsm.MeetingDateTime >= @StartDate", sql)
        self.assertIn("tsm.MeetingDateTime < @EndDateExclusive", sql)
        self.assertIn("ISNULL(tssg.IsDeleted, 0) = 0", sql)
        self.assertIn("v.IsActive <> 0", sql)
        self.assertIn("v.DateServiceEnded IS NULL", sql)
        self.assertIn("ISNULL(tsm.IsDeleted, 0) = 0", sql)
        self.assertIn("ISNULL(tsmt.IsDeleted, 0) = 0", sql)
        self.assertIn("ISNULL(m.Canceled, 0) = 0", sql)
        self.assertIn("tsmv.IsActive AS MeetingVolunteerActive", sql)
        self.assertIn("tsmv.IsSub", sql)
        source = REPORT_PATH.read_text(encoding="utf-8")
        self.assertIn('"StartDate": sql_datetime(start_date)', source)
        self.assertIn('"EndDateExclusive": sql_datetime(', source)


class DeploymentSafetyTests(unittest.TestCase):
    def render_script_with_empty_touchpoint(self, path):
        module = types.ModuleType("cgi")
        module.escape = html.escape
        sys.modules["cgi"] = module

        class EmptyData:
            pass

        class MockModel:
            CmsHost = "https://example.tpsdb.com"
            ScriptName = "VolunteerScheduleReport"
            UserPeopleId = 1

            def Setting(self, key, default=""):
                return default

            def TextContent(self, key):
                return ""

            def UserIsInRole(self, role):
                return True

        class MockQuery:
            def QuerySql(self, *args, **kwargs):
                return []

        output = io.StringIO()
        namespace = {"model": MockModel(), "Data": EmptyData(), "q": MockQuery()}
        with contextlib.redirect_stdout(output):
            exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), namespace)
        return output.getvalue()

    def test_report_defaults_email_off_and_uses_state(self):
        source = REPORT_PATH.read_text(encoding="utf-8")
        self.assertIn('bool_setting("EmailEnabled", False)', source)
        self.assertIn("VolunteerScheduleReportState", source)
        self.assertIn('state["sent"].get(profile_id) == window_key', source)
        self.assertIn('#Roles=Access', source)
        self.assertIn('is_admin or is_manager', source)
        self.assertIn('runtime_action == "run_profiles" and not is_admin', source)
        self.assertIn("o.RegistrationTypeId = 22", source)
        self.assertIn('action="/PyScriptForm/VolunteerScheduleReport"', source)
        self.assertIn("model.Form = content", source)
        self.assertIn('email_is_enabled = bool_setting("EmailEnabled", False)', source)
        self.assertIn('id="vsrEmailButton"', source)
        self.assertIn("updateEmailButton", source)
        self.assertIn('id="vsrProfilePreset"', source)
        self.assertIn("profile_presets(profiles)", source)
        self.assertIn("Selecting a preset fills this form only", source)
        self.assertIn(".vsr-gap{background:#fde2e2", source)

    def test_admin_requires_privacy_confirmation_and_stable_ids(self):
        source = ADMIN_PATH.read_text(encoding="utf-8")
        self.assertIn('#Roles=Admin', source)
        self.assertIn('not acknowledged', source)
        self.assertIn('"staff_people_ids": staff_ids', source)
        self.assertIn('model.UserIsInRole("Admin")', source)
        self.assertIn('action="/PyScriptForm/VolunteerScheduleReportAdmin"', source)
        self.assertIn("model.Form = content", source)
        self.assertIn('"include_volunteer_email": include_email', source)
        self.assertIn('"include_volunteer_phone": include_phone', source)

    def test_interactive_pages_render_with_empty_mock_data(self):
        report = self.render_script_with_empty_touchpoint(REPORT_PATH)
        admin = self.render_script_with_empty_touchpoint(ADMIN_PATH)
        diagnostic = self.render_script_with_empty_touchpoint(DIAGNOSTIC_PATH)
        self.assertIn("Volunteer Schedule Report", report)
        self.assertIn("Saved Monday profiles", admin)
        self.assertIn("Run diagnostic", diagnostic)
        self.assertIn("Enter the ID", diagnostic)

    def test_diagnostic_is_read_only(self):
        source = DIAGNOSTIC_PATH.read_text(encoding="utf-8")
        self.assertIn("DEFAULT_INVOLVEMENT_ID = 0", source)
        function_source = source[source.index("def requested_org_id"):]
        self.assertLess(function_source.index('posted("OrganizationId")'),
                        function_source.index("DEFAULT_INVOLVEMENT_ID"))
        self.assertNotIn("for raw in", function_source.split("def render_rows")[0])
        self.assertNotIn("raise SystemExit", source)
        self.assertLess(source.rindex("def main"), source.rindex("\nmain()"))
        self.assertNotIn("\nif org_id:", source[source.rindex("\nmain()"):])
        self.assertNotIn("model.Email(", source)
        self.assertNotIn("model.SetSetting(", source)
        self.assertNotIn("model.WriteContentText(", source)

    def test_sql_diagnostic_is_read_only_and_hardcodes_involvement(self):
        source = SQL_DIAGNOSTIC_PATH.read_text(encoding="utf-8")
        upper = source.upper()
        self.assertIn("DECLARE @INVOLVEMENTID INT = 0", upper)
        self.assertIn("INFORMATION_SCHEMA.COLUMNS", upper)
        self.assertIn("REGISTRATIONTYPEID", upper)
        self.assertNotIn("\nINSERT ", upper)
        self.assertNotIn("\nUPDATE ", upper)
        self.assertNotIn("\nDELETE ", upper)
        self.assertNotIn("\nMERGE ", upper)

    def test_assignment_diagnostic_covers_scheduler_status_fields(self):
        source = ASSIGNMENT_DIAGNOSTIC_PATH.read_text(encoding="utf-8")
        upper = source.upper()
        self.assertIn("DECLARE @INVOLVEMENTID INT = 315", upper)
        self.assertIn("DATESERVICEENDED", upper)
        self.assertIn("VOLUNTEEROPTION", upper)
        self.assertIn("COMMITMENTSTATUS", upper)
        self.assertIn("ISSUB", upper)
        self.assertIn("NUMBERNEEDED", upper)
        self.assertNotIn("\nINSERT ", upper)
        self.assertNotIn("\nUPDATE ", upper)
        self.assertNotIn("\nDELETE ", upper)
        self.assertNotIn("\nMERGE ", upper)


if __name__ == "__main__":
    unittest.main()
