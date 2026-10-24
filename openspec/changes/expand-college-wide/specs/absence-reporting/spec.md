# Spec Delta

## MODIFIED Requirements

### Requirement: Seeded demo data
The system SHALL ship with a fictional college dataset (departments, faculty, subjects, rooms, divisions, weekly timetables) loaded automatically so every feature works without external setup.

#### Scenario: Fresh launch
- **WHEN** the app starts with no user data
- **THEN** departments, faculty, divisions, rooms, and weekly timetables are already populated and visible

#### Scenario: Dataset spans departments
- **WHEN** the seed data loads
- **THEN** five engineering departments (CSE, ECE, EEE, ME, CE) each contain faculty and divisions with their own timetables, and a Basic Science department supplies cross-department faculty

## ADDED Requirements

### Requirement: Absence uncovers all assigned slots
When a faculty member is absent, the system SHALL list as needing coverage every slot they were scheduled to teach that day across all departments, including cross-department teaching assignments.

#### Scenario: Cross-department slots uncovered
- **WHEN** a faculty member teaches one slot for their home department's division and one slot for another department's division on the same day
- **THEN** the absence lists both periods as needing coverage, each attributed to its own division

### Requirement: Absence reporting is role-scoped
An absence SHALL be reported by an Admin or by the department coordinator of the absent faculty member's home department.

#### Scenario: Coordinator reports own-department faculty
- **WHEN** a coordinator reports an absence for a faculty member of their own department
- **THEN** the absence is recorded

#### Scenario: Other department's faculty not reportable
- **WHEN** a coordinator tries to report an absence for a faculty member of another department
- **THEN** the action is refused
