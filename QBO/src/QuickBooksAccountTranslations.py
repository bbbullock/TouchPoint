#roles=Finance,Admin

import json
import datetime

# =============================================================================
# QuickBooks Account Translations
# Version: 1.6.0
# Last Updated: 2026-05-04
#
# Purpose:
#   Standalone TouchPoint tool for maintaining QuickBooks account translation
#   mappings used by the QBO export process:
#     - FundId translations
#     - Account Code translations
#     - Bank Batch Type / Bank Account translations
#     - Merchant Fees translations
#
# Features:
#   - True top-tab UI for FundId, Account Code, Bank Code, and Merchant Fees grids
#   - Displays all open funds
#   - Displays AccountCode values from AccountCode object/table
#   - Displays one row per Bank Batch Type
#   - Displays Merchant Fees mapping row for FundID 6050
#   - Inline editing for mapping values
#   - Save one row or save all changed rows
#   - Clear one row
#   - Search/filter
#   - Unmapped-only toggle
#   - Changed-row tracking
#   - Sortable columns
#   - JSON import/export per active tab
#   - User-managed Bank Batch Type list
#
# Storage:
#   - TPxi_FinanceExport_Mappings
#   - TPxi_FinanceExport_Config
#   - TPxi_FinanceExport_AccountCodeMappings
#   - TPxi_FinanceExport_AccountCodeConfig
#   - TPxi_FinanceExport_BankMappings
#   - TPxi_FinanceExport_BankConfig
#   - TPxi_FinanceExport_BankBatchTypeOptions
#   - TPxi_FinanceExport_MerchantFeeMapping
#   - TPxi_FinanceExport_MerchantFeeConfig
# =============================================================================

SCRIPT_VERSION = "1.6.0"
SCRIPT_LAST_UPDATED = "2026-04-24"

FUND_MAPPING_CONTENT_NAME = "TPxi_FinanceExport_Mappings"
FUND_CONFIG_CONTENT_NAME = "TPxi_FinanceExport_Config"

ACCOUNT_MAPPING_CONTENT_NAME = "TPxi_FinanceExport_AccountCodeMappings"
ACCOUNT_CONFIG_CONTENT_NAME = "TPxi_FinanceExport_AccountCodeConfig"

BANK_MAPPING_CONTENT_NAME = "TPxi_FinanceExport_BankMappings"
BANK_CONFIG_CONTENT_NAME = "TPxi_FinanceExport_BankConfig"
BANK_BATCH_TYPE_OPTIONS_CONTENT_NAME = "TPxi_FinanceExport_BankBatchTypeOptions"

MERCHANT_FEE_MAPPING_CONTENT_NAME = "TPxi_FinanceExport_MerchantFeeMapping"
MERCHANT_FEE_CONFIG_CONTENT_NAME = "TPxi_FinanceExport_MerchantFeeConfig"

MERCHANT_FEE_FUND_ID = "6050"
MERCHANT_FEE_LABEL = "Merchant Fees"

DEFAULT_COLUMNS = [
    {"key": "account", "label": "Account"},
    {"key": "acct_class", "label": "Class"},
]

DEFAULT_MAPPINGS = {}

DEFAULT_MERCHANT_FEE_MAPPINGS = {
    MERCHANT_FEE_FUND_ID: {
        "account": "Bank Service Charges",
        "acct_class": "General Fund:Administration"
    }
}

DEFAULT_BANK_BATCH_TYPE_OPTIONS = [
    "Online",
    "Loose Cash",
    "Loose Checks",
    "Stock"
]

ACCOUNT_CODE_LOAD_ERROR = ""

# =============================================================================
# Helpers
# =============================================================================

def get_map_type():
    if model.HttpMethod == "post" and hasattr(Data, "map_type"):
        mt = str(Data.map_type).strip().lower()
        if mt in ["fund", "account", "bank", "merchant"]:
            return mt
    return "fund"

def get_storage_names(map_type):
    if map_type == "account":
        return ACCOUNT_MAPPING_CONTENT_NAME, ACCOUNT_CONFIG_CONTENT_NAME
    if map_type == "bank":
        return BANK_MAPPING_CONTENT_NAME, BANK_CONFIG_CONTENT_NAME
    if map_type == "merchant":
        return MERCHANT_FEE_MAPPING_CONTENT_NAME, MERCHANT_FEE_CONFIG_CONTENT_NAME
    return FUND_MAPPING_CONTENT_NAME, FUND_CONFIG_CONTENT_NAME

def get_default_mappings(map_type):
    if map_type == "merchant":
        return dict(DEFAULT_MERCHANT_FEE_MAPPINGS)
    return dict(DEFAULT_MAPPINGS)

def load_config(map_type):
    mapping_name, config_name = get_storage_names(map_type)
    try:
        content = model.TextContent(config_name)
        if content:
            cfg = json.loads(content)
            if isinstance(cfg, dict):
                if map_type == "bank":
                    return cfg
                if cfg.get("columns"):
                    return cfg
    except:
        pass

    if map_type == "bank":
        cfg = {"columns": []}
    else:
        cfg = {"columns": list(DEFAULT_COLUMNS)}

    save_config(map_type, cfg)
    return cfg

def save_config(map_type, cfg):
    mapping_name, config_name = get_storage_names(map_type)
    model.WriteContentText(config_name, json.dumps(cfg, indent=2), "")

def load_mappings(map_type):
    mapping_name, config_name = get_storage_names(map_type)
    try:
        content = model.TextContent(mapping_name)
        if content:
            mappings = json.loads(content)
            if isinstance(mappings, dict):
                return mappings
    except:
        pass

    defaults = get_default_mappings(map_type)
    save_mappings(map_type, defaults)
    return defaults

def save_mappings(map_type, mappings):
    mapping_name, config_name = get_storage_names(map_type)
    model.WriteContentText(mapping_name, json.dumps(mappings, indent=2), "")

def normalize_batch_type_option(value):
    if value is None:
        return ""
    return str(value).strip()

def load_bank_batch_type_options():
    try:
        content = model.TextContent(BANK_BATCH_TYPE_OPTIONS_CONTENT_NAME)
        if content:
            options = json.loads(content)
            if isinstance(options, list):
                cleaned = []
                seen = {}
                for item in options:
                    val = normalize_batch_type_option(item)
                    if val and val not in seen:
                        seen[val] = True
                        cleaned.append(val)
                if cleaned:
                    return cleaned
    except:
        pass

    save_bank_batch_type_options(DEFAULT_BANK_BATCH_TYPE_OPTIONS)
    return list(DEFAULT_BANK_BATCH_TYPE_OPTIONS)

def save_bank_batch_type_options(options):
    cleaned = []
    seen = {}
    for item in options:
        val = normalize_batch_type_option(item)
        if val and val not in seen:
            seen[val] = True
            cleaned.append(val)

    model.WriteContentText(BANK_BATCH_TYPE_OPTIONS_CONTENT_NAME, json.dumps(cleaned, indent=2), "")
    return cleaned

def add_bank_batch_type(option_name):
    option_name = normalize_batch_type_option(option_name)
    if not option_name:
        return False, "Batch Type is required"

    options = load_bank_batch_type_options()
    if option_name in options:
        return False, "That Batch Type already exists"

    options.append(option_name)
    save_bank_batch_type_options(options)
    return True, "Added Batch Type " + option_name

def delete_bank_batch_type(option_name):
    option_name = normalize_batch_type_option(option_name)
    if not option_name:
        return False, "Batch Type is required"

    options = load_bank_batch_type_options()
    if option_name not in options:
        return False, "Batch Type not found"

    options = [x for x in options if x != option_name]
    save_bank_batch_type_options(options)

    mappings = load_mappings("bank")
    if option_name in mappings:
        del mappings[option_name]
        save_mappings("bank", mappings)

    return True, "Deleted Batch Type " + option_name

def get_open_funds():
    sql = '''
        SELECT
            cf.FundId,
            cf.FundName,
            cf.FundStatusId
        FROM ContributionFund cf
        WHERE cf.FundStatusId = 1
          AND cf.FundName IS NOT NULL
        ORDER BY cf.FundName, cf.FundId
    '''
    try:
        results = list(q.QuerySql(sql))
        funds = []
        for r in results:
            funds.append({
                "FundId": str(r.FundId),
                "FundName": str(r.FundName),
                "FundStatusId": str(r.FundStatusId)
            })
        return funds
    except:
        return []

