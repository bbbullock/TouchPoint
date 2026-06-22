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
SCRIPT_LAST_UPDATED: 2026-04-24
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

## Notes For Future Updates

- This script is designed for the TouchPoint Python scripting environment and references globals such as `model`, `Data`, and `q`.
- Keep the header version, `SCRIPT_VERSION`, and `SCRIPT_LAST_UPDATED` synchronized when changing behavior.
- The mapping content names overlap with `QBOBatchExportTool.py`; update both scripts together if the storage schema changes.
