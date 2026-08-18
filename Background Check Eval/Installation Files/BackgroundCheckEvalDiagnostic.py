#Roles=Admin

# Background Check Evaluator Diagnostic
# Version: 3.1.1
# 2026-08-18 3.1.1 - Kept diagnostic version aligned with the evaluator's
# default-off Process Builder reminder display switch.
# 2026-08-18 3.1.0 - Kept diagnostic version aligned with Process Builder
# report integration.
# 2026-08-18 3.0.4 - Added privacy-safe Process Builder object, column, and
# relationship discovery for reminder-step reporting.
# 2026-08-18 3.0.3 - Limit evaluate-through diagnostics to unexpired dates.
# 2026-08-18 3.0.2 - Kept diagnostic version aligned with report presentation.
# 2026-08-18 3.0.1 - Report only populated evaluate-through DateValues.
# 2026-08-18 3.0.0 - Replaced the deprecated program-year flag diagnostic
# with EvaluateBackgroundCheckThroughDate DateValue reporting.
# 2026-08-17 2.0.3 - Kept diagnostic version aligned with Admin action routing.
# 2026-08-17 2.0.2 - Kept diagnostic version aligned with reset-state fix.
# 2026-08-17 2.0.1 - Corrected target EV summary and coverage calculations to
# use the tenant-confirmed AppStatus-qualified application fields.
# 2026-08-17 2.0.0 - Added aggregate AppStatus/application EV storage
# diagnostics and removed the diagnostic's legacy migration framing.
# 2026-08-17 1.2.4 - Kept diagnostic version aligned with Admin toast semantics.
# 2026-08-17 1.2.3 - Kept diagnostic version aligned with the Admin in-frame fix.
# 2026-08-17 1.2.2 - Kept diagnostic version aligned with the Admin toast fix.
# 2026-08-17 1.2.1 - Kept diagnostic version aligned with evaluator and Admin.
# 2026-08-17 1.2.0 - Added Involvement Extra Value schema, flagged
# Involvement, meeting, and member coverage diagnostics.
# 2026-08-16 1.1.0 - Added privacy-safe People Extra Value schema and
# migration coverage checks.
# 2026-07-27 1.0.0 - Added tenant schema and Volunteer Code diagnostics.
# Written by: Brian Bullock with Codex assistance
# Email: bbbullock@mac.com
# GitHub: https://github.com/bbbullock/TouchPoint

"""
Background Check Evaluator - Read-Only Diagnostic

Install temporarily as a TouchPoint Python Script and run it manually.
This script reads schema metadata, lookup values, and aggregate counts only.
It does not display volunteer names, send email, or modify any records.
"""

import cgi

APP_VERSION = "3.1.1"
model.Header = "Background Check Evaluator - Diagnostic"


def html_escape(value):
    if value is None:
        return ""
    return cgi.escape(str(value), True)


def render_table(title, rows, columns):
    parts = [
        "<h2>{0}</h2>".format(html_escape(title)),
        '<table class="table table-striped table-bordered" style="width:auto">',
        "<thead><tr>",
    ]
    for column in columns:
        parts.append("<th>{0}</th>".format(html_escape(column)))
    parts.append("</tr></thead><tbody>")

    if not rows:
        parts.append(
            '<tr><td colspan="{0}"><em>No rows returned.</em></td></tr>'.format(
                len(columns)
            )
        )
    else:
        for row in rows:
            parts.append("<tr>")
            for column in columns:
                parts.append(
                    "<td>{0}</td>".format(
                        html_escape(getattr(row, column, None))
                    )
                )
            parts.append("</tr>")

    parts.append("</tbody></table>")
    return "".join(parts)


def run_section(title, sql, columns):
    try:
        rows = list(q.QuerySql(sql))
        return render_table(title, rows, columns)
    except Exception as exc:
        return (
            "<h2>{0}</h2>"
            '<div class="alert alert-danger"><strong>Query failed:</strong> {1}</div>'
        ).format(html_escape(title), html_escape(exc))


sections = []

sections.append(
    run_section(
        "OrganizationExtra Table Columns",
        """
        SELECT
            c.column_id AS ColumnOrder,
            c.name AS ColumnName,
            t.name AS DataType,
            c.max_length AS MaxLength,
            c.is_nullable AS IsNullable
        FROM sys.columns c
        JOIN sys.types t ON t.user_type_id = c.user_type_id
        WHERE c.object_id = OBJECT_ID('dbo.OrganizationExtra')
        ORDER BY c.column_id
        """,
        ["ColumnOrder", "ColumnName", "DataType", "MaxLength", "IsNullable"],
    )
)

