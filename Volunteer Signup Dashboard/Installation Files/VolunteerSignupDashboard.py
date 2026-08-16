#Roles=Access
# -*- coding: utf-8 -*-
# Application: Volunteer Signup Dashboard
# Version: 1.0.0
# Released: 2026-08-15
# Written by: Brian Bullock with Codex assistance
# Email: bbbullock@mac.com
# GitHub: https://github.com/bbbullock/TouchPoint
#
# Version history
# 1.0.0 (2026-08-15)
# - Builds reusable dashboards from Registration Form subgroup questions.
# - Supports Involvement lookup, multi-question profiles, and profile deletion.
# - Groups shifts chronologically and conditionally displays capacity columns.
# - Reveals alphabetized volunteer details through accessible shift controls.
# - Uses #Roles=Access as the sole interactive authorization authority.

"""Volunteer Signup Dashboard v1.0.0 for TouchPoint.

Registration Form options are the authoritative shift catalog. MemberTags and
OrgMemMemTags are consulted only to attach people who have actually selected a
shift. Consequently, a shift remains visible when nobody has selected it and
TouchPoint has not created its MemberTag yet.

The report is read-only with respect to TouchPoint source records. The only
writes are this extension's saved configurations in Text Content.
"""

import datetime
import json
import re


APP_VERSION = "1.0.0"
CONTENT_NAME = "VolunteerSignupDashboardProfiles"
DOCUMENT_VERSION = 1
MAX_OPTIONS = 200


def html_escape(value):
    text = str(value if value is not None else "")
    return (text.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;")
            .replace("'", "&#39;"))


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def truthy(value):
    return str(value or "").strip().lower() in ("1", "true", "yes", "y", "on")


def parse_keys(raw):
    if isinstance(raw, (list, tuple)):
        parts = raw
    else:
        parts = str(raw or "").replace(";", ",").split(",")
    values = []
    for part in parts:
        value = str(part or "").strip()
        if value and value not in values:
            values.append(value)
    return values


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
    return str(data_value("VSUDAction", data_value("action", "")) or "").strip().lower()


def row_value(row, names, default=None):
    for name in names:
        try:
            value = getattr(row, name)
            if value is not None:
                return value
        except Exception:
            pass
        try:
            value = row[name]
            if value is not None:
                return value
        except Exception:
            pass
    return default


def option_value(option, names, default=None):
    if not isinstance(option, dict):
        return default
    lowered = {}
    for key in option:
        lowered[str(key).lower()] = option[key]
    for name in names:
        if str(name).lower() in lowered:
            return lowered[str(name).lower()]
    return default


def parse_registration_options(raw):
    """Parse RegQuestion.Options into an ordered, unambiguous shift catalog."""
    if raw is None or not str(raw).strip():
        return []
    try:
        value = json.loads(str(raw))
    except Exception:
        raise ValueError("The selected Registration Form question has invalid Options JSON.")
    if isinstance(value, dict):
        value = option_value(value, ("options", "items"), [])
    if not isinstance(value, list):
        raise ValueError("The selected Registration Form question does not contain an option list.")
    if len(value) > MAX_OPTIONS:
        raise ValueError("The selected question has more than {0} options.".format(MAX_OPTIONS))

    results = []
    seen = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            continue
        subgroup = str(option_value(item, ("Value",), "") or "").strip()
        if not subgroup:
            continue
        match_key = subgroup.lower()
        if match_key in seen:
            raise ValueError("The Registration Form contains the subgroup value more than once: {0}".format(subgroup))
        seen.add(match_key)
        label = str(option_value(item, ("Text", "Label"), subgroup) or subgroup).strip()
        raw_limit = option_value(item, ("Limit",), None)
        limit = None
        if raw_limit is not None and str(raw_limit).strip() != "":
            limit = safe_int(raw_limit, -1)
            if limit < 0:
                raise ValueError("Shift limit must be a non-negative whole number for {0}.".format(subgroup))
        results.append({
            "order": index,
            "subgroup": subgroup,
            "label": label,
            "limit": limit,
        })
    return results


def parse_excluded_values(raw):
    text = str(raw or "").replace("\r", "\n").replace(";", "\n").replace(",", "\n")
    values = []
    seen = set()
    for part in text.split("\n"):
        value = part.strip()
        key = value.lower()
        if value and key not in seen:
            values.append(value)
            seen.add(key)
    return values


def question_identity(row):
    candidates = (
        ("RegQuestionId", ("RegQuestionId",)),
        ("QuestionId", ("QuestionId",)),
        ("Id", ("Id",)),
    )
    for prefix, names in candidates:
        value = row_value(row, names, None)
        if value is not None and str(value).strip():
            return "{0}:{1}".format(prefix, str(value).strip())
    return ""


def question_label(row, identity):
    value = row_value(row, ("Question", "Label", "Name", "Title", "Description"), "")
    text = str(value or "").strip()
    return text if text else "Registration question {0}".format(identity)


def registration_questions(rows, involvement_name=""):
    results = []
    seen = set()
    for row in rows:
        identity = question_identity(row)
        if not identity:
            continue
        if identity in seen:
            raise ValueError("Registration Form question identifiers are not unique.")
        options_raw = row_value(row, ("Options",), "")
        try:
            options = parse_registration_options(options_raw)
        except ValueError:
            continue
        dated_options = []
        for option in options:
            value = subgroup_date(option["subgroup"], involvement_name)
            if value is not None:
                dated_options.append(value)
        if not dated_options:
            continue
        seen.add(identity)
        results.append({
            "key": identity,
            "label": question_label(row, identity),
            "options_raw": str(options_raw or ""),
            "option_count": len(options),
            "first_date": min(dated_options).strftime("%Y-%m-%d"),
        })
    results.sort(key=lambda item: (item["first_date"], item["label"].lower(), item["key"]))
    return results


def selected_question(questions, key):
    wanted = str(key or "")
    for question in questions:
        if question["key"] == wanted:
            return question
    return None


