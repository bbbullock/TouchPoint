#Roles=Admin

"""Administrator UI for Volunteer Schedule Report settings and profiles."""

import cgi
import datetime
import json


SETTING_PREFIX = "VSR."
PROFILES_CONTENT = "VolunteerScheduleReportProfiles"
PROFILE_VERSION = 1


DEFAULTS = {
    "EmailEnabled": "false",
    "QueuedByPeopleId": "0",
    "FromAddress": "",
    "FromName": "Volunteer Scheduler",
    "FailureRecipientPeopleIds": "",
}

for setting_name in DEFAULTS:
    if len(SETTING_PREFIX + setting_name) > 50:
        raise ValueError("TouchPoint setting key exceeds 50 characters: {0}".format(setting_name))


model.Header = "Volunteer Schedule Report Administration"
model.Transactional = True


def escape(value):
    return cgi.escape(str(value if value is not None else ""), True)


def posted(name, default=""):
    try:
        value = getattr(Data, name)
        return str(value if value is not None else default).strip()
    except Exception:
        return default


def action():
    return posted("VSRAdminAction", posted("action", "")).lower()


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def parse_ids(raw):
    values = []
    if isinstance(raw, (list, tuple)):
        parts = raw
    else:
        parts = str(raw or "").replace(";", ",").split(",")
    for part in parts:
        value = safe_int(str(part).strip(), 0)
        if value > 0 and value not in values:
            values.append(value)
    return values


def truthy(raw):
    return str(raw or "").strip().lower() in ("true", "1", "yes", "y", "on")


def json_for_script(value):
    return json.dumps(value).replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def current(name):
    return str(model.Setting(SETTING_PREFIX + name, DEFAULTS[name]) or DEFAULTS[name])


def load_document():
    raw = str(model.TextContent(PROFILES_CONTENT) or "").strip()
    if not raw:
        return {"version": PROFILE_VERSION, "profiles": []}
    try:
        value = json.loads(raw)
    except Exception:
        raise ValueError("Saved profile content is not valid JSON. Correct or archive the Text Content before saving.")
    if not isinstance(value, dict) or safe_int(value.get("version"), 0) != PROFILE_VERSION:
        raise ValueError("Saved profile content has an unsupported version.")
    if not isinstance(value.get("profiles"), list):
        value["profiles"] = []
    return value


def save_document(document):
    model.WriteContentText(PROFILES_CONTENT, json.dumps(document, sort_keys=True), "")


def profile_id(name):
    base = "".join(char.lower() if char.isalnum() else "-" for char in str(name)).strip("-")
    while "--" in base:
        base = base.replace("--", "-")
    if not base:
        base = "profile"
    return "{0}-{1}".format(base[:28], datetime.datetime.now().strftime("%Y%m%d%H%M%S"))


def selected_profile(document):
    wanted = posted("profileId")
    for profile in document["profiles"]:
        if str(profile.get("id", "")) == wanted:
            return profile
    return None


def search_people():
    term = posted("term")
    exact_id = safe_int(term, 0)
    if len(term) < 2 and not exact_id:
        return '{"success":true,"items":[]}'
    rows = list(q.QuerySql("""
        SELECT TOP 15 PeopleId, Name2, EmailAddress, CellPhone
        FROM People
        WHERE PeopleId = @ExactId
           OR ((Name LIKE @LikeTerm OR Name2 LIKE @LikeTerm OR EmailAddress LIKE @LikeTerm)
               AND ISNULL(IsDeceased, 0) = 0 AND ISNULL(ArchivedFlag, 0) = 0)
        ORDER BY CASE WHEN PeopleId = @ExactId THEN 0 ELSE 1 END, Name2
    """, {"ExactId": exact_id, "LikeTerm": "%" + term + "%"}))
    items = []
    for row in rows:
        items.append({"id": safe_int(row.PeopleId), "name": str(row.Name2 or ""),
                      "email": str(row.EmailAddress or ""), "phone": str(row.CellPhone or "")})
    return json.dumps({"success": True, "items": items})