sections.append(
    run_section(
        "Process Builder Database Objects",
        """
        SELECT
            s.name AS SchemaName,
            o.name AS ObjectName,
            o.type_desc AS ObjectType,
            HAS_PERMS_BY_NAME(
                QUOTENAME(s.name) + '.' + QUOTENAME(o.name),
                'OBJECT',
                'SELECT'
            ) AS HasSelectPermission
        FROM sys.objects o
        JOIN sys.schemas s ON s.schema_id = o.schema_id
        WHERE o.type IN ('U', 'V')
          AND (
              o.name LIKE '%Process%'
              OR o.name LIKE '%Step%'
              OR o.name LIKE '%Workflow%'
          )
        ORDER BY s.name, o.name
        """,
        ["SchemaName", "ObjectName", "ObjectType", "HasSelectPermission"],
    )
)

sections.append(
    run_section(
        "Process Builder Object Columns",
        """
        SELECT
            s.name AS SchemaName,
            o.name AS ObjectName,
            c.column_id AS ColumnOrder,
            c.name AS ColumnName,
            t.name AS DataType,
            c.max_length AS MaxLength,
            c.is_nullable AS IsNullable
        FROM sys.objects o
        JOIN sys.schemas s ON s.schema_id = o.schema_id
        JOIN sys.columns c ON c.object_id = o.object_id
        JOIN sys.types t ON t.user_type_id = c.user_type_id
        WHERE o.type IN ('U', 'V')
          AND (
              o.name LIKE '%Process%'
              OR o.name LIKE '%Step%'
              OR o.name LIKE '%Workflow%'
          )
        ORDER BY s.name, o.name, c.column_id
        """,
        [
            "SchemaName", "ObjectName", "ColumnOrder", "ColumnName",
            "DataType", "MaxLength", "IsNullable",
        ],
    )
)

sections.append(
    run_section(
        "Process Builder Foreign Keys",
        """
        SELECT
            OBJECT_SCHEMA_NAME(fkc.parent_object_id) AS ParentSchema,
            OBJECT_NAME(fkc.parent_object_id) AS ParentTable,
            pc.name AS ParentColumn,
            OBJECT_SCHEMA_NAME(fkc.referenced_object_id) AS ReferencedSchema,
            OBJECT_NAME(fkc.referenced_object_id) AS ReferencedTable,
            rc.name AS ReferencedColumn
        FROM sys.foreign_key_columns fkc
        JOIN sys.columns pc
          ON pc.object_id = fkc.parent_object_id
         AND pc.column_id = fkc.parent_column_id
        JOIN sys.columns rc
          ON rc.object_id = fkc.referenced_object_id
         AND rc.column_id = fkc.referenced_column_id
        WHERE OBJECT_NAME(fkc.parent_object_id) LIKE '%Process%'
           OR OBJECT_NAME(fkc.parent_object_id) LIKE '%Step%'
           OR OBJECT_NAME(fkc.parent_object_id) LIKE '%Workflow%'
           OR OBJECT_NAME(fkc.referenced_object_id) LIKE '%Process%'
           OR OBJECT_NAME(fkc.referenced_object_id) LIKE '%Step%'
           OR OBJECT_NAME(fkc.referenced_object_id) LIKE '%Workflow%'
        ORDER BY ParentSchema, ParentTable, ParentColumn
        """,
        [
            "ParentSchema", "ParentTable", "ParentColumn",
            "ReferencedSchema", "ReferencedTable", "ReferencedColumn",
        ],
    )
)