def selected_questions(questions, keys):
    wanted = parse_keys(keys)
    results = []
    for key in wanted:
        question = selected_question(questions, key)
        if question is None:
            raise ValueError("One or more selected Registration Form subgroup questions are no longer available.")
        results.append(question)
    return results


def empty_document():
    return {"version": DOCUMENT_VERSION, "profiles": []}


def load_document_from_text(raw):
    if raw is None or not str(raw).strip():
        return empty_document()
    try:
        document = json.loads(str(raw))
    except Exception:
        raise ValueError("Saved dashboard configuration is not valid JSON.")
    if not isinstance(document, dict) or safe_int(document.get("version"), 0) != DOCUMENT_VERSION:
        raise ValueError("Saved dashboard configuration has an unsupported version.")
    if not isinstance(document.get("profiles"), list):
        raise ValueError("Saved dashboard configuration does not contain a profile list.")
    return document


def valid_profile(profile):
    keys = parse_keys(profile.get("question_keys", profile.get("question_key", ""))) if isinstance(profile, dict) else []
    return (isinstance(profile, dict) and
            bool(str(profile.get("id", "")).strip()) and
            bool(str(profile.get("name", "")).strip()) and
            safe_int(profile.get("organization_id"), 0) > 0 and bool(keys))


def profiles_from_document(document):
    return [item for item in document.get("profiles", []) if valid_profile(item)]


def find_profile(profiles, profile_id):
    wanted = str(profile_id or "")
    for profile in profiles:
        if str(profile.get("id", "")) == wanted:
            return profile
    return None


def existing_profile_for_save(profiles, profile_id, submitted_name):
    """Update only when the loaded profile keeps its saved configuration name."""
    existing = find_profile(profiles, profile_id)
    if existing is None:
        return None
    saved_name = str(existing.get("name", "") or "").strip().lower()
    wanted_name = str(submitted_name or "").strip().lower()
    return existing if saved_name == wanted_name else None


def new_profile_id(name, now=None):
    base = "".join(char.lower() if char.isalnum() else "-" for char in str(name)).strip("-")
    while "--" in base:
        base = base.replace("--", "-")
    if not base:
        base = "configuration"
    value = now or datetime.datetime.now()
    return "{0}-{1}".format(base[:28], value.strftime("%Y%m%d%H%M%S%f"))


def build_profile(form, existing=None, now=None, user_people_id=0):
    name = str(form.get("profile_name", "") or "").strip()
    if not name:
        raise ValueError("Configuration name is required.")
    organization_id = safe_int(form.get("organization_id"), 0)
    if organization_id <= 0:
        raise ValueError("Enter a valid Involvement ID.")
    question_keys = parse_keys(form.get("question_keys", form.get("question_key", "")))
    if not question_keys:
        raise ValueError("Select at least one Registration Form subgroup question.")
    report_title = str(form.get("report_title", "") or "").strip()
    if not report_title:
        report_title = name
    excluded = parse_excluded_values(form.get("excluded_values", ""))
    include_names = bool(form.get("include_member_names", True))
    include_emails = bool(form.get("include_member_emails", False))
    if include_emails and not include_names:
        raise ValueError("Volunteer names must be displayed when email addresses are displayed.")
    privacy_acknowledged = bool(form.get("privacy_acknowledged", False))
    if include_emails and not privacy_acknowledged:
        raise ValueError("Confirm the Contact Information Notice before displaying volunteer email addresses.")
    profile_id = str(existing.get("id")) if existing else new_profile_id(name, now)
    return {
        "id": profile_id,
        "name": name,
        "organization_id": organization_id,
        "organization_name": str(form.get("organization_name", "") or "").strip(),
        "question_keys": question_keys,
        "question_labels": list(form.get("question_labels", []) or []),
        "report_title": report_title,
        "excluded_values": excluded,
        "include_member_names": include_names,
        "include_member_emails": include_emails,
        "privacy_acknowledged": privacy_acknowledged,
        "show_subgroup_names": bool(form.get("show_subgroup_names", True)),
        "last_saved_people_id": safe_int(user_people_id, 0),
        "last_saved_at": (now or datetime.datetime.now()).strftime("%Y-%m-%dT%H:%M:%S"),
    }


def save_profile_in_document(document, profile):
    profiles = document["profiles"]
    current = find_profile(profiles, profile["id"])
    wanted_name = profile["name"].strip().lower()
    for item in profiles:
        if item is not current and str(item.get("name", "")).strip().lower() == wanted_name:
            raise ValueError("A saved configuration with this name already exists.")
    if current is None:
        profiles.append(profile)
    else:
        profiles[profiles.index(current)] = profile
    profiles.sort(key=lambda item: str(item.get("name", "")).lower())
    return profile


def delete_profile_from_document(document, profile_id, confirmation):
    profile = find_profile(document["profiles"], profile_id)
    if profile is None:
        raise ValueError("The selected saved configuration was not found.")
    if str(confirmation or "") != str(profile_id or ""):
        raise ValueError("Configuration deletion was not confirmed.")
    document["profiles"].remove(profile)
    return profile


def volunteer_name_sort_key(volunteer):
    """Sort TouchPoint Name2 or display-style names by last name."""
    name = str(volunteer.get("name", "") or "").strip().lower()
    if "," in name:
        last_name, given_names = name.split(",", 1)
        return (last_name.strip(), given_names.strip(),
                safe_int(volunteer.get("people_id"), 0))
    parts = name.split()
    suffixes = ("jr", "jr.", "sr", "sr.", "ii", "iii", "iv")
    last_index = len(parts) - 1
    if last_index > 0 and parts[last_index] in suffixes:
        last_index -= 1
    last_name = parts[last_index] if parts else ""
    return (last_name, name, safe_int(volunteer.get("people_id"), 0))


