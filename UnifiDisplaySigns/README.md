# Unifi Display Signs

Local signage app for the Immanuel Lutheran Church activities display.

The app shows today's TouchPoint calendar events, church branding, scheduled promo graphics, and optional full-screen override images. It is designed to run on a local PC on the church network and be viewed by a display sign through a browser URL.

## Main Pages

- Display: `http://127.0.0.1:8080/activities-display.html`
- Settings: `http://127.0.0.1:8080/settings.html`
- Config API test: `http://127.0.0.1:8080/api/config`

For the actual sign, use the Windows PC network address:

```text
http://WINDOWS-PC-IP:8080/activities-display.html
```

Example:

```text
http://192.168.1.50:8080/activities-display.html
```

## Files

- `activities-display.html`: public display page for the sign.
- `settings.html`: settings page for branding, calendar feeds, promos, and overrides.
- `config.json`: saved app configuration.
- `server.py`: local web server and password-protected settings API.
- `server.local.example.json`: example local password file.
- `server.local.json`: local password file, not committed to git.
- `assets/uploads/`: locally uploaded image files, not committed to git.
- `LOCAL_SERVER.md`: detailed local/Windows startup notes.

## How The App Works

The display page first asks the local server for `config.json` through `/api/config`. If the server is not running, the page may try to fall back to `config.json`, but production should use the server URL, not a file opened directly.

The settings page also uses `/api/config`. It cannot save settings unless the local server is running.

## Settings Page

The settings page has four tabs:

- Display Settings
- Calendar Feeds
- Scheduled Promos
- Full-Screen Override

The Access / Save password field appears above the tabs. The password is required only when saving settings.

Image uploads can be selected and staged without the password. The image file is not actually written into `assets/uploads/` until `Save Settings` is clicked and the password is accepted.

## Display Settings

Display Settings controls:

- church name
- church subtitle
- website
- hashtag
- logo image
- refresh minutes
- page rotation
- page rotation seconds
- max events per page
- background color
- feed-name visibility
- end-time visibility
- blank-location filtering
- general-calendar-only loading

## Calendar Feeds

Calendar Feeds controls the TouchPoint `.ics` feed URLs used by the display.

Each feed has:

- enabled/disabled state
- calendar name
- feed URL

Calendar feed URLs are stored in `config.json` and are no longer hard-coded into `activities-display.html`.

## Scheduled Promos

Scheduled Promos supports two promo image types:

- Banner Image: `1920 x 1080 px`
- Event Image: `600 x 200 px`

Each scheduled promo can have:

- enabled/disabled state
- title
- fit mode: `contain` or `cover`
- image URL
- uploaded image
- start date/time
- stop date/time

The app validates scheduled promos so that two Banner Images cannot overlap each other, and two Event Images cannot overlap each other.

Expired promo slots are removed from active config when settings are loaded or saved.

## Full-Screen Override

Full-Screen Override images are `1920 x 1080 px`.

When active, a full-screen override hides the calendar and promo rail and shows only the override image.

Multiple full-screen overrides can be scheduled in advance. The app validates them so two overrides cannot overlap.

Full-screen overrides require both a start date/time and a stop date/time when enabled.

## Password

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

`server.local.json` is ignored by git and should stay only on the production PC.

You can also set the password using the `DISPLAY_CONFIG_PASSWORD` environment variable before starting the server.

## Windows Production Folder

The production Windows folder is:

```text
C:\TouchPointExtensionApps\UnifiDisplaySigns
```

The app files should be directly inside that folder:

```text
C:\TouchPointExtensionApps\UnifiDisplaySigns\server.py
C:\TouchPointExtensionApps\UnifiDisplaySigns\config.json
C:\TouchPointExtensionApps\UnifiDisplaySigns\settings.html
C:\TouchPointExtensionApps\UnifiDisplaySigns\activities-display.html
```

Avoid accidentally nesting the project like this:

```text
C:\TouchPointExtensionApps\UnifiDisplaySigns\UnifiDisplaySigns\server.py
```

## Windows Startup Batch File

The startup `.bat` file should use this pattern:

```bat
@echo off
cd /d C:\TouchPointExtensionApps\UnifiDisplaySigns
python server.py
```

If the PC uses the Python launcher instead:

```bat
@echo off
cd /d C:\TouchPointExtensionApps\UnifiDisplaySigns
py server.py
```

The `cd /d` line matters. It makes sure `server.py` reads `config.json`, `server.local.json`, and `assets/uploads/` from the correct folder.

## Manual Windows Test

From Command Prompt:

```bat
cd /d C:\TouchPointExtensionApps\UnifiDisplaySigns
dir config.json
python server.py
```

Leave that Command Prompt window open, then test in a browser:

```text
http://127.0.0.1:8080/api/config
```

Expected result: raw JSON appears in the browser.

Then test:

```text
http://127.0.0.1:8080/settings.html
http://127.0.0.1:8080/activities-display.html
```

## Common Troubleshooting

If `/api/config` does not load, check these first:

- The server is running.
- `config.json` is directly inside the app folder.
- The app was started from `C:\TouchPointExtensionApps\UnifiDisplaySigns`.
- The browser is using `http://127.0.0.1:8080/settings.html`, not a double-clicked file.
- Port `8080` is not already in use.

Check whether anything is listening on port `8080`:

```bat
netstat -aon | findstr LISTENING | findstr :8080
```

If nothing returns, the server is not running.

If Python reports `No module named 'tzdata'`, use the current `server.py`. It includes a fallback for Windows Python installs that do not include timezone data.

## Updating Production

When copying a new app version to the Windows PC:

1. Stop the running server.
2. Copy updated app files into `C:\TouchPointExtensionApps\UnifiDisplaySigns`.
3. Do not overwrite production-only `server.local.json` unless intentionally changing the password.
4. Do not delete `assets/uploads/` unless intentionally removing uploaded images.
5. Start the server.
6. Confirm `http://127.0.0.1:8080/api/config` loads JSON.
7. Confirm the display URL loads on the sign.

