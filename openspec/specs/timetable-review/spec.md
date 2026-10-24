# timetable-review Specification

## Purpose
Gives a coordinator a review queue of proposed substitutions so no timetable change is applied until a human approves it.

## Requirements

### Requirement: Review queue of pending proposals
The system SHALL present every proposed substitution as a pending item showing the absent teacher, class, period, proposed substitute, room, and any warnings, so the coordinator can approve or reject each one.

#### Scenario: Pending items listed
- **WHEN** allocation has produced proposals for an absence
- **THEN** each proposal appears in a pending review list with its details before any timetable change occurs

#### Scenario: Warnings surfaced
- **WHEN** a proposal is non-subject-matched or a period is uncovered
- **THEN** the review item clearly displays that warning

### Requirement: Approval applies the change
The system MUST apply an approved substitution to the timetable, marking the period as covered by the substitute.

#### Scenario: Approve publishes change
- **WHEN** the coordinator approves a pending proposal
- **THEN** the timetable for that period shows the substitute teacher and the proposal leaves the pending list

### Requirement: Rejection leaves the period uncovered
The system MUST allow rejecting a proposal; the period SHALL remain flagged as needing coverage and MUST NOT change the timetable.

#### Scenario: Reject keeps flag
- **WHEN** the coordinator rejects a pending proposal
- **THEN** the timetable is unchanged and the period stays flagged uncovered for manual follow-up

### Requirement: No timetable mutation before review
The system MUST NOT alter the published timetable for pending proposals.

#### Scenario: Pending proposal not visible in timetable
- **WHEN** a proposal is pending and not yet approved
- **THEN** the timetable still shows the period as uncovered rather than assigned
