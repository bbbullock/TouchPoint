--Roles=Admin

/*
Volunteer Schedule Report - read-only tenant diagnostic

INSTALL THIS FILE AS A TOUCHPOINT SQL SCRIPT, NOT AS A PYTHON SCRIPT.
Replace 0 below with the numeric ID of a known Scheduler Involvement.
This script only reads data. It does not send email or change TouchPoint data.
*/

DECLARE @InvolvementId INT = 0;

;WITH UpcomingTeams AS
(
    SELECT
        ROW_NUMBER() OVER
        (
            ORDER BY tsm.MeetingDateTime, tsmt.TeamName,
                     tsmt.TimeSlotMeetingTeamId
        ) AS RowNumber,
        tsm.MeetingDateTime,
        tsmt.TeamName,
        m.MeetingId
    FROM dbo.TimeSlotMeetingTeams tsmt
    INNER JOIN dbo.TimeSlotMeetings tsm
        ON tsm.TimeSlotMeetingId = tsmt.TimeSlotMeetingId
    INNER JOIN dbo.Meetings m ON m.MeetingId = tsm.MeetingId
    WHERE m.OrganizationId = @InvolvementId
      AND tsm.MeetingDateTime >= GETDATE()
),
DiagnosticRows AS
(
    SELECT
        1 AS SortGroup,
        0 AS SortOrder,
        CAST('Configuration' AS NVARCHAR(100)) AS Section,
        CAST('Selected Involvement ID' AS NVARCHAR(256)) AS Item,
        CONVERT(NVARCHAR(4000), @InvolvementId) AS Value,
        CAST(CASE
            WHEN @InvolvementId > 0 THEN 'Ready'
            ELSE 'Edit DECLARE @InvolvementId INT = 0 near the top of this script.'
        END AS NVARCHAR(4000)) AS Detail

    UNION ALL

    SELECT
        2,
        0,
        'Involvement',
        CONVERT(NVARCHAR(256), o.OrganizationName),
        'StatusId=' + CONVERT(NVARCHAR(20), o.OrganizationStatusId),
        'RegistrationTypeId=' + CONVERT(NVARCHAR(20), o.RegistrationTypeId)
    FROM dbo.Organizations o
    WHERE o.OrganizationId = @InvolvementId

    UNION ALL

    SELECT
        3,
        c.ORDINAL_POSITION,
        'Schema',
        CONVERT(NVARCHAR(256), c.TABLE_NAME + '.' + c.COLUMN_NAME),
        CONVERT(NVARCHAR(4000), c.DATA_TYPE),
        CONVERT(NVARCHAR(4000), 'Nullable=' + c.IS_NULLABLE)
    FROM INFORMATION_SCHEMA.COLUMNS c
    WHERE c.TABLE_NAME IN
    (
        'TimeSlots',
        'TimeSlotTeams',
        'TimeSlotMeetings',
        'TimeSlotMeetingTeams',
        'TimeSlotTeamSubGroups',
        'TimeSlotMeetingTeamSubGroups',
        'TimeSlotMeetingTeamSubGroupVolunteers',
        'TimeSlotMeetingVolunteers',
        'Attend',
        'Meetings',
        'MemberTags',
        'People'
    )

    UNION ALL

    SELECT
        4,
        1,
        'Count',
        'Time Slot Meetings',
        CONVERT(NVARCHAR(4000), COUNT_BIG(*)),
        'Rows connected to the selected Involvement'
    FROM dbo.TimeSlotMeetings tsm
    INNER JOIN dbo.Meetings m ON m.MeetingId = tsm.MeetingId
    WHERE m.OrganizationId = @InvolvementId

    UNION ALL

    SELECT
        4,
        2,
        'Count',
        'Meeting Teams',
        CONVERT(NVARCHAR(4000), COUNT_BIG(*)),
        'Rows connected to the selected Involvement'
    FROM dbo.TimeSlotMeetingTeams tsmt
    INNER JOIN dbo.TimeSlotMeetings tsm
        ON tsm.TimeSlotMeetingId = tsmt.TimeSlotMeetingId
    INNER JOIN dbo.Meetings m ON m.MeetingId = tsm.MeetingId
    WHERE m.OrganizationId = @InvolvementId

    UNION ALL

    SELECT
        5,
        ut.RowNumber,
        'Upcoming Team',
        CONVERT(NVARCHAR(256), ut.TeamName),
        CONVERT(NVARCHAR(4000), ut.MeetingDateTime, 120),
        'MeetingId=' + CONVERT(NVARCHAR(20), ut.MeetingId)
    FROM UpcomingTeams ut
    WHERE ut.RowNumber <= 50
)
SELECT Section, Item, Value, Detail
FROM DiagnosticRows
ORDER BY SortGroup, SortOrder, Item;
