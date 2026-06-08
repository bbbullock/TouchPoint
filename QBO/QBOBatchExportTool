#roles=Finance,Admin

# =============================================================================
# QBOBatchExportTool
# Version: 2.2.0
# Last Updated: 2026-06-02
#
# Purpose:
#   Provides the TouchPoint web UI for selecting eligible contribution batches
#   and generating the final QuickBooks Online journal import CSV directly.
#
# Major v2.0 Change:
#   Combined the batch-selection functionality formerly handled by
#   QBOBatchExportTool with the QBO CSV generation logic formerly handled by
#   QBOEnrichedExport.
#
# Major v2.1 Change:
#   Adds a Setup tab backed by Special Content JSON configuration.
#
#   Setup controls:
#       - Enable / disable the Clear Export Flag testing feature
#       - Set the Last Paper Batch ID
#
# Major v2.1.1 Change:
#   - When Clear Export Flag is disabled, already-exported batches are no longer
#     selectable.
#   - Ready-to-export batches are highlighted light green.
#   - Open/non-Reconciled batches are highlighted light red.
#
# Major v2.2.0 Change:
#   - Removes dependency on standalone Special Content SQL script:
#         TESTMultiBatchReportSQL
#   - Batch detail SQL is now embedded directly in this Python script.
#
# Configuration Storage:
#   Tool setup is stored in:
#       TPxi_QBOBatchExportTool_Config
#
#   Example:
#       {
#         "enable_clear_export_flag": true,
#         "last_paper_batch_id": 1993
#       }
#
# Mapping Sources:
#   - TPxi_FinanceExport_Mappings
#       FundId-based Account / Class mappings
#
#   - TPxi_FinanceExport_AccountCodeMappings
#       AccountCode-based Account / Class mappings
#
#   - TPxi_FinanceExport_BankMappings
#       BatchType -> Bank Name mappings
#
#   - TPxi_FinanceExport_MerchantFeeMapping
#       Merchant Fees FundID 6050 Account / Class mapping
#
# Export Tracking:
#   Export history is stored in:
#       TPxi_QBOExport_ExportLog
#
# Export Eligibility:
#   A batch can be exported only when:
#       - BundleHeaderId > Last Paper Batch ID
#       - Status = Reconciled
#       - Export Status = No
#
# Server-Side Validation:
#   Export action re-validates selected batches server-side before generating
#   the CSV. The UI is not trusted as the only enforcement layer.
#
#   Export is blocked if:
#       - No batch IDs are received
#       - Any selected batch is historical/paper
#       - Any selected batch is not found
#       - Any selected batch is not Reconciled
#       - Any selected batch is already exported
#       - Generated CSV would be out of balance
#       - Generated CSV has rows with blank AccountName
#
# Notes:
#   - This script replaces the former two-script flow:
#         QBOBatchExportTool -> QBOEnrichedExport
#   - This script no longer requires TESTMultiBatchReportSQL.
# =============================================================================

import re
import json
import datetime

model.Title = 'QBO Batch Export Tool'

SCRIPT_VERSION = "2.2.0"
SCRIPT_LAST_UPDATED = "2026-06-02"

CONFIG_CONTENT_NAME = "TPxi_QBOBatchExportTool_Config"

FUND_MAPPING_CONTENT_NAME = "TPxi_FinanceExport_Mappings"
ACCOUNT_MAPPING_CONTENT_NAME = "TPxi_FinanceExport_AccountCodeMappings"
BANK_MAPPING_CONTENT_NAME = "TPxi_FinanceExport_BankMappings"
MERCHANT_FEE_MAPPING_CONTENT_NAME = "TPxi_FinanceExport_MerchantFeeMapping"
EXPORT_LOG_CONTENT_NAME = "TPxi_QBOExport_ExportLog"

MERCHANT_FEE_FUND_ID = "6050"
REQUIRED_EXPORT_STATUS = "Reconciled"

DEFAULT_CONFIG = {
    "enable_clear_export_flag": True,
    "last_paper_batch_id": 1993
}


# =============================================================================
# Basic Helpers
# =============================================================================

def h(s):
    if s is None:
        return ""
    s = str(s)
    s = s.replace("&", "&amp;")
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    s = s.replace('"', "&quot;")
    return s

def js_escape(s):
    if s is None:
        return ""
    s = str(s)
    s = s.replace("\\", "\\\\")
    s = s.replace("'", "\\'")
    s = s.replace("\r", "\\r")
    s = s.replace("\n", "\\n")
    return s

def csv_escape(v):
    if v is None:
        v = ""
    v = str(v)
    if '"' in v:
        v = v.replace('"', '""')
    if ',' in v or '"' in v or '\r' in v or '\n' in v:
        v = '"' + v + '"'
    return v

def fmt_money(v):
    try:
        return "{0:,.2f}".format(float(v))
    except:
        return "0.00"

def fmt2(v):
    try:
        return "{0:.2f}".format(float(v))
    except:
        return "0.00"

def to_int(v, default_value=0):
    try:
        return int(str(v).strip())
    except:
        return default_value

def to_float(v, default_value=0.0):
    try:
        return float(v)
    except:
        return default_value

def Disinfect(s):
    if s is None:
        return ""
    idlist = str(s).split(',')
    idstr = ''
    for id in idlist:
        idInt = re.sub('[^\d]', '', id)
        if idInt:
            idstr = idstr + ',' + idInt
    return idstr[1:] if idstr else ""

def parse_batch_ids(cleanlist):
    ids = []
    for x in str(cleanlist or "").split(","):
        x = str(x).strip()
        if x:
            ids.append(x)
    return ids

def row_value(row, names, default=""):
    for name in names:
        try:
            v = getattr(row, name)
            if v is not None:
                return v
        except:
            pass
        try:
            if name in row:
                v = row[name]
                if v is not None:
                    return v
        except:
            pass
    return default

def row_str(row, names, default=""):
    v = row_value(row, names, default)
    if v is None:
        return ""
    return str(v).strip()

def row_num(row, names, default=0):
    v = row_value(row, names, default)
    try:
        return float(v)
    except:
        return 0.0


# =============================================================================
# JSON Content Helpers
# =============================================================================

def load_json_content(name):
    try:
        txt = model.TextContent(name)
        if txt:
            obj = json.loads(txt)
            if isinstance(obj, dict):
                return obj
    except:
        pass
    return {}

def save_json_content(name, obj):
    model.WriteContentText(name, json.dumps(obj, indent=2), "")

def load_export_log():
    return load_json_content(EXPORT_LOG_CONTENT_NAME)

def save_export_log(log_obj):
    save_json_content(EXPORT_LOG_CONTENT_NAME, log_obj)


# =============================================================================
# Setup / Config Helpers
# =============================================================================

