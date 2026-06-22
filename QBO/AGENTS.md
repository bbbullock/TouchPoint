# Codex Instructions

This repository contains TouchPoint Python scripts used to export and translate financial data for QuickBooks Online.

## Project structure

- `src/` contains the active TouchPoint Python scripts.
- `legacy/` contains older or retired versions kept for reference.
- `docs/` contains configuration and account translation documentation.

## Runtime constraints

- These scripts are intended for TouchPoint.
- Preserve TouchPoint compatibility.
- Avoid unnecessary modern Python syntax unless already confirmed to work in TouchPoint.
- Do not introduce external dependencies without approval.
- Preserve existing behavior unless explicitly asked to change it.

## Financial data safety

- Do not commit real donor data, contribution data, batch exports, bank data, QuickBooks credentials, TouchPoint credentials, API keys, passwords, or private configuration.
- Use only redacted examples in documentation or tests.

## Editing rules

- Make small, reviewable changes.
- Do not broadly refactor without approval.
- Preserve export column names, order, formatting, and mapping behavior unless explicitly asked to change them.
- Before editing code, summarize the files involved, expected behavior change, and validation plan.

## Active scripts

- `src/QBOBatchExportTool.py`
- `src/QuickBooksAccountTranslations.py`

## Documentation

Before making code changes, review:

- `readme.md`
- `docs/account-translations.md`
- `docs/configuration.md`
- `docs/maintenance.md`