def search_involvements():
    term = posted("term")
    exact_id = safe_int(term, 0)
    if len(term) < 2 and not exact_id:
        return '{"success":true,"items":[]}'
    rows = list(q.QuerySql("""
        SELECT TOP 15 o.OrganizationId, o.OrganizationName
        FROM Organizations o
        WHERE o.OrganizationStatusId = 30
          AND o.RegistrationTypeId = 22
          AND (o.OrganizationId = @ExactId OR o.OrganizationName LIKE @LikeTerm)
          AND EXISTS (
              SELECT 1 FROM TimeSlotMeetings tsm
              JOIN Meetings m ON m.MeetingId = tsm.MeetingId
              WHERE m.OrganizationId = o.OrganizationId
          )
        ORDER BY CASE WHEN o.OrganizationId = @ExactId THEN 0 ELSE 1 END,
                 o.OrganizationName
    """, {"ExactId": exact_id, "LikeTerm": "%" + term + "%"}))
    items = [{"id": safe_int(row.OrganizationId), "name": str(row.OrganizationName or "")} for row in rows]
    return json.dumps({"success": True, "items": items})


def validate_people_ids(ids):
    values = parse_ids(ids)
    if not values:
        return []
    rows = list(q.QuerySql("""
        SELECT PeopleId FROM People
        WHERE PeopleId IN ({0})
          AND ISNULL(IsDeceased, 0) = 0 AND ISNULL(ArchivedFlag, 0) = 0
    """.format(",".join(str(value) for value in values))))
    found = sorted(safe_int(row.PeopleId) for row in rows)
    if found != sorted(values):
        raise ValueError("One or more selected staff People IDs are invalid or inactive.")
    return values


def validate_scheduler_ids(ids):
    values = parse_ids(ids)
    if not values:
        raise ValueError("Select at least one Scheduler Involvement.")
    rows = list(q.QuerySql("""
        SELECT o.OrganizationId
        FROM Organizations o
        WHERE o.OrganizationId IN ({0})
          AND o.OrganizationStatusId = 30
          AND o.RegistrationTypeId = 22
          AND EXISTS (
              SELECT 1 FROM TimeSlotMeetings tsm
              JOIN Meetings m ON m.MeetingId = tsm.MeetingId
              WHERE m.OrganizationId = o.OrganizationId
          )
    """.format(",".join(str(value) for value in values))))
    found = sorted(safe_int(row.OrganizationId) for row in rows)
    if found != sorted(values):
        raise ValueError("One or more selected Involvements are not active Schedulers.")
    return values


def save_profile(document):
    name = posted("profileName")
    if not name:
        raise ValueError("Profile name is required.")
    scheduler_ids = validate_scheduler_ids(posted("schedulerIds"))
    staff_ids = validate_people_ids(posted("staffPeopleIds"))
    include_volunteers = truthy(posted("includeServingVolunteers"))
    include_email = truthy(posted("includeVolunteerEmail"))
    include_phone = truthy(posted("includeVolunteerPhone"))
    enabled = truthy(posted("enabled"))
    acknowledged = truthy(posted("privacyAcknowledged"))
    if not include_volunteers and not staff_ids:
        raise ValueError("Choose serving volunteers and/or at least one retained staff recipient.")
    if include_volunteers and enabled and (include_email or include_phone) and not acknowledged:
        raise ValueError("Confirm the contact-information notice before enabling volunteer delivery.")
    existing = selected_profile(document)
    value = {
        "id": str(existing.get("id")) if existing else profile_id(name),
        "name": name,
        "scheduler_ids": scheduler_ids,
        "include_serving_volunteers": include_volunteers,
        "include_volunteer_email": include_email,
        "include_volunteer_phone": include_phone,
        "staff_people_ids": staff_ids,
        "enabled": enabled,
        "send_weekday": 0,
        "privacy_acknowledged": acknowledged,
    }
    if existing:
        document["profiles"][document["profiles"].index(existing)] = value
    else:
        document["profiles"].append(value)
    document["profiles"].sort(key=lambda item: str(item.get("name", "")).lower())
    save_document(document)
    return value


def delete_profile(document):
    existing = selected_profile(document)
    if existing is None:
        raise ValueError("Profile was not found.")
    document["profiles"].remove(existing)
    save_document(document)