sections.append(
    run_section(
        "Involvements With Evaluate-Through Dates",
        """
        DECLARE @Today date = CAST(GETDATE() AS date);

        SELECT
            o.OrganizationId,
            o.OrganizationName AS Involvement,
            oe.Type AS ExtraValueType,
            oe.DateValue AS EvaluateThroughDate,
            COUNT(DISTINCT CASE
                WHEN om.InactiveDate IS NULL AND ISNULL(om.Pending, 0) = 0
                THEN om.PeopleId END) AS CurrentMemberCount,
            COUNT(DISTINCT CASE
                WHEN ISNULL(m.DidNotMeet, 0) = 0
                 AND m.MeetingDate >= @Today
                THEN m.MeetingId END) AS FutureMeetingCount,
            MAX(CASE
                WHEN ISNULL(m.DidNotMeet, 0) = 0
                 AND m.MeetingDate >= @Today
                THEN CAST(m.MeetingDate AS date) END) AS LatestFutureMeeting
        FROM dbo.Organizations o
        JOIN dbo.Division d ON d.Id = o.DivisionId
        JOIN dbo.Program p ON p.Id = d.ProgId
        JOIN dbo.OrganizationExtra oe
         ON oe.OrganizationId = o.OrganizationId
         AND oe.Field = 'EvaluateBackgroundCheckThroughDate'
         AND oe.DateValue >= @Today
        LEFT JOIN dbo.OrganizationMembers om
          ON om.OrganizationId = o.OrganizationId
        LEFT JOIN dbo.Meetings m
          ON m.OrganizationId = o.OrganizationId
        WHERE p.Name = 'Administration'
          AND d.Name = 'Requires Volunteer Application'
          AND o.OrganizationStatusId = 30
        GROUP BY
            o.OrganizationId,
            o.OrganizationName,
            oe.Type,
            oe.DateValue
        ORDER BY o.OrganizationName, o.OrganizationId
        """,
        [
            "OrganizationId",
            "Involvement",
            "ExtraValueType",
            "EvaluateThroughDate",
            "CurrentMemberCount",
            "FutureMeetingCount",
            "LatestFutureMeeting",
        ],
    )
)

sections.append(
    run_section(
        "PeopleExtra Table Columns",
        """
        SELECT
            c.column_id AS ColumnOrder,
            c.name AS ColumnName,
            t.name AS DataType,
            c.max_length AS MaxLength,
            c.is_nullable AS IsNullable
        FROM sys.columns c
        JOIN sys.types t ON t.user_type_id = c.user_type_id
        WHERE c.object_id = OBJECT_ID('dbo.PeopleExtra')
        ORDER BY c.column_id
        """,
        ["ColumnOrder", "ColumnName", "DataType", "MaxLength", "IsNullable"],
    )
)

sections.append(
    run_section(
        "Application and AppStatus Extra Value Storage",
        """
        SELECT
            Field,
            Type,
            BitValue,
            StrValue,
            COUNT(*) AS RecordCount,
            COUNT(DISTINCT PeopleId) AS DistinctPeopleCount
        FROM dbo.PeopleExtra
        WHERE Field LIKE '%Application%'
           OR Field LIKE 'AppStatus%'
        GROUP BY Field, Type, BitValue, StrValue
        ORDER BY Field, Type, BitValue, StrValue
        """,
        [
            "Field", "Type", "BitValue", "StrValue", "RecordCount",
            "DistinctPeopleCount",
        ],
    )
)

sections.append(
    run_section(
        "Target Volunteer Extra Value Summary",
        """
        SELECT
            Field,
            Type,
            BitValue,
            COUNT(*) AS RecordCount,
            COUNT(DISTINCT PeopleId) AS DistinctPeopleCount
        FROM dbo.PeopleExtra
        WHERE Field IN (
            'AppStatus:Application Approved',
            'AppStatus:Application on File',
            'College Student (no background check)',
            'Individual Refuses Background Check'
        )
        GROUP BY Field, Type, BitValue
        ORDER BY Field, Type, BitValue
        """,
        ["Field", "Type", "BitValue", "RecordCount", "DistinctPeopleCount"],
    )
)

sections.append(
    run_section(
        "Extra Value Migration Coverage",
        """
        ;WITH Flags AS (
            SELECT
                PeopleId,
                MAX(CASE WHEN Field = 'AppStatus:Application Approved'
                          AND BitValue = 1 THEN 1 ELSE 0 END) AS HasApproved,
                MAX(CASE WHEN Field = 'AppStatus:Application on File'
                          AND BitValue = 1 THEN 1 ELSE 0 END) AS HasOnFile,
                MAX(CASE WHEN Field = 'College Student (no background check)'
                          AND BitValue = 1 THEN 1 ELSE 0 END) AS HasCollege,
                MAX(CASE WHEN Field = 'Individual Refuses Background Check'
                          AND BitValue = 1 THEN 1 ELSE 0 END) AS HasRefuses
            FROM dbo.PeopleExtra
            WHERE Field IN (
                'AppStatus:Application Approved',
                'AppStatus:Application on File',
                'College Student (no background check)',
                'Individual Refuses Background Check'
            )
            GROUP BY PeopleId
        )
        SELECT
            COUNT(*) AS PeopleWithAnyTargetEV,
            SUM(CASE WHEN HasApproved = 1 AND HasOnFile = 1
                     THEN 1 ELSE 0 END) AS CompleteApplications,
            SUM(CASE WHEN HasApproved <> HasOnFile
                     THEN 1 ELSE 0 END) AS PartialApplications,
            SUM(HasCollege) AS CollegeFlags,
            SUM(HasRefuses) AS RefusalFlags
        FROM Flags
        """,
        [
            "PeopleWithAnyTargetEV",
            "CompleteApplications",
            "PartialApplications",
            "CollegeFlags",
            "RefusalFlags",
        ],
    )
)