def load_tool_config():
    cfg = load_json_content(CONFIG_CONTENT_NAME)
    if not isinstance(cfg, dict):
        cfg = {}

    enable_clear = cfg.get(
        "enable_clear_export_flag",
        DEFAULT_CONFIG["enable_clear_export_flag"]
    )

    if str(enable_clear).strip().lower() in ["false", "0", "no", "off"]:
        enable_clear = False
    else:
        enable_clear = bool(enable_clear)

    last_paper = to_int(
        cfg.get("last_paper_batch_id", DEFAULT_CONFIG["last_paper_batch_id"]),
        DEFAULT_CONFIG["last_paper_batch_id"]
    )

    if last_paper < 1:
        last_paper = DEFAULT_CONFIG["last_paper_batch_id"]

    return {
        "enable_clear_export_flag": enable_clear,
        "last_paper_batch_id": last_paper
    }

def save_tool_config(enable_clear_export_flag, last_paper_batch_id):
    last_paper = to_int(last_paper_batch_id, 0)

    if last_paper < 1:
        raise Exception("Last Paper Batch ID must be a whole number greater than zero.")

    cfg = {
        "enable_clear_export_flag": bool(enable_clear_export_flag),
        "last_paper_batch_id": last_paper
    }

    save_json_content(CONFIG_CONTENT_NAME, cfg)
    return cfg

TOOL_CONFIG = load_tool_config()
ENABLE_CLEAR_EXPORT_FLAG = TOOL_CONFIG["enable_clear_export_flag"]
LAST_PAPER_BATCH_ID = TOOL_CONFIG["last_paper_batch_id"]
MIN_EXPORTABLE_BATCH_ID = LAST_PAPER_BATCH_ID + 1

def is_paper_batch_id(batch_id):
    return to_int(batch_id, 0) <= LAST_PAPER_BATCH_ID


# =============================================================================
# General Data Helpers
# =============================================================================

def get_church_name():
    sql = '''
        SELECT Setting
        FROM dbo.Setting
        WHERE Id = 'NameOfChurch'
    '''
    try:
        return str(q.QuerySqlScalar(sql))
    except:
        return ""

def get_recent_batches():
    sql = '''
    ;WITH gifts AS (
        SELECT 
            bh.BundleHeaderId,
            c.ContributionAmount
        FROM dbo.BundleHeader bh
        JOIN dbo.BundleDetail bd ON bd.BundleHeaderId = bh.BundleHeaderId
        JOIN dbo.Contribution c ON c.ContributionId = bd.ContributionId
        WHERE bh.DepositDate >= DATEADD(day, -180, GETDATE())
          AND c.ContributionStatusId = 0
          AND c.ContributionTypeId NOT IN (6,7,8)
    )
    SELECT TOP 250
        bh.BundleHeaderId,
        CONVERT(VARCHAR(10), bh.DepositDate, 101) AS DepositDate,
        CONVERT(nvarchar(100), bh.ReferenceId) AS RefId,
        bt.Description AS BatchType,
        ISNULL(cs.Description, '') AS Source,
        (SELECT COUNT(*)
           FROM gifts g
          WHERE g.BundleHeaderId = bh.BundleHeaderId) AS Items,
        (SELECT ISNULL(SUM(g.ContributionAmount), 0)
           FROM gifts g
          WHERE g.BundleHeaderId = bh.BundleHeaderId) AS Amount,
        ISNULL(bst.Description, '') AS Status
    FROM dbo.BundleHeader bh
    JOIN lookup.BundleHeaderTypes bt
        ON bt.Id = bh.BundleHeaderTypeId
    LEFT JOIN lookup.ContributionSources cs
        ON cs.Id = bh.SourceId
    LEFT JOIN lookup.BundleStatusTypes bst
        ON bst.Id = bh.BundleStatusId
    WHERE bh.DepositDate >= DATEADD(day, -180, GETDATE())
    ORDER BY bh.DepositDate DESC, bh.BundleHeaderId DESC
    '''
    try:
        return list(q.QuerySql(sql))
    except:
        return []


# =============================================================================
# Export Data Helpers
# =============================================================================

def get_batch_summary(cleanlist):
    sql = '''
    SELECT
        bh.BundleHeaderId,
        CONVERT(VARCHAR(10), bh.DepositDate, 101) AS DepositDate,
        bt.Description AS BatchType,
        ISNULL(bst.Description, '') AS Status
    FROM dbo.BundleHeader bh
    JOIN lookup.BundleHeaderTypes bt
        ON bt.Id = bh.BundleHeaderTypeId
    LEFT JOIN lookup.BundleStatusTypes bst
        ON bst.Id = bh.BundleStatusId
    WHERE bh.BundleHeaderId IN (SELECT Value FROM dbo.SplitInts('{0}'))
    ORDER BY bh.DepositDate, bh.BundleHeaderId
    '''.format(cleanlist)

    try:
        return list(q.QuerySql(sql))
    except:
        return []

def get_batch_detail(cleanlist):
    sqlgifts = '''
    DECLARE @Results1 TABLE (
        BundleHeaderId int,
        DepositDate   date,
        FundName      nvarchar(256),
        GeneralLedger nvarchar(100),
        Amount        numeric(11,2),
        Base          numeric(11,2),
        Fees          numeric(11,2)
    );

    INSERT INTO @Results1 (
        BundleHeaderId,
        DepositDate,
        FundName,
        GeneralLedger,
        Amount,
        Base,
        Fees
    )
    SELECT
        h.BundleHeaderId,
        CONVERT(date, h.DepositDate) AS DepositDate,
        CASE 
            WHEN cb.ContributionTypeId = 99 
                THEN ISNULL(accnt.Description, '') 
            ELSE cf.FundName + ' (' + CONVERT(nvarchar(12), cb.FundId) + ')' 
        END AS FundName,
        CASE 
            WHEN cb.ContributionTypeId = 99 
                THEN ISNULL(accnt.Code, '') 
            ELSE cf.FundIncomeAccount 
        END AS GeneralLedger,
        cb.ContributionAmount AS Amount,
        CASE 
            WHEN cb.DonorCoveredFee = 0 
                THEN cb.ContributionAmount
            ELSE cb.ContributionAmount - ISNULL(cb.ChargedFee, 0) 
        END AS Base,
        CASE 
            WHEN cb.DonorCoveredFee = 0 
                THEN 0
            ELSE ISNULL(cb.ChargedFee, 0) 
        END AS Fees
    FROM dbo.Contribution AS cb
    LEFT JOIN dbo.People AS p
        ON p.PeopleId = cb.PeopleId
    LEFT JOIN lookup.AccountCode AS accnt
        ON accnt.Id = cb.AccountCodeId
    JOIN dbo.BundleDetail AS d
        ON d.ContributionId = cb.ContributionId
    JOIN dbo.BundleHeader AS h
        ON h.BundleHeaderId = d.BundleHeaderId
    RIGHT JOIN lookup.BundleHeaderTypes bt
        ON bt.Id = h.BundleHeaderTypeId
    INNER JOIN dbo.ContributionFund AS cf
        ON cf.FundId = cb.FundId
    WHERE d.BundleHeaderId IN (SELECT Value FROM dbo.SplitInts(@batchids))
      AND ISNULL(cb.PledgeFlag, 0) = 0
      AND cb.ContributionStatusId = 0
      AND cb.ContributionTypeId NOT IN (6,7,8);

    SELECT
        DepositDate AS GiftDate,
        DepositDate,
        CASE 
            WHEN BundleHeaderId IS NULL THEN 'Total'
            WHEN FundName IS NULL THEN ''
            ELSE FundName
        END AS Fund,
        GeneralLedger,
        COUNT(*) AS [Count],
        SUM(Amount) AS Amount,
        SUM(Base) AS Base,
        SUM(Fees) AS Fees,
        BundleHeaderId AS BatchId
    FROM @Results1
    GROUP BY GROUPING SETS
    (
        (BundleHeaderId, DepositDate, FundName, GeneralLedger),
        (BundleHeaderId, DepositDate),
        ()
    )
    ORDER BY
        BatchId,
        DepositDate,
        Fund;
    '''
    params = { 'batchids': cleanlist }
    return list(q.QuerySql(sqlgifts, params))

