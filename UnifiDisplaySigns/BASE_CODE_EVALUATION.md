# Landscape Activities Display - Base Code Evaluation

## Scope

This evaluates the pasted landscape version of the Activities Today display. The code is a single embedded HTML/CSS/JavaScript artifact that loads TouchPoint ICS feeds, parses events in the browser, filters to today's activities, and renders a landscape signage layout with optional promotion art.

## Overall Assessment

The base code is a workable prototype for a landscape signage display. It has the right broad shape: feed configuration is centralized, the display auto-refreshes, multiple feeds can load progressively, empty/error states exist, and the layout is designed for a 16:9 embedded display.

Before using this as the production baseline, I would harden the calendar parsing and visual behavior. The biggest risks are date/time correctness, incomplete recurrence handling, fragile single-file maintainability, and a few unused or inconsistent configuration paths.

## What Works Well

- The `CONFIG`, `PROMOTION_SETTINGS`, and `ICS_FEEDS` blocks make common operator changes easy to find.
- Feed loading uses cache busting, per-feed timeouts, and `Promise.allSettled`, so one failed calendar feed does not stop the whole display.
- Progressive rendering gives the screen useful content before every feed has finished loading.
- Event titles, locations, and error messages are escaped before rendering, which lowers the risk of malformed feed text breaking the page.
- The display has explicit empty and error states instead of leaving the screen blank.
- Page rotation is built in for days with more events than fit on one screen.
- The promotion zones are configurable and can be turned off without removing layout code.

## Key Risks

### 1. Timezone Handling Is Fragile

The UI formats dates and times with `CONFIG.timezone`, but `parseICSDate()` creates non-UTC ICS timestamps with `new Date(year, month, day, hour, minute, second)`. That uses the browser or signage device's local timezone, not necessarily `America/Chicago`.

If the TV device, browser profile, or hosting environment is not set to Central Time, events may show on the wrong day or at the wrong time. This is the highest-priority production risk.

Recommended fix: parse ICS `TZID` parameters explicitly or use a real ICS/date library. At minimum, document that the signage device timezone must be America/Chicago and add a visible/testable diagnostic for timezone drift.

### 2. Recurrence Support Is Narrow

The recurrence expansion only supports weekly `RRULE` values with `BYDAY`. It does not fully support common ICS recurrence fields such as:

- `COUNT`
- `INTERVAL`
- monthly or yearly recurrence
- multiple `EXDATE` parameter forms
- recurrence exceptions with changed times
- timezone-bearing `RECURRENCE-ID` and `EXDATE` values

This may be fine if the TouchPoint feeds only emit simple weekly patterns, but it should not be treated as a general ICS parser.

Recommended fix: either verify the actual TouchPoint feed shapes and document the supported subset, or replace the custom recurrence logic with a tested ICS recurrence parser.

### 3. Feed Colors Are Defined But Not Used

`FEED_COLORS` defines per-feed colors, but rendering currently hardcodes every event card to green:

```js
const color = { bg: "#628D33", text: "#ffffff" };
```

That makes the color config misleading and removes an expected visual cue. If feed names are hidden, color may be the only way to distinguish categories.

Recommended fix: use `FEED_COLORS[event.feedKey] || defaultColor` during rendering, or remove the unused configuration.

### 4. The Single-File Structure Will Get Hard To Maintain

The file currently mixes:

- display markup
- visual design tokens
- promotion settings
- feed configuration
- ICS parsing
- recurrence handling
- rendering
- refresh behavior

That is acceptable for a quick embed, but it will slow down future changes and make testing difficult.

Recommended fix: keep a single deployable bundle if needed, but maintain source modules for `config`, `icsParser`, `recurrence`, `renderEvents`, and `promotions`.

### 5. The HTML Wrapper Looks Incomplete

The pasted code starts with a standalone `<meta>` tag and does not show a normal `<!doctype html>`, `<html>`, `<head>`, or `<body>` wrapper. That may be intentional if this is pasted into an existing website embed area, but it is not a complete standalone HTML document as written.

Recommended fix: decide whether this artifact is an embed snippet or a full page. If it is a full page, wrap it properly. If it is an embed snippet, document the required host page assumptions.

### 6. Layout May Clip On Some Screens

The body uses `overflow: hidden`, the `.page` default height is `72vh`, and event containers also hide overflow. This is useful for signage, but it can conceal failures when event text, browser zoom, or promo art changes.

Recommended fix: verify with screenshots at the actual TV resolution, kiosk browser zoom, and any website container where this will be embedded. Add a maximum event count/layout rule for side-promo mode.

### 7. URL Filtering Contains A Suspicious Character

The `isUrlLike()` regex appears to contain a non-printing control character before the domain pattern:

```js
/(?:https?:\/\/|www\.|[a-z0-9-]+\.[a-z]{2,}(?:\/|$))/i
```

That may be a paste artifact, but it should be cleaned up because it makes the expression hard to reason about and may prevent plain domain filtering from working as intended.

Recommended fix: replace it with an explicit, readable regex and add quick test cases for location cleanup.

## Production Readiness Checklist

- Confirm the deployment context: standalone HTML page or embedded snippet.
- Confirm the signage device timezone and browser zoom level.
- Test the live TouchPoint ICS feeds on a day with multiple events.
- Test an empty day.
- Test a cancelled event.
- Test a recurring weekly event.
- Test a recurring event with an exception or skipped date.
- Test a day with more than 10 events and page rotation enabled.
- Test with side promotion enabled and disabled.
- Test with bottom banner enabled and disabled.
- Test with slow or unavailable feeds.
- Verify there are no console errors in the target browser.

## Suggested Fix Order

1. Fix timezone parsing or lock down/document the device timezone dependency.
2. Clean the `isUrlLike()` regex and add small parser/cleanup tests.
3. Decide whether this is a standalone page or embed snippet and structure it accordingly.
4. Use or remove `FEED_COLORS`.
5. Add test fixtures for real TouchPoint ICS examples, including recurrence and cancellation.
6. Split the source into maintainable modules while preserving the final deployable format.
7. Run visual QA at the exact production display resolution.

## Recommended Baseline Decision

Use this as the visual and behavioral prototype, not yet as the hardened production baseline. The UI direction is solid, but the calendar logic needs verification against real TouchPoint feed samples before it should be trusted unattended on a lobby display.