def build_shift_catalog(options, signup_rows, excluded_values=None):
    excluded = set(str(value).strip().lower() for value in (excluded_values or []))
    shifts = []
    by_subgroup = {}
    for option in options:
        subgroup = str(option["subgroup"])
        if subgroup.lower() in excluded:
            continue
        shift = {
            "order": safe_int(option.get("order"), len(shifts)),
            "subgroup": subgroup,
            "label": str(option.get("label", subgroup) or subgroup),
            "question_label": str(option.get("question_label", "") or ""),
            "limit": option.get("limit"),
            "volunteers": {},
        }
        shifts.append(shift)
        by_subgroup[subgroup.lower()] = shift

    for row in signup_rows:
        subgroup = str(row_value(row, ("SubGroupName", "MemberTagName"), "") or "").strip()
        shift = by_subgroup.get(subgroup.lower())
        if shift is None:
            continue
        people_id = safe_int(row_value(row, ("PeopleId",), 0), 0)
        if people_id <= 0:
            continue
        volunteer = {
            "people_id": people_id,
            "name": str(row_value(row, ("MemberName", "Name2", "Name"), "") or "Person {0}".format(people_id)),
            "email": str(row_value(row, ("EmailAddress",), "") or ""),
        }
        existing = shift["volunteers"].get(people_id)
        if existing is None or volunteer["name"].lower() < existing["name"].lower():
            shift["volunteers"][people_id] = volunteer

    for shift in shifts:
        volunteers = list(shift["volunteers"].values())
        volunteers.sort(key=volunteer_name_sort_key)
        shift["volunteers"] = volunteers
        shift["count"] = len(volunteers)
        limit = shift["limit"]
        shift["remaining"] = None if limit is None else max(safe_int(limit) - shift["count"], 0)
        shift["over_limit"] = limit is not None and shift["count"] > safe_int(limit)
    shifts.sort(key=lambda item: (item["order"], item["label"].lower()))
    return shifts


def report_summary(shifts):
    people = set()
    signups = 0
    vacancies = 0
    limited_shifts = 0
    for shift in shifts:
        signups += shift["count"]
        for volunteer in shift["volunteers"]:
            people.add(volunteer["people_id"])
        if shift["remaining"] is not None:
            limited_shifts += 1
            vacancies += shift["remaining"]
    return {
        "shifts": len(shifts),
        "unique_volunteers": len(people),
        "shift_signups": signups,
        "vacancies": vacancies,
        "limited_shifts": limited_shifts,
    }


def event_year(involvement_name, today=None):
    match = re.search(r"\b(20\d{2})\b", str(involvement_name or ""))
    if match:
        return int(match.group(1))
    return int((today or datetime.datetime.now().date()).year)


def subgroup_date(subgroup, involvement_name, today=None):
    token = str(subgroup or "").split(":", 1)[0].strip()
    year = event_year(involvement_name, today)
    match = re.match(r"^(20\d{2})-(\d{1,2})-(\d{1,2})$", token)
    if match:
        year, month, day = [int(value) for value in match.groups()]
    else:
        match = re.match(r"^(\d{1,2})/(\d{1,2})(?:/(20\d{2}))?$", token)
        if match:
            month = int(match.group(1))
            day = int(match.group(2))
            if match.group(3):
                year = int(match.group(3))
        elif token.isdigit() and len(token) in (3, 4):
            if len(token) == 3:
                month = int(token[0])
                day = int(token[1:])
            else:
                month = int(token[:2])
                day = int(token[2:])
        else:
            return None
    try:
        return datetime.date(year, month, day)
    except Exception:
        return None


def shift_time_key(shift):
    subgroup = str(shift.get("subgroup", "") or "")
    value = subgroup.split(":", 1)[1] if ":" in subgroup else str(shift.get("label", "") or "")
    compact = value.lower().replace(" ", "")
    match = re.search(r"(\d{1,2})(?::?(\d{2}))?(am|pm)", compact)
    if not match:
        return (99, 99, safe_int(shift.get("order"), 0))
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    period = match.group(3)
    if hour < 1 or hour > 12 or minute > 59:
        return (99, 99, safe_int(shift.get("order"), 0))
    if period == "pm" and hour != 12:
        hour += 12
    elif period == "am" and hour == 12:
        hour = 0
    return (hour, minute, safe_int(shift.get("order"), 0))


def date_groups(shifts, involvement_name, today=None):
    groups = {}
    unknown = []
    for shift in shifts:
        value = subgroup_date(shift.get("subgroup", ""), involvement_name, today)
        if value is None:
            unknown.append(shift)
            continue
        key = value.strftime("%Y-%m-%d")
        if key not in groups:
            label = value.strftime("%A, %B %d, %Y").replace(" 0", " ")
            groups[key] = {"key": key, "label": label, "shifts": []}
        groups[key]["shifts"].append(shift)
    results = []
    for key in sorted(groups):
        group = groups[key]
        group["shifts"].sort(key=shift_time_key)
        results.append(group)
    if unknown:
        unknown.sort(key=lambda item: (safe_int(item.get("order"), 0), item.get("label", "").lower()))
        results.append({"key": "unknown", "label": "Other shifts", "shifts": unknown})
    return results


def report_date_window(groups):
    dated = [group for group in groups if group["key"] != "unknown"]
    if not dated:
        return "Dates could not be determined from the subgroup values"
    if len(dated) == 1:
        return dated[0]["label"]
    return "{0} through {1}".format(dated[0]["label"], dated[-1]["label"])


def load_document():
    return load_document_from_text(model.TextContent(CONTENT_NAME))


def write_document(document):
    model.WriteContentText(CONTENT_NAME, json.dumps(document, sort_keys=True), "")


def load_involvement(organization_id):
    rows = list(q.QuerySql("""
        SELECT OrganizationId, OrganizationName, OrganizationStatusId
        FROM dbo.Organizations
        WHERE OrganizationId = @OrganizationId
    """, {"OrganizationId": organization_id}))
    if not rows:
        raise ValueError("The selected Involvement was not found.")
    row = rows[0]
    if safe_int(row_value(row, ("OrganizationStatusId",), 0), 0) != 30:
        raise ValueError("The selected Involvement is not active.")
    return {
        "id": safe_int(row_value(row, ("OrganizationId",), 0), 0),
        "name": str(row_value(row, ("OrganizationName",), "") or ""),
    }