def derive_fund_id_and_name(fund_text):
    fund_text = str(fund_text or "").strip()
    if not fund_text:
        return "", ""

    m = re.search(r'\((\d+)\)\s*$', fund_text)
    if m:
        fund_id = m.group(1)
        fund_name = re.sub(r'\s*\(\d+\)\s*$', '', fund_text).strip()
        return fund_id, fund_name

    return "", fund_text

def is_total_row(fund_text):
    fund_text = str(fund_text or "").strip().lower()
    return fund_text == "" or fund_text == "total"

def load_merchant_fee_mapping():
    mappings = load_json_content(MERCHANT_FEE_MAPPING_CONTENT_NAME)
    entry = mappings.get(MERCHANT_FEE_FUND_ID, {})

    account_name = ""
    acct_class = ""

    if isinstance(entry, dict):
        account_name = str(entry.get("account", "")).strip()
        acct_class = str(entry.get("acct_class", "")).strip()

    return account_name, acct_class

def resolve_income_mapping(derived_fund_id, general_ledger, fund_mappings, acct_mappings):
    derived_fund_id = str(derived_fund_id or "").strip()
    general_ledger = str(general_ledger or "").strip()

    account_name = ""
    acct_class = ""

    if derived_fund_id and derived_fund_id in fund_mappings:
        entry = fund_mappings.get(derived_fund_id, {})
        if isinstance(entry, dict):
            account_name = str(entry.get("account", "")).strip()
            acct_class = str(entry.get("acct_class", "")).strip()
            return account_name, acct_class

    if general_ledger and general_ledger in acct_mappings:
        entry = acct_mappings.get(general_ledger, {})
        if isinstance(entry, dict):
            account_name = str(entry.get("account", "")).strip()
            acct_class = str(entry.get("acct_class", "")).strip()
            return account_name, acct_class

    return "", ""

def build_description(journal_no, fund_name):
    fund_name = str(fund_name or "").strip()
    if fund_name:
        return journal_no + ":" + fund_name
    return journal_no


# =============================================================================
# Export Eligibility / Validation
# =============================================================================

def get_exported_batch_ids(cleanlist):
    batch_ids = parse_batch_ids(cleanlist)
    log_obj = load_export_log()
    already_exported = []

    for bid in batch_ids:
        info = log_obj.get(bid, {})
        if isinstance(info, dict) and str(info.get("exported_on", "")).strip():
            already_exported.append(bid)

    return already_exported

def validate_selected_batches(cleanlist):
    errors = []
    batch_ids = parse_batch_ids(cleanlist)

    if not batch_ids:
        errors.append("No batch IDs were received.")
        return errors

    paper_ids = []
    for bid in batch_ids:
        if is_paper_batch_id(bid):
            paper_ids.append(bid)

    if paper_ids:
        errors.append("These selected batches are historical/paper batches and cannot be exported: " + ", ".join(paper_ids))

    already_exported = get_exported_batch_ids(cleanlist)
    if already_exported:
        errors.append("These selected batches are already flagged as exported: " + ", ".join(already_exported))

    summary_rows = get_batch_summary(cleanlist)

    found = {}
    not_reconciled = []

    for r in summary_rows:
        bid = row_str(r, ["BundleHeaderId"])
        status = row_str(r, ["Status"])
        found[bid] = True

        if status.strip().lower() != REQUIRED_EXPORT_STATUS.lower():
            not_reconciled.append("{0} ({1})".format(bid, status if status else "blank status"))

    missing = []
    for bid in batch_ids:
        if bid not in found:
            missing.append(bid)

    if missing:
        errors.append("These selected batches were not found: " + ", ".join(missing))

    if not_reconciled:
        errors.append("These selected batches are not Reconciled: " + ", ".join(not_reconciled))

    return errors

def validate_journal_rows(journal_rows):
    errors = []

    if not journal_rows:
        errors.append("No journal rows were generated.")
        return errors

    total_debits = 0.0
    total_credits = 0.0
    blank_account_rows = []

    rownum = 1
    for row in journal_rows:
        debit = to_float(row.get("Debits", ""), 0.0)
        credit = to_float(row.get("Credits", ""), 0.0)

        total_debits += debit
        total_credits += credit

        account_name = str(row.get("AccountName", "")).strip()
        if not account_name:
            row_detail = "JournalNo={0} Date={1} Debits={2} Credits={3} Class={4} Desc={5}".format(
                row.get("JournalNo", ""),
                row.get("JournalDate", ""),
                row.get("Debits", ""),
                row.get("Credits", ""),
                row.get("Class", ""),
                row.get("Description", "")
            )
            blank_account_rows.append("Row {0}: {1}".format(rownum, row_detail))

        rownum += 1

    diff = round(total_debits - total_credits, 2)

    if abs(diff) > 0.004:
        errors.append("Generated export is out of balance. Debits: {0}. Credits: {1}. Difference: {2}.".format(
            fmt2(total_debits),
            fmt2(total_credits),
            fmt2(diff)
        ))

    if blank_account_rows:
        shown = blank_account_rows[:20]
        msg = "Generated export contains row(s) with blank AccountName: " + "; ".join(shown)
        if len(blank_account_rows) > 20:
            msg += "; plus {0} more.".format(len(blank_account_rows) - 20)
        errors.append(msg)

    return errors


# =============================================================================
# QBO Export Builder
# =============================================================================