def get_merchant_fee_fund_name():
    sql = '''
        SELECT TOP 1
            cf.FundName
        FROM ContributionFund cf
        WHERE cf.FundId = 6050
    '''
    try:
        val = q.QuerySqlScalar(sql)
        if val:
            return str(val)
    except:
        pass
    return MERCHANT_FEE_LABEL

def get_account_codes():
    global ACCOUNT_CODE_LOAD_ERROR
    ACCOUNT_CODE_LOAD_ERROR = ""

    try:
        schema_sql = '''
            SELECT TOP 1
                c.TABLE_SCHEMA
            FROM INFORMATION_SCHEMA.COLUMNS c
            WHERE c.TABLE_NAME = 'AccountCode'
            ORDER BY c.TABLE_SCHEMA
        '''
        schema_results = list(q.QuerySql(schema_sql))

        if not schema_results:
            ACCOUNT_CODE_LOAD_ERROR = "Could not find AccountCode in INFORMATION_SCHEMA.COLUMNS."
            return []

        table_schema = str(schema_results[0].TABLE_SCHEMA).strip()
        full_table_name = "[{0}].[AccountCode]".format(table_schema.replace("]", "]]"))

        cols_sql = '''
            SELECT
                c.COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS c
            WHERE c.TABLE_NAME = 'AccountCode'
            ORDER BY c.ORDINAL_POSITION
        '''
        col_results = list(q.QuerySql(cols_sql))
        cols = [str(r.COLUMN_NAME) for r in col_results]

        code_col = None
        desc_col = None

        for cand in ["Code", "AccountCode", "AcctCode", "Id", "ID"]:
            if cand in cols:
                code_col = cand
                break

        for cand in ["Description", "Descr", "Name", "AccountName", "Title", "FullName", "LongName"]:
            if cand in cols:
                desc_col = cand
                break

        if not code_col:
            ACCOUNT_CODE_LOAD_ERROR = "AccountCode exists, but no usable code column was found."
            return []

        code_expr = "LTRIM(RTRIM(CONVERT(nvarchar(100), [{0}])))".format(code_col)

        if desc_col:
            desc_expr = "LTRIM(RTRIM(CONVERT(nvarchar(255), [{0}])))".format(desc_col)
        else:
            desc_expr = "CAST('' AS nvarchar(255))"

        sql = '''
            SELECT DISTINCT
                {0} AS AccountCode,
                {1} AS Description
            FROM {2}
            WHERE {0} IS NOT NULL
              AND {0} <> ''
            ORDER BY {0}
        '''.format(code_expr, desc_expr, full_table_name)

        results = list(q.QuerySql(sql))
        rows = []

        for r in results:
            acct = str(r.AccountCode).strip() if r.AccountCode is not None else ""
            desc = str(r.Description).strip() if r.Description is not None else ""
            if acct:
                rows.append({
                    "AccountCode": acct,
                    "Description": desc
                })

        if not rows:
            ACCOUNT_CODE_LOAD_ERROR = "AccountCode table was found at {0}, but returned no rows.".format(full_table_name)

        return rows

    except Exception as e:
        ACCOUNT_CODE_LOAD_ERROR = str(e)
        return []

def build_fund_grid_rows():
    mappings = load_mappings("fund")
    cfg = load_config("fund")
    funds = get_open_funds()
    columns = cfg.get("columns", DEFAULT_COLUMNS)

    rows = []
    for f in funds:
        fund_id = str(f["FundId"])
        saved = mappings.get(fund_id, {})
        row = {
            "row_id": fund_id,
            "id_value": fund_id,
            "name_value": f["FundName"],
            "status_value": f["FundStatusId"],
            "id_label": "FundId",
            "name_label": "Fund Name",
            "has_mapping": fund_id in mappings,
            "mapped_values": {}
        }
        for col in columns:
            row["mapped_values"][col["key"]] = saved.get(col["key"], "")
        rows.append(row)

    return columns, rows

def build_account_grid_rows():
    mappings = load_mappings("account")
    cfg = load_config("account")
    account_codes = get_account_codes()
    columns = cfg.get("columns", DEFAULT_COLUMNS)

    rows = []
    for a in account_codes:
        account_code = str(a["AccountCode"])
        saved = mappings.get(account_code, {})
        row = {
            "row_id": account_code,
            "id_value": account_code,
            "name_value": str(a.get("Description", "")),
            "status_value": "",
            "id_label": "Account Code",
            "name_label": "Description",
            "has_mapping": account_code in mappings,
            "mapped_values": {}
        }
        for col in columns:
            row["mapped_values"][col["key"]] = saved.get(col["key"], "")
        rows.append(row)

    return columns, rows

def build_bank_grid_rows():
    mappings = load_mappings("bank")
    batch_type_options = load_bank_batch_type_options()
    rows = []

    for batch_type in batch_type_options:
        saved = mappings.get(batch_type, {})
        bank_name = str(saved.get("bank_name", ""))

        rows.append({
            "row_id": batch_type,
            "id_value": batch_type,
            "name_value": bank_name,
            "status_value": "",
            "id_label": "Batch Type",
            "name_label": "Bank Name",
            "has_mapping": bool(bank_name),
            "mapped_values": {}
        })

    return [], rows

def build_merchant_grid_rows():
    mappings = load_mappings("merchant")
    cfg = load_config("merchant")
    columns = cfg.get("columns", DEFAULT_COLUMNS)
    fund_id = MERCHANT_FEE_FUND_ID
    fund_name = get_merchant_fee_fund_name()
    saved = mappings.get(fund_id, {})

    row = {
        "row_id": fund_id,
        "id_value": fund_id,
        "name_value": fund_name,
        "status_value": "Special Merchant Fees Mapping",
        "id_label": "FundId",
        "name_label": "Fund Name",
        "has_mapping": fund_id in mappings,
        "mapped_values": {}
    }

    for col in columns:
        row["mapped_values"][col["key"]] = saved.get(col["key"], "")

    return columns, [row]

def build_grid_rows(map_type):
    if map_type == "account":
        return build_account_grid_rows()
    if map_type == "bank":
        return build_bank_grid_rows()
    if map_type == "merchant":
        return build_merchant_grid_rows()
    return build_fund_grid_rows()

# =============================================================================
# Request Handling
# =============================================================================

is_post = model.HttpMethod == "post"
action = str(Data.action) if is_post and hasattr(Data, "action") else ""
map_type = get_map_type()

if action == "get_grid":
    columns, rows = build_grid_rows(map_type)
    response = {
        "success": True,
        "version": SCRIPT_VERSION,
        "last_updated": SCRIPT_LAST_UPDATED,
        "map_type": map_type,
        "columns": columns,
        "rows": rows
    }
    if map_type == "account" and ACCOUNT_CODE_LOAD_ERROR:
        response["warning"] = ACCOUNT_CODE_LOAD_ERROR
    if map_type == "bank":
        response["batch_type_options"] = load_bank_batch_type_options()
    print json.dumps(response)

elif action == "add_bank_batch_type":
    batch_type_name = str(Data.batch_type_name).strip() if hasattr(Data, "batch_type_name") else ""
    ok, msg = add_bank_batch_type(batch_type_name)
    print json.dumps({
        "success": ok,
        "message": msg,
        "batch_type_options": load_bank_batch_type_options()
    })

elif action == "delete_bank_batch_type":
    batch_type_name = str(Data.batch_type_name).strip() if hasattr(Data, "batch_type_name") else ""
    ok, msg = delete_bank_batch_type(batch_type_name)
    print json.dumps({
        "success": ok,
        "message": msg,
        "batch_type_options": load_bank_batch_type_options()
    })