def load_questions(organization_id, involvement_name=""):
    rows = list(q.QuerySql("""
        SELECT *
        FROM dbo.RegQuestion
        WHERE OrganizationId = @OrganizationId
          AND ISJSON(Options) = 1
    """, {"OrganizationId": organization_id}))
    questions = registration_questions(rows, involvement_name)
    if not questions:
        raise ValueError("No Registration Form questions with dated shift subgroup Values were found for this Involvement.")
    return questions


def search_involvements():
    term = str(data_value("term", "") or "").strip()
    exact_id = safe_int(term, 0)
    if len(term) < 2 and not exact_id:
        return json.dumps({"success": True, "items": []})
    rows = list(q.QuerySql("""
        SELECT TOP 15 o.OrganizationId, o.OrganizationName
        FROM dbo.Organizations o
        WHERE o.OrganizationStatusId = 30
          AND (o.OrganizationId = @ExactId OR o.OrganizationName LIKE @LikeTerm)
          AND EXISTS (
              SELECT 1 FROM dbo.RegQuestion rq
              WHERE rq.OrganizationId = o.OrganizationId
                AND ISJSON(rq.Options) = 1
          )
        ORDER BY CASE WHEN o.OrganizationId = @ExactId THEN 0 ELSE 1 END,
                 o.OrganizationName
    """, {"ExactId": exact_id, "LikeTerm": "%" + term + "%"}))
    items = []
    for row in rows:
        items.append({
            "id": safe_int(row_value(row, ("OrganizationId",), 0), 0),
            "name": str(row_value(row, ("OrganizationName",), "") or ""),
        })
    return json.dumps({"success": True, "items": items})


def combined_options(questions):
    results = []
    seen = {}
    for question in questions:
        for option in parse_registration_options(question["options_raw"]):
            key = option["subgroup"].lower()
            if key in seen:
                raise ValueError(
                    "Subgroup value {0} appears in both {1} and {2}. Remove one of those questions because a signup cannot be matched unambiguously.".format(
                        option["subgroup"], seen[key], question["label"]))
            seen[key] = question["label"]
            item = dict(option)
            item["order"] = len(results)
            item["question_label"] = question["label"]
            results.append(item)
    return results


def query_signups(organization_id, subgroup_values):
    values = []
    seen = set()
    for raw in subgroup_values:
        value = str(raw or "").strip()
        key = value.lower()
        if value and key not in seen:
            values.append(value)
            seen.add(key)
    if not values:
        return []
    if len(values) > MAX_OPTIONS:
        raise ValueError("Too many subgroup values were selected.")
    parameters = {"OrganizationId": organization_id}
    placeholders = []
    for index, value in enumerate(values):
        name = "Subgroup{0}".format(index)
        placeholders.append("@" + name)
        parameters[name] = value
    sql = """
        SELECT
            mt.Name AS SubGroupName,
            p.PeopleId,
            p.Name2 AS MemberName,
            p.EmailAddress
        FROM dbo.MemberTags mt
        INNER JOIN dbo.OrgMemMemTags ommt ON ommt.MemberTagId = mt.Id
        INNER JOIN dbo.People p ON p.PeopleId = ommt.PeopleId
        WHERE ommt.OrgId = @OrganizationId
          AND mt.Name IN ({0})
          AND ISNULL(p.IsDeceased, 0) = 0
          AND ISNULL(p.ArchivedFlag, 0) = 0
        ORDER BY mt.Name, p.Name2, p.PeopleId
    """.format(",".join(placeholders))
    return list(q.QuerySql(sql, parameters))


def profile_form_values(profile=None):
    value = profile or {}
    question_keys = parse_keys(value.get("question_keys", value.get("question_key", "")))
    question_labels = value.get("question_labels", [])
    if not isinstance(question_labels, list):
        question_labels = []
    if not question_labels and value.get("question_label"):
        question_labels = [str(value.get("question_label"))]
    return {
        "profile_id": str(value.get("id", "") or ""),
        "profile_name": str(value.get("name", "") or ""),
        "organization_id": safe_int(value.get("organization_id"), 0),
        "organization_name": str(value.get("organization_name", "") or ""),
        "question_keys": question_keys,
        "question_labels": question_labels,
        "report_title": str(value.get("report_title", "") or ""),
        "excluded_values": "\n".join(value.get("excluded_values", []) or []),
        "include_member_names": bool(value.get("include_member_names", True)),
        "include_member_emails": bool(value.get("include_member_emails", False)),
        "privacy_acknowledged": bool(value.get("privacy_acknowledged", False)),
        "show_subgroup_names": bool(value.get("show_subgroup_names", True)),
    }


def posted_form_values():
    return {
        "profile_id": str(data_value("profileId", "") or "").strip(),
        "profile_name": str(data_value("profileName", "") or "").strip(),
        "organization_id": safe_int(data_value("organizationId", 0), 0),
        "organization_name": str(data_value("organizationName", "") or "").strip(),
        "question_keys": parse_keys(data_value("questionKeys", "")),
        "question_labels": [],
        "report_title": str(data_value("reportTitle", "") or "").strip(),
        "excluded_values": str(data_value("excludedValues", "") or ""),
        "include_member_names": truthy(data_value("includeMemberNames", "")),
        "include_member_emails": truthy(data_value("includeMemberEmails", "")),
        "privacy_acknowledged": truthy(data_value("privacyAcknowledged", "")),
        "show_subgroup_names": truthy(data_value("showSubgroupNames", "")),
    }