def build_journal_rows(cleanlist):
    summary_rows = get_batch_summary(cleanlist)
    detail_rows = get_batch_detail(cleanlist)

    fund_mappings = load_json_content(FUND_MAPPING_CONTENT_NAME)
    acct_mappings = load_json_content(ACCOUNT_MAPPING_CONTENT_NAME)
    bank_mappings = load_json_content(BANK_MAPPING_CONTENT_NAME)
    merchant_fee_account, merchant_fee_class = load_merchant_fee_mapping()

    batch_lookup = {}
    for b in summary_rows:
        batch_id = row_str(b, ["BundleHeaderId"])
        batch_lookup[batch_id] = {
            "DepositDate": row_str(b, ["DepositDate"]),
            "BatchType": row_str(b, ["BatchType"]),
            "Status": row_str(b, ["Status"])
        }

    by_batch = {}
    for r in detail_rows:
        batch_id = row_str(r, ["BatchId", "BundleHeaderId", "BatchID"])
        if batch_id not in by_batch:
            by_batch[batch_id] = []
        by_batch[batch_id].append(r)

    batch_ids = by_batch.keys()
    try:
        batch_ids = sorted(batch_ids, key=lambda x: int(x))
    except:
        batch_ids = sorted(batch_ids)

    journal_rows = []

    for batch_id in batch_ids:
        batch_info = batch_lookup.get(batch_id, {})
        deposit_date = batch_info.get("DepositDate", "")
        batch_type = batch_info.get("BatchType", "")
        journal_no = "TP-" + str(batch_id)

        rows = by_batch.get(batch_id, [])

        batch_base_total = 0.0
        batch_fee_total = 0.0

        for r in rows:
            fund_text = row_str(r, ["Fund"])
            if is_total_row(fund_text):
                continue

            batch_base_total += row_num(r, ["Base"], 0)
            batch_fee_total += row_num(r, ["Fees"], 0)

        bank_debit_total = batch_base_total + batch_fee_total

        bank_name = ""
        bank_entry = bank_mappings.get(batch_type, {})
        if isinstance(bank_entry, dict):
            bank_name = str(bank_entry.get("bank_name", "")).strip()

        if bank_debit_total != 0:
            journal_rows.append({
                "JournalNo": journal_no,
                "JournalDate": deposit_date,
                "AccountName": bank_name,
                "Debits": fmt2(bank_debit_total),
                "Credits": "",
                "Description": build_description(journal_no, "Checking"),
                "Name": "",
                "Currency": "",
                "Location": "",
                "Class": ""
            })

        for r in rows:
            fund_text = row_str(r, ["Fund"])
            if is_total_row(fund_text):
                continue

            amount = row_num(r, ["Base"], 0)
            if amount == 0:
                continue

            general_ledger = row_str(r, ["GeneralLedger"])
            derived_fund_id, cleaned_fund_name = derive_fund_id_and_name(fund_text)

            if derived_fund_id == MERCHANT_FEE_FUND_ID:
                continue

            account_name, acct_class = resolve_income_mapping(
                derived_fund_id,
                general_ledger,
                fund_mappings,
                acct_mappings
            )

            journal_rows.append({
                "JournalNo": journal_no,
                "JournalDate": deposit_date,
                "AccountName": account_name,
                "Debits": "",
                "Credits": fmt2(amount),
                "Description": build_description(journal_no, cleaned_fund_name),
                "Name": "",
                "Currency": "",
                "Location": "",
                "Class": acct_class
            })

        if batch_fee_total != 0:
            journal_rows.append({
                "JournalNo": journal_no,
                "JournalDate": deposit_date,
                "AccountName": merchant_fee_account,
                "Debits": "",
                "Credits": fmt2(batch_fee_total),
                "Description": build_description(journal_no, "Merchant Fees"),
                "Name": "",
                "Currency": "",
                "Location": "",
                "Class": merchant_fee_class
            })

    return journal_rows

def build_csv(journal_rows):
    headers = [
        "JournalNo",
        "JournalDate",
        "AccountName",
        "Debits",
        "Credits",
        "Description",
        "Name",
        "Currency",
        "Location",
        "Class"
    ]

    lines = []
    lines.append(",".join(headers))

    for row in journal_rows:
        vals = []
        for hname in headers:
            vals.append(csv_escape(row.get(hname, "")))
        lines.append(",".join(vals))

    return "\r\n".join(lines)

def get_export_filename(cleanlist):
    batch_ids_for_name = parse_batch_ids(cleanlist)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    if len(batch_ids_for_name) == 1:
        return "QBO_Export_Batch_{0}_{1}.csv".format(
            batch_ids_for_name[0],
            timestamp
        )

    if len(batch_ids_for_name) <= 5:
        return "QBO_Export_{0}_{1}.csv".format(
            "-".join(batch_ids_for_name),
            timestamp
        )

    return "QBO_Export_{0}batches_{1}_to_{2}_{3}.csv".format(
        len(batch_ids_for_name),
        batch_ids_for_name[0],
        batch_ids_for_name[-1],
        timestamp
    )


# =============================================================================
# Export Log Updates
# =============================================================================

def mark_batches_exported(cleanlist):
    batch_ids = parse_batch_ids(cleanlist)
    log_obj = load_export_log()

    exported_on = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    exported_by = ""
    try:
        exported_by = str(model.UserPeopleId)
    except:
        exported_by = ""

    for bid in batch_ids:
        log_obj[bid] = {
            "exported_on": exported_on,
            "exported_by": exported_by
        }

    save_export_log(log_obj)


# =============================================================================
# Response Helpers
# =============================================================================

def render_error_page(title, errors):
    if isinstance(errors, basestring):
        errors = [errors]

    items = []
    for e in errors:
        items.append("<li>{0}</li>".format(h(e)))

    print '''
    <div style="max-width:1000px;margin:30px auto;font-family:Segoe UI,Arial,sans-serif">
        <h3>{0}</h3>
        <div style="border:1px solid #d9534f;background:#fff7f7;border-radius:6px;padding:14px">
            <ul style="margin:0 0 0 20px;padding:0">
                {1}
            </ul>
        </div>
        <p style="margin-top:16px">
            Close this tab/window and return to the QBO Batch Export Tool.
        </p>
    </div>
    '''.format(h(title), "".join(items))

def render_csv_download(csv_text, export_filename):
    safe_filename = js_escape(export_filename)
    safe_csv = js_escape(csv_text)

    print '''
    <div style="max-width:900px;margin:30px auto;font-family:Segoe UI,Arial,sans-serif">
        <h3>Preparing QBO export...</h3>
        <p>Your CSV download should begin automatically.</p>
    </div>

    <script>
    (function() {{
        var csvText = '{0}';
        var filename = '{1}';

        function downloadCsv() {{
            var blob = new Blob([csvText], {{ type: 'text/csv;charset=utf-8;' }});
            var a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);

            setTimeout(function() {{
                try {{
                    window.close();
                }} catch (e) {{}}
            }}, 700);
        }}

        downloadCsv();
    }})();
    </script>
    '''.format(safe_csv, safe_filename)