def save_settings():
    email_enabled = truthy(posted("EmailEnabled"))
    queued_by = safe_int(posted("QueuedByPeopleId"), 0)
    from_address = posted("FromAddress")
    from_name = posted("FromName")
    failures = validate_people_ids(posted("FailureRecipientPeopleIds"))
    if email_enabled:
        if queued_by <= 0:
            raise ValueError("Queued-by People ID is required before email can be enabled.")
        validate_people_ids([queued_by])
        if not from_address or "@" not in from_address:
            raise ValueError("A valid from address is required before email can be enabled.")
        if not from_name:
            raise ValueError("From name is required before email can be enabled.")
    values = {
        "EmailEnabled": "true" if email_enabled else "false",
        "QueuedByPeopleId": str(queued_by),
        "FromAddress": from_address,
        "FromName": from_name,
        "FailureRecipientPeopleIds": ",".join(str(value) for value in failures),
    }
    for name in values:
        model.SetSetting(SETTING_PREFIX + name, values[name])


def people_data(ids):
    values = parse_ids(ids)
    if not values:
        return []
    rows = list(q.QuerySql("""
        SELECT PeopleId, Name2, EmailAddress, CellPhone
        FROM People WHERE PeopleId IN ({0}) ORDER BY Name2
    """.format(",".join(str(value) for value in values))))
    return [{"id": safe_int(row.PeopleId), "name": str(row.Name2 or ""),
             "email": str(row.EmailAddress or ""), "phone": str(row.CellPhone or "")} for row in rows]


def involvement_data(ids):
    values = parse_ids(ids)
    if not values:
        return []
    rows = list(q.QuerySql("""
        SELECT OrganizationId, OrganizationName FROM Organizations
        WHERE OrganizationId IN ({0}) ORDER BY OrganizationName
    """.format(",".join(str(value) for value in values))))
    return [{"id": safe_int(row.OrganizationId), "name": str(row.OrganizationName or "")} for row in rows]


def profile_card(profile):
    status = "Enabled" if profile.get("enabled") else "Disabled"
    volunteers = "Serving volunteers plus selected staff" if profile.get("include_serving_volunteers") else "Selected staff only"
    contacts = []
    if profile.get("include_volunteer_email", True):
        contacts.append("email")
    if profile.get("include_volunteer_phone", True):
        contacts.append("mobile phone")
    contact_text = "Includes " + " and ".join(contacts) if contacts else "Contact details excluded"
    return """
    <div class="vsra-card"><div><h4>{0}</h4><p>{1} &middot; Monday &middot; {2}</p><p>{3} Scheduler(s), {4} retained staff recipient(s) &middot; {6}</p></div>
    <div><form action="/PyScriptForm/VolunteerScheduleReportAdmin" method="post" style="display:inline"><input type="hidden" name="profileId" value="{5}"><button class="btn btn-default btn-sm" name="VSRAdminAction" value="edit">Edit</button></form>
    <form action="/PyScriptForm/VolunteerScheduleReportAdmin" method="post" style="display:inline" onsubmit="return confirm('Delete this saved report profile?')"><input type="hidden" name="profileId" value="{5}"><button class="btn btn-danger btn-sm" name="VSRAdminAction" value="delete">Delete</button></form></div></div>
    """.format(escape(profile.get("name")), escape(status), escape(volunteers),
               len(parse_ids(profile.get("scheduler_ids", []))),
               len(parse_ids(profile.get("staff_people_ids", []))), escape(profile.get("id")),
               escape(contact_text))


