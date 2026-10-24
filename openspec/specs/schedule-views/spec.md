# schedule-views Specification

## Purpose
Publishes the outcome of approved substitutions as read-only views: updated timetable, class notices, substitute workload summary, and a CSV export.

## Requirements

### Requirement: Dashboard overview
The system SHALL display a dashboard summarizing today's absences, pending reviews, uncovered periods, and approved changes for the selected date.

#### Scenario: Overview counts
- **WHEN** a coordinator opens the dashboard on a date with absences and pending proposals
- **THEN** counts of absences, pending reviews, uncovered periods, and approved changes are shown correctly

### Requirement: Updated timetable view
The system SHALL display the timetable for a selected date reflecting all approved substitutions, including uncovered flags for unassigned periods.

#### Scenario: Approved change visible
- **WHEN** a substitution has been approved
- **THEN** the timetable view shows the substitute teacher for that class and period

#### Scenario: Uncovered period visible
- **WHEN** a period has no approved substitute
- **THEN** the timetable view marks it as uncovered instead of showing a teacher

### Requirement: Notices for affected classes
The system SHALL generate a notice per affected class describing the schedule change after approval.

#### Scenario: Notice generated
- **WHEN** a substitution for a class period is approved
- **THEN** a notice naming the class, period, original teacher, and substitute is produced

### Requirement: Substitute workload summary
The system SHALL show, per teacher, how many substitute periods they have taken in the current week, including assigned pending and approved substitutions.

#### Scenario: Workload counts
- **WHEN** a teacher has 2 approved and 1 pending substitution this week
- **THEN** the workload summary reports 3 assigned periods for that teacher

### Requirement: CSV export
The system SHALL let the coordinator download the day's substitution results as a CSV file covering approved, pending, and uncovered items.

#### Scenario: Export includes all states
- **WHEN** the coordinator exports the day's data
- **THEN** the CSV contains one row per affected period with class, period, absent teacher, substitute or uncovered status, and approval state