# =============================================================================
# Request Handling
# =============================================================================

is_post = model.HttpMethod == "post"
action = str(Data.action).strip() if is_post and hasattr(Data, "action") else ""


# -----------------------------------------------------------------------------
# AJAX: Save Setup
# -----------------------------------------------------------------------------

if action == "save_setup":
    try:
        enable_raw = str(Data.enable_clear_export_flag).strip() if hasattr(Data, "enable_clear_export_flag") else "0"
        last_paper_raw = str(Data.last_paper_batch_id).strip() if hasattr(Data, "last_paper_batch_id") else ""

        enable_clear = enable_raw == "1"
        last_paper = to_int(last_paper_raw, 0)

        if last_paper < 1:
            raise Exception("Last Paper Batch ID must be a whole number greater than zero.")

        saved = save_tool_config(enable_clear, last_paper)

        print json.dumps({
            "success": True,
            "message": "Setup saved.",
            "enable_clear_export_flag": saved["enable_clear_export_flag"],
            "last_paper_batch_id": saved["last_paper_batch_id"],
            "min_exportable_batch_id": saved["last_paper_batch_id"] + 1
        })

    except Exception as e:
        print json.dumps({
            "success": False,
            "message": str(e)
        })


# -----------------------------------------------------------------------------
# AJAX: Clear Export Flags
# -----------------------------------------------------------------------------

elif action == "clear_export_flags":
    if not ENABLE_CLEAR_EXPORT_FLAG:
        print json.dumps({
            "success": False,
            "message": "Clear Export Flag is disabled in Setup."
        })
    else:
        raw = str(Data.batchids).strip() if hasattr(Data, "batchids") else ""
        cleanlist = Disinfect(raw)
        batch_ids = parse_batch_ids(cleanlist)

        log_obj = load_export_log()
        cleared = 0
        skipped_paper = 0
        not_found = 0

        for bid in batch_ids:
            if is_paper_batch_id(bid):
                skipped_paper += 1
                continue

            if bid in log_obj:
                del log_obj[bid]
                cleared += 1
            else:
                not_found += 1

        save_export_log(log_obj)

        msg = "Cleared export flag for {0} batch(es).".format(cleared)
        if skipped_paper:
            msg += " Skipped {0} paper batch(es).".format(skipped_paper)
        if not_found:
            msg += " {0} selected batch(es) did not have an export flag.".format(not_found)

        print json.dumps({
            "success": True,
            "message": msg
        })


# -----------------------------------------------------------------------------
# POST: Export Selected Batches
# -----------------------------------------------------------------------------

elif action == "export_selected":
    raw = str(Data.batchids).strip() if hasattr(Data, "batchids") else ""
    cleanlist = Disinfect(raw)

    try:
        batch_errors = validate_selected_batches(cleanlist)

        if batch_errors:
            render_error_page("Export blocked", batch_errors)
        else:
            journal_rows = build_journal_rows(cleanlist)
            row_errors = validate_journal_rows(journal_rows)

            if row_errors:
                render_error_page("Export validation failed", row_errors)
            else:
                csv_text = build_csv(journal_rows)
                export_filename = get_export_filename(cleanlist)

                mark_batches_exported(cleanlist)

                render_csv_download(csv_text, export_filename)

    except Exception as e:
        render_error_page("Script error", str(e))


# -----------------------------------------------------------------------------
# GET: Main UI
# -----------------------------------------------------------------------------

