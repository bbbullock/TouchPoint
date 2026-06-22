# TouchPoint to QuickBooks Online

This project stores TouchPoint Python scripts used to maintain QuickBooks Online account translations and export reconciled contribution batches into a QuickBooks Online journal import CSV.

## Current Tools

- Tool: `QuickBooksAccountTranslations`
  - Version: `1.6.1`
  - Last updated in script header: `2026-06-22`
  - Source file: `src/QuickBooksAccountTranslations.py`
- Tool: `QBOBatchExportTool`
  - Version: `2.3.2`
  - Last updated in script: `2026-06-22`
  - Source file: `src/QBOBatchExportTool.py`

## Purpose

`QuickBooksAccountTranslations.py` provides the TouchPoint web UI for maintaining the mapping records consumed by the export process:

- FundId translations
- Account code translations
- Bank batch type / bank account translations
- Merchant fee translations

`QBOBatchExportTool.py` provides the TouchPoint web UI for:

- Selecting eligible contribution batches
- Validating export eligibility server-side
- Building the final QuickBooks Online journal import CSV
- Tracking exported batches in TouchPoint Special Content JSON
- Managing setup values from a TouchPoint Setup tab

Normal exports are restricted to batches dated before the current month. The setup testing flag, `enable_clear_export_flag`, bypasses that month restriction for testing.

## TouchPoint Content Dependencies

The script expects these TouchPoint Special Content records:

- `TPxi_QBOBatchExportTool_Config`
- `TPxi_FinanceExport_Mappings`
- `TPxi_FinanceExport_Config`
- `TPxi_FinanceExport_AccountCodeMappings`
- `TPxi_FinanceExport_AccountCodeConfig`
- `TPxi_FinanceExport_BankMappings`
- `TPxi_FinanceExport_BankConfig`
- `TPxi_FinanceExport_BankBatchTypeOptions`
- `TPxi_FinanceExport_MerchantFeeMapping`
- `TPxi_FinanceExport_MerchantFeeConfig`
- `TPxi_QBOExport_ExportLog`

See `docs/configuration.md` for the storage schemas and export contract.

## Updating Workflow

1. Edit the relevant file in `src/`.
2. Keep the version header and `SCRIPT_VERSION` / `SCRIPT_LAST_UPDATED` values in sync.
3. Record meaningful behavior changes in the header comments.
4. Paste the updated script into the corresponding TouchPoint Python script.
5. For translation changes, verify the grids load and save in TouchPoint.
6. For export changes, test with a small reconciled batch before normal use.

Follow `docs/maintenance.md` for the complete backup, deployment, validation,
rollback, and Git safety procedure. JSON imports replace the stored mappings for
the active tab, so export a backup before importing.

## Notes

This script is designed for the TouchPoint Python scripting environment. It references TouchPoint globals such as `model`, `Data`, and `q`, so it is not expected to run directly as a normal local Python program.