def render_page(document, edit_profile, message):
    profile = edit_profile or {}
    orgs = involvement_data(profile.get("scheduler_ids", []))
    staff = people_data(profile.get("staff_people_ids", []))
    checked_volunteers = " checked" if profile.get("include_serving_volunteers") else ""
    checked_email = " checked" if profile.get("include_volunteer_email", True) else ""
    checked_phone = " checked" if profile.get("include_volunteer_phone", True) else ""
    checked_enabled = " checked" if profile.get("enabled") else ""
    checked_privacy = " checked" if profile.get("privacy_acknowledged") else ""
    email_enabled = " checked" if truthy(current("EmailEnabled")) else ""
    failure_people = people_data(current("FailureRecipientPeopleIds"))
    queued_people = people_data(current("QueuedByPeopleId"))
    return """
<style>
.vsra{{max-width:1180px;margin:20px auto;color:#263746}}.vsra-section{{border:1px solid #d8e0e7;border-radius:8px;padding:18px;margin-bottom:18px;background:#fff}}.vsra-grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}.vsra-wide{{grid-column:1/-1}}.vsra-card{{display:flex;justify-content:space-between;gap:15px;border-top:1px solid #e2e8ed;padding:12px 0}}.vsra-selected{{display:flex;gap:6px;flex-wrap:wrap;margin-top:7px}}.vsra-pill{{background:#e8f1f8;border-radius:14px;padding:4px 9px}}.vsra-search{{position:relative}}.vsra-list{{position:absolute;z-index:5;width:100%;background:white;border:1px solid #ccd6df;box-shadow:0 3px 10px #999;max-height:220px;overflow:auto}}.vsra-result{{display:block;width:100%;border:0;border-bottom:1px solid #eee;background:#fff;text-align:left;padding:8px}}.vsra-privacy{{border-left:5px solid #b43535;background:#fff3f3;padding:12px}}@media(max-width:700px){{.vsra-grid{{grid-template-columns:1fr}}.vsra-card{{display:block}}}}
</style>
<div class="vsra"><h2>Volunteer Schedule Report Administration</h2>{0}
<div class="vsra-section"><h3>Delivery settings</h3><p>Email remains off until explicitly enabled after live preview validation.</p>
<form action="/PyScriptForm/VolunteerScheduleReportAdmin" method="post"><div class="vsra-grid">
<div><label>Queued-by person</label><div class="vsra-search"><input class="form-control" id="queuedSearch" placeholder="Search by name, email, or People ID"><div id="queuedResults"></div></div><div class="vsra-selected" id="selectedQueued"></div><input type="hidden" name="QueuedByPeopleId" id="queuedById"></div>
<div><label>From name</label><input class="form-control" name="FromName" value="{2}"></div>
<div><label>From address</label><input class="form-control" type="email" name="FromAddress" value="{3}"></div>
<div><label>Failure recipients</label><div class="vsra-search"><input class="form-control" id="failureSearch" placeholder="Search people"><div id="failureResults"></div></div><div class="vsra-selected" id="selectedFailures"></div><input type="hidden" name="FailureRecipientPeopleIds" id="failureIds" value="{4}"></div>
<div class="vsra-wide"><label><input type="checkbox" name="EmailEnabled" value="true"{5}> Enable manual and automated email</label></div>
</div><button class="btn btn-primary" name="VSRAdminAction" value="save_settings">Save delivery settings</button></form></div>
<div class="vsra-section"><h3>Saved Monday profiles</h3>{6}</div>
<div class="vsra-section"><h3>{7}</h3>
<form action="/PyScriptForm/VolunteerScheduleReportAdmin" method="post"><input type="hidden" name="profileId" value="{8}"><div class="vsra-grid">
<div class="vsra-wide"><label>Profile name</label><input class="form-control" name="profileName" value="{9}" required></div>
<div class="vsra-wide"><label>Scheduler Involvements</label><div class="vsra-search"><input class="form-control" id="orgSearch" placeholder="Search by name or ID"><div id="orgResults"></div></div><div class="vsra-selected" id="selectedOrgs"></div><input type="hidden" name="schedulerIds" id="schedulerIds"></div>
<div class="vsra-wide"><label>Retained staff recipients</label><div class="vsra-search"><input class="form-control" id="staffSearch" placeholder="Search by name, email, or People ID"><div id="staffResults"></div></div><div class="vsra-selected" id="selectedStaff"></div><input type="hidden" name="staffPeopleIds" id="staffIds"></div>
<div class="vsra-wide"><label><input type="checkbox" name="includeServingVolunteers" value="true"{10}> Email all volunteers counted as serving during the report window</label></div>
<div><label><input type="checkbox" name="includeVolunteerEmail" value="true"{13}> Include volunteer email addresses</label></div>
<div><label><input type="checkbox" name="includeVolunteerPhone" value="true"{14}> Include volunteer mobile phones</label></div>
<div class="vsra-wide vsra-privacy"><strong>Contact-information notice</strong><p>Each recipient receives the same complete report. Any contact fields selected above are visible for every listed volunteer.</p><label><input type="checkbox" name="privacyAcknowledged" value="true"{11}> I confirm this profile is authorized to distribute the selected contact details.</label></div>
<div class="vsra-wide"><label><input type="checkbox" name="enabled" value="true"{12}> Enable this profile for Monday Morning Batch</label></div>
</div><button class="btn btn-primary" name="VSRAdminAction" value="save_profile">Save profile</button> <a class="btn btn-default" href="?">Clear</a></form></div></div>
<script>
(function(){{
var orgs={13},staff={14},failures={15},queued={16};
function esc(v){{return String(v||'').replace(/[&<>"']/g,function(c){{return {{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c];}});}}
function draw(items,box,hidden){{box.innerHTML='';items.forEach(function(x,i){{var s=document.createElement('span');s.className='vsra-pill';s.innerHTML=esc(x.name)+' ('+x.id+') <button type="button">&times;</button>';s.querySelector('button').onclick=function(){{items.splice(i,1);draw(items,box,hidden);}};box.appendChild(s);}});hidden.value=items.map(function(x){{return x.id;}}).join(',');}}
function wire(inputId,resultId,action,items,boxId,hiddenId,single){{var input=document.getElementById(inputId),result=document.getElementById(resultId),box=document.getElementById(boxId),hidden=document.getElementById(hiddenId),timer;draw(items,box,hidden);input.oninput=function(){{clearTimeout(timer);var term=input.value.trim();if(term.length<2){{result.innerHTML='';return;}}timer=setTimeout(function(){{fetch('/PyScriptForm/VolunteerScheduleReportAdmin',{{method:'POST',headers:{{'Content-Type':'application/x-www-form-urlencoded'}},body:'VSRAdminAction='+action+'&term='+encodeURIComponent(term)}}).then(function(r){{return r.json();}}).then(function(d){{result.className='vsra-list';result.innerHTML='';(d.items||[]).forEach(function(x){{var b=document.createElement('button');b.type='button';b.className='vsra-result';b.textContent=x.name+' ('+x.id+')'+(x.email?' — '+x.email:'');b.onclick=function(){{if(single)items.splice(0,items.length);if(!items.some(function(y){{return y.id===x.id;}}))items.push(x);draw(items,box,hidden);result.innerHTML='';input.value='';}};result.appendChild(b);}});}});}},250);}};}}
wire('orgSearch','orgResults','search_involvements',orgs,'selectedOrgs','schedulerIds');
wire('staffSearch','staffResults','search_people',staff,'selectedStaff','staffIds');
wire('failureSearch','failureResults','search_people',failures,'selectedFailures','failureIds');
wire('queuedSearch','queuedResults','search_people',queued,'selectedQueued','queuedById',true);
}})();
</script>
""".format(
        message,
        escape(current("QueuedByPeopleId")), escape(current("FromName")),
        escape(current("FromAddress")), escape(current("FailureRecipientPeopleIds")),
        email_enabled,
        "".join(profile_card(value) for value in document["profiles"]) or "<p>No profiles saved yet.</p>",
        "Edit profile" if edit_profile else "New profile", escape(profile.get("id", "")),
        escape(profile.get("name", "")), checked_volunteers, checked_privacy,
        checked_enabled, json_for_script(orgs), json_for_script(staff),
        json_for_script(failure_people), json_for_script(queued_people),
        checked_email, checked_phone,
    )


def run_admin():
    if not model.UserIsInRole("Admin"):
        return '<div class="alert alert-danger">Administrator access is required.</div>'

    current_action = action()
    if current_action == "search_people":
        return search_people()
    if current_action == "search_involvements":
        return search_involvements()

    message = ""
    document = {"version": PROFILE_VERSION, "profiles": []}
    edit_profile = None
    try:
        document = load_document()
        if current_action == "save_settings":
            save_settings()
            message = '<div class="alert alert-success">Delivery settings saved.</div>'
        elif current_action == "save_profile":
            saved = save_profile(document)
            message = '<div class="alert alert-success">Profile saved: {0}</div>'.format(escape(saved["name"]))
        elif current_action == "delete":
            delete_profile(document)
            message = '<div class="alert alert-success">Profile deleted.</div>'
        elif current_action == "edit":
            edit_profile = selected_profile(document)
            if edit_profile is None:
                raise ValueError("Profile was not found.")
    except Exception as error:
        message = '<div class="alert alert-danger">{0}</div>'.format(escape(error))
        try:
            document = load_document()
            edit_profile = selected_profile(document)
        except Exception:
            pass
    return render_page(document, edit_profile, message)


def emit_form(content):
    model.Form = content
    print(content)


emit_form(run_admin())
