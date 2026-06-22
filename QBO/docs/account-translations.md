# QuickBooks Account Translations Notes

Source file:

```text
src/QuickBooksAccountTranslations.py
```

TouchPoint script metadata from the pasted source:

```text
Tool: QuickBooks Account Translations
Version: 1.6.2
Header last updated: 2026-06-22
SCRIPT_LAST_UPDATED: 2026-06-22
```

## Purpose

This TouchPoint Python script maintains the mapping data used by the QuickBooks Online batch export process.

It includes tabs for:

- FundId translations
- Account code translations
- Bank batch type / bank account translations
- Merchant fee translations

## TouchPoint Content Dependencies

The script reads and writes these TouchPoint Special Content records:

```text
TPxi_FinanceExport_Mappings
TPxi_FinanceExport_Config
TPxi_FinanceExport_AccountCodeMappings
TPxi_FinanceExport_AccountCodeConfig
TPxi_FinanceExport_BankMappings
TPxi_FinanceExport_BankConfig
TPxi_FinanceExport_BankBatchTypeOptions
TPxi_FinanceExport_MerchantFeeMapping
TPxi_FinanceExport_MerchantFeeConfig
```

## Configuration Records

Fund, account-code, and merchant-fee configuration records use this shape:

```json
{
  "columns": [
    {"key": "account", "label": "Account"},
    {"key": "acct_class", "label": "Class"}
  ]
}
```

For fund, account-code, and merchant-fee configuration, the script writes this
default only when the record is missing or blank.
`TPxi_FinanceExport_BankConfig` uses `{"columns": []}` because the bank grid
stores only `bank_name`; the script writes that default when the record is
missing or blank.

Invalid JSON and valid JSON with the wrong top-level type raise an error naming
the affected Special Content record. The script does not include the stored
value in the error and does not replace malformed content with defaults.

Existing configuration objects must contain a `columns` array. Non-bank
configuration requires at least one column, and every column requires unique,
nonblank `key` and `label` text. Mapping records must be JSON objects whose row
values are also JSON objects. Bank batch-type options must be an array of
nonblank text values. Schema failures are treated as malformed content.

Grid requests return `success: false` with the affected Special Content name
when associated storage is malformed. Save, Save All, delete, import, and bank
batch-type actions run the same storage preflight before mutation. Save helpers
also re-read current storage immediately before writing, preventing malformed
content from being overwritten if it changes between grid load and save.

The default bank batch types are `Online`, `Loose Cash`, `Loose Checks`, and
`Stock`. The default merchant-fee mapping is FundId `6050` to account
`Bank Service Charges` and class `General Fund:Administration`. Confirm those
values are appropriate for the TouchPoint database before relying on defaults.

## Import, Export, And Recovery

- **Export JSON** downloads a backup of the active tab's mappings.
- **Import JSON** replaces all saved mappings for the active tab; it does not
  merge with existing mappings.
- Import requires a JSON object with row IDs as keys and JSON objects as values.
- The browser displays a replace-all confirmation before submitting an import,
  and successful responses explicitly report that saved mappings were replaced.
- Before importing, export the current tab and retain the file outside Git.
- To roll back an import, import the saved JSON backup for that same tab.
- Bank imports accept only entries whose keys are in the saved bank batch-type
  options. Merchant-fee imports retain only the `6050` entry.
- Deleting a bank batch type also removes its saved bank mapping.

## Notes For Future Updates

- This script is designed for the TouchPoint Python scripting environment and references globals such as `model`, `Data`, and `q`.
- Keep the header version, `SCRIPT_VERSION`, and `SCRIPT_LAST_UPDATED` synchronized when changing behavior.
- The mapping content names overlap with `QBOBatchExportTool.py`; update both scripts together if the storage schema changes.
- Preserve the mapping keys `account`, `acct_class`, and `bank_name`; the exporter consumes those exact names.
- Follow `docs/maintenance.md` before deploying or changing stored mappings.