STYLE = """
<style>
.vsud{max-width:1180px;margin:0 auto;font-family:"Helvetica Neue",Helvetica,Arial,sans-serif}.vsud-panel{background:#fff;border:1px solid #d9dde3;border-radius:6px;padding:18px;margin-bottom:18px}
.vsud-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.vsud-wide{grid-column:1/-1}.vsud label{font-weight:600;display:block}
.vsud-help,.vsud .help-block{color:#5f6772;font-size:.9em;margin-top:4px}.vsud-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}.vsud-profile-row{display:flex;gap:8px;align-items:end}
.vsud-profile-row>div{flex:1}.vsud-summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:16px 0}.vsud-metric{border:1px solid #d9dde3;border-radius:5px;padding:10px;text-align:center}.vsud-metric strong{font-size:1.5em;display:block}.vsud-metric-danger{border-color:#b42318;background:#fdecec;color:#8a1c13}
.vsud table{width:100%;border-collapse:collapse}.vsud th,.vsud td{padding:8px;border:1px solid #d9dde3;vertical-align:top}.vsud th{background:#f4f6f8}.vsud-date-row th{background:#244b6b;color:#fff;font-size:1.08em;text-align:left;padding:10px 12px}.vsud-date-row:not(:first-child) th{border-top:8px solid #fff}.vsud-zero{background:#fff6e5}.vsud-vacancy,.vsud-over{background:#fdecec}.vsud-subgroup{color:#5f6772;font-size:.85em}.vsud-members{font-size:.92em}.vsud-volunteer-toggle{white-space:nowrap}.vsud-toggle-arrow{display:inline-block;margin-left:3px}.vsud-volunteer-toggle[aria-expanded="true"] .vsud-toggle-arrow{transform:rotate(180deg)}.vsud-volunteer-detail td{background:#eef5fb;padding:10px 16px 12px;font-size:.84em}.vsud-volunteer-detail.vsud-collapsed{display:none}.vsud-volunteer-heading{color:#244b6b;font-size:.9em;font-weight:600;margin-bottom:6px;text-transform:uppercase}.vsud-volunteer-list{columns:2;column-fill:balance;column-gap:32px;margin:0;padding-left:22px}.vsud-volunteer-list li{break-inside:avoid;margin-bottom:4px;padding-left:2px;overflow-wrap:anywhere}.vsud-private{border-left:4px solid #c98600;padding:8px 12px;background:#fff8e8}.vsud-results{position:relative}.vsud-results-list{position:absolute;z-index:10;background:#fff;border:1px solid #bbb;width:100%;max-height:240px;overflow:auto}.vsud-result{display:block;width:100%;padding:8px;text-align:left;border:0;border-bottom:1px solid #eee;background:#fff}.vsud-result:hover{background:#eef5fb}.vsud-selected{padding:8px;margin-top:5px;background:#f4f6f8;border-radius:4px}.vsud-pill{display:inline-flex;align-items:center;gap:7px;background:#e9f1f7;border:1px solid #bfd0de;border-radius:14px;padding:4px 9px}.vsud-pill button{border:0;background:transparent;font-weight:bold}.vsud-questions label{font-weight:400;margin:5px 0}.no-print{margin-bottom:14px}
@media(max-width:760px){.vsud-grid{grid-template-columns:1fr}.vsud-wide{grid-column:auto}.vsud-summary{grid-template-columns:repeat(2,minmax(0,1fr))}.vsud-profile-row{display:block}.vsud-profile-row .btn{margin-top:8px}}
@media(max-width:760px){.vsud-volunteer-list{columns:1}.vsud-volunteer-toggle{white-space:normal}}
@media print{body *{visibility:hidden!important}.vsud-report,.vsud-report *{visibility:visible!important}.vsud-report{position:absolute;left:0;top:0;width:100%}.vsud-controls,.vsud-message,.no-print,.vsud-volunteer-toggle{display:none!important}.vsud-volunteer-detail{display:table-row!important}.vsud{max-width:none}.vsud-panel{border:0;padding:0}.vsud table{font-size:10pt}.vsud tr{break-inside:avoid;page-break-inside:avoid}}
</style>
"""


