# QBOBatchExportTool Configuration Notes

## Special Content Contract

The tools distinguish two failure states:

- **Missing or blank** means the record does not exist or contains no
  non-whitespace text. The behavior in the table below applies.
- **Malformed** means invalid JSON, the wrong top-level JSON type, or a JSON
  value that fails the documented schema. Malformed content is never replaced
  automatically.

| Special Content record | Top-level type | Missing or blank behavior | Malformed behavior |
| --- | --- | --- | --- |
| `TPxi_QBOBatchExportTool_Config` | Object | Use safe in-memory defaults without writing | Display an error, force testing off, and block Setup saves |
| `TPxi_FinanceExport_Mappings` | Object | Translations tool creates `{}`; exporter blocks until present | Block the affected grid/actions and block export |
| `TPxi_FinanceExport_Config` | Object | Create the documented mapping-column default | Block the affected grid/actions |
| `TPxi_FinanceExport_AccountCodeMappings` | Object | Translations tool creates `{}`; exporter blocks until present | Block the affected grid/actions and block export |
| `TPxi_FinanceExport_AccountCodeConfig` | Object | Create the documented mapping-column default | Block the affected grid/actions |
| `TPxi_FinanceExport_BankMappings` | Object | Translations tool creates `{}`; exporter blocks until present | Block the affected grid/actions and block export |
| `TPxi_FinanceExport_BankConfig` | Object | Create `{"columns": []}` | Block the affected grid/actions |
| `TPxi_FinanceExport_BankBatchTypeOptions` | Array | Create the documented default option list | Block bank grids and bank-type/mapping actions |
| `TPxi_FinanceExport_MerchantFeeMapping` | Object | Create the documented `6050` default; exporter blocks until present | Block the affected grid/actions and block export |
| `TPxi_FinanceExport_MerchantFeeConfig` | Object | Create the documented mapping-column default | Block the affected grid/actions |
| `TPxi_QBOExport_ExportLog` | Object | Treat as `{}` and create it on the next successful export | Block export and Clear Export Flag operations |

In this documentation, **Object** means a JSON object (`{...}`), and **Array**
means a JSON array (`[...]`). Mapping objects must contain object values keyed
by row ID. Configuration and bank-option schema requirements are documented in
`docs/account-translations.md`.

Errors may identify the record and expected schema, but must never include the
stored JSON value. This prevents financial mappings, identifiers, and private
configuration from leaking into browser errors, logs, screenshots, or support
tickets.

## Tool Setup

Special Content name:

```json
TPxi_QBOBatchExportTool_Config
```

Example:

```json
{
  "enable_clear_export_flag": false,
  "last_paper_batch_id": 1993
}
```

If the record is missing or blank, the script uses and displays these same
defaults, so testing behavior remains disabled. Invalid JSON or a valid value
that is not a JSON object displays an error naming this Special Content record
without exposing its stored value. Testing remains disabled, and Setup cannot
overwrite the malformed record. `last_paper_batch_id` must be a whole number
greater than zero.

When `enable_clear_export_flag` is `true`, the tool allows testing behavior:

- The Clear Export Flag button is available.
- Batches from a month that is still open can be exported.

When `enable_clear_export_flag` is `false`, exports are limited to batches dated before the current month.

Keep this flag `false` during normal production use. Enabling it also exposes
the action that removes entries from the export log.

The code default is fail-closed: `enable_clear_export_flag` is `false`. A
missing configuration record cannot enable testing, and malformed configuration
forces testing off until an administrator repairs the record manually.

## Mapping Content

These mapping records are maintained by `src/QuickBooksAccountTranslations.py` and consumed by `src/QBOBatchExportTool.py`.

Each mapping record below must be a JSON object. Invalid JSON and valid JSON
with another top-level type raise a record-specific error without exposing the
stored value. The exporter treats missing or blank mapping content as an empty
object only for general reads; export prerequisite validation treats every
missing or blank mapping record as required content and blocks the export. The
translations tool initializes its documented defaults only for missing or
blank content.

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

Fund mappings take precedence over account-code mappings when both could apply.

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

Account-code mappings are used only when the row has no matching FundId mapping.

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

The top-level key must exactly match the TouchPoint batch-type description.

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

These options control the rows accepted by the translations tool. They do not
change TouchPoint's batch-type lookup table.

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

FundId `6050` is treated specially: normal income-row generation skips it and
the exporter creates a separate merchant-fee credit using this mapping.

## Export Construction Contract

The CSV columns and order are part of the QBO import contract and must not be
changed without an approved migration:

```text
JournalNo,JournalDate,AccountName,Debits,Credits,Description,Name,Currency,Location,Class
```

For each batch, the exporter creates:

1. One bank debit for base contributions plus donor-covered fees, using the
   batch-type bank mapping.
2. Income credits for each non-total, nonzero detail row. FundId mapping is
   tried first, then account-code mapping.
3. One merchant-fee credit when the batch contains donor-covered fees.

`JournalNo` is `TP-<batch ID>`. Monetary values use two decimal places and CSV
lines use CRLF endings. Export is blocked when the journal is out of balance or
any generated row has a blank `AccountName`.

## Batch Retrieval And Eligibility

The main grid retrieves at most 250 batches deposited within the previous 180
days. This is a display/query limit, not an archival policy.

The server revalidates selected IDs. A batch must:

- Be greater than `last_paper_batch_id`.
- Have status `Reconciled`.
- Have no export-log entry.
- Have a deposit date before the first day of the current month, unless the
  testing flag is enabled.

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

The export log must be a JSON object. Invalid JSON and other top-level types
block exports and Clear Export Flag operations rather than being treated as an
empty log. A missing or blank export log is treated as an empty object and may
be created by the next successful export. Before either setup or export-log
content is saved, the current record is read again; malformed content is never
overwritten by these save operations.

The script writes the export-log entry immediately before rendering the browser
download response. If the download does not complete, verify that no QBO import
occurred, temporarily enable the testing feature, clear the affected export
flag, disable the testing feature again, and retry. Never clear an export flag
without confirming whether the original file was imported into QBO.

## Related Translation Configuration

The translation tool also owns these configuration records:

- `TPxi_FinanceExport_Config`
- `TPxi_FinanceExport_AccountCodeConfig`
- `TPxi_FinanceExport_BankConfig`
- `TPxi_FinanceExport_MerchantFeeConfig`

Their schemas and recovery behavior are documented in
`docs/account-translations.md`.