sections.append(
    run_section(
        "Qualifying Program and Division",
        """
        SELECT
            p.Id AS ProgramId,
            p.Name AS ProgramName,
            d.Id AS DivisionId,
            d.Name AS DivisionName,
            COUNT(DISTINCT o.OrganizationId) AS ActiveInvolvementCount
        FROM dbo.Program p
        JOIN dbo.Division d ON d.ProgId = p.Id
        LEFT JOIN dbo.Organizations o
            ON o.DivisionId = d.Id
           AND o.OrganizationStatusId = 30
        WHERE p.Name = 'Administration'
          AND d.Name = 'Requires Volunteer Application'
        GROUP BY p.Id, p.Name, d.Id, d.Name
        ORDER BY p.Id, d.Id
        """,
        [
            "ProgramId",
            "ProgramName",
            "DivisionId",
            "DivisionName",
            "ActiveInvolvementCount",
        ],
    )
)

sections.append(
    run_section(
        "Volunteer Application Status Lookup",
        """
        SELECT Id, Code, Description
        FROM lookup.VolApplicationStatus
        ORDER BY Id
        """,
        ["Id", "Code", "Description"],
    )
)

sections.append(
    run_section(
        "Volunteer Codes Lookup",
        """
        SELECT *
        FROM lookup.VolunteerCodes
        ORDER BY Id
        """,
        ["Id", "Code", "Description"],
    )
)

sections.append(
    run_section(
        "Volunteer-Related Tables and Views",
        """
        SELECT
            s.name AS SchemaName,
            o.name AS ObjectName,
            o.type_desc AS ObjectType
        FROM sys.objects o
        JOIN sys.schemas s ON s.schema_id = o.schema_id
        WHERE o.name LIKE '%Volunteer%'
          AND o.type IN ('U', 'V')
        ORDER BY s.name, o.name
        """,
        ["SchemaName", "ObjectName", "ObjectType"],
    )
)

sections.append(
    run_section(
        "Volunteer-Related Columns",
        """
        SELECT
            s.name AS SchemaName,
            o.name AS ObjectName,
            c.column_id AS ColumnOrder,
            c.name AS ColumnName,
            t.name AS DataType,
            c.max_length AS MaxLength,
            c.is_nullable AS IsNullable
        FROM sys.objects o
        JOIN sys.schemas s ON s.schema_id = o.schema_id
        JOIN sys.columns c ON c.object_id = o.object_id
        JOIN sys.types t ON t.user_type_id = c.user_type_id
        WHERE o.type IN ('U', 'V')
          AND (
              o.name LIKE '%Volunteer%'
              OR c.name LIKE '%Volunteer%'
              OR c.name LIKE '%ApprovalCode%'
          )
        ORDER BY s.name, o.name, c.column_id
        """,
        [
            "SchemaName",
            "ObjectName",
            "ColumnOrder",
            "ColumnName",
            "DataType",
            "MaxLength",
            "IsNullable",
        ],
    )
)

sections.append(
    run_section(
        "Foreign Keys Involving Volunteer Objects",
        """
        SELECT
            OBJECT_SCHEMA_NAME(fkc.parent_object_id) AS ParentSchema,
            OBJECT_NAME(fkc.parent_object_id) AS ParentTable,
            pc.name AS ParentColumn,
            OBJECT_SCHEMA_NAME(fkc.referenced_object_id) AS ReferencedSchema,
            OBJECT_NAME(fkc.referenced_object_id) AS ReferencedTable,
            rc.name AS ReferencedColumn
        FROM sys.foreign_key_columns fkc
        JOIN sys.columns pc
          ON pc.object_id = fkc.parent_object_id
         AND pc.column_id = fkc.parent_column_id
        JOIN sys.columns rc
          ON rc.object_id = fkc.referenced_object_id
         AND rc.column_id = fkc.referenced_column_id
        WHERE OBJECT_NAME(fkc.parent_object_id) LIKE '%Volunteer%'
           OR OBJECT_NAME(fkc.referenced_object_id) LIKE '%Volunteer%'
        ORDER BY ParentSchema, ParentTable, ParentColumn
        """,
        [
            "ParentSchema",
            "ParentTable",
            "ParentColumn",
            "ReferencedSchema",
            "ReferencedTable",
            "ReferencedColumn",
        ],
    )
)