def render_report(profile, involvement, questions, shifts):
    summary = report_summary(shifts)
    groups = date_groups(shifts, involvement["name"])
    show_capacity = summary["limited_shifts"] > 0
    parts = [STYLE, '<div class="vsud"><div class="vsud-panel vsud-report">']
    parts.append('<div class="no-print"><button type="button" class="btn btn-primary" onclick="window.print()">Print Report</button></div>')
    parts.append("<h2>{0}</h2>".format(html_escape(profile["report_title"])))
    parts.append("<p><strong>Involvement:</strong> {0} (ID: {1})</p>".format(
        html_escape(involvement["name"]), involvement["id"]))
    parts.append("<p><strong>Dates:</strong> {0}</p>".format(html_escape(report_date_window(groups))))
    parts.append('<div class="vsud-summary">')
    metrics = (
        ("Shifts", summary["shifts"]),
        ("Unique Volunteers", summary["unique_volunteers"]),
        ("Shift Signups", summary["shift_signups"]),
        ("Open Positions", summary["vacancies"] if summary["limited_shifts"] else "—"),
    )
    for label, value in metrics:
        metric_class = " vsud-metric-danger" if label == "Open Positions" and summary["vacancies"] > 0 else ""
        parts.append('<div class="vsud-metric{0}"><strong>{1}</strong>{2}</div>'.format(
            metric_class, html_escape(value), html_escape(label)))
    parts.append("</div>")
    if profile.get("include_member_emails"):
        parts.append('<div class="vsud-private"><strong>Contact information is displayed.</strong> This report contains volunteer email addresses.</div>')
    parts.append('<table><thead><tr><th>Shift</th><th>Signed Up</th>')
    if show_capacity:
        parts.append("<th>Limit</th><th>Remaining</th>")
    if profile.get("include_member_names"):
        parts.append("<th>Volunteers</th>")
    parts.append("</tr></thead><tbody>")
    column_count = 2
    if show_capacity:
        column_count += 2
    if profile.get("include_member_names"):
        column_count += 1
    shift_number = 0
    for group in groups:
        parts.append('<tr class="vsud-date-row"><th colspan="{0}">{1}</th></tr>'.format(
            column_count, html_escape(group["label"])))
        for shift in group["shifts"]:
            shift_number += 1
            volunteer_panel_id = "vsud-volunteers-{0}".format(shift_number)
            if shift["over_limit"] or (shift["remaining"] is not None and shift["remaining"] > 0):
                row_class = "vsud-vacancy"
            elif shift["count"] == 0:
                row_class = "vsud-zero"
            else:
                row_class = ""
            parts.append('<tr class="{0}"><td><strong>{1}</strong>'.format(row_class, html_escape(shift["label"])))
            if profile.get("show_subgroup_names"):
                parts.append('<div class="vsud-subgroup">Subgroup: {0}</div>'.format(html_escape(shift["subgroup"])))
                if len(questions) > 1:
                    parts.append('<div class="vsud-subgroup">Question: {0}</div>'.format(html_escape(shift["question_label"])))
            parts.append("</td><td>{0}</td>".format(shift["count"]))
            if show_capacity:
                parts.append("<td>{0}</td><td>{1}</td>".format(
                    "—" if shift["limit"] is None else shift["limit"],
                    "—" if shift["remaining"] is None else shift["remaining"]))
            if profile.get("include_member_names"):
                member_lines = []
                for volunteer in shift["volunteers"]:
                    line = html_escape(volunteer["name"])
                    if profile.get("include_member_emails") and volunteer["email"]:
                        line += " &lt;{0}&gt;".format(html_escape(volunteer["email"]))
                    member_lines.append(line)
                if member_lines:
                    parts.append('<td class="vsud-members"><button type="button" class="btn btn-default btn-sm vsud-volunteer-toggle" aria-expanded="false" aria-controls="{0}"><span class="vsud-toggle-label">View volunteers</span> ({1}) <span class="vsud-toggle-arrow" aria-hidden="true">&#8964;</span></button></td>'.format(
                        volunteer_panel_id, shift["count"]))
                else:
                    parts.append('<td class="vsud-members">No volunteers</td>')
            parts.append("</tr>")
            if profile.get("include_member_names") and member_lines:
                parts.append('<tr id="{0}" class="vsud-volunteer-detail vsud-collapsed"><td colspan="{1}"><div class="vsud-volunteer-heading">Volunteers for this shift</div><ol class="vsud-volunteer-list">'.format(
                    volunteer_panel_id, column_count))
                for line in member_lines:
                    parts.append("<li>{0}</li>".format(line))
                parts.append("</ol></td></tr>")
    parts.append("</tbody></table>")
    if profile.get("include_member_names"):
        parts.append('''<noscript><style>.vsud-volunteer-toggle{display:none!important}.vsud-volunteer-detail.vsud-collapsed{display:table-row!important}</style></noscript>
<script>
(function(){
var report=document.querySelector(".vsud-report");
if(!report){return;}
var buttons=report.querySelectorAll(".vsud-volunteer-toggle");
for(var i=0;i<buttons.length;i+=1){
buttons[i].onclick=function(){
var expanded=this.getAttribute("aria-expanded")==="true";
var panel=document.getElementById(this.getAttribute("aria-controls"));
if(!panel){return;}
this.setAttribute("aria-expanded",expanded?"false":"true");
panel.className=expanded?"vsud-volunteer-detail vsud-collapsed":"vsud-volunteer-detail";
var label=this.querySelector(".vsud-toggle-label");
if(label){label.textContent=expanded?"View volunteers":"Hide volunteers";}
};
}
}());
</script>''')
    if profile.get("show_subgroup_names"):
        question_note = "Shift definitions come from Registration Form question(s): {0}.".format(
            html_escape(", ".join(question["label"] for question in questions)))
    else:
        question_note = "Shift definitions come from the selected Registration Form questions."
    parts.append('<p class="vsud-help">{0} Yellow rows have no signups and no configured limit. Red rows need attention because positions remain open or signups exceed the configured limit.</p>'.format(question_note))
    parts.append("</div></div>")
    return "".join(parts)


