# Spec Delta

## MODIFIED Requirements

### Requirement: Review queue of pending proposals
The system SHALL present every proposed substitution as a pending item showing the absent faculty, division, period, proposed substitute, room, and any warnings, so the coordinator can approve or reject each one; a department coordinator SHALL see only items affecting their own department's divisions, while an Admin SHALL see all items.

#### Scenario: Pending items listed
- **WHEN** allocation has produced proposals for an absence
- **THEN** each proposal appears in a pending review list with its details before any timetable change occurs

#### Scenario: Warnings surfaced
- **WHEN** a proposal is non-subject-matched or a period is uncovered
- **THEN** the review item clearly displays that warning

#### Scenario: Queue scoped to coordinator's department
- **WHEN** pending proposals exist for divisions in departments CSE and ECE
- **THEN** the CSE coordinator's queue shows only the CSE items

## ADDED Requirements

### Requirement: Approval authority is department-scoped
Only the coordinator of the department owning the affected division, or an Admin, SHALL approve or reject a pending proposal.

#### Scenario: Cross-department approval refused
- **WHEN** the ECE coordinator attempts to approve a proposal affecting a CSE division
- **THEN** the action is refused and the item stays pending
