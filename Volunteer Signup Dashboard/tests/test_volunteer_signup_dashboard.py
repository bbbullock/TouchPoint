import datetime
import ast
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest


PROJECT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT / "VolunteerSignupDashboard.py"


def load_module():
    spec = importlib.util.spec_from_file_location("volunteer_signup_dashboard", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class VolunteerSignupDashboardTests(unittest.TestCase):
    def setUp(self):
        self.app = load_module()

    def test_form_options_are_authoritative_and_keep_empty_shift(self):
        options = self.app.parse_registration_options(json.dumps([
            {"Text": "Friday 9:00 AM", "Value": "509:900am", "Limit": 2},
            {"Text": "Friday 11:00 AM", "Value": "509:1100am", "Limit": 3},
        ]))
        rows = [SimpleNamespace(SubGroupName="509:900am", PeopleId=10,
                                MemberName="Able, Amy", EmailAddress="amy@example.org")]
        shifts = self.app.build_shift_catalog(options, rows)
        self.assertEqual(2, len(shifts))
        self.assertEqual(1, shifts[0]["count"])
        self.assertEqual(0, shifts[1]["count"])
        self.assertEqual(3, shifts[1]["remaining"])

    def test_signup_matching_is_case_insensitive_and_deduplicates_people(self):
        options = self.app.parse_registration_options('[{"Text":"Shift","Value":"A:Shift"}]')
        rows = [
            SimpleNamespace(SubGroupName="a:shift", PeopleId=7, MemberName="Zulu", EmailAddress="z@example.org"),
            SimpleNamespace(SubGroupName="A:SHIFT", PeopleId=7, MemberName="Zulu", EmailAddress="z@example.org"),
        ]
        shifts = self.app.build_shift_catalog(options, rows)
        self.assertEqual(1, shifts[0]["count"])

    def test_volunteers_are_sorted_by_last_name_for_both_name_formats(self):
        options = self.app.parse_registration_options('[{"Text":"Shift","Value":"A"}]')
        rows = [
            SimpleNamespace(SubGroupName="A", PeopleId=1, MemberName="Amy Young", EmailAddress=""),
            SimpleNamespace(SubGroupName="A", PeopleId=2, MemberName="Zulu, Zoe", EmailAddress=""),
            SimpleNamespace(SubGroupName="A", PeopleId=3, MemberName="Carlos Baker Jr.", EmailAddress=""),
            SimpleNamespace(SubGroupName="A", PeopleId=4, MemberName="Able, Alex", EmailAddress=""),
        ]

        shifts = self.app.build_shift_catalog(options, rows)

        self.assertEqual(["Able, Alex", "Carlos Baker Jr.", "Amy Young", "Zulu, Zoe"],
                         [item["name"] for item in shifts[0]["volunteers"]])

    def test_duplicate_form_values_are_rejected(self):
        raw = '[{"Text":"One","Value":"Shift"},{"Text":"Two","Value":"shift"}]'
        with self.assertRaisesRegex(ValueError, "more than once"):
            self.app.parse_registration_options(raw)

    def test_invalid_and_negative_limits_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "non-negative"):
            self.app.parse_registration_options('[{"Text":"One","Value":"Shift","Limit":-1}]')
        with self.assertRaisesRegex(ValueError, "non-negative"):
            self.app.parse_registration_options('[{"Text":"One","Value":"Shift","Limit":"many"}]')

    def test_exclusions_use_exact_case_insensitive_values(self):
        options = self.app.parse_registration_options('[{"Text":"Unknown","Value":"? 99"},{"Text":"Real","Value":"510:9am"}]')
        shifts = self.app.build_shift_catalog(options, [], ["? 99"])
        self.assertEqual(["510:9am"], [shift["subgroup"] for shift in shifts])

    def test_question_identity_uses_stable_id(self):
        rows = [SimpleNamespace(Id=4, Question="Choose a shift", Options='[{"Text":"A","Value":"509:A"}]')]
        questions = self.app.registration_questions(rows, "Event 2026")
        self.assertEqual("Id:4", questions[0]["key"])
        self.assertEqual("Choose a shift", questions[0]["label"])

    def test_question_selector_filters_non_subgroups_and_sorts_by_date(self):
        rows = [
            SimpleNamespace(Id=1, Question="Saturday shifts",
                            Options='[{"Text":"Late","Value":"510:9am"}]'),
            SimpleNamespace(Id=2, Question="Friday shifts",
                            Options='[{"Text":"Early","Value":"509:9am"}]'),
            SimpleNamespace(Id=3, Question="Ordinary answer",
                            Options='[{"Text":"Yes","Value":"Yes"}]'),
            SimpleNamespace(Id=4, Question="Text only",
                            Options='[{"Text":"Comment"}]'),
        ]
        questions = self.app.registration_questions(rows, "Event 2026")
        self.assertEqual(["Id:2", "Id:1"], [question["key"] for question in questions])

    def test_saved_document_is_versioned(self):
        self.assertEqual({"version": 1, "profiles": []}, self.app.load_document_from_text(""))
        with self.assertRaisesRegex(ValueError, "unsupported version"):
            self.app.load_document_from_text('{"version":2,"profiles":[]}')

    def test_profile_privacy_defaults_hide_email(self):
        profile = self.app.build_profile({
            "profile_name": "Flea Market",
            "organization_id": 42,
            "question_key": "Id:8",
            "report_title": "",
            "excluded_values": "",
        }, now=datetime.datetime(2026, 8, 12, 10, 30), user_people_id=577)
        self.assertFalse(profile["include_member_emails"])
        self.assertTrue(profile["include_member_names"])
        self.assertEqual(577, profile["last_saved_people_id"])

    def test_email_display_requires_member_names(self):
        with self.assertRaisesRegex(ValueError, "names must be displayed"):
            self.app.build_profile({
                "profile_name": "Private",
                "organization_id": 42,
                "question_key": "Id:8",
                "include_member_names": False,
                "include_member_emails": True,
            }, now=datetime.datetime(2026, 8, 12))

    def test_update_preserves_stable_profile_id(self):
        existing = {"id": "stable-123"}
        profile = self.app.build_profile({
            "profile_name": "Updated",
            "organization_id": 42,
            "question_key": "Id:8",
        }, existing=existing, now=datetime.datetime(2026, 8, 12))
        self.assertEqual("stable-123", profile["id"])

    def test_changed_name_saves_as_new_instead_of_overwriting_loaded_profile(self):
        profiles = [{
            "id": "first-1", "name": "First", "organization_id": 42,
            "question_keys": ["Id:8"],
        }]

        self.assertIs(profiles[0],
                      self.app.existing_profile_for_save(profiles, "first-1", "First"))
        self.assertIsNone(
            self.app.existing_profile_for_save(profiles, "first-1", "Second"))

    def test_delete_requires_matching_stable_id_confirmation(self):
        document = {"version": 1, "profiles": [{
            "id": "alpha-1", "name": "Alpha", "organization_id": 1, "question_key": "Id:2"
        }]}
        with self.assertRaisesRegex(ValueError, "not confirmed"):
            self.app.delete_profile_from_document(document, "alpha-1", "Alpha")
        deleted = self.app.delete_profile_from_document(document, "alpha-1", "alpha-1")
        self.assertEqual("Alpha", deleted["name"])
        self.assertEqual([], document["profiles"])

    def test_html_escaping_covers_attributes_and_member_data(self):
        self.assertEqual("&lt;x&gt;&quot;&#39;&amp;", self.app.html_escape('<x>"\'&'))
        options = self.app.parse_registration_options('[{"Text":"<Shift>","Value":"A"}]')
        rows = [SimpleNamespace(SubGroupName="A", PeopleId=1,
                                MemberName='<script>alert(1)</script>', EmailAddress='x"@example.org')]
        shifts = self.app.build_shift_catalog(options, rows)
        profile = self.app.build_profile({
            "profile_name": "Test", "organization_id": 1, "question_key": "Id:1",
            "include_member_names": True, "include_member_emails": True,
            "privacy_acknowledged": True,
        }, now=datetime.datetime(2026, 8, 12))
        html = self.app.render_report(profile, {"id": 1, "name": "Org"},
                                      [{"label": "Question"}], shifts)
        self.assertNotIn("<script>alert", html)
        self.assertIn("&lt;script&gt;alert", html)
        self.assertIn("x&quot;@example.org", html)

    def test_volunteer_names_use_accessible_per_shift_disclosure(self):
        options = self.app.parse_registration_options(
            '[{"Text":"Busy shift","Value":"509:9am","Limit":12}]')
        rows = []
        for number in range(1, 11):
            rows.append(SimpleNamespace(
                SubGroupName="509:9am", PeopleId=number,
                MemberName="Volunteer {0:02d}".format(number), EmailAddress=""))
        shifts = self.app.build_shift_catalog(options, rows)
        profile = self.app.build_profile({
            "profile_name": "Disclosure", "organization_id": 1,
            "question_key": "Id:1", "include_member_names": True,
        }, now=datetime.datetime(2026, 8, 12))

        html = self.app.render_report(profile, {"id": 1, "name": "Event 2026"},
                                      [{"label": "Shifts"}], shifts)

        self.assertIn('aria-expanded="false"', html)
        self.assertIn('aria-controls="vsud-volunteers-1"', html)
        self.assertIn('id="vsud-volunteers-1" class="vsud-volunteer-detail vsud-collapsed"', html)
        self.assertIn('View volunteers</span> (10)', html)
        self.assertIn('<li>Volunteer 01</li>', html)
        self.assertIn('<li>Volunteer 10</li>', html)
        self.assertIn('label.textContent=expanded?"View volunteers":"Hide volunteers"', html)
        self.assertIn('panel.className=expanded?"vsud-volunteer-detail vsud-collapsed"', html)
        self.assertIn('.vsud-volunteer-detail{display:table-row!important}', html)

    def test_empty_shift_has_no_useless_volunteer_disclosure(self):
        options = self.app.parse_registration_options(
            '[{"Text":"Empty shift","Value":"509:9am"}]')
        shifts = self.app.build_shift_catalog(options, [])
        profile = self.app.build_profile({
            "profile_name": "Empty", "organization_id": 1,
            "question_key": "Id:1", "include_member_names": True,
        }, now=datetime.datetime(2026, 8, 12))

        html = self.app.render_report(profile, {"id": 1, "name": "Event 2026"},
                                      [{"label": "Shifts"}], shifts)

        self.assertIn('<td class="vsud-members">No volunteers</td>', html)
        self.assertNotIn('aria-controls="vsud-volunteers-1"', html)

    def test_capacity_columns_are_hidden_when_no_shift_has_a_limit(self):
        options = self.app.parse_registration_options(
            '[{"Text":"Morning","Value":"509:9am"},'
            '{"Text":"Afternoon","Value":"509:1pm"}]')
        shifts = self.app.build_shift_catalog(options, [])
        profile = self.app.build_profile({
            "profile_name": "No limits", "organization_id": 1,
            "question_key": "Id:1", "include_member_names": True,
        }, now=datetime.datetime(2026, 8, 12))

        html = self.app.render_report(profile, {"id": 1, "name": "Event 2026"},
                                      [{"label": "Shifts"}], shifts)

        self.assertNotIn("<th>Limit</th>", html)
        self.assertNotIn("<th>Remaining</th>", html)
        self.assertIn('class="vsud-date-row"><th colspan="3"', html)

    def test_capacity_columns_remain_when_any_shift_has_a_limit(self):
        options = self.app.parse_registration_options(
            '[{"Text":"No limit","Value":"509:9am"},'
            '{"Text":"Limited","Value":"509:1pm","Limit":4}]')
        shifts = self.app.build_shift_catalog(options, [])
        profile = self.app.build_profile({
            "profile_name": "Mixed limits", "organization_id": 1,
            "question_key": "Id:1", "include_member_names": False,
        }, now=datetime.datetime(2026, 8, 12))

        html = self.app.render_report(profile, {"id": 1, "name": "Event 2026"},
                                      [{"label": "Shifts"}], shifts)

        self.assertIn("<th>Limit</th><th>Remaining</th>", html)
        self.assertIn('class="vsud-date-row"><th colspan="4"', html)

    def test_expanded_volunteer_details_use_smaller_type(self):
        source = SCRIPT.read_text()
        self.assertIn(".vsud-volunteer-detail td{background:#eef5fb;padding:10px 16px 12px;font-size:.84em}", source)
        self.assertIn(".vsud-volunteer-heading{color:#244b6b;font-size:.9em", source)

    def test_volunteer_columns_flow_down_then_across_and_balance(self):
        source = SCRIPT.read_text()
        self.assertIn(".vsud-volunteer-list{columns:2;column-fill:balance;", source)
        self.assertIn(".vsud-volunteer-list li{break-inside:avoid;", source)
        self.assertIn("@media(max-width:760px){.vsud-volunteer-list{columns:1}", source)
        self.assertNotIn("grid-template-columns:repeat(2,minmax(0,1fr));gap:4px 24px", source)

    def test_report_summary_counts_unique_people_across_shifts(self):
        options = self.app.parse_registration_options('[{"Text":"A","Value":"A","Limit":2},{"Text":"B","Value":"B","Limit":2}]')
        rows = [
            SimpleNamespace(SubGroupName="A", PeopleId=1, MemberName="One", EmailAddress=""),
            SimpleNamespace(SubGroupName="B", PeopleId=1, MemberName="One", EmailAddress=""),
            SimpleNamespace(SubGroupName="B", PeopleId=2, MemberName="Two", EmailAddress=""),
        ]
        summary = self.app.report_summary(self.app.build_shift_catalog(options, rows))
        self.assertEqual(2, summary["unique_volunteers"])
        self.assertEqual(3, summary["shift_signups"])
        self.assertEqual(1, summary["vacancies"])

    def test_script_uses_touchpoint_directive_as_authorization_gate(self):
        source = SCRIPT.read_text()
        self.assertIn("#Roles=Access", source)
        self.assertNotIn("model.UserIsInRole", source)
        self.assertIn('action="/PyScriptForm/VolunteerSignupDashboard"', source)
        self.assertIn('value="inspect" formnovalidate', source)
        self.assertIn('id="vsudQuestionList"', source)
        self.assertIn("function clearQuestions()", source)
        self.assertIn("questionList.innerHTML=", source)
        self.assertIn('values["question_keys"] = [item["key"] for item in questions]', source)
        self.assertIn('value="load_profile" formnovalidate', source)
        self.assertIn('value="preview" formtarget="_blank"', source)
        self.assertIn('class="btn btn-primary" onclick="window.print()">Print Report', source)
        self.assertIn('Discard unsaved changes and load another configuration?', source)
        self.assertIn('id="vsudContactNotice"', source)
        self.assertIn("Show stored subgroup values and questions", source)
        self.assertIn('aria-label="Remove selected Involvement"', source)
        self.assertIn("No matching Involvements.", source)
        self.assertIn("body *{visibility:hidden!important}", source)
        self.assertIn('font-family:"Helvetica Neue",Helvetica,Arial,sans-serif', source)
        self.assertIn(".vsud-volunteer-detail{display:table-row!important}", source)
        self.assertIn("@media(max-width:760px)", source)
        self.assertIn("model.Form = content", source)
        tree = ast.parse(source)
        self.assertFalse(any(isinstance(node, ast.JoinedStr) for node in ast.walk(tree)))
        self.assertNotIn("model.AddMember", source)
        self.assertNotIn("model.Update", source)

    def test_app_version_is_tracked_in_code_header_and_displayed(self):
        source = SCRIPT.read_text()
        self.assertEqual("1.0.0", self.app.APP_VERSION)
        self.assertIn("# Version: 1.0.0", source)
        self.assertIn("# Written by: Brian Bullock with Codex assistance", source)
        self.assertIn("# Email: bbbullock@mac.com", source)
        self.assertIn("# GitHub: https://github.com/bbbullock/TouchPoint", source)
        self.assertIn("# Version history", source)
        self.assertIn("# 1.0.0 (2026-08-15)", source)
        html = self.app.render_page(self.app.empty_document(),
                                    self.app.profile_form_values(), [])
        self.assertIn("Volunteer Signup Dashboard <small>v1.0.0</small>", html)
        self.assertNotIn("beta", html.lower())

    def test_initial_ui_state_follows_safe_defaults(self):
        values = self.app.profile_form_values()
        initial = self.app.render_page(self.app.empty_document(), values, [])
        self.assertIn('name="includeMemberEmails" id="vsudIncludeEmails" value="true">', initial)
        self.assertIn('id="vsudContactNotice" style="display:none"', initial)
        self.assertIn('name="privacyAcknowledged"', initial)
        self.assertIn('value="save_profile">Save configuration', initial)
        self.assertNotIn('value="save_profile" disabled', initial)
        self.assertIn('value="delete_profile" disabled', initial)

    def test_inspect_button_is_beneath_involvement_and_before_questions(self):
        html = self.app.render_page(self.app.empty_document(),
                                    self.app.profile_form_values(), [])
        selected_position = html.index('id="vsudSelectedOrg"')
        inspect_position = html.index('value="inspect"')
        questions_position = html.index('id="vsudQuestionList"')
        actions_position = html.index('<div class="vsud-actions">')

        self.assertLess(selected_position, inspect_position)
        self.assertLess(inspect_position, questions_position)
        self.assertLess(questions_position, actions_position)
        self.assertEqual(1, html.count('value="inspect"'))

    def test_question_list_clears_when_involvement_changes(self):
        values = self.app.profile_form_values()
        values["organization_id"] = 42
        values["organization_name"] = "Old Involvement"
        values["question_keys"] = ["Id:8"]
        html = self.app.render_page(
            self.app.empty_document(), values,
            [{"key": "Id:8", "label": "Old shifts", "option_count": 2}])

        self.assertIn("function clearQuestions()", html)
        self.assertIn("input.value='';clearQuestions();dirty=true;", html)
        self.assertIn("selected.innerHTML='<span class=\"vsud-help\">No Involvement selected</span>';clearQuestions();", html)

    def test_email_display_requires_privacy_acknowledgement(self):
        with self.assertRaisesRegex(ValueError, "Contact Information Notice"):
            self.app.build_profile({
                "profile_name": "Contact report", "organization_id": 1,
                "question_key": "Id:1", "include_member_names": True,
                "include_member_emails": True, "privacy_acknowledged": False,
            }, now=datetime.datetime(2026, 8, 12))

    def test_signup_query_uses_parameters_for_form_values(self):
        source = SCRIPT.read_text()
        self.assertIn('parameters[name] = value', source)
        self.assertIn('mt.Name IN ({0})', source)
        self.assertNotIn("DELETE FROM", source.upper())

    def test_simulated_touchpoint_save_preview_and_delete_flow(self):
        class FakeModel:
            UserPeopleId = 577

            def __init__(self):
                self.content = ""

            def TextContent(self, key):
                return self.content

            def WriteContentText(self, key, value, notes):
                self.content = value

        class FakeQuery:
            def QuerySql(self, sql, parameters):
                if "FROM dbo.Organizations" in sql:
                    return [SimpleNamespace(OrganizationId=42,
                                            OrganizationName="Sample Signup",
                                            OrganizationStatusId=30)]
                if "FROM dbo.RegQuestion" in sql:
                    return [
                        SimpleNamespace(
                            Id=8, Question="Choose a shift",
                            Options='[{"Text":"Afternoon","Value":"510:1pm","Limit":2},'
                                    '{"Text":"Morning","Value":"509:9am","Limit":2}]'),
                        SimpleNamespace(
                            Id=9, Question="Choose setup",
                            Options='[{"Text":"Setup","Value":"509:7am","Limit":4}]'),
                    ]
                if "FROM dbo.MemberTags" in sql:
                    return [SimpleNamespace(SubGroupName="509:9am", PeopleId=10,
                                            MemberName="Able, Amy",
                                            EmailAddress="amy@example.org")]
                raise AssertionError(sql)

        app = self.app
        app.model = FakeModel()
        app.q = FakeQuery()
        app.Data = SimpleNamespace(
            VSUDAction="save_profile", profileId="", profileName="Sample",
            reportTitle="Sample Dashboard", organizationId="42",
            questionKeys="Id:8,Id:9",
            excludedValues="", includeMemberNames="true",
            includeMemberEmails="", showSubgroupNames="true")
        saved_html = app.run_app()
        self.assertIn("Configuration saved", saved_html)
        document = json.loads(app.model.content)
        profile_id = document["profiles"][0]["id"]
        self.assertEqual(["Id:8", "Id:9"], document["profiles"][0]["question_keys"])

        app.Data.profileId = profile_id
        app.Data.profileName = "Second Sample"
        app.Data.reportTitle = "Second Sample Dashboard"
        second_saved_html = app.run_app()
        self.assertIn("Configuration saved", second_saved_html)
        document = json.loads(app.model.content)
        self.assertEqual(["Sample", "Second Sample"],
                         [profile["name"] for profile in document["profiles"]])
        self.assertIn(">Sample</option>", second_saved_html)
        self.assertIn(">Second Sample</option>", second_saved_html)

        second_profile_id = [profile["id"] for profile in document["profiles"]
                             if profile["name"] == "Second Sample"][0]
        app.Data.profileId = second_profile_id
        app.Data.reportTitle = "Updated Second Sample Dashboard"
        updated_html = app.run_app()
        self.assertIn("Configuration saved", updated_html)
        document = json.loads(app.model.content)
        self.assertEqual(2, len(document["profiles"]))
        self.assertEqual("Updated Second Sample Dashboard",
                         [profile for profile in document["profiles"]
                          if profile["id"] == second_profile_id][0]["report_title"])

        app.Data.VSUDAction = "preview"
        app.Data.profileId = second_profile_id
        preview_html = app.run_app()
        self.assertIn("Updated Second Sample Dashboard", preview_html)
        self.assertNotIn('<form action="/PyScriptForm/VolunteerSignupDashboard"', preview_html)
        self.assertIn("Print Report", preview_html)
        self.assertIn("Afternoon", preview_html)
        self.assertIn("Setup", preview_html)
        self.assertIn("Question: Choose setup", preview_html)
        self.assertLess(preview_html.index("Saturday, May 9, 2026"),
                        preview_html.index("Sunday, May 10, 2026"))
        self.assertIn('class="vsud-vacancy"', preview_html)
        self.assertIn("vsud-metric-danger", preview_html)

        app.Data = SimpleNamespace(VSUDAction="delete_profile", profileId=second_profile_id,
                                   deleteConfirmation=second_profile_id)
        deleted_html = app.run_app()
        self.assertIn("Configuration deleted", deleted_html)
        self.assertEqual(["Sample"], [profile["name"] for profile in
                                    json.loads(app.model.content)["profiles"]])

        app.Data = SimpleNamespace(VSUDAction="search_involvements", term="Sample")
        search_result = json.loads(app.run_app())
        self.assertEqual([{"id": 42, "name": "Sample Signup"}], search_result["items"])

    def test_multiple_questions_are_combined_in_selected_order(self):
        questions = [
            {"label": "Meals", "options_raw": '[{"Text":"Lunch","Value":"M:lunch"}]'},
            {"label": "Setup", "options_raw": '[{"Text":"Tables","Value":"S:tables"}]'},
        ]
        options = self.app.combined_options(questions)
        self.assertEqual(["M:lunch", "S:tables"], [item["subgroup"] for item in options])
        self.assertEqual(["Meals", "Setup"], [item["question_label"] for item in options])

    def test_duplicate_subgroup_across_questions_is_rejected(self):
        questions = [
            {"label": "First", "options_raw": '[{"Text":"A","Value":"same"}]'},
            {"label": "Second", "options_raw": '[{"Text":"B","Value":"SAME"}]'},
        ]
        with self.assertRaisesRegex(ValueError, "cannot be matched unambiguously"):
            self.app.combined_options(questions)

    def test_legacy_single_question_profile_remains_valid(self):
        profile = {"id": "old", "name": "Old", "organization_id": 4,
                   "question_key": "Id:7", "question_label": "Shift"}
        self.assertTrue(self.app.valid_profile(profile))
        values = self.app.profile_form_values(profile)
        self.assertEqual(["Id:7"], values["question_keys"])

    def test_involvement_search_is_parameterized_and_form_scoped(self):
        source = SCRIPT.read_text()
        self.assertIn('VSUDAction=search_involvements', source)
        self.assertIn('o.OrganizationName LIKE @LikeTerm', source)
        self.assertIn('rq.OrganizationId = o.OrganizationId', source)
        self.assertIn('placeholder="Search by Involvement name or ID"', source)

    def test_date_groups_sort_dates_and_shift_times(self):
        options = self.app.parse_registration_options(json.dumps([
            {"Text": "Saturday", "Value": "510:900am"},
            {"Text": "Friday Late", "Value": "509:1pm"},
            {"Text": "Friday Early", "Value": "509:700am"},
        ]))
        shifts = self.app.build_shift_catalog(options, [])
        groups = self.app.date_groups(shifts, "Flea Market 2026",
                                      today=datetime.date(2025, 1, 1))
        self.assertEqual(["2026-05-09", "2026-05-10"],
                         [group["key"] for group in groups])
        self.assertEqual(["Friday Early", "Friday Late"],
                         [shift["label"] for shift in groups[0]["shifts"]])

    def test_supported_subgroup_date_formats(self):
        today = datetime.date(2026, 1, 1)
        self.assertEqual(datetime.date(2026, 5, 9),
                         self.app.subgroup_date("509:9am", "Event 2026", today))
        self.assertEqual(datetime.date(2027, 11, 2),
                         self.app.subgroup_date("11/2/2027:9am", "Event", today))
        self.assertEqual(datetime.date(2028, 5, 9),
                         self.app.subgroup_date("2028-05-09:9am", "Event", today))

    def test_unrecognized_date_values_are_grouped_last(self):
        options = self.app.parse_registration_options(json.dumps([
            {"Text": "Unknown", "Value": "other:shift"},
            {"Text": "Dated", "Value": "509:9am"},
        ]))
        groups = self.app.date_groups(self.app.build_shift_catalog(options, []),
                                      "Event 2026")
        self.assertEqual(["2026-05-09", "unknown"], [group["key"] for group in groups])
        self.assertEqual("Other shifts", groups[-1]["label"])

    def test_hidden_technical_details_omit_subgroup_and_question_names(self):
        questions = [
            {"label": "First question", "options_raw": '[{"Text":"Morning","Value":"509:9am"}]'},
            {"label": "Second question", "options_raw": '[{"Text":"Afternoon","Value":"509:1pm"}]'},
        ]
        shifts = self.app.build_shift_catalog(self.app.combined_options(questions), [])
        profile = self.app.build_profile({
            "profile_name": "Simple", "organization_id": 1,
            "question_keys": ["Id:1", "Id:2"], "report_title": "Simple",
            "show_subgroup_names": False,
        }, now=datetime.datetime(2026, 8, 12))
        html = self.app.render_report(profile, {"id": 1, "name": "Event 2026"},
                                      questions, shifts)
        self.assertNotIn("Subgroup:", html)
        self.assertNotIn("Question:", html)
        self.assertNotIn("First question", html)
        self.assertNotIn("Second question", html)


if __name__ == "__main__":
    unittest.main()