def render_page(document, values, questions, message="", report_html=""):
    profiles = profiles_from_document(document)
    options = ['<option value="">New configuration</option>']
    for profile in sorted(profiles, key=lambda item: str(item["name"]).lower()):
        selected = " selected" if profile["id"] == values["profile_id"] else ""
        options.append('<option value="{0}"{1}>{2}</option>'.format(
            html_escape(profile["id"]), selected, html_escape(profile["name"])))
    question_options = []
    for question in questions:
        checked = " checked" if question["key"] in values["question_keys"] else ""
        question_options.append('<label><input type="checkbox" class="vsud-question" value="{0}"{1}> {2} ({3} shifts)</label>'.format(
            html_escape(question["key"]), checked, html_escape(question["label"]),
            question["option_count"]))
    if not question_options:
        question_options.append('<div class="vsud-help">Choose an Involvement, then inspect its Registration Form.</div>')
    checked_names = " checked" if values["include_member_names"] else ""
    checked_emails = " checked" if values["include_member_emails"] else ""
    checked_privacy = " checked" if values["privacy_acknowledged"] else ""
    checked_subgroups = " checked" if values["show_subgroup_names"] else ""
    privacy_style = "" if values["include_member_emails"] else ' style="display:none"'
    if values["organization_id"]:
        selected_org_html = '<span class="vsud-pill">{0} (ID: {1}) <button type="button" id="vsudRemoveOrg" aria-label="Remove selected Involvement">&times;</button></span>'.format(
            html_escape(values["organization_name"]), values["organization_id"])
    else:
        selected_org_html = '<span class="vsud-help">No Involvement selected</span>'
    delete_disabled = "" if values["profile_id"] else " disabled"
    parts = [STYLE, '<div class="vsud"><div class="vsud-panel vsud-controls"><h2>Volunteer Signup Dashboard <small>v{0}</small></h2>'.format(APP_VERSION)]
    parts.append(message)
    parts.append("""
<form action="/PyScriptForm/VolunteerSignupDashboard" method="post" id="vsudForm">
  <input type="hidden" name="profileId" value="{0}">
  <input type="hidden" name="questionKeys" id="vsudQuestionKeys" value="{1}">
  <div class="vsud-profile-row vsud-wide"><div><label for="vsudProfilePreset">Saved configuration</label><select class="form-control" name="selectedProfileId" id="vsudProfilePreset">{2}</select></div><button class="btn btn-default" name="VSUDAction" value="load_profile" formnovalidate>Load</button></div>
  <hr>
  <div class="vsud-grid">
    <div><label>Configuration name</label><input class="form-control" name="profileName" maxlength="100" value="{3}" required></div>
    <div><label>Report title</label><input class="form-control" name="reportTitle" maxlength="150" value="{4}"></div>
    <div class="vsud-wide"><label for="vsudOrgSearch">Involvement</label><div class="vsud-results"><input class="form-control" type="search" id="vsudOrgSearch" placeholder="Search by Involvement name or ID" autocomplete="off"><div id="vsudOrgResults"></div></div><div class="vsud-selected" id="vsudSelectedOrg">{5}</div><input type="hidden" name="organizationId" id="vsudOrganizationId" value="{6}"><input type="hidden" name="organizationName" id="vsudOrganizationName" value="{7}"><div class="help-block">After choosing a different Involvement, inspect its Registration Form.</div><button class="btn btn-default" name="VSUDAction" value="inspect" formnovalidate style="margin-top:8px">Inspect Registration Form</button></div>
    <div class="vsud-wide vsud-questions"><label>Registration Form subgroup questions</label><div id="vsudQuestionList">{8}</div><div class="vsud-help">All eligible questions are selected by default. Clear any question that should not appear in this report.</div></div>
    <div class="vsud-wide"><label>Hide specific shifts (optional)</label><textarea class="form-control" name="excludedValues" rows="3" placeholder="One stored subgroup value per line">{9}</textarea><div class="vsud-help">Normally leave this blank. Use it only to hide a non-shift option or placeholder such as <code>? 99</code>. Enter the exact option Value/member-tag name, not the displayed label.</div></div>
    <div><label><input type="checkbox" name="includeMemberNames" id="vsudIncludeNames" value="true"{10}> Show volunteer names</label></div>
    <div><label><input type="checkbox" name="includeMemberEmails" id="vsudIncludeEmails" value="true"{11}> Show volunteer email addresses</label><div class="help-block">Off by default.</div></div>
    <div class="vsud-wide vsud-private" id="vsudContactNotice"{12}><strong>Contact Information Notice</strong><p>Every person who can open this dashboard will see the displayed volunteer email addresses.</p><label><input type="checkbox" name="privacyAcknowledged" id="vsudPrivacyAcknowledged" value="true"{13}> I confirm this dashboard is authorized to display volunteer email addresses.</label></div>
    <div><label><input type="checkbox" name="showSubgroupNames" value="true"{14}> Show stored subgroup values and questions</label><div class="help-block">When cleared, technical subgroup values and Registration Form question names are omitted from the report.</div></div>
  </div>
  <div class="vsud-actions">
    <button class="btn btn-primary" name="VSUDAction" value="preview" formtarget="_blank">Preview dashboard</button>
    <button class="btn btn-default" name="VSUDAction" value="save_profile"{15}>Save configuration</button>
  </div>
</form>
<form action="/PyScriptForm/VolunteerSignupDashboard" method="post" style="margin-top:10px" onsubmit="return confirm('Permanently delete this saved dashboard configuration?')">
  <input type="hidden" name="profileId" value="{0}"><input type="hidden" name="deleteConfirmation" value="{0}">
  <button class="btn btn-danger" name="VSUDAction" value="delete_profile"{16}>Delete loaded configuration</button>
</form>
<script>
(function(){{
 var hidden=document.getElementById('vsudQuestionKeys'),checks=document.querySelectorAll('.vsud-question'),questionList=document.getElementById('vsudQuestionList');
 function syncQuestions(){{var keys=[],i;for(i=0;i<checks.length;i++)if(checks[i].checked)keys.push(checks[i].value);hidden.value=keys.join(',');}}
 for(var i=0;i<checks.length;i++)checks[i].onchange=syncQuestions;
 var form=document.getElementById('vsudForm'),input=document.getElementById('vsudOrgSearch'),results=document.getElementById('vsudOrgResults'),id=document.getElementById('vsudOrganizationId'),name=document.getElementById('vsudOrganizationName'),selected=document.getElementById('vsudSelectedOrg'),emails=document.getElementById('vsudIncludeEmails'),names=document.getElementById('vsudIncludeNames'),notice=document.getElementById('vsudContactNotice'),ack=document.getElementById('vsudPrivacyAcknowledged'),timer,dirty=false;
 function esc(v){{return String(v||'').replace(/[&<>"']/g,function(c){{return {{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c];}});}}
 function clearQuestions(){{hidden.value='';questionList.innerHTML='<div class="vsud-help">Choose an Involvement, then inspect its Registration Form.</div>';}}
 function clearOrg(){{id.value='';name.value='';selected.innerHTML='<span class="vsud-help">No Involvement selected</span>';clearQuestions();dirty=true;}}
 function wireRemove(){{var remove=document.getElementById('vsudRemoveOrg');if(remove)remove.onclick=clearOrg;}}
 function updatePrivacy(){{if(!names.checked&&emails.checked)emails.checked=false;notice.style.display=emails.checked?'':'none';if(!emails.checked)ack.checked=false;}}
 wireRemove();emails.onchange=updatePrivacy;names.onchange=updatePrivacy;updatePrivacy();
 form.oninput=function(e){{if(e.target.id!=='vsudOrgSearch')dirty=true;}};
 form.onchange=function(e){{if(e.target.id!=='vsudProfilePreset')dirty=true;}};
 form.onsubmit=function(e){{var action=e.submitter?e.submitter.value:'';if(action==='load_profile'&&dirty&&!confirm('Discard unsaved changes and load another configuration?'))return false;if(action!=='preview')dirty=false;return true;}};
 input.oninput=function(){{clearTimeout(timer);var term=input.value.trim();if(term.length<2&&!/^\\d+$/.test(term)){{results.innerHTML='';return;}}timer=setTimeout(function(){{fetch('/PyScriptForm/VolunteerSignupDashboard',{{method:'POST',headers:{{'Content-Type':'application/x-www-form-urlencoded'}},body:'VSUDAction=search_involvements&term='+encodeURIComponent(term)}}).then(function(r){{return r.json();}}).then(function(d){{var items=d.items||[];results.className='vsud-results-list';results.innerHTML='';if(!items.length){{results.innerHTML='<div class="vsud-result">No matching Involvements.</div>';return;}}items.forEach(function(x){{var b=document.createElement('button');b.type='button';b.className='vsud-result';b.textContent=x.name+' ('+x.id+')';b.onclick=function(){{id.value=x.id;name.value=x.name;selected.innerHTML='<span class="vsud-pill">'+esc(x.name)+' (ID: '+x.id+') <button type="button" id="vsudRemoveOrg" aria-label="Remove selected Involvement">&times;</button></span>';wireRemove();results.innerHTML='';input.value='';clearQuestions();dirty=true;}};results.appendChild(b);}});}});}},250);}};
}})();
</script>
""".format(
        html_escape(values["profile_id"]), html_escape(",".join(values["question_keys"])), "".join(options),
        html_escape(values["profile_name"]), html_escape(values["report_title"]),
        selected_org_html,
        html_escape(values["organization_id"] or ""), html_escape(values["organization_name"]),
        "".join(question_options), html_escape(values["excluded_values"]), checked_names,
        checked_emails, privacy_style, checked_privacy, checked_subgroups,
        "", delete_disabled,
    ))
    parts.append("</div>")
    if report_html:
        parts.append(report_html)
    parts.append("</div>")
    return "".join(parts)