elif action == "save_mapping":
    row_id = ""

    if map_type == "account":
        row_id = str(Data.row_id).strip() if hasattr(Data, "row_id") else ""
        if not row_id and hasattr(Data, "account_code"):
            row_id = str(Data.account_code).strip()
    elif map_type == "bank":
        row_id = str(Data.row_id).strip() if hasattr(Data, "row_id") else ""
    elif map_type == "merchant":
        row_id = str(Data.row_id).strip() if hasattr(Data, "row_id") else MERCHANT_FEE_FUND_ID
        if row_id != MERCHANT_FEE_FUND_ID:
            row_id = MERCHANT_FEE_FUND_ID
    else:
        row_id = str(Data.row_id).strip() if hasattr(Data, "row_id") else ""
        if not row_id and hasattr(Data, "fund_id"):
            row_id = str(Data.fund_id).strip()

    if not row_id:
        print json.dumps({"success": False, "message": "Row ID is required"})
    else:
        if map_type == "bank":
            bank_batch_type_options = load_bank_batch_type_options()
            mappings = load_mappings("bank")
            bank_name = str(Data.bank_name).strip() if hasattr(Data, "bank_name") else ""

            if row_id not in bank_batch_type_options:
                print json.dumps({"success": False, "message": "Invalid Batch Type"})
            else:
                if bank_name:
                    mappings[row_id] = {
                        "bank_name": bank_name
                    }
                    save_mappings("bank", mappings)
                    print json.dumps({"success": True, "message": "Saved bank mapping"})
                else:
                    if row_id in mappings:
                        del mappings[row_id]
                        save_mappings("bank", mappings)
                    print json.dumps({"success": True, "message": "Cleared bank mapping"})
        else:
            cfg = load_config(map_type)
            columns = cfg.get("columns", DEFAULT_COLUMNS)
            mappings = load_mappings(map_type)

            entry = {}
            has_any_value = False

            for col in columns:
                param_name = "col_" + col["key"]
                val = str(getattr(Data, param_name)) if hasattr(Data, param_name) else ""
                val = val.strip()
                entry[col["key"]] = val
                if val:
                    has_any_value = True

            if has_any_value:
                mappings[row_id] = entry
                save_mappings(map_type, mappings)
                if map_type == "account":
                    print json.dumps({"success": True, "message": "Saved mapping for Account Code " + row_id})
                elif map_type == "merchant":
                    print json.dumps({"success": True, "message": "Saved Merchant Fees mapping"})
                else:
                    print json.dumps({"success": True, "message": "Saved mapping for FundId " + row_id})
            else:
                if row_id in mappings:
                    del mappings[row_id]
                    save_mappings(map_type, mappings)
                if map_type == "account":
                    print json.dumps({"success": True, "message": "Cleared mapping for Account Code " + row_id})
                elif map_type == "merchant":
                    print json.dumps({"success": True, "message": "Cleared Merchant Fees mapping"})
                else:
                    print json.dumps({"success": True, "message": "Cleared mapping for FundId " + row_id})

elif action == "save_bulk":
    raw = str(Data.rows_json) if hasattr(Data, "rows_json") else ""
    if not raw:
        print json.dumps({"success": False, "message": "No rows supplied"})
    else:
        try:
            rows = json.loads(raw)
            if not isinstance(rows, list):
                raise Exception("rows_json must be a JSON array")

            if map_type == "bank":
                bank_batch_type_options = load_bank_batch_type_options()
                mappings = load_mappings("bank")
                saved_count = 0
                cleared_count = 0

                for row in rows:
                    row_id = str(row.get("row_id", "")).strip()
                    values = row.get("values", {})
                    if not row_id:
                        continue
                    if not isinstance(values, dict):
                        values = {}

                    if row_id not in bank_batch_type_options:
                        continue

                    bank_name = str(values.get("bank_name", "")).strip()

                    if bank_name:
                        mappings[row_id] = {
                            "bank_name": bank_name
                        }
                        saved_count += 1
                    else:
                        if row_id in mappings:
                            del mappings[row_id]
                        cleared_count += 1

                save_mappings("bank", mappings)
                print json.dumps({
                    "success": True,
                    "message": "Saved {0} row(s), cleared {1} row(s)".format(saved_count, cleared_count)
                })
            else:
                cfg = load_config(map_type)
                columns = cfg.get("columns", DEFAULT_COLUMNS)
                mappings = load_mappings(map_type)

                saved_count = 0
                cleared_count = 0

                for row in rows:
                    row_id = str(row.get("row_id", "")).strip()
                    if map_type == "merchant":
                        row_id = MERCHANT_FEE_FUND_ID

                    values = row.get("values", {})
                    if not row_id:
                        continue
                    if not isinstance(values, dict):
                        values = {}

                    entry = {}
                    has_any_value = False

                    for col in columns:
                        key = col["key"]
                        val = str(values.get(key, "")).strip()
                        entry[key] = val
                        if val:
                            has_any_value = True

                    if has_any_value:
                        mappings[row_id] = entry
                        saved_count += 1
                    else:
                        if row_id in mappings:
                            del mappings[row_id]
                        cleared_count += 1

                save_mappings(map_type, mappings)

                print json.dumps({
                    "success": True,
                    "message": "Saved {0} row(s), cleared {1} row(s)".format(saved_count, cleared_count)
                })
        except Exception as e:
            print json.dumps({"success": False, "message": str(e)})

elif action == "delete_mapping":
    row_id = str(Data.row_id).strip() if hasattr(Data, "row_id") else ""
    if map_type == "merchant":
        row_id = MERCHANT_FEE_FUND_ID

    if not row_id:
        print json.dumps({"success": False, "message": "Row ID is required"})
    else:
        mappings = load_mappings(map_type)
        if row_id in mappings:
            del mappings[row_id]
            save_mappings(map_type, mappings)
            if map_type == "account":
                print json.dumps({"success": True, "message": "Deleted mapping for Account Code " + row_id})
            elif map_type == "bank":
                print json.dumps({"success": True, "message": "Cleared bank mapping"})
            elif map_type == "merchant":
                print json.dumps({"success": True, "message": "Cleared Merchant Fees mapping"})
            else:
                print json.dumps({"success": True, "message": "Deleted mapping for FundId " + row_id})
        else:
            if map_type == "account":
                print json.dumps({"success": True, "message": "No saved mapping existed for Account Code " + row_id})
            elif map_type == "bank":
                print json.dumps({"success": True, "message": "No saved bank mapping existed"})
            elif map_type == "merchant":
                print json.dumps({"success": True, "message": "No saved Merchant Fees mapping existed"})
            else:
                print json.dumps({"success": True, "message": "No saved mapping existed for FundId " + row_id})

elif action == "import_mappings":
    raw = str(Data.mappings_json) if hasattr(Data, "mappings_json") else ""
    if not raw:
        print json.dumps({"success": False, "message": "No data"})
    else:
        try:
            new_mappings = json.loads(raw)
            if not isinstance(new_mappings, dict):
                raise Exception("JSON must be an object with row IDs as keys")

            if map_type == "bank":
                bank_batch_type_options = load_bank_batch_type_options()
                cleaned = {}
                for batch_type in bank_batch_type_options:
                    item = new_mappings.get(batch_type, {})
                    if isinstance(item, dict):
                        bank_name = str(item.get("bank_name", "")).strip()
                        if bank_name:
                            cleaned[batch_type] = {"bank_name": bank_name}
                save_mappings("bank", cleaned)
                print json.dumps({"success": True, "message": "Imported {0} bank mappings".format(len(cleaned))})
            elif map_type == "merchant":
                item = new_mappings.get(MERCHANT_FEE_FUND_ID, {})
                cleaned = {}
                if isinstance(item, dict):
                    entry = {}
                    has_any_value = False
                    for col in DEFAULT_COLUMNS:
                        key = col["key"]
                        val = str(item.get(key, "")).strip()
                        entry[key] = val
                        if val:
                            has_any_value = True
                    if has_any_value:
                        cleaned[MERCHANT_FEE_FUND_ID] = entry
                save_mappings("merchant", cleaned)
                print json.dumps({"success": True, "message": "Imported Merchant Fees mapping"})
            else:
                save_mappings(map_type, new_mappings)
                print json.dumps({"success": True, "message": "Imported {0} mappings".format(len(new_mappings))})
        except Exception as e:
            print json.dumps({"success": False, "message": str(e)})

