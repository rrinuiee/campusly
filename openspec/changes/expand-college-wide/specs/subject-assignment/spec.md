# Spec Delta

## Purpose

Records which faculty member teaches which subject to which division each semester, so timetables reflect real teaching assignments and a faculty member can teach for a department other than their own.

## ADDED Requirements

### Requirement: Subjects are owned by departments
Every subject SHALL belong to an owning department, while remaining teachable to divisions in other departments.

#### Scenario: Subject catalog per department
- **WHEN** a user browses subjects
- **THEN** each subject shows its owning department

### Requirement: Subject offerings per division
The system SHALL let an Admin or the division's department coordinator record a subject offering for a division in a semester, and each offering SHALL occupy one or more weekly slots on that division's timetable.

#### Scenario: Offering creates timetable slots
- **WHEN** a coordinator adds a Mathematics offering for division CSE-S3-A at two weekly periods
- **THEN** those slots appear on the CSE-S3-A timetable

### Requirement: Faculty assigned per offering
Every offering SHALL name the faculty member who teaches it; assigning or changing that faculty member SHALL update the division's timetable slots for the offering.

#### Scenario: Reassignment updates timetable
- **WHEN** the assigned faculty for an offering is changed
- **THEN** the division's timetable slots for that offering show the new faculty member

### Requirement: Assignments respect college-wide availability
An assignment MUST NOT place a faculty member in a slot at a day and period where they already teach anywhere in the college.

#### Scenario: Conflicting assignment rejected
- **WHEN** the chosen faculty member already teaches another division at the proposed day and period
- **THEN** the assignment is rejected and the conflict is shown

### Requirement: Cross-department teaching allowed and flagged
An offering MAY be assigned to a faculty member whose home department differs from the division's department; such assignments SHALL be visibly flagged as cross-department in timetable and assignment views.

#### Scenario: Cross-department assignment flagged
- **WHEN** a Basic Science faculty member teaches an offering for a CSE division
- **THEN** the slot is marked as cross-department teaching wherever it appears