else:
    church_name = get_church_name()
    batches = get_recent_batches()
    export_log = load_export_log()

    status_values = {}
    rows_html = []

    for b in batches:
        batch_id = str(b.BundleHeaderId)
        is_paper = is_paper_batch_id(batch_id)

        deposit_date = str(b.DepositDate) if b.DepositDate is not None else ""
        ref_id = str(b.RefId) if hasattr(b, "RefId") and b.RefId is not None else ""
        batch_type = str(b.BatchType) if hasattr(b, "BatchType") and b.BatchType is not None else ""
        source = str(b.Source) if hasattr(b, "Source") and b.Source is not None else ""
        items = str(b.Items) if hasattr(b, "Items") and b.Items is not None else "0"
        amount = fmt_money(b.Amount if hasattr(b, "Amount") else 0)
        status = str(b.Status) if hasattr(b, "Status") and b.Status is not None else ""

        if status.strip():
            status_values[status.strip()] = True

        export_info = export_log.get(batch_id, {})
        exported_on = ""
        exported_by = ""
        if isinstance(export_info, dict):
            exported_on = str(export_info.get("exported_on", "")).strip()
            exported_by = str(export_info.get("exported_by", "")).strip()

        is_exported = bool(exported_on)
        is_reconciled = status.strip().lower() == REQUIRED_EXPORT_STATUS.lower()

        exported_text = "No"
        export_filter_value = "0"

        if is_paper:
            exported_text = "Paper"
            export_filter_value = "paper"
        elif is_exported:
            exported_text = "Yes"
            export_filter_value = "1"
            if exported_on:
                exported_text = "Yes - " + exported_on
            if exported_by:
                exported_text += " (" + exported_by + ")"

        eligibility_text = "Ready"
        if is_paper:
            eligibility_text = "Paper"
        elif not is_reconciled:
            eligibility_text = "Not Reconciled"
        elif is_exported:
            eligibility_text = "Exported"

        search_text = " ".join([
            batch_id,
            deposit_date,
            ref_id,
            batch_type,
            source,
            items,
            amount,
            status,
            exported_text,
            eligibility_text
        ]).lower()

        row_class = "batch-row"

        if is_paper:
            row_class += " batch-row-paper"
        elif is_exported:
            row_class += " batch-row-exported"
        elif not is_reconciled:
            row_class += " batch-row-notready"
        else:
            row_class += " batch-row-ready"

        checkbox_disabled = False
        checkbox_title = ""

        if is_paper:
            checkbox_disabled = True
            checkbox_title = "Paper batch - not exportable"
        elif not is_reconciled:
            checkbox_disabled = True
            checkbox_title = "Batch is not Reconciled"
        elif is_exported and not ENABLE_CLEAR_EXPORT_FLAG:
            checkbox_disabled = True
            checkbox_title = "Batch is already exported"
        else:
            checkbox_disabled = False
            checkbox_title = ""

        checkbox_html = '<input type="checkbox" class="batch-check" value="{0}" onchange="updateSelectionSummary()">'.format(h(batch_id))
        if checkbox_disabled:
            checkbox_html = '<input type="checkbox" class="batch-check" value="{0}" disabled title="{1}">'.format(h(batch_id), h(checkbox_title))

        rows_html.append('''
        <tr class="{0}" data-search="{1}" data-status="{2}" data-exported="{3}" data-paper="{4}" data-exportable="{5}" data-reconciled="{6}">
            <td>{7}</td>
            <td>{8}</td>
            <td>{9}</td>
            <td>{10}</td>
            <td>{11}</td>
            <td>{12}</td>
            <td class="right">{13}</td>
            <td class="right">{14}</td>
            <td>{15}</td>
            <td>{16}</td>
            <td>{17}</td>
        </tr>
        '''.format(
            row_class,
            h(search_text),
            h(status.strip().lower()),
            h(export_filter_value),
            "1" if is_paper else "0",
            "1" if (not is_paper and is_reconciled and not is_exported) else "0",
            "1" if is_reconciled else "0",
            checkbox_html,
            h(batch_id),
            h(deposit_date),
            h(ref_id),
            h(batch_type),
            h(source),
            h(items),
            h(amount),
            h(status),
            h(exported_text),
            h(eligibility_text)
        ))

    status_options = ['<option value="">All Statuses</option>']
    sorted_statuses = sorted(status_values.keys())
    for s in sorted_statuses:
        status_options.append('<option value="{0}">{1}</option>'.format(h(s.lower()), h(s)))

    clear_button_html = ""
    setup_clear_checked = ""

    if ENABLE_CLEAR_EXPORT_FLAG:
        setup_clear_checked = "checked"
        clear_button_html = '''
            <button type="button" class="qbo-btn qbo-btn-warning" onclick="clearExportFlags()">Clear Export Flag</button>
        '''

    model.Form = '''
    <div class="qbo-wrap" style="max-width:1800px;margin:20px auto;font-family:Segoe UI,Arial,sans-serif">
        <style>
            .qbo-card {{
                background:#fff;
                border:1px solid #ddd;
                border-radius:8px;
                padding:16px;
                margin-bottom:16px;
            }}
            .qbo-tabs {{
                display:flex;
                gap:8px;
                margin-bottom:14px;
                border-bottom:1px solid #ddd;
            }}
            .qbo-tab {{
                padding:9px 14px;
                border:1px solid #ddd;
                border-bottom:none;
                background:#f7f7f7;
                border-radius:8px 8px 0 0;
                cursor:pointer;
                font-size:13px;
            }}
            .qbo-tab.active {{
                background:#fff;
                font-weight:600;
                color:#23527c;
            }}
            .qbo-panel {{
                display:none;
            }}
            .qbo-panel.active {{
                display:block;
            }}
            .qbo-btn {{
                padding:8px 14px;
                border:none;
                border-radius:4px;
                cursor:pointer;
                font-size:13px;
            }}
            .qbo-btn-primary {{ background:#337ab7; color:#fff; }}
            .qbo-btn-success {{ background:#28a745; color:#fff; }}
            .qbo-btn-secondary {{ background:#6c757d; color:#fff; }}
            .qbo-btn-warning {{ background:#f0ad4e; color:#fff; }}
            .qbo-input {{
                padding:6px 8px;
                border:1px solid #ccc;
                border-radius:4px;
                box-sizing:border-box;
            }}
            .qbo-table {{
                width:100%;
                border-collapse:collapse;
            }}
            .qbo-table th, .qbo-table td {{
                padding:8px;
                border-bottom:1px solid #e9ecef;
                vertical-align:top;
            }}
            .qbo-table th {{
                background:#f5f5f5;
                text-align:left;
                position:sticky;
                top:0;
                z-index:2;
            }}
            .qbo-table th.right,
            .qbo-table td.right {{
                text-align:right;
            }}
            .qbo-scroll {{
                max-height:560px;
                overflow:auto;
                border:1px solid #ddd;
                border-radius:8px;
            }}
            .muted {{ color:#666; font-size:12px; }}
            .summary-pill {{
                display:inline-block;
                padding:4px 10px;
                border-radius:999px;
                background:#eef3f8;
                font-size:12px;
                margin-right:8px;
                margin-bottom:4px;
            }}

            .batch-row-ready {{
                background:#eef9ee;
            }}
            .batch-row-ready:hover {{
                background:#e1f4e1;
            }}
            .batch-row-exported {{
                background:#faf7f2;
            }}
            .batch-row-exported:hover {{
                background:#f5efe5;
            }}
            .batch-row-paper {{
                background:#f1f1f1;
                color:#777;
            }}
            .batch-row-notready {{
                background:#fdecec;
            }}
            .batch-row-notready:hover {{
                background:#f9dddd;
            }}
            .batch-row-paper td {{
                opacity:0.92;
            }}

            .paper-note {{
                background:#f8f9fa;
                border:1px solid #ddd;
                border-radius:6px;
                padding:8px 10px;
                margin-top:10px;
                color:#555;
                font-size:12px;
            }}
            .v2-note {{
                background:#eef7ee;
                border:1px solid #cfe8cf;
                border-radius:6px;
                padding:8px 10px;
                margin-top:10px;
                color:#335533;
                font-size:12px;
            }}
            .setup-row {{
                margin-bottom:18px;
            }}
            .setup-label {{
                font-weight:600;
                display:block;
                margin-bottom:5px;
            }}
            .setup-help {{
                font-size:12px;
                color:#666;
                margin-top:5px;
                max-width:900px;
            }}
            .setup-current {{
                background:#f8f9fa;
                border:1px solid #ddd;
                border-radius:6px;
                padding:10px;
                font-size:13px;
                margin-bottom:16px;
            }}
        </style>

        <div style="text-align:center;margin-bottom:16px">
            <h2 style="margin:0">{0}</h2>
            <h3 style="margin:6px 0 0 0">QBO Batch Export Tool</h3>
            <div class="muted" style="margin-top:6px">Version {1} &mdash; Updated {2}</div>
        </div>

        <div class="qbo-tabs">
            <button type="button" id="tabExport" class="qbo-tab active" onclick="showTab('export')">Export Batches</button>
            <button type="button" id="tabSetup" class="qbo-tab" onclick="showTab('setup')">Setup</button>
        </div>

        <div id="panelExport" class="qbo-panel active">
            <div class="qbo-card">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap">
                    <div>
                        <h3 style="margin:0">Select Batches for Export</h3>
                        <div class="muted" style="margin-top:6px">
                            Version 2.2.0 generates the final QBO CSV directly from this tool.
                            Export is allowed only for batches with Status = <strong>Reconciled</strong>, Exported = <strong>No</strong>, and Batch ID {5} or higher.
                        </div>
                        <div class="paper-note">
                            Batches with Batch ID {6} and below are historical paper batches. They display <strong>Exported = Paper</strong> and cannot be selected or exported.
                        </div>
                        <div class="v2-note">
                            Ready-to-export batches are highlighted green. Open/non-Reconciled batches are highlighted red.
                            Exported batches can only be selected when the Clear Export Flag testing feature is enabled.
                            This version no longer depends on TESTMultiBatchReportSQL.
                        </div>
                    </div>
                    <div style="display:flex;gap:8px;flex-wrap:wrap">
                        <button type="button" class="qbo-btn qbo-btn-primary" onclick="toggleAllVisible(true)">Select Visible</button>
                        <button type="button" class="qbo-btn qbo-btn-secondary" onclick="toggleAllVisible(false)">Clear Visible</button>
                        {7}
                        <button type="button" class="qbo-btn qbo-btn-success" onclick="exportSelected()">Export Selected Batches</button>
                    </div>
                </div>

                <div style="display:flex;gap:16px;align-items:flex-end;flex-wrap:wrap;margin-top:16px;margin-bottom:12px">
                    <div>
                        <label style="font-weight:600;font-size:13px">Search batches</label><br>
                        <input type="text" id="batchFilter" class="qbo-input" style="width:320px" placeholder="Filter current list" onkeyup="filterBatchRows()">
                    </div>
                    <div>
                        <label style="font-weight:600;font-size:13px">Filter by Status</label><br>
                        <select id="statusFilter" class="qbo-input" style="width:220px" onchange="filterBatchRows()">
                            {3}
                        </select>
                    </div>
                    <div>
                        <label style="font-weight:600;font-size:13px">Export Status</label><br>
                        <select id="exportFilter" class="qbo-input" style="width:220px" onchange="filterBatchRows()">
                            <option value="">All</option>
                            <option value="1">Exported Only</option>
                            <option value="0">Not Exported Only</option>
                            <option value="paper">Paper Only</option>
                        </select>
                    </div>
                    <div id="selectionSummary" style="padding-bottom:6px;font-size:13px;color:#444"></div>
                </div>

                <div id="topMessage" style="margin-bottom:10px;font-size:13px;min-height:18px"></div>

                <div class="qbo-scroll">
                    <table class="qbo-table" id="batchSelectTable">
                        <thead>
                            <tr>
                                <th style="width:40px"></th>
                                <th>Batch ID</th>
                                <th>Deposit Date</th>
                                <th>Ref. ID</th>
                                <th>Batch Type</th>
                                <th>Source</th>
                                <th class="right">Items</th>
                                <th class="right">Amount</th>
                                <th>Status</th>
                                <th>Exported</th>
                                <th>Eligibility</th>
                            </tr>
                        </thead>
                        <tbody>
                            {4}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <div id="panelSetup" class="qbo-panel">
            <div class="qbo-card">
                <h3 style="margin-top:0">QBO Batch Export Tool Setup</h3>

                <div class="setup-current">
                    <div><strong>Current Setup</strong></div>
                    <div>Clear Export Flag enabled: <strong>{8}</strong></div>
                    <div>Last Paper Batch ID: <strong>{6}</strong></div>
                    <div>Minimum Exportable Batch ID: <strong>{5}</strong></div>
                </div>

                <div id="setupMessage" style="margin-bottom:12px;font-size:13px;min-height:18px"></div>

                <div class="setup-row">
                    <label class="setup-label">
                        <input type="checkbox" id="setupEnableClearExportFlag" {9}>
                        Enable Clear Export Flag testing feature
                    </label>
                    <div class="setup-help">
                        When enabled, the Export Batches tab shows the Clear Export Flag button and already-exported batches may be selected for clearing.
                        When disabled, the button is hidden, already-exported batches cannot be selected, and the server-side clear action is blocked.
                    </div>
                </div>

                <div class="setup-row">
                    <label class="setup-label" for="setupLastPaperBatchId">Last Paper Batch ID</label>
                    <input type="text" id="setupLastPaperBatchId" class="qbo-input" style="width:180px" value="{6}">
                    <div class="setup-help">
                        Batches with this Batch ID and below are treated as historical paper batches.
                        For example, if this is set to 1993, then batches 1993 and below are Paper, and batches 1994 and above may be exportable if Reconciled and not already exported.
                    </div>
                </div>

                <button type="button" class="qbo-btn qbo-btn-success" onclick="saveSetup()">Save Setup</button>
            </div>
        </div>
    </div>
    '''.format(
        h(church_name),
        h(SCRIPT_VERSION),
        h(SCRIPT_LAST_UPDATED),
        "".join(status_options),
        "".join(rows_html),
        h(str(MIN_EXPORTABLE_BATCH_ID)),
        h(str(LAST_PAPER_BATCH_ID)),
        clear_button_html,
        "Yes" if ENABLE_CLEAR_EXPORT_FLAG else "No",
        setup_clear_checked
    )

    model.Script = '''
    function showTab(which) {
        var exportPanel = document.getElementById('panelExport');
        var setupPanel = document.getElementById('panelSetup');
        var exportTab = document.getElementById('tabExport');
        var setupTab = document.getElementById('tabSetup');

        exportPanel.className = 'qbo-panel';
        setupPanel.className = 'qbo-panel';
        exportTab.className = 'qbo-tab';
        setupTab.className = 'qbo-tab';

        if (which === 'setup') {
            setupPanel.className = 'qbo-panel active';
            setupTab.className = 'qbo-tab active';
        } else {
            exportPanel.className = 'qbo-panel active';
            exportTab.className = 'qbo-tab active';
        }
    }

    function setTopMessage(html) {
        document.getElementById('topMessage').innerHTML = html || '';
    }

    function setSetupMessage(html) {
        document.getElementById('setupMessage').innerHTML = html || '';
    }

    function getScriptFormUrl() {
        return '/PyScriptForm/' + window.location.pathname.split('/').pop().split('?')[0];
    }

    function postData(data, callback) {
        $.ajax({
            url: getScriptFormUrl(),
            type: 'POST',
            data: data,
            success: function(resp) {
                try {
                    callback(JSON.parse(resp));
                } catch (e) {
                    alert('Could not parse server response.');
                }
            },
            error: function(x) {
                alert('Request failed: ' + x.status);
            }
        });
    }

    function saveSetup() {
        var enableClear = document.getElementById('setupEnableClearExportFlag').checked ? '1' : '0';
        var lastPaper = document.getElementById('setupLastPaperBatchId').value || '';

        lastPaper = lastPaper.replace(/[^0-9]/g, '');

        if (!lastPaper) {
            alert('Enter a Last Paper Batch ID.');
            return;
        }

        if (!confirm('Save setup changes?\\n\\nThe page will reload after saving.')) {
            return;
        }

        setSetupMessage('<span style="color:#666">Saving setup...</span>');

        postData({
            action: 'save_setup',
            enable_clear_export_flag: enableClear,
            last_paper_batch_id: lastPaper
        }, function(d) {
            if (d.success) {
                setSetupMessage('<span style="color:green">' + (d.message || 'Setup saved.') + '</span>');
                window.location.reload();
            } else {
                setSetupMessage('<span style="color:red">' + (d.message || 'Save failed.') + '</span>');
            }
        });
    }

    function filterBatchRows() {
        var txt = (document.getElementById('batchFilter').value || '').toLowerCase();
        var statusVal = (document.getElementById('statusFilter').value || '').toLowerCase();
        var exportVal = (document.getElementById('exportFilter').value || '');
        var rows = document.querySelectorAll('#batchSelectTable tbody tr.batch-row');

        for (var i = 0; i < rows.length; i++) {
            var hay = (rows[i].getAttribute('data-search') || '').toLowerCase();
            var rowStatus = (rows[i].getAttribute('data-status') || '').toLowerCase();
            var rowExported = (rows[i].getAttribute('data-exported') || '');

            var matchesText = hay.indexOf(txt) >= 0;
            var matchesStatus = !statusVal || rowStatus === statusVal;
            var matchesExport = !exportVal || rowExported === exportVal;

            rows[i].style.display = (matchesText && matchesStatus && matchesExport) ? '' : 'none';
        }

        updateSelectionSummary();
    }

    function toggleAllVisible(checked) {
        var rows = document.querySelectorAll('#batchSelectTable tbody tr.batch-row');

        for (var i = 0; i < rows.length; i++) {
            if (rows[i].style.display === 'none') continue;

            var cb = rows[i].querySelector('input.batch-check');
            if (cb && !cb.disabled) {
                cb.checked = checked;
            }
        }

        updateSelectionSummary();
    }

    function getSelectedBatchIds() {
        var ids = [];
        var checks = document.querySelectorAll('input.batch-check:checked');

        for (var i = 0; i < checks.length; i++) {
            ids.push(checks[i].value);
        }

        return ids;
    }

    function getSelectedExportedBatchIds() {
        var ids = [];
        var checks = document.querySelectorAll('input.batch-check:checked');

        for (var i = 0; i < checks.length; i++) {
            var row = checks[i].closest('tr');
            if (row && row.getAttribute('data-exported') === '1') {
                ids.push(checks[i].value);
            }
        }

        return ids;
    }

    function getSelectedPaperBatchIds() {
        var ids = [];
        var checks = document.querySelectorAll('input.batch-check:checked');

        for (var i = 0; i < checks.length; i++) {
            var row = checks[i].closest('tr');
            if (row && row.getAttribute('data-paper') === '1') {
                ids.push(checks[i].value);
            }
        }

        return ids;
    }

    function getSelectedNotReconciledBatchIds() {
        var ids = [];
        var checks = document.querySelectorAll('input.batch-check:checked');

        for (var i = 0; i < checks.length; i++) {
            var row = checks[i].closest('tr');
            if (row && row.getAttribute('data-reconciled') !== '1') {
                ids.push(checks[i].value);
            }
        }

        return ids;
    }

    function updateSelectionSummary() {
        var rows = document.querySelectorAll('#batchSelectTable tbody tr.batch-row');
        var visible = 0;
        var visiblePaper = 0;
        var visibleReady = 0;

        for (var i = 0; i < rows.length; i++) {
            if (rows[i].style.display !== 'none') {
                visible++;
                if (rows[i].getAttribute('data-paper') === '1') {
                    visiblePaper++;
                }
                if (rows[i].getAttribute('data-exportable') === '1') {
                    visibleReady++;
                }
            }
        }

        var selected = getSelectedBatchIds();
        var exportedSelected = getSelectedExportedBatchIds();

        var html = '';
        html += '<span class="summary-pill">Visible: <strong>' + visible + '</strong></span>';
        html += '<span class="summary-pill">Ready Visible: <strong>' + visibleReady + '</strong></span>';
        html += '<span class="summary-pill">Selected: <strong>' + selected.length + '</strong></span>';

        if (visiblePaper) {
            html += '<span class="summary-pill">Visible Paper: <strong>' + visiblePaper + '</strong></span>';
        }

        if (exportedSelected.length) {
            html += '<span class="summary-pill">Already Exported Selected: <strong>' + exportedSelected.length + '</strong></span>';
        }

        if (selected.length) {
            html += '<span class="summary-pill">Batch IDs: <strong>' + selected.join(', ') + '</strong></span>';
        }

        document.getElementById('selectionSummary').innerHTML = html;
    }

    function submitExportForm(ids) {
        var form = document.createElement('form');
        form.method = 'POST';
        form.action = getScriptFormUrl();
        form.target = '_blank';

        var actionInput = document.createElement('input');
        actionInput.type = 'hidden';
        actionInput.name = 'action';
        actionInput.value = 'export_selected';
        form.appendChild(actionInput);

        var batchInput = document.createElement('input');
        batchInput.type = 'hidden';
        batchInput.name = 'batchids';
        batchInput.value = ids.join(',');
        form.appendChild(batchInput);

        document.body.appendChild(form);
        form.submit();
        document.body.removeChild(form);
    }

    function exportSelected() {
        var ids = getSelectedBatchIds();

        if (!ids.length) {
            alert('Select at least one batch.');
            return;
        }

        var paperIds = getSelectedPaperBatchIds();
        if (paperIds.length) {
            alert('These selected batches are paper batches and cannot be exported: ' + paperIds.join(', ') + '.');
            return;
        }

        var notReconciledIds = getSelectedNotReconciledBatchIds();
        if (notReconciledIds.length) {
            alert('These selected batches are not Reconciled and cannot be exported: ' + notReconciledIds.join(', ') + '.');
            return;
        }

        var exportedIds = getSelectedExportedBatchIds();
        if (exportedIds.length) {
            alert('These selected batches are already flagged as exported and cannot be exported again: ' + exportedIds.join(', ') + '.\\n\\nUse Clear Export Flag first if you need to re-export during testing.');
            return;
        }

        submitExportForm(ids);
    }

    function clearExportFlags() {
        var ids = getSelectedBatchIds();

        if (!ids.length) {
            alert('Select at least one batch.');
            return;
        }

        if (!confirm('Clear export flag for selected batch(es)?\\n\\nPaper batches, if any, will be skipped.')) {
            return;
        }

        setTopMessage('<span style="color:#666">Clearing export flag(s)...</span>');

        postData({
            action: 'clear_export_flags',
            batchids: ids.join(',')
        }, function(d) {
            if (d.success) {
                setTopMessage('<span style="color:green">' + (d.message || 'Done') + '</span>');
                window.location.reload();
            } else {
                setTopMessage('<span style="color:red">' + (d.message || 'Failed') + '</span>');
            }
        });
    }

    updateSelectionSummary();
    '''
