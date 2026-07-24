# Local Server Runbook

This app should be opened through the local server, not by double-clicking the HTML files.

## URLs

- Display: `http://127.0.0.1:8080/activities-display.html`
- Settings: `http://127.0.0.1:8080/settings.html`
- Config API test: `http://127.0.0.1:8080/api/config`

For the actual sign, use the Windows PC network IP:

```text
http://WINDOWS-PC-IP:8080/activities-display.html
```

## Start On Mac

From the app folder:

```bash
python3 server.py
```

## Start On Windows

Production folder:

```text
C:\TouchPointExtensionApps\UnifiDisplaySigns
```

Manual start:

```bat
cd /d C:\TouchPointExtensionApps\UnifiDisplaySigns
python server.py
```

If Windows uses the Python launcher:

```bat
cd /d C:\TouchPointExtensionApps\UnifiDisplaySigns
py server.py
```

## Startup Batch File

Use this pattern in the startup `.bat` file:

```bat
@echo off
cd /d C:\TouchPointExtensionApps\UnifiDisplaySigns
python server.py
```

The `cd /d` line is required so the server reads `config.json`, `server.local.json`, and `assets/uploads/` from the app folder.

## Settings Password

The default first-run password is:

```text
change-me
```

For production, create `server.local.json` in the app folder:

```json
{
  "password": "your-private-password"
}
```

`server.local.json` is ignored by git and should remain local to the production PC.

You can also set the password with the `DISPLAY_CONFIG_PASSWORD` environment variable before starting the server.

## Image Uploads

The settings page can stage image uploads without the password.

The image is only written into `assets/uploads/` after:

1. The user clicks `Save Settings`.
2. The save password is accepted.
3. The settings payload passes validation.

If the settings page is refreshed before saving, staged images are discarded.

## Troubleshooting

Check whether the server is running:

```bat
netstat -aon | findstr LISTENING | findstr :8080
```

If nothing returns, the server is not running.

To test config loading:

```text
http://127.0.0.1:8080/api/config
```

Expected result: raw JSON appears in the browser.

If `/api/config` fails:

- Confirm `config.json` exists directly in the app folder.
- Confirm the batch file uses `cd /d C:\TouchPointExtensionApps\UnifiDisplaySigns`.
- Confirm the app folder was not nested one level too deep.
- Confirm the page is opened with `http://127.0.0.1:8080/settings.html`.

If Python reports `No module named 'tzdata'`, use the current `server.py`; it has a Windows fallback for missing timezone data.