def values_for_build(values):
    return {
        "profile_name": values["profile_name"],
        "organization_id": values["organization_id"],
        "organization_name": values["organization_name"],
        "question_keys": values["question_keys"],
        "question_labels": values["question_labels"],
        "report_title": values["report_title"],
        "excluded_values": values["excluded_values"],
        "include_member_names": values["include_member_names"],
        "include_member_emails": values["include_member_emails"],
        "privacy_acknowledged": values["privacy_acknowledged"],
        "show_subgroup_names": values["show_subgroup_names"],
    }


def run_app():
    action = requested_action()
    if action == "preview":
        model.Header = ""
    if action == "search_involvements":
        return search_involvements()
    message = ""
    report_html = ""
    questions = []
    values = profile_form_values()
    try:
        document = load_document()
    except Exception as error:
        document = empty_document()
        message = '<div class="alert alert-danger">{0}</div>'.format(html_escape(error))
        return render_page(document, values, questions, message, report_html)

    try:
        if action == "load_profile":
            profile_id = str(data_value("selectedProfileId", "") or "").strip()
            profile = find_profile(profiles_from_document(document), profile_id)
            if profile is None:
                if profile_id:
                    raise ValueError("The selected saved configuration was not found.")
            else:
                values = profile_form_values(profile)
                involvement = load_involvement(values["organization_id"])
                values["organization_name"] = involvement["name"]
                questions = load_questions(values["organization_id"], involvement["name"])
        elif action in ("inspect", "preview", "save_profile"):
            values = posted_form_values()
            involvement = load_involvement(values["organization_id"])
            values["organization_name"] = involvement["name"]
            questions = load_questions(values["organization_id"], involvement["name"])
            if action == "inspect":
                values["question_keys"] = [item["key"] for item in questions]
                message = '<div class="alert alert-success">Found {0} Registration Form questions with options for {1}.</div>'.format(len(questions), html_escape(involvement["name"]))
            else:
                chosen_questions = selected_questions(questions, values["question_keys"])
                if not chosen_questions:
                    raise ValueError("Select at least one Registration Form subgroup question.")
                values["question_labels"] = [item["label"] for item in chosen_questions]
                options = combined_options(chosen_questions)
                excluded = parse_excluded_values(values["excluded_values"])
                usable = [item for item in options if item["subgroup"].lower() not in set(value.lower() for value in excluded)]
                if not usable:
                    raise ValueError("The selected question has no reportable shifts after exclusions.")
                existing = find_profile(profiles_from_document(document), values["profile_id"])
                if action == "save_profile":
                    existing = existing_profile_for_save(
                        profiles_from_document(document), values["profile_id"],
                        values["profile_name"])
                profile = build_profile(values_for_build(values), existing,
                                        user_people_id=getattr(model, "UserPeopleId", 0))
                if action == "save_profile":
                    save_profile_in_document(document, profile)
                    write_document(document)
                    values = profile_form_values(profile)
                    message = '<div class="alert alert-success">Configuration saved: {0}</div>'.format(html_escape(profile["name"]))
                else:
                    signup_rows = query_signups(involvement["id"], [item["subgroup"] for item in usable])
                    shifts = build_shift_catalog(options, signup_rows, excluded)
                    report_html = render_report(profile, involvement, chosen_questions, shifts)
                    return report_html
        elif action == "delete_profile":
            profile_id = str(data_value("profileId", "") or "").strip()
            deleted = delete_profile_from_document(document, profile_id, data_value("deleteConfirmation", ""))
            write_document(document)
            values = profile_form_values()
            message = '<div class="alert alert-success">Configuration deleted: {0}</div>'.format(html_escape(deleted["name"]))
    except Exception as error:
        message = '<div class="alert alert-danger">{0}</div>'.format(html_escape(error))
        if action == "preview":
            return STYLE + '<div class="vsud"><div class="vsud-panel"><h2>Dashboard preview unavailable</h2>{0}</div></div>'.format(message)
        if values["organization_id"] > 0 and not questions:
            try:
                questions = load_questions(values["organization_id"], values["organization_name"])
            except Exception:
                pass
    return render_page(document, values, questions, message, report_html)


def emit_form(content):
    model.Form = content
    print(content)


if "model" in globals():
    model.Header = "Volunteer Signup Dashboard"
    model.Transactional = True
    emit_form(run_app())
