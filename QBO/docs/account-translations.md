# QuickBooks Account Translations Notes

Source file:

```text
src/QuickBooksAccountTranslations.py
```

TouchPoint script metadata from the pasted source:

```text
Tool: QuickBooks Account Translations
Version: 1.6.0
Header last updated: 2026-05-04
SCRIPT_LAST_UPDATED: 2026-05-04
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
default when the record is absent, invalid JSON, or lacks usable columns.
`TPxi_FinanceExport_BankConfig` uses `{"columns": []}` because the bank grid
stores only `bank_name`; the script writes that default when the record is
absent or invalid JSON.

The default bank batch types are `Online`, `Loose Cash`, `Loose Checks`, and
`Stock`. The default merchant-fee mapping is FundId `6050` to account
`Bank Service Charges` and class `General Fund:Administration`. Confirm those
values are appropriate for the TouchPoint database before relying on defaults.

## Import, Export, And Recovery

- **Export JSON** downloads a backup of the active tab's mappings.
- **Import JSON** replaces all saved mappings for the active tab; it does not
  merge with existing mappings.
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
