--Roles=Admin

/*
Volunteer Schedule Report - focused assignment diagnostic

Install as a TouchPoint SQL Script. This query is read-only and is configured
for the confirmed Media Ministry Scheduler Involvement. Change the ID when
validating another Scheduler.
*/

DECLARE @InvolvementId INT = 315;
DECLARE @StartDate DATETIME = CONVERT(DATE, GETDATE());
DECLARE @EndDateExclusive DATETIME = DATEADD(DAY, 46, @StartDate);

;WITH LatestVolunteers AS
(
    SELECT
        TimeSlotMeetingId,
        PeopleId,
        MAX(TimeSlotMeetingVolunteerId) AS TimeSlotMeetingVolunteerId
    FROM dbo.TimeSlotMeetingVolunteers
    GROUP BY TimeSlotMeetingId, PeopleId
),
LatestAttend AS
(
    SELECT
        MeetingId,
        PeopleId,
        MAX(AttendId) AS AttendId
    FROM dbo.Attend
    GROUP BY MeetingId, PeopleId
)
SELECT TOP (250)
    o.OrganizationName AS Involvement,
    tsm.MeetingDateTime AS ServiceDateTime,
    m.MeetingId,
    m.Canceled AS MeetingCanceled,
    tsm.IsDeleted AS TimeSlotMeetingDeleted,
    tsmt.IsDeleted AS MeetingTeamDeleted,
    tsmt.TeamName AS Team,
    tsmt.UseSubGroup,
    COALESCE(mt.Name, '') AS SubGroup,
    tssg.IsDeleted AS MeetingSubGroupDeleted,
    CASE
        WHEN tsmt.UseSubGroup = 0 THEN tst.NumberVolunteersNeeded
        ELSE tssg.NumberVolunteersNeeded
    END AS NumberNeeded,
    COALESCE(tstsg.Require, 0) AS IsRequired,
    v.PeopleId,
    p.Name2 AS Volunteer,
    v.IsActive AS RosterAssignmentActive,
    v.DateServiceEnded,
    tsmv.IsActive AS MeetingVolunteerActive,
    tsmv.IsSub,
    tsmv.AutoCommit,
    tsmv.VolunteerOption,
    a.Commitment AS CommitmentCode,
    CASE
        WHEN a.Commitment = 0 THEN 'Regrets'
        WHEN a.Commitment = 1 THEN 'Attending'
        WHEN a.Commitment = 2 THEN 'Find Sub'
        WHEN a.Commitment = 3 THEN 'Sub Found'
        WHEN a.Commitment = 4 THEN 'Substitute'
        WHEN a.Commitment = 99 OR a.Commitment IS NULL THEN 'Uncommitted'
        ELSE 'Other'
    END AS CommitmentStatus,
    p.EmailAddress,
    p.CellPhone
FROM dbo.TimeSlotMeetingTeams tsmt
INNER JOIN dbo.TimeSlotMeetings tsm
    ON tsm.TimeSlotMeetingId = tsmt.TimeSlotMeetingId
INNER JOIN dbo.Meetings m
    ON m.MeetingId = tsm.MeetingId
INNER JOIN dbo.Organizations o
    ON o.OrganizationId = m.OrganizationId
LEFT JOIN dbo.TimeSlotTeams tst
    ON tst.TimeSlotId = tsm.TimeSlotId
   AND tst.TeamName = tsmt.TeamName
LEFT JOIN dbo.TimeSlotMeetingTeamSubGroups tssg
    ON tssg.TimeSlotMeetingTeamId = tsmt.TimeSlotMeetingTeamId
LEFT JOIN dbo.TimeSlotTeamSubGroups tstsg
    ON tstsg.TimeSlotTeamSubGroupId = tssg.TimeSlotTeamSubGroupId
LEFT JOIN dbo.MemberTags mt
    ON mt.Id = tssg.MemberTagId
   AND mt.OrgId = m.OrganizationId
LEFT JOIN dbo.TimeSlotMeetingTeamSubGroupVolunteers v
    ON v.TimeSlotMeetingTeamId = tsmt.TimeSlotMeetingTeamId
   AND
   (
       (v.TimeSlotMeetingTeamSubGroupId IS NULL
        AND tssg.TimeSlotMeetingTeamSubGroupId IS NULL)
       OR v.TimeSlotMeetingTeamSubGroupId =
          tssg.TimeSlotMeetingTeamSubGroupId
   )
LEFT JOIN dbo.People p
    ON p.PeopleId = v.PeopleId
LEFT JOIN LatestVolunteers lv
    ON lv.TimeSlotMeetingId = tsm.TimeSlotMeetingId
   AND lv.PeopleId = v.PeopleId
LEFT JOIN dbo.TimeSlotMeetingVolunteers tsmv
    ON tsmv.TimeSlotMeetingVolunteerId = lv.TimeSlotMeetingVolunteerId
LEFT JOIN LatestAttend la
    ON la.MeetingId = m.MeetingId
   AND la.PeopleId = v.PeopleId
LEFT JOIN dbo.Attend a
    ON a.AttendId = la.AttendId
WHERE m.OrganizationId = @InvolvementId
  AND tsm.MeetingDateTime >= @StartDate
  AND tsm.MeetingDateTime < @EndDateExclusive
ORDER BY
    tsm.MeetingDateTime,
    tsmt.TeamName,
    COALESCE(mt.Name, ''),
    p.Name2;