else:
    model.Header = "QuickBooks Account Translations v" + SCRIPT_VERSION

    model.Form = '''
    <div class="qat-shell">
        <style>
            .qat-shell {
                max-width:1500px;
                margin:20px auto;
                font-family:Segoe UI, Arial, sans-serif;
                color:#333;
            }

            .qat-card {
                background:#fff;
                border:1px solid #ddd;
                border-radius:0 0 8px 8px;
                border-top:none;
                padding:22px 24px 24px 24px;
                box-shadow:0 1px 2px rgba(0,0,0,0.04);
            }

            .qat-title-row {
                display:flex;
                justify-content:space-between;
                align-items:flex-start;
                gap:12px;
                margin-bottom:14px;
                flex-wrap:wrap;
            }

            .qat-tool-title h3 {
                margin:0;
                font-size:24px;
                line-height:1.25;
            }

            .qat-tool-title p {
                margin:6px 0 0 0;
                color:#666;
                font-size:14px;
            }

            .qat-version {
                margin-top:6px;
                font-size:12px;
                color:#888;
            }

            .qat-tabs {
                display:flex;
                gap:0;
                border-bottom:1px solid #ccc;
                margin:0;
                padding:0;
                flex-wrap:wrap;
            }

            .qat-tab {
                border:1px solid #ccc;
                border-bottom:none;
                background:#f5f5f5;
                padding:12px 22px;
                font-size:15px;
                font-weight:600;
                color:#333;
                cursor:pointer;
                margin-right:4px;
                border-radius:8px 8px 0 0;
                text-decoration:none;
                position:relative;
                top:1px;
            }

            .qat-tab:hover {
                background:#e9ecef;
                color:#333;
                text-decoration:none;
            }

            .qat-tab-active {
                background:#fff;
                color:#337ab7;
                border-top:3px solid #337ab7;
                padding-top:10px;
                z-index:2;
            }

            .qat-actionbar {
                display:flex;
                gap:8px;
                flex-wrap:wrap;
                margin:16px 0 18px 0;
            }

            .fe-btn {
                padding:8px 18px;
                border:none;
                border-radius:5px;
                cursor:pointer;
                font-size:13px;
                font-weight:600;
            }

            .fe-btn-primary { background:#337ab7;color:#fff; }
            .fe-btn-success { background:#28a745;color:#fff; }
            .fe-btn-danger { background:#dc3545;color:#fff; }
            .fe-btn-warning { background:#ffc107;color:#333; }
            .fe-btn-secondary { background:#6c757d;color:#fff; }

            .fe-btn:hover {
                filter:brightness(0.96);
            }

            .fe-input {
                padding:7px 9px;
                border:1px solid #ccc;
                border-radius:4px;
                box-sizing:border-box;
                width:100%;
                min-width:140px;
                font-size:13px;
            }

            .fe-toolbar {
                display:flex;
                gap:12px;
                align-items:center;
                flex-wrap:wrap;
                margin-bottom:14px;
            }

            .fe-row-unmapped { background:#fffdf2; }
            .fe-row-mapped { background:#f8fff8; }
            .fe-row-changed { outline:2px solid #cfe2ff; outline-offset:-2px; }

            .fe-sticky-wrap {
                overflow:auto;
                border:1px solid #dee2e6;
                border-radius:8px;
            }

            .fe-table {
                width:100%;
                border-collapse:collapse;
                min-width:1100px;
            }

            .fe-table th,
            .fe-table td {
                border-bottom:1px solid #e9ecef;
                padding:8px;
                vertical-align:top;
                font-size:13px;
            }

            .fe-table th {
                background:#f5f5f5;
                position:sticky;
                top:0;
                z-index:2;
                text-align:left;
                font-weight:700;
            }

            .fe-table th.fe-sortable {
                cursor:pointer;
                user-select:none;
            }

            .fe-table th.fe-sortable:hover {
                background:#ebebeb;
            }

            .fe-save-msg {
                font-size:12px;
                margin-top:4px;
                min-height:14px;
            }

            .fe-pill {
                display:inline-block;
                padding:2px 8px;
                border-radius:999px;
                font-size:11px;
                font-weight:600;
            }

            .fe-pill-mapped { background:#d4edda;color:#155724; }
            .fe-pill-unmapped { background:#fff3cd;color:#856404; }
            .fe-pill-changed { background:#cfe2ff;color:#084298; }

            .fe-sort-ind {
                color:#666;
                font-size:11px;
                margin-left:6px;
            }

            .fe-warning-box {
                background:#fff3cd;
                border:1px solid #ffe69c;
                color:#856404;
                padding:10px 12px;
                border-radius:6px;
                margin-bottom:12px;
                display:none;
            }

            .fe-inline-tools {
                display:flex;
                gap:12px;
                align-items:flex-end;
                flex-wrap:wrap;
                margin-bottom:16px;
                padding:14px;
                background:#f8f9fa;
                border:1px solid #e5e5e5;
                border-radius:8px;
            }

            .merchant-note {
                display:none;
                background:#eef6ff;
                border:1px solid #cfe2ff;
                color:#084298;
                padding:10px 12px;
                border-radius:6px;
                margin-bottom:14px;
                font-size:13px;
            }

            #topMessage {
                margin-bottom:10px;
                font-size:13px;
                min-height:18px;
            }

            #loading {
                color:#666;
                padding:20px;
                text-align:center;
            }
        </style>

        <div class="qat-tabs" role="tablist" aria-label="QuickBooks Account Translation Tabs">
            <button id="tab_fund" class="qat-tab qat-tab-active" onclick="switchTab('fund')" type="button">
                FundId Mapping Grid
            </button>
            <button id="tab_account" class="qat-tab" onclick="switchTab('account')" type="button">
                Account Code Mapping Grid
            </button>
            <button id="tab_bank" class="qat-tab" onclick="switchTab('bank')" type="button">
                Bank Code Mapping Grid
            </button>
            <button id="tab_merchant" class="qat-tab" onclick="switchTab('merchant')" type="button">
                Merchant Fees Mapping Grid
            </button>
        </div>

        <div class="qat-card">
            <div class="qat-title-row">
                <div class="qat-tool-title">
                    <h3 id="pageTitle">FundId Mapping Grid</h3>
                    <p id="pageDesc">
                        Shows all open funds. Existing mappings are prefilled. Unmapped rows appear blank and can be updated directly.
                    </p>
                    <div class="qat-version">
                        Version ''' + SCRIPT_VERSION + ''' &mdash; Updated ''' + SCRIPT_LAST_UPDATED + '''
                    </div>
                </div>
            </div>

            <div class="qat-actionbar">
                <button onclick="loadGrid(currentTab)" class="fe-btn fe-btn-warning" type="button">Refresh</button>
                <button onclick="saveAllChanged()" class="fe-btn fe-btn-success" type="button">Save All Changed Rows</button>
                <button onclick="exportMappingsJson()" class="fe-btn fe-btn-secondary" type="button">Export JSON</button>
                <button onclick="showImportForm()" class="fe-btn fe-btn-secondary" type="button">Import JSON</button>
            </div>

            <div id="warningBox" class="fe-warning-box"></div>

            <div id="merchantNote" class="merchant-note">
                This tab controls the special Merchant Fees mapping for FundID <strong>6050</strong>.
                The QBO export should use this mapping when it creates the merchant fee line.
            </div>

            <div id="bankBatchTypeTools" class="fe-inline-tools" style="display:none">
                <div>
                    <label style="font-weight:600;font-size:13px">Add Batch Type</label><br>
                    <input type="text" id="newBankBatchType" class="fe-input" style="width:260px" placeholder="Enter new Batch Type">
                </div>
                <div>
                    <button onclick="addBankBatchType()" class="fe-btn fe-btn-primary" type="button">Add Batch Type</button>
                </div>
                <div>
                    <label style="font-weight:600;font-size:13px">Delete Batch Type</label><br>
                    <select id="deleteBankBatchTypeSelect" class="fe-input" style="width:260px"></select>
                </div>
                <div>
                    <button onclick="deleteBankBatchType()" class="fe-btn fe-btn-danger" type="button">Delete Selected Batch Type</button>
                </div>
            </div>

            <div class="fe-toolbar">
                <div>
                    <label style="font-weight:600;font-size:13px">Search</label><br>
                    <input type="text" id="filterText" class="fe-input" style="width:320px"
                           placeholder="Filter current tab"
                           onkeyup="applyFilters()">
                </div>
                <div style="padding-top:18px">
                    <label style="font-size:13px">
                        <input type="checkbox" id="toggleUnmappedOnly" onchange="applyFilters()">
                        Show Unmapped Only
                    </label>
                </div>
                <div style="padding-top:18px">
                    <label style="font-size:13px">
                        <input type="checkbox" id="toggleChangedOnly" onchange="applyFilters()">
                        Show Changed Only
                    </label>
                </div>
                <div id="summaryCounts" style="padding-top:18px;font-size:13px;color:#666"></div>
            </div>

            <div id="importForm" style="display:none;background:#f8f9fa;padding:16px;border-radius:8px;border:1px solid #dee2e6;margin-bottom:16px">
                <label id="importLabel" style="font-weight:600">Paste JSON mappings:</label>
                <textarea id="importJson" rows="10" style="width:100%;font-family:monospace;font-size:12px;margin-top:6px;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box"></textarea>
                <div style="margin-top:8px">
                    <button onclick="doImport()" class="fe-btn fe-btn-success" type="button">Import (Replace All)</button>
                    <button onclick="document.getElementById('importForm').style.display='none'" class="fe-btn fe-btn-danger" style="margin-left:4px" type="button">Cancel</button>
                </div>
            </div>

            <div id="topMessage"></div>

            <div id="loading">Loading...</div>

            <div id="gridWrap" class="fe-sticky-wrap" style="display:none">
                <table class="fe-table">
                    <thead id="gridHead"></thead>
                    <tbody id="gridBody"></tbody>
                </table>
            </div>
        </div>
    </div>
    '''

    model.Script = '''
    var scriptName = window.location.pathname.split("/").pop().split("?")[0];
    var scriptVersion = "";
    var currentTab = "fund";
    var bankBatchTypeOptions = ["Online","Loose Cash","Loose Checks","Stock"];

    var tabState = {
        fund: {
            columns: [],
            rows: [],
            originalRowValues: {},
            changedRows: {},
            currentSort: { field: "name_value", direction: "asc", type: "base" },
            warning: "",
            loaded: false
        },
        account: {
            columns: [],
            rows: [],
            originalRowValues: {},
            changedRows: {},
            currentSort: { field: "id_value", direction: "asc", type: "base" },
            warning: "",
            loaded: false
        },
        bank: {
            columns: [],
            rows: [],
            originalRowValues: {},
            changedRows: {},
            currentSort: { field: "id_value", direction: "asc", type: "base" },
            warning: "",
            loaded: false
        },
        merchant: {
            columns: [],
            rows: [],
            originalRowValues: {},
            changedRows: {},
            currentSort: { field: "id_value", direction: "asc", type: "base" },
            warning: "",
            loaded: false
        }
    };

    function getInitialTabFromHash() {
        var h = String(window.location.hash || "").replace("#", "").toLowerCase();
        if (h === "fund" || h === "account" || h === "bank" || h === "merchant") return h;
        return "fund";
    }

    function setHashForTab(tabName) {
        if (window.history && window.history.replaceState) {
            window.history.replaceState(null, "", "#" + tabName);
        } else {
            window.location.hash = tabName;
        }
    }

    function getCurrentState() {
        return tabState[currentTab];
    }

    function postData(data, callback) {
        $.ajax({
            url: "/PyScriptForm/" + scriptName,
            type: "POST",
            data: data,
            success: function(resp) {
                try {
                    callback(JSON.parse(resp));
                } catch (e) {
                    console.error("Parse error:", e, resp.substring(0, 300));
                    alert("Could not parse server response.");
                }
            },
            error: function(x) {
                console.error("Request failed:", x.status, x.responseText);
                alert("Request failed: " + x.status);
            }
        });
    }

    function esc(s) {
        var d = document.createElement("div");
        d.appendChild(document.createTextNode(s || ""));
        return d.innerHTML;
    }

    function deepClone(obj) {
        return JSON.parse(JSON.stringify(obj || {}));
    }

    function setTopMessage(html) {
        document.getElementById("topMessage").innerHTML = html || "";
    }

    function refreshBankBatchTypeDeleteOptions() {
        var sel = document.getElementById("deleteBankBatchTypeSelect");
        if (!sel) return;

        var html = "";
        for (var i = 0; i < bankBatchTypeOptions.length; i++) {
            html += '<option value="' + esc(bankBatchTypeOptions[i]) + '">' + esc(bankBatchTypeOptions[i]) + '</option>';
        }
        sel.innerHTML = html;
    }

    function updateSpecialToolVisibility() {
        var bankTools = document.getElementById("bankBatchTypeTools");
        var merchantNote = document.getElementById("merchantNote");

        if (bankTools) {
            bankTools.style.display = currentTab === "bank" ? "flex" : "none";
            if (currentTab === "bank") {
                refreshBankBatchTypeDeleteOptions();
            }
        }

        if (merchantNote) {
            merchantNote.style.display = currentTab === "merchant" ? "block" : "none";
        }
    }

    function addBankBatchType() {
        var el = document.getElementById("newBankBatchType");
        var val = el ? (el.value || "").trim() : "";

        if (!val) {
            alert("Enter a Batch Type to add.");
            return;
        }

        postData({
            action: "add_bank_batch_type",
            map_type: "bank",
            batch_type_name: val
        }, function(d) {
            if (d.success) {
                bankBatchTypeOptions = d.batch_type_options || bankBatchTypeOptions;
                if (el) el.value = "";
                setTopMessage("<span style=\\"color:green\\">" + esc(d.message || "Added") + "</span>");
                refreshBankBatchTypeDeleteOptions();
                loadGrid("bank");
            } else {
                setTopMessage("<span style=\\"color:red\\">" + esc(d.message || "Unable to add Batch Type") + "</span>");
            }
        });
    }

    function deleteBankBatchType() {
        var sel = document.getElementById("deleteBankBatchTypeSelect");
        var val = sel ? (sel.value || "").trim() : "";

        if (!val) {
            alert("Select a Batch Type to delete.");
            return;
        }

        if (!confirm("Delete Batch Type '" + val + "'? Any saved bank mapping for this Batch Type will also be removed.")) {
            return;
        }

        postData({
            action: "delete_bank_batch_type",
            map_type: "bank",
            batch_type_name: val
        }, function(d) {
            if (d.success) {
                bankBatchTypeOptions = d.batch_type_options || bankBatchTypeOptions;
                setTopMessage("<span style=\\"color:green\\">" + esc(d.message || "Deleted") + "</span>");
                refreshBankBatchTypeDeleteOptions();
                loadGrid("bank");
            } else {
                setTopMessage("<span style=\\"color:red\\">" + esc(d.message || "Unable to delete Batch Type") + "</span>");
            }
        });
    }

    function updateWarningBox() {
        var box = document.getElementById("warningBox");
        var st = getCurrentState();
        if (st.warning) {
            box.style.display = "block";
            box.innerHTML = "<strong>Warning:</strong> " + esc(st.warning);
        } else {
            box.style.display = "none";
            box.innerHTML = "";
        }
    }

    function updateTabHeaders() {
        var title = document.getElementById("pageTitle");
        var desc = document.getElementById("pageDesc");
        var importLabel = document.getElementById("importLabel");
        var filter = document.getElementById("filterText");

        if (currentTab === "fund") {
            title.innerHTML = "FundId Mapping Grid";
            desc.innerHTML = "Shows all open funds. Existing mappings are prefilled. Unmapped rows appear blank and can be updated directly.";
            importLabel.innerHTML = "Paste JSON mappings (FundId keys):";
            filter.placeholder = "Filter by FundId or Fund Name";
        } else if (currentTab === "account") {
            title.innerHTML = "Account Code Mapping Grid";
            desc.innerHTML = "Shows all AccountCode values from the AccountCode object. Existing mappings are prefilled. Unmapped rows appear blank and can be updated directly.";
            importLabel.innerHTML = "Paste JSON mappings (Account Code keys):";
            filter.placeholder = "Filter by Account Code or Description";
        } else if (currentTab === "bank") {
            title.innerHTML = "Bank Code Mapping Grid";
            desc.innerHTML = "One row per Batch Type. Enter the Bank Name for each Batch Type as needed. Batch Types can be managed directly from this tab.";
            importLabel.innerHTML = "Paste JSON mappings (Batch Type keys):";
            filter.placeholder = "Filter by Batch Type or Bank Name";
        } else {
            title.innerHTML = "Merchant Fees Mapping Grid";
            desc.innerHTML = "Special mapping for FundID 6050 Merchant Fees. This maps merchant fee lines into the correct QBO Account and Class.";
            importLabel.innerHTML = "Paste JSON mappings (FundID 6050 key):";
            filter.placeholder = "Filter by FundId, Fund Name, Account, or Class";
        }

        document.getElementById("tab_fund").className = currentTab === "fund" ? "qat-tab qat-tab-active" : "qat-tab";
        document.getElementById("tab_account").className = currentTab === "account" ? "qat-tab qat-tab-active" : "qat-tab";
        document.getElementById("tab_bank").className = currentTab === "bank" ? "qat-tab qat-tab-active" : "qat-tab";
        document.getElementById("tab_merchant").className = currentTab === "merchant" ? "qat-tab qat-tab-active" : "qat-tab";

        updateWarningBox();
        updateSpecialToolVisibility();
    }

    function resetFiltersForTab() {
        var filter = document.getElementById("filterText");
        var unmapped = document.getElementById("toggleUnmappedOnly");
        var changed = document.getElementById("toggleChangedOnly");

        if (filter) filter.value = "";
        if (unmapped) unmapped.checked = false;
        if (changed) changed.checked = false;
    }

    function switchTab(tabName) {
        if (tabName !== "fund" && tabName !== "account" && tabName !== "bank" && tabName !== "merchant") return;

        currentTab = tabName;
        setHashForTab(tabName);

        document.getElementById("importForm").style.display = "none";
        setTopMessage("");
        resetFiltersForTab();
        updateTabHeaders();
        loadGrid(currentTab);
    }

    function loadGrid(mapType) {
        var st = tabState[mapType];

        document.getElementById("loading").style.display = "block";
        document.getElementById("gridWrap").style.display = "none";
        setTopMessage("");
        st.warning = "";
        updateWarningBox();

        postData({ action: "get_grid", map_type: mapType }, function(d) {
            document.getElementById("loading").style.display = "none";
            if (!d.success) {
                alert(d.message || "Unable to load grid.");
                return;
            }

            scriptVersion = d.version || "";
            st.columns = d.columns || [];
            st.rows = d.rows || [];
            st.originalRowValues = {};
            st.changedRows = {};
            st.warning = d.warning || "";
            st.loaded = true;

            if (d.batch_type_options && d.batch_type_options.length >= 0) {
                bankBatchTypeOptions = d.batch_type_options;
                refreshBankBatchTypeDeleteOptions();
            }

            for (var i = 0; i < st.rows.length; i++) {
                if (mapType === "bank") {
                    st.originalRowValues[String(st.rows[i].row_id)] = {
                        bank_name: st.rows[i].name_value || ""
                    };
                } else {
                    st.originalRowValues[String(st.rows[i].row_id)] = deepClone(st.rows[i].mapped_values || {});
                }
            }

            sortRows(mapType);
            renderGrid();
            document.getElementById("gridWrap").style.display = "block";
            updateWarningBox();
            updateSpecialToolVisibility();
            applyFilters();
        });
    }

    function buildSortIndicator(field, type) {
        var st = getCurrentState();
        if (st.currentSort.field !== field || st.currentSort.type !== type) {
            return '<span class="fe-sort-ind">↕</span>';
        }
        return st.currentSort.direction === "asc"
            ? '<span class="fe-sort-ind">▲</span>'
            : '<span class="fe-sort-ind">▼</span>';
    }

    function compareNatural(a, b) {
        a = String(a || "");
        b = String(b || "");
        a = a.toLowerCase();
        b = b.toLowerCase();
        if (a < b) return -1;
        if (a > b) return 1;
        return 0;
    }

    function sortRows(mapType) {
        var st = tabState[mapType];
        st.rows.sort(function(a, b) {
            var av = a[st.currentSort.field] || "";
            var bv = b[st.currentSort.field] || "";
            var cmp = compareNatural(av, bv);
            if (cmp === 0) {
                cmp = compareNatural(a.name_value || "", b.name_value || "");
            }
            if (cmp === 0) {
                cmp = compareNatural(a.row_id || "", b.row_id || "");
            }
            return st.currentSort.direction === "asc" ? cmp : -cmp;
        });
    }

    function toggleSort(field, type) {
        var st = getCurrentState();

        if (st.currentSort.field === field && st.currentSort.type === type) {
            st.currentSort.direction = st.currentSort.direction === "asc" ? "desc" : "asc";
        } else {
            st.currentSort.field = field;
            st.currentSort.type = type;
            st.currentSort.direction = "asc";
        }

        sortRows(currentTab);
        renderGrid();
        applyFilters();
    }

    function encodeId(s) {
        return String(s).replace(/[^A-Za-z0-9_\\-]/g, "_");
    }

    function jsArg(s) {
        return String(s).replace(/\\\\/g, "\\\\\\\\").replace(/'/g, "\\\\'").replace(/"/g, "&quot;");
    }

    function renderGrid() {
        var st = getCurrentState();

        if (currentTab === "bank") {
            renderBankGrid();
            return;
        }

        var nameHeader = (st.rows[0] && st.rows[0].name_label) ? st.rows[0].name_label : "Name";
        if (!nameHeader) nameHeader = "&nbsp;";

        var idHeader = (st.rows[0] && st.rows[0].id_label) ? st.rows[0].id_label : "ID";

        var headHtml = "<tr>"
            + "<th class=\\"fe-sortable\\" style=\\"min-width:110px\\" onclick=\\"toggleSort('id_value','base')\\">" + esc(idHeader) + buildSortIndicator("id_value", "base") + "</th>"
            + "<th class=\\"fe-sortable\\" style=\\"min-width:320px\\" onclick=\\"toggleSort('name_value','base')\\">" + nameHeader + buildSortIndicator("name_value", "base") + "</th>";

        for (var c = 0; c < st.columns.length; c++) {
            headHtml += "<th>" + esc(st.columns[c].label) + "</th>";
        }

        headHtml += "<th style=\\"min-width:170px\\">Actions</th></tr>";
        document.getElementById("gridHead").innerHTML = headHtml;

        var bodyHtml = "";
        for (var i = 0; i < st.rows.length; i++) {
            var r = st.rows[i];
            var rowClass = r.has_mapping ? "fe-row-mapped" : "fe-row-unmapped";
            if (st.changedRows[String(r.row_id)]) rowClass += " fe-row-changed";

            var domId = encodeId(r.row_id);
            var safeRowId = jsArg(r.row_id);

            bodyHtml += "<tr class=\\"" + rowClass + "\\" id=\\"row_" + domId + "\\">";
            bodyHtml += "<td id=\\"status_" + domId + "\\">" + buildStatusCellHtml(r) + "</td>";
            bodyHtml += "<td>" + esc(r.name_value) + "</td>";

            for (var c2 = 0; c2 < st.columns.length; c2++) {
                var col = st.columns[c2];
                var val = (r.mapped_values && r.mapped_values[col.key]) ? r.mapped_values[col.key] : "";
                bodyHtml += "<td><input type=\\"text\\" id=\\"cell_" + domId + "_" + esc(col.key) + "\\" value=\\"" + esc(val) + "\\" class=\\"fe-input\\" oninput=\\"markRowChanged('" + safeRowId + "')\\"></td>";
            }

            bodyHtml += "<td>"
                + "<button onclick=\\"saveRow('" + safeRowId + "')\\" class=\\"fe-btn fe-btn-success\\" style=\\"padding:4px 10px;margin-right:4px\\" type=\\"button\\">Save</button>"
                + "<button onclick=\\"clearRow('" + safeRowId + "')\\" class=\\"fe-btn fe-btn-danger\\" style=\\"padding:4px 10px\\" type=\\"button\\">Clear</button>"
                + "<div id=\\"msg_" + domId + "\\" class=\\"fe-save-msg\\"></div>"
                + "</td>";

            bodyHtml += "</tr>";
        }

        if (st.rows.length === 0) {
            bodyHtml = "<tr><td colspan=\\"" + (st.columns.length + 3) + "\\" style=\\"text-align:center;color:#999;padding:20px\\">No rows found.</td></tr>";
        }

        document.getElementById("gridBody").innerHTML = bodyHtml;
    }

    function renderBankGrid() {
        var st = getCurrentState();

        var headHtml = "<tr>"
            + "<th class=\\"fe-sortable\\" style=\\"min-width:220px\\" onclick=\\"toggleSort('id_value','base')\\">Batch Type" + buildSortIndicator("id_value", "base") + "</th>"
            + "<th class=\\"fe-sortable\\" style=\\"min-width:320px\\" onclick=\\"toggleSort('name_value','base')\\">Bank Name" + buildSortIndicator("name_value", "base") + "</th>"
            + "<th style=\\"min-width:170px\\">Actions</th>"
            + "</tr>";
        document.getElementById("gridHead").innerHTML = headHtml;

        var bodyHtml = "";
        for (var i = 0; i < st.rows.length; i++) {
            var r = st.rows[i];
            var domId = encodeId(r.row_id);
            var safeRowId = jsArg(r.row_id);
            var rowClass = r.has_mapping ? "fe-row-mapped" : "fe-row-unmapped";
            if (st.changedRows[String(r.row_id)]) rowClass += " fe-row-changed";

            bodyHtml += "<tr class=\\"" + rowClass + "\\" id=\\"row_" + domId + "\\">";
            bodyHtml += "<td id=\\"status_" + domId + "\\">" + buildStatusCellHtml(r) + "</td>";
            bodyHtml += "<td>"
                + "<input type=\\"text\\" id=\\"bank_name_" + domId + "\\" class=\\"fe-input\\" value=\\"" + esc(r.name_value || "") + "\\" oninput=\\"markBankRowChanged('" + safeRowId + "')\\">"
                + "</td>";
            bodyHtml += "<td>"
                + "<button onclick=\\"saveRow('" + safeRowId + "')\\" class=\\"fe-btn fe-btn-success\\" style=\\"padding:4px 10px;margin-right:4px\\" type=\\"button\\">Save</button>"
                + "<button onclick=\\"clearBankRow('" + safeRowId + "')\\" class=\\"fe-btn fe-btn-danger\\" style=\\"padding:4px 10px\\" type=\\"button\\">Clear</button>"
                + "<div id=\\"msg_" + domId + "\\" class=\\"fe-save-msg\\"></div>"
                + "</td>";
            bodyHtml += "</tr>";
        }

        if (st.rows.length === 0) {
            bodyHtml = "<tr><td colspan=\\"3\\" style=\\"text-align:center;color:#999;padding:20px\\">No Bank Batch Types found.</td></tr>";
        }

        document.getElementById("gridBody").innerHTML = bodyHtml;
    }

    function buildStatusCellHtml(row) {
        var parts = [];
        parts.push("<strong>" + esc(row.id_value) + "</strong>");
        parts.push("<div style=\\"margin-top:4px\\">");
        if (row.has_mapping) parts.push("<span class=\\"fe-pill fe-pill-mapped\\">Mapped</span>");
        else parts.push("<span class=\\"fe-pill fe-pill-unmapped\\">Unmapped</span>");
        if (getCurrentState().changedRows[String(row.row_id)]) parts.push(" <span class=\\"fe-pill fe-pill-changed\\">Changed</span>");
        parts.push("</div>");
        if (currentTab === "merchant" && row.status_value) {
            parts.push("<div style=\\"margin-top:6px;color:#666;font-size:12px\\">" + esc(row.status_value) + "</div>");
        }
        return parts.join("");
    }

    function getRowById(rowId) {
        var st = getCurrentState();
        for (var i = 0; i < st.rows.length; i++) {
            if (String(st.rows[i].row_id) === String(rowId)) return st.rows[i];
        }
        return null;
    }

    function getRowValues(rowId) {
        if (currentTab === "bank") {
            return getBankRowValues(rowId);
        }

        var st = getCurrentState();
        var data = {};
        var domId = encodeId(rowId);
        for (var c = 0; c < st.columns.length; c++) {
            var col = st.columns[c];
            var el = document.getElementById("cell_" + domId + "_" + col.key);
            data[col.key] = el ? el.value.trim() : "";
        }
        return data;
    }

    function getBankRowValues(rowId) {
        var domId = encodeId(rowId);
        var bankEl = document.getElementById("bank_name_" + domId);
        return {
            bank_name: bankEl ? bankEl.value.trim() : ""
        };
    }

    function valuesEqual(a, b) {
        if (currentTab === "bank") {
            return String((a || {}).bank_name || "") === String((b || {}).bank_name || "");
        }

        var st = getCurrentState();
        a = a || {};
        b = b || {};
        for (var c = 0; c < st.columns.length; c++) {
            var key = st.columns[c].key;
            if (String(a[key] || "") !== String(b[key] || "")) return false;
        }
        return true;
    }

    function hasAnyValue(values) {
        if (currentTab === "bank") {
            return !!String((values || {}).bank_name || "").trim();
        }

        var st = getCurrentState();
        for (var c = 0; c < st.columns.length; c++) {
            var key = st.columns[c].key;
            if (String(values[key] || "").trim()) return true;
        }
        return false;
    }

    function setRowMessage(rowId, html) {
        var el = document.getElementById("msg_" + encodeId(rowId));
        if (el) el.innerHTML = html || "";
    }

    function refreshRowVisuals(rowId) {
        var st = getCurrentState();
        var rowObj = getRowById(rowId);
        var domId = encodeId(rowId);
        var rowEl = document.getElementById("row_" + domId);
        var statusEl = document.getElementById("status_" + domId);

        if (!rowObj || !rowEl) return;

        rowEl.className = rowObj.has_mapping ? "fe-row-mapped" : "fe-row-unmapped";
        if (st.changedRows[String(rowId)]) {
            rowEl.className += " fe-row-changed";
        }

        if (statusEl) {
            statusEl.innerHTML = buildStatusCellHtml(rowObj);
        }
    }

    function updateSummaryCounts() {
        var st = getCurrentState();
        var total = st.rows.length;
        var mapped = 0;
        var unmapped = 0;
        var changed = 0;
        var visible = 0;

        for (var i = 0; i < st.rows.length; i++) {
            var r = st.rows[i];
            if (r.has_mapping) mapped++;
            else unmapped++;
            if (st.changedRows[String(r.row_id)]) changed++;

            var rowEl = document.getElementById("row_" + encodeId(r.row_id));
            if (rowEl && rowEl.style.display !== "none") visible++;
        }

        document.getElementById("summaryCounts").innerHTML =
            "Visible: <b>" + visible + "</b> &nbsp; " +
            "Total: <b>" + total + "</b> &nbsp; " +
            "Mapped: <b>" + mapped + "</b> &nbsp; " +
            "Unmapped: <b>" + unmapped + "</b> &nbsp; " +
            "Changed: <b>" + changed + "</b>";
    }

    function applyFilters() {
        var st = getCurrentState();
        var txt = (document.getElementById("filterText").value || "").toLowerCase().trim();
        var unmappedOnly = document.getElementById("toggleUnmappedOnly").checked;
        var changedOnly = document.getElementById("toggleChangedOnly").checked;

        for (var i = 0; i < st.rows.length; i++) {
            var r = st.rows[i];
            var rowEl = document.getElementById("row_" + encodeId(r.row_id));
            if (!rowEl) continue;

            var hay = (String(r.id_value || "") + " " + String(r.name_value || "") + " " + String(r.status_value || "")).toLowerCase();

            if (currentTab !== "bank") {
                for (var c = 0; c < st.columns.length; c++) {
                    var key = st.columns[c].key;
                    hay += " " + String((r.mapped_values || {})[key] || "").toLowerCase();
                }
            }

            var matchesText = !txt || hay.indexOf(txt) >= 0;
            var matchesUnmapped = !unmappedOnly || !r.has_mapping;
            var matchesChanged = !changedOnly || !!st.changedRows[String(r.row_id)];

            rowEl.style.display = (matchesText && matchesUnmapped && matchesChanged) ? "" : "none";
        }

        updateSummaryCounts();
    }

    function markRowChanged(rowId) {
        if (currentTab === "bank") {
            markBankRowChanged(rowId);
            return;
        }

        var st = getCurrentState();
        var current = getRowValues(rowId);
        var row = getRowById(rowId);
        if (row) {
            row.mapped_values = deepClone(current);
            row.has_mapping = hasAnyValue(current);
        }

        var original = st.originalRowValues[String(rowId)] || {};
        if (valuesEqual(current, original)) delete st.changedRows[String(rowId)];
        else st.changedRows[String(rowId)] = true;

        refreshRowVisuals(rowId);
        applyFilters();
    }

    function markBankRowChanged(rowId) {
        var st = getCurrentState();
        var current = getBankRowValues(rowId);
        var row = getRowById(rowId);

        if (row) {
            row.name_value = current.bank_name;
            row.has_mapping = hasAnyValue(current);
        }

        var original = st.originalRowValues[String(rowId)] || { bank_name: "" };
        if (valuesEqual(current, original)) {
            delete st.changedRows[String(rowId)];
        } else {
            st.changedRows[String(rowId)] = true;
        }

        refreshRowVisuals(rowId);
        applyFilters();
    }

    function updateCachedRowAfterSave(rowId, values) {
        var st = getCurrentState();
        var row = getRowById(rowId);
        if (!row) return;

        if (currentTab === "bank") {
            row.name_value = values.bank_name || "";
            row.has_mapping = hasAnyValue(values);
            st.originalRowValues[String(rowId)] = deepClone(values);
        } else {
            row.mapped_values = deepClone(values);
            row.has_mapping = hasAnyValue(values);
            st.originalRowValues[String(rowId)] = deepClone(values);
        }

        delete st.changedRows[String(rowId)];
        refreshRowVisuals(rowId);
    }

    function saveRow(rowId) {
        var values = getRowValues(rowId);
        var data = { action: "save_mapping", map_type: currentTab, row_id: rowId };

        if (currentTab === "bank") {
            data.bank_name = values.bank_name || "";
        } else {
            for (var k in values) {
                if (values.hasOwnProperty(k)) data["col_" + k] = values[k];
            }
        }

        setRowMessage(rowId, "<span style=\\"color:#666\\">Saving...</span>");

        postData(data, function(d) {
            if (d.success) {
                updateCachedRowAfterSave(rowId, values);
                setRowMessage(rowId, "<span style=\\"color:green\\">Saved</span>");
                setTimeout(function(){ setRowMessage(rowId, ""); }, 2000);
                applyFilters();
            } else {
                setRowMessage(rowId, "<span style=\\"color:red\\">" + esc(d.message || "Save failed") + "</span>");
            }
        });
    }

    function clearRow(rowId) {
        if (currentTab === "bank") {
            clearBankRow(rowId);
            return;
        }

        var promptText = currentTab === "fund"
            ? "Clear all mapping fields for FundId " + rowId + "?"
            : currentTab === "account"
                ? "Clear all mapping fields for Account Code " + rowId + "?"
                : "Clear Merchant Fees mapping?";

        if (!confirm(promptText)) return;

        var st = getCurrentState();
        var domId = encodeId(rowId);

        for (var c = 0; c < st.columns.length; c++) {
            var col = st.columns[c];
            var el = document.getElementById("cell_" + domId + "_" + col.key);
            if (el) el.value = "";
        }

        var blankValues = {};
        for (var c2 = 0; c2 < st.columns.length; c2++) blankValues[st.columns[c2].key] = "";

        var row = getRowById(rowId);
        if (row) {
            row.mapped_values = deepClone(blankValues);
            row.has_mapping = false;
        }

        st.changedRows[String(rowId)] = true;
        setRowMessage(rowId, "<span style=\\"color:#666\\">Cleared locally. Save row or Save All to commit.</span>");
        refreshRowVisuals(rowId);
        applyFilters();
    }

    function clearBankRow(rowId) {
        if (!confirm("Clear Bank Name for " + rowId + "?")) return;

        var domId = encodeId(rowId);
        var el = document.getElementById("bank_name_" + domId);
        if (el) el.value = "";

        var st = getCurrentState();
        var row = getRowById(rowId);
        if (row) {
            row.name_value = "";
            row.has_mapping = false;
        }

        st.changedRows[String(rowId)] = true;
        setRowMessage(rowId, "<span style=\\"color:#666\\">Cleared locally. Save row or Save All to commit.</span>");
        refreshRowVisuals(rowId);
        applyFilters();
    }

    function saveAllChanged() {
        var st = getCurrentState();
        var payload = [];

        for (var rowId in st.changedRows) {
            if (st.changedRows.hasOwnProperty(rowId)) {
                payload.push({
                    row_id: rowId,
                    values: getRowValues(rowId)
                });
            }
        }

        if (payload.length === 0) {
            setTopMessage("<span style=\\"color:#666\\">No changed rows to save.</span>");
            return;
        }

        setTopMessage("<span style=\\"color:#666\\">Saving " + payload.length + " changed row(s)...</span>");

        postData({
            action: "save_bulk",
            map_type: currentTab,
            rows_json: JSON.stringify(payload)
        }, function(d) {
            if (d.success) {
                for (var i = 0; i < payload.length; i++) {
                    updateCachedRowAfterSave(payload[i].row_id, payload[i].values);
                    setRowMessage(payload[i].row_id, "<span style=\\"color:green\\">Saved</span>");
                }
                setTopMessage("<span style=\\"color:green\\">" + esc(d.message || "Saved.") + "</span>");
                setTimeout(function(){ setTopMessage(""); }, 2500);
                applyFilters();
            } else {
                setTopMessage("<span style=\\"color:red\\">" + esc(d.message || "Bulk save failed") + "</span>");
            }
        });
    }

    function showImportForm() {
        var st = getCurrentState();
        var exportObj = {};

        if (currentTab === "bank") {
            for (var i = 0; i < st.rows.length; i++) {
                exportObj[String(st.rows[i].row_id)] = {
                    bank_name: st.rows[i].name_value || ""
                };
            }
        } else {
            for (var j = 0; j < st.rows.length; j++) {
                if (st.rows[j].has_mapping) {
                    exportObj[String(st.rows[j].row_id)] = st.rows[j].mapped_values || {};
                }
            }
        }

        document.getElementById("importJson").value = JSON.stringify(exportObj, null, 2);
        document.getElementById("importForm").style.display = "block";
    }

    function doImport() {
        var raw = document.getElementById("importJson").value;
        var confirmText = currentTab === "fund"
            ? "This will REPLACE all saved FundId mappings. Continue?"
            : currentTab === "account"
                ? "This will REPLACE all saved Account Code mappings. Continue?"
                : currentTab === "bank"
                    ? "This will REPLACE all saved Bank Code mappings. Continue?"
                    : "This will REPLACE the saved Merchant Fees mapping. Continue?";

        if (!confirm(confirmText)) return;

        postData({ action: "import_mappings", map_type: currentTab, mappings_json: raw }, function(d) {
            if (d.success) {
                document.getElementById("importForm").style.display = "none";
                setTopMessage("<span style=\\"color:green\\">" + esc(d.message || "Import complete") + "</span>");
                loadGrid(currentTab);
            } else {
                alert(d.message || "Import failed");
            }
        });
    }

    function exportMappingsJson() {
        var st = getCurrentState();
        var exportObj = {};

        if (currentTab === "bank") {
            for (var i = 0; i < st.rows.length; i++) {
                exportObj[String(st.rows[i].row_id)] = {
                    bank_name: st.rows[i].name_value || ""
                };
            }
        } else {
            for (var j = 0; j < st.rows.length; j++) {
                if (st.rows[j].has_mapping) {
                    exportObj[String(st.rows[j].row_id)] = st.rows[j].mapped_values || {};
                }
            }
        }

        var filePrefix = currentTab === "fund"
            ? "quickbooks_account_translations_by_fundid_v"
            : currentTab === "account"
                ? "quickbooks_account_translations_by_accountcode_v"
                : currentTab === "bank"
                    ? "quickbooks_bank_account_translations_v"
                    : "quickbooks_merchant_fees_translation_v";

        var blob = new Blob([JSON.stringify(exportObj, null, 2)], { type: "application/json" });
        var a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = filePrefix + (scriptVersion || "unknown") + ".json";
        a.click();
    }

    currentTab = getInitialTabFromHash();
    updateTabHeaders();
    loadGrid(currentTab);
    '''