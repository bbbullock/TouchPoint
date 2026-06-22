# Safe Maintenance And Deployment

Use this checklist for changes to either active script.

## Runtime And Access

- The active sources are `src/QBOBatchExportTool.py` and
  `src/QuickBooksAccountTranslations.py`.
- Both scripts target TouchPoint's Python environment and depend on `model`,
  `Data`, and `q`; they are not standalone local applications.
- The `#roles=Finance,Admin` directive restricts access to users with Finance or
  Admin roles.
- The executing user must be able to query the referenced contribution, batch,
  fund, account-code, lookup, and setting objects and write the documented
  Special Content records.
- Do not add external packages or newer Python syntax without confirming that
  the deployed TouchPoint runtime supports them.

## Before Editing

1. Confirm the requested behavior and identify the smallest affected file set.
2. Review `README.md`, `docs/configuration.md`, and
   `docs/account-translations.md`.
3. Export JSON backups for any mapping tabs whose storage may change.
4. Copy the affected TouchPoint Special Content JSON to secure operational
   storage when its schema or values may change. Do not commit the backup.
5. Record the deployed script version so it can be restored.

## Special Content Backup And Manual Repair

Use this procedure when either tool reports malformed Special Content.

1. Stop mapping edits and QBO exports until the affected record is repaired.
2. Record the sanitized error, script version, time, and Special Content name.
   Do not copy the stored JSON into tickets, email, chat, logs, or screenshots.
3. Open the affected record directly in TouchPoint Special Content. The tools
   intentionally block writes to malformed records and cannot repair them from
   their normal UI.
4. Before editing, copy the complete current value to approved, access-restricted
   operational storage. Do not place this backup in Git or the project folder.
5. Back up related valid records as well. Use **Export JSON** for translation
   tabs that still load; otherwise copy each record directly from TouchPoint.
6. Prefer restoring the most recent known-good backup. If no backup exists,
   repair only the minimum JSON syntax, top-level type, or schema defect using
   the contract in `docs/configuration.md` and redacted examples in the docs.
7. Save the repaired value under the same Special Content name. Never rename a
   record as part of recovery.
8. Reload the affected tool. Confirm the record-specific error is gone and all
   related grids load. For exporter configuration recovery, confirm
   `enable_clear_export_flag` is `false`.
9. Complete the relevant Translation or Export Validation checklist below.
10. Retain the pre-repair backup according to the organization's financial-data
    retention policy, then document who repaired the record and when without
    recording its contents.

Missing or blank records are different from malformed records. The tools may
initialize documented translation defaults, use safe exporter defaults, or
treat a missing export log as empty. Administrators must review any generated
defaults before production use.

Treat export-log repair as a financial-control operation. Never replace a
malformed export log with `{}` unless authorized staff reconcile the affected
batches against QBO import history; otherwise previously exported batches could
be exported again.

## Editing Contract

- Preserve TouchPoint compatibility and the existing `#roles` directive.
- Preserve CSV column names, order, CRLF formatting, mapping keys, journal-row
  behavior, and Special Content names unless a migration is explicitly approved.
- Keep the header version, header date, `SCRIPT_VERSION`, and
  `SCRIPT_LAST_UPDATED` synchronized.
- Record meaningful behavior changes in the script header.
- Use only redacted examples. Never add donor, contribution, batch-export, bank,
  credential, token, or private configuration data to Git.
- User-facing and logged errors may name a Special Content record and expected
  schema, but must never include its stored JSON value.

## Deployment

1. Paste the complete updated source into the corresponding TouchPoint Python
   script; do not deploy a file from `legacy/`.
2. Save the TouchPoint script and confirm it remains limited to Finance/Admin.
3. Open the tool as an authorized test user and complete the relevant checks
   below.
4. Retain the previous deployed source until validation is complete.

## Translation Validation

- Load all four tabs and confirm there are no account-code discovery warnings.
- Save and clear one redacted/test mapping, then restore its prior value.
- Test **Save All** with a controlled change.
- Export each affected tab to JSON and confirm its keys and shapes.
- If import behavior changed, import only a controlled backup and verify that
  replacement behavior is intentional.
- Confirm the exporter can resolve a FundId mapping, an account-code fallback,
  a batch-type bank mapping, and merchant-fee FundId `6050`.

## Export Validation

- Use a small reconciled prior-month batch that has not been imported into QBO.
- Confirm paper, non-reconciled, already-exported, and open-month batches remain
  blocked under normal production settings.
- Confirm all generated `AccountName` values are populated.
- Confirm total debits equal total credits and the CSV header/order matches
  `docs/configuration.md`.
- Inspect the file using redacted/test data before importing it into QBO.
- Confirm the export log records the selected batch and user.
- Return `enable_clear_export_flag` to `false` after any controlled testing.

## Rollback

1. Restore the previous TouchPoint script source.
2. Restore mapping/configuration JSON only from the matching pre-change backup.
3. Do not remove export-log entries until operational staff confirm whether the
   corresponding CSV was imported into QBO.
4. Repeat the relevant validation checklist after rollback.

## Legacy Provenance

- `legacy/QBOBatchExportTool_root_legacy.py` is the archived root-level exporter
  at version 2.2.0. It predates the prior-month restriction in active version
  2.3.0, the fail-closed testing default in version 2.3.1, and strict JSON
  reading in version 2.3.2. Active version 2.3.3 adds guarded exporter
  prerequisites and prevents malformed setup or export-log records from being
  overwritten.
- `legacy/Quickbooks_Account_Translations_root_legacy.py` is an archived
  root-level copy of version 1.6.0. Active version 1.6.1 adds strict JSON
  reading, and active version 1.6.2 adds guarded translation actions and schema
  validation.
- Legacy files are reference snapshots. Never patch or deploy them as the active
  production source.

## Git Safety

The Git root is one directory above this project (`/Users/brianbullock/TouchPoint`).
Review staged paths carefully so sibling projects are not included. The QBO
`.gitignore` excludes exports, spreadsheets, local/private configuration, logs,
temporary files, bytecode, virtual environments, and macOS metadata.
