#!/usr/bin/env python3
import base64
import json
import mimetypes
import os
import re
import socket
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
UPLOAD_DIR = ROOT / "assets" / "uploads"
PASSWORD_PATH = ROOT / "server.local.json"
DEFAULT_PASSWORD = "change-me"
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
MAX_PROMO_ITEMS = 7
DEFAULT_TIMEZONE = "America/Chicago"
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8080
APP_TIMEZONE = None


def load_password():
    env_password = os.environ.get("DISPLAY_CONFIG_PASSWORD")
    if env_password:
        return env_password
    if PASSWORD_PATH.exists():
        with PASSWORD_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        password = str(data.get("password", "")).strip()
        if password:
            return password
    return DEFAULT_PASSWORD


def read_json_body(handler):
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw.decode("utf-8"))


def send_json(handler, status, payload):
    body = json.dumps(payload, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def app_timezone():
    global APP_TIMEZONE
    if APP_TIMEZONE is False:
        return None
    if APP_TIMEZONE is not None:
        return APP_TIMEZONE
    try:
        APP_TIMEZONE = ZoneInfo(DEFAULT_TIMEZONE)
    except ZoneInfoNotFoundError:
        APP_TIMEZONE = False
        return None
    return APP_TIMEZONE


def local_now():
    timezone = app_timezone()
    return datetime.now(timezone) if timezone else datetime.now()


def apply_app_timezone(value):
    timezone = app_timezone()
    return value.replace(tzinfo=timezone) if timezone else value


def validate_url(value, field_name, allow_relative=True):
    value = str(value or "").strip()
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        return value
    if allow_relative and not parsed.scheme and not value.startswith("//"):
        if re.match(r"^[A-Za-z0-9._~!$&'()*+,;=:@/%-]+$", value):
            return value
    raise ValueError(f"{field_name} must be blank, an http(s) URL, or a local relative path")


def validate_http_url(value, field_name):
    value = str(value or "").strip()
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return value
    raise ValueError(f"{field_name} must be an http(s) URL")


def validate_bool(value, field_name):
    if isinstance(value, bool):
        return value
    raise ValueError(f"{field_name} must be true or false")


def validate_int(value, field_name, low, high):
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a number")
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a number")
    if number < low or number > high:
        raise ValueError(f"{field_name} must be between {low} and {high}")
    return number


def validate_fit(value, field_name):
    value = str(value or "").strip()
    if value not in {"contain", "cover"}:
        raise ValueError(f"{field_name} must be contain or cover")
    return value


def validate_date(value, field_name):
    value = str(value or "").strip()
    if not value:
        return ""
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        raise ValueError(f"{field_name} must be blank or use YYYY-MM-DD")
    return value


def validate_time(value, field_name):
    value = str(value or "").strip()
    if not value:
        return ""
    if not re.match(r"^\d{2}:\d{2}$", value):
        raise ValueError(f"{field_name} must be blank or use HH:MM")
    hours, minutes = value.split(":")
    if int(hours) > 23 or int(minutes) > 59:
        raise ValueError(f"{field_name} must be a valid time")
    return value


def local_schedule_datetime(date_value, time_value, default_time):
    if not date_value:
        return None
    time_part = time_value or default_time
    return apply_app_timezone(datetime.fromisoformat(f"{date_value}T{time_part}"))


def validate_hex_color(value, field_name):
    value = str(value or "").strip()
    if not value:
        return "#EAF1F7"
    if re.match(r"^#[0-9A-Fa-f]{6}$", value):
        return value.upper()
    if re.match(r"^[0-9A-Fa-f]{6}$", value):
        return f"#{value.upper()}"
    raise ValueError(f"{field_name} must use #RRGGBB format")


def today_key(timezone=DEFAULT_TIMEZONE):
    return local_now().strftime("%Y-%m-%d")


def validate_promo_items(items, fallback, field_name):
    source = items if isinstance(items, list) else []
    if not source and fallback:
        source = [fallback]
    result = []
    now = local_now()
    for index, item in enumerate(source[:MAX_PROMO_ITEMS]):
        item = item or {}
        enabled = validate_bool(item.get("enabled", False), f"{field_name} {index + 1} enabled")
        title = str(item.get("title") or "")[:120]
        image_url = validate_url(item.get("imageUrl"), f"{field_name} {index + 1} image URL")
        fit = validate_fit(item.get("fit") or "contain", f"{field_name} {index + 1} fit")
        start_date = validate_date(item.get("startDate"), f"{field_name} {index + 1} start date")
        stop_date = validate_date(item.get("stopDate"), f"{field_name} {index + 1} stop date")
        start_time = validate_time(item.get("startTime"), f"{field_name} {index + 1} start time")
        stop_time = validate_time(item.get("stopTime"), f"{field_name} {index + 1} stop time")
        start_datetime = local_schedule_datetime(start_date, start_time, "00:01")
        stop_datetime = local_schedule_datetime(stop_date, stop_time, "23:59")
        if start_datetime and stop_datetime and start_datetime > stop_datetime:
            raise ValueError(f"{field_name} {index + 1} stop date/time cannot be before start date/time")
        if stop_datetime and stop_datetime < now:
            continue
        if enabled and not image_url:
            raise ValueError(f"{field_name} {index + 1} needs an image URL when enabled")
        if enabled or title or image_url or start_date or stop_date:
            promo_item = {
                "enabled": enabled,
                "title": title,
                "imageUrl": image_url,
                "fit": fit,
                "startDate": start_date,
                "startTime": start_time,
                "stopDate": stop_date,
                "stopTime": stop_time,
            }
            result.append(promo_item)
    validate_promo_overlaps(result, field_name)
    return result


def promo_window(item):
    start = local_schedule_datetime(item.get("startDate"), item.get("startTime"), "00:01") or apply_app_timezone(datetime.min)
    stop = local_schedule_datetime(item.get("stopDate"), item.get("stopTime"), "23:59") or apply_app_timezone(datetime.max)
    return start, stop


def validate_promo_overlaps(items, field_name):
    scheduled = [
        (index, item, *promo_window(item))
        for index, item in enumerate(items)
        if item.get("enabled")
    ]
    for left_pos, left in enumerate(scheduled):
        left_index, left_item, left_start, left_stop = left
        for right_index, right_item, right_start, right_stop in scheduled[left_pos + 1:]:
            if left_start <= right_stop and right_start <= left_stop:
                raise ValueError(
                    f"{field_name} {right_index + 1} overlaps {field_name} {left_index + 1}. "
                    "Adjust the start/stop date and time."
                )


def empty_full_screen_override():
    return {
        "enabled": False,
        "title": "",
        "imageUrl": "",
        "fit": "contain",
        "startDate": "",
        "startTime": "",
        "stopDate": "",
        "stopTime": "",
    }


def validate_full_screen_override_item(item, index):
    item = item or {}
    label = f"Full-screen Override {index + 1}"
    enabled = validate_bool(item.get("enabled", False), f"{label} enabled")
    title = str(item.get("title") or "")[:120]
    image_url = validate_url(item.get("imageUrl"), f"{label} image URL")
    fit = validate_fit(item.get("fit") or "contain", f"{label} fit")
    start_date = validate_date(item.get("startDate"), f"{label} start date")
    stop_date = validate_date(item.get("stopDate"), f"{label} stop date")
    start_time = validate_time(item.get("startTime"), f"{label} start time")
    stop_time = validate_time(item.get("stopTime"), f"{label} stop time")
    start_datetime = local_schedule_datetime(start_date, start_time, "00:01")
    stop_datetime = local_schedule_datetime(stop_date, stop_time, "23:59")
    now = local_now()

    if stop_datetime and stop_datetime < now:
        return None
    if enabled:
        if not image_url:
            raise ValueError(f"{label} needs an image URL when enabled")
        if not start_date or not stop_date:
            raise ValueError(f"{label} requires start and stop dates when enabled")
    if start_datetime and stop_datetime and start_datetime > stop_datetime:
        raise ValueError(f"{label} stop date/time cannot be before start date/time")

    if not (enabled or title or image_url or start_date or start_time or stop_date or stop_time):
        return None
    return {
        "enabled": enabled,
        "title": title,
        "imageUrl": image_url,
        "fit": fit,
        "startDate": start_date,
        "startTime": start_time,
        "stopDate": stop_date,
        "stopTime": stop_time,
    }


def validate_full_screen_overrides(items, fallback):
    source = items if isinstance(items, list) else []
    if not source and fallback:
        source = [fallback]
    result = []
    for index, item in enumerate(source[:MAX_PROMO_ITEMS]):
        override = validate_full_screen_override_item(item, index)
        if override:
            result.append(override)
    validate_promo_overlaps(result, "Full-screen Override")
    return result


def slugify_key(value, fallback):
    key = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return key[:80] or fallback


def validate_calendar_feeds(items):
    if not isinstance(items, list):
        return []
    result = []
    used_keys = set()
    for index, item in enumerate(items):
        item = item or {}
        enabled = validate_bool(item.get("enabled", True), f"Calendar feed {index + 1} enabled")
        label = str(item.get("label") or "").strip()[:120]
        url = validate_http_url(item.get("url"), f"Calendar feed {index + 1} URL")
        if not label and not url:
            continue
        if not label:
            raise ValueError(f"Calendar feed {index + 1} needs a name")
        if not url:
            raise ValueError(f"Calendar feed {index + 1} needs a URL")
        key = slugify_key(item.get("key") or label, f"feed-{index + 1}")
        base_key = key
        counter = 2
        while key in used_keys:
            key = f"{base_key}-{counter}"
            counter += 1
        used_keys.add(key)
        result.append({
            "enabled": enabled,
            "key": key,
            "label": label,
            "url": url,
        })
    return result


def validate_config(data):
    brand = data.get("brand") or {}
    display = data.get("display") or {}
    promotions = data.get("promotions") or {}
    side = promotions.get("sidePanel") or {}
    bottom = promotions.get("bottomBanner") or {}
    full_screen_overrides = validate_full_screen_overrides(promotions.get("fullScreenOverrides"), promotions.get("fullScreenOverride"))
    banner_images = validate_promo_items(promotions.get("bannerImages"), side, "Banner Image")
    event_images = validate_promo_items(promotions.get("eventImages"), bottom, "Event Image")
    active_full_screen_fallback = next((item for item in full_screen_overrides if item.get("enabled")), None)
    active_banner_fallback = next((item for item in banner_images if item.get("enabled")), None)
    active_event_fallback = next((item for item in event_images if item.get("enabled")), None)

    return {
        "brand": {
            "logoUrl": validate_url(brand.get("logoUrl"), "Logo URL"),
            "hashtag": str(brand.get("hashtag") or "")[:80],
            "website": str(brand.get("website") or "ilcsp.org")[:80],
            "churchName": str(brand.get("churchName") or "Immanuel")[:80],
            "churchSubtitle": str(brand.get("churchSubtitle") or "Lutheran Church")[:120],
        },
        "display": {
            "refreshMinutes": validate_int(display.get("refreshMinutes"), "Refresh minutes", 1, 60),
            "rotatePages": validate_bool(display.get("rotatePages"), "Rotate pages"),
            "pageRotationSeconds": validate_int(display.get("pageRotationSeconds"), "Page rotation seconds", 5, 120),
            "maxEventsPerPage": validate_int(display.get("maxEventsPerPage"), "Max events per page", 1, 20),
            "backgroundColor": validate_hex_color(display.get("backgroundColor"), "Background color"),
            "showFeedName": validate_bool(display.get("showFeedName"), "Show feed names"),
            "showEndTime": validate_bool(display.get("showEndTime"), "Show end times"),
            "hideEventsWithBlankLocation": validate_bool(display.get("hideEventsWithBlankLocation"), "Hide blank locations"),
            "loadGeneralCalendarOnly": validate_bool(display.get("loadGeneralCalendarOnly"), "Load general calendar only"),
        },
        "calendarFeeds": validate_calendar_feeds(data.get("calendarFeeds")),
        "promotions": {
            "fullScreenOverrides": full_screen_overrides,
            "fullScreenOverride": active_full_screen_fallback or empty_full_screen_override(),
            "bannerImages": banner_images,
            "eventImages": event_images,
            "sidePanel": {
                "enabled": bool(active_banner_fallback),
                "title": active_banner_fallback.get("title", "") if active_banner_fallback else "",
                "imageUrl": active_banner_fallback.get("imageUrl", "") if active_banner_fallback else "",
                "fit": active_banner_fallback.get("fit", "contain") if active_banner_fallback else "contain",
            },
            "bottomBanner": {
                "enabled": bool(active_event_fallback),
                "title": active_event_fallback.get("title", "") if active_event_fallback else "",
                "imageUrl": active_event_fallback.get("imageUrl", "") if active_event_fallback else "",
                "fit": active_event_fallback.get("fit", "contain") if active_event_fallback else "contain",
            },
        },
    }


def sanitize_filename(filename):
    name = Path(filename or "upload").name
    stem = re.sub(r"[^A-Za-z0-9_-]+", "-", Path(name).stem).strip("-") or "upload"
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("File must be png, jpg, jpeg, webp, or svg")
    return f"{stem}{ext}"


def upload_content_from_payload(filename, data_url):
    filename = sanitize_filename(filename)
    data_url = str(data_url or "")
    match = re.match(r"^data:([^;,]+);base64,(.+)$", data_url)
    if not match:
        raise ValueError("Upload payload is invalid")
    content_type = match.group(1)
    content = base64.b64decode(match.group(2), validate=True)
    if len(content) > 8 * 1024 * 1024:
        raise ValueError("File must be 8 MB or smaller")
    guessed_type = mimetypes.guess_type(filename)[0] or ""
    if content_type not in {"image/png", "image/jpeg", "image/webp", "image/svg+xml"}:
        raise ValueError("Only image uploads are allowed")
    if guessed_type and guessed_type != content_type and not filename.endswith(".jpg"):
        raise ValueError("File extension does not match the uploaded image type")
    return filename, content


def save_upload_content(filename, content):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    target = UPLOAD_DIR / filename
    counter = 1
    while target.exists():
        target = UPLOAD_DIR / f"{Path(filename).stem}-{counter}{Path(filename).suffix}"
        counter += 1
    target.write_bytes(content)
    return str(target.relative_to(ROOT)).replace(os.sep, "/")


def save_upload_payload(filename, data_url):
    filename, content = upload_content_from_payload(filename, data_url)
    return save_upload_content(filename, content)


def pending_upload_refs(value):
    if isinstance(value, dict):
        refs = set()
        for item in value.values():
            refs.update(pending_upload_refs(item))
        return refs
    if isinstance(value, list):
        refs = set()
        for item in value:
            refs.update(pending_upload_refs(item))
        return refs
    if isinstance(value, str) and value.startswith("__pending_upload__:"):
        return {value.split(":", 1)[1]}
    return set()


def replace_pending_upload_refs(value, upload_urls):
    if isinstance(value, dict):
        return {key: replace_pending_upload_refs(item, upload_urls) for key, item in value.items()}
    if isinstance(value, list):
        return [replace_pending_upload_refs(item, upload_urls) for item in value]
    if isinstance(value, str) and value.startswith("__pending_upload__:"):
        upload_id = value.split(":", 1)[1]
        return upload_urls.get(upload_id, "")
    return value


def config_from_payload(payload):
    if "config" not in payload:
        return payload
    config = validate_config(payload.get("config") or {})
    uploads = payload.get("uploads") or {}
    prepared_uploads = {}
    for upload_id in pending_upload_refs(config):
        upload = uploads.get(upload_id)
        if upload:
            prepared_uploads[upload_id] = upload_content_from_payload(upload.get("filename"), upload.get("dataUrl"))
    upload_urls = {}
    for upload_id, (filename, content) in prepared_uploads.items():
        upload_urls[upload_id] = save_upload_content(filename, content)
    return replace_pending_upload_refs(config, upload_urls)


def local_network_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return ""


class DisplayHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        if self.path == "/api/config":
            if not CONFIG_PATH.exists():
                send_json(self, 404, {"error": "config.json not found"})
                return
            with CONFIG_PATH.open("r", encoding="utf-8") as handle:
                raw_config = json.load(handle)
            config = validate_config(raw_config)
            if config != raw_config:
                with CONFIG_PATH.open("w", encoding="utf-8") as handle:
                    json.dump(config, handle, indent=2)
                    handle.write("\n")
            send_json(self, 200, config)
            return
        super().do_GET()

    def do_POST(self):
        if self.path not in {"/api/config", "/api/upload"}:
            send_json(self, 404, {"error": "Not found"})
            return
        if self.headers.get("X-Config-Password", "") != load_password():
            send_json(self, 401, {"error": "Invalid save password"})
            return
        try:
            if self.path == "/api/config":
                config = validate_config(config_from_payload(read_json_body(self)))
                with CONFIG_PATH.open("w", encoding="utf-8") as handle:
                    json.dump(config, handle, indent=2)
                    handle.write("\n")
                send_json(self, 200, {"ok": True, "config": config})
                return
            payload = read_json_body(self)
            url = save_upload_payload(payload.get("filename"), payload.get("dataUrl"))
            send_json(self, 200, {"ok": True, "url": url})
        except (ValueError, json.JSONDecodeError) as error:
            send_json(self, 400, {"error": str(error)})


def main():
    os.chdir(ROOT)
    password = load_password()
    if password == DEFAULT_PASSWORD:
        print("WARNING: using default settings password 'change-me'.")
        print("Create server.local.json or set DISPLAY_CONFIG_PASSWORD before production use.")
    server = ThreadingHTTPServer((SERVER_HOST, SERVER_PORT), DisplayHandler)
    network_ip = local_network_ip()
    print(f"Serving display locally at http://127.0.0.1:{SERVER_PORT}/activities-display.html")
    print(f"Serving settings locally at http://127.0.0.1:{SERVER_PORT}/settings.html")
    if network_ip:
        print(f"Display sign URL: http://{network_ip}:{SERVER_PORT}/activities-display.html")
        print(f"Network settings URL: http://{network_ip}:{SERVER_PORT}/settings.html")
    else:
        print(f"Display sign URL: http://<your-mac-ip>:{SERVER_PORT}/activities-display.html")
    server.serve_forever()


if __name__ == "__main__":
    main()
