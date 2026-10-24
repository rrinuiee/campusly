# absence-reporting Specification

## Purpose
Lets staff record that a teacher is absent on a given date so the system can derive which scheduled periods need substitute coverage.

## Requirements

### Requirement: Report a teacher absence
The system SHALL allow a user to mark a teacher as absent for a specific date and record the absence as pending coverage.

#### Scenario: Absence recorded
- **WHEN** a user selects a teacher and a date and submits the absence
- **THEN** the system stores the absence and lists every period that teacher was scheduled to teach on that date as needing coverage

#### Scenario: Teacher with no classes that day
- **WHEN** a user reports an absence for a teacher who has no scheduled periods on that date
- **THEN** the system records the absence and reports zero periods needing coverage

### Requirement: Prevent duplicate absences
The system MUST NOT create a second absence record for the same teacher on the same date.

#### Scenario: Duplicate absence rejected
- **WHEN** a user reports an absence for a teacher already marked absent on that date
- **THEN** the system rejects the report and shows the existing absence

### Requirement: Seeded demo data
The system SHALL ship with a fictional institution dataset (teachers, subjects, rooms, classes, weekly timetable) loaded automatically so every feature works without external setup.

#### Scenario: Fresh launch
- **WHEN** the app starts with no user data
- **THEN** teachers, classes, rooms, and a weekly timetable are already populated and visible
