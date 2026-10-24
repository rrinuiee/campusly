# Spec Delta

## MODIFIED Requirements

### Requirement: Updated timetable view
The system SHALL display the timetable for a selected department, semester, and division on a working date, reflecting all approved substitutions and applied exchanges, including uncovered flags for unassigned periods.

#### Scenario: Approved change visible
- **WHEN** a substitution has been approved
- **THEN** the division timetable view shows the substitute faculty for that period

#### Scenario: Uncovered period visible
- **WHEN** a period has no approved substitute
- **THEN** the timetable view marks it as uncovered instead of showing a teacher

#### Scenario: Applied exchange visible
- **WHEN** a period exchange has been approved
- **THEN** both affected division and faculty timetables show the swapped faculty

## ADDED Requirements

### Requirement: Department and semester timetable views
The system SHALL provide aggregate timetable views showing all divisions of a chosen department and all divisions of a chosen semester.

#### Scenario: Department view aggregates its divisions
- **WHEN** a user selects a department timetable for a day
- **THEN** every slot of that department's divisions in active semesters is shown

#### Scenario: Semester view aggregates across departments
- **WHEN** a user selects a semester timetable for a day
- **THEN** every slot of divisions in that semester across all departments is shown

### Requirement: Faculty timetable view
The system SHALL show a selected faculty member's weekly timetable across all departments, including teaching slots, supervision meetings, approved substitutions, and applied exchanges.

#### Scenario: Cross-department schedule on one view
- **WHEN** a faculty member teaches slots in two different departments
- **THEN** both slots appear on their single timetable view

### Requirement: Student timetable view
The system SHALL let a Student view their own division's timetable and class notices as read-only.

#### Scenario: Student reads division timetable
- **WHEN** a student selects their division
- **THEN** the timetable and its notices are shown with no editing actions