sections.append(
    run_section(
        "Approval-Related Database Objects",
        """
        SELECT
            s.name AS SchemaName,
            o.name AS ObjectName,
            o.type AS ObjectTypeCode,
            o.type_desc AS ObjectType,
            o.object_id AS ObjectId,
            HAS_PERMS_BY_NAME(
                QUOTENAME(s.name) + '.' + QUOTENAME(o.name),
                'OBJECT',
                'SELECT'
            ) AS HasSelectPermission
        FROM sys.objects o
        JOIN sys.schemas s ON s.schema_id = o.schema_id
        WHERE o.name LIKE '%Approval%'
           OR o.name LIKE '%VolunteerCode%'
        ORDER BY s.name, o.name
        """,
        [
            "SchemaName",
            "ObjectName",
            "ObjectTypeCode",
            "ObjectType",
            "ObjectId",
            "HasSelectPermission",
        ],
    )
)

sections.append(
    run_section(
        "Approval-Related Synonyms",
        """
        SELECT
            SCHEMA_NAME(schema_id) AS SchemaName,
            name AS SynonymName,
            base_object_name AS BaseObjectName
        FROM sys.synonyms
        WHERE name LIKE '%Approval%'
           OR name LIKE '%VolunteerCode%'
           OR base_object_name LIKE '%Approval%'
           OR base_object_name LIKE '%VolunteerCode%'
        ORDER BY SchemaName, SynonymName
        """,
        ["SchemaName", "SynonymName", "BaseObjectName"],
    )
)

sections.append(
    run_section(
        "VoluteerApprovalIds Direct Access Test",
        """
        SELECT
            COUNT(*) AS [TotalRows],
            COUNT(DISTINCT PeopleId) AS DistinctPeopleCount,
            COUNT(DISTINCT ApprovalId) AS DistinctApprovalCodeCount
        FROM dbo.VoluteerApprovalIds
        """,
        ["TotalRows", "DistinctPeopleCount", "DistinctApprovalCodeCount"],
    )
)

sections.append(
    run_section(
        "BackgroundChecks Columns",
        """
        SELECT
            c.column_id AS ColumnOrder,
            c.name AS ColumnName,
            t.name AS DataType,
            c.max_length AS MaxLength,
            c.is_nullable AS IsNullable
        FROM sys.columns c
        JOIN sys.types t ON t.user_type_id = c.user_type_id
        WHERE c.object_id = OBJECT_ID('dbo.BackgroundChecks')
        ORDER BY c.column_id
        """,
        ["ColumnOrder", "ColumnName", "DataType", "MaxLength", "IsNullable"],
    )
)

sections.append(
    run_section(
        "Background Check Type and Label Summary",
        """
        SELECT
            bc.ReportTypeId,
            bc.ReportLabelID,
            bcl.Description AS ReportLabel,
            bc.ServiceCode,
            bc.ApprovalStatus,
            COUNT(*) AS RecordCount,
            MIN(bc.Updated) AS EarliestUpdated,
            MAX(bc.Updated) AS LatestUpdated
        FROM dbo.BackgroundChecks bc
        LEFT JOIN lookup.BackgroundCheckLabels bcl
          ON bcl.Id = bc.ReportLabelID
        GROUP BY
            bc.ReportTypeId,
            bc.ReportLabelID,
            bcl.Description,
            bc.ServiceCode,
            bc.ApprovalStatus
        ORDER BY
            bc.ReportTypeId,
            bc.ReportLabelID,
            bc.ServiceCode,
            bc.ApprovalStatus
        """,
        [
            "ReportTypeId",
            "ReportLabelID",
            "ReportLabel",
            "ServiceCode",
            "ApprovalStatus",
            "RecordCount",
            "EarliestUpdated",
            "LatestUpdated",
        ],
    )
)

page = """
<div class="container-fluid">
  <h1>Background Check Evaluator Diagnostic</h1>
  <p class="text-muted">Version {version}</p>
  <div class="alert alert-info">
    <strong>Read-only diagnostic.</strong>
    Copy the rendered tables or save the page as a PDF and return the results.
    The report intentionally omits names, People IDs, email addresses, comments,
    report IDs, and other person-level information.
  </div>
  {content}
</div>
""".format(version=APP_VERSION, content="".join(sections))

print(page)
