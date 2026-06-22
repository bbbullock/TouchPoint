# QBOBatchExportTool Configuration Notes

## Tool Setup

Special Content name:

```json
TPxi_QBOBatchExportTool_Config
```

Example:

```json
{
  "enable_clear_export_flag": true,
  "last_paper_batch_id": 1993
}
```

When `enable_clear_export_flag` is `true`, the tool allows testing behavior:

- The Clear Export Flag button is available.
- Batches from a month that is still open can be exported.

When `enable_clear_export_flag` is `false`, exports are limited to batches dated before the current month.

## Mapping Content

These mapping records are maintained by `src/QuickBooksAccountTranslations.py` and consumed by `src/QBOBatchExportTool.py`.

### Fund mappings

Special Content name:

```json
TPxi_FinanceExport_Mappings
```

Expected shape:

```json
{
  "1000": {
    "account": "Contribution Income",
    "acct_class": "General"
  }
}
```

### Account code mappings

Special Content name:

```json
TPxi_FinanceExport_AccountCodeMappings
```

Expected shape:

```json
{
  "4000": {
    "account": "Contribution Income",
    "acct_class": "General"
  }
}
```

### Bank mappings

Special Content name:

```json
TPxi_FinanceExport_BankMappings
```

Expected shape:

```json
{
  "Online Giving": {
    "bank_name": "Checking"
  }
}
```

### Bank batch type options

Special Content name:

```json
TPxi_FinanceExport_BankBatchTypeOptions
```

Expected shape:

```json
[
  "Online",
  "Loose Cash",
  "Loose Checks",
  "Stock"
]
```

### Merchant fee mapping

Special Content name:

```json
TPxi_FinanceExport_MerchantFeeMapping
```

Expected shape:

```json
{
  "6050": {
    "account": "Merchant Fees",
    "acct_class": "General"
  }
}
```

## Export Log

Special Content name:

```json
TPxi_QBOExport_ExportLog
```

Expected shape:

```json
{
  "2001": {
    "exported_on": "2026-06-02 14:30:00",
    "exported_by": "123"
  }
}
```
