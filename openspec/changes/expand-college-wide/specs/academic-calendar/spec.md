# Spec Delta

## Purpose

Defines the college's eight-semester academic calendar — the default odd/even semester date windows and admin overrides — so every scheduling feature can tell which semesters are active on a working date.

## ADDED Requirements

### Requirement: Eight-semester calendar
The system SHALL define semesters S1 through S8. By default, odd semesters (S1, S3, S5, S7) SHALL span January–June and even semesters (S2, S4, S6, S8) SHALL span July–December of the configured academic year.

#### Scenario: Default windows apply
- **WHEN** the calendar has no admin overrides
- **THEN** S1, S3, S5, and S7 span January through June and S2, S4, S6, and S8 span July through December

### Requirement: Resolve active semesters for a date
The system SHALL determine which semesters are active on a given working date from the configured semester windows.

#### Scenario: Second-half date selects even semesters
- **WHEN** the working date falls within the July–December window
- **THEN** the active semesters are S2, S4, S6, and S8

#### Scenario: First-half date selects odd semesters
- **WHEN** the working date falls within the January–June window
- **THEN** the active semesters are S1, S3, S5, and S7

### Requirement: Admin calendar override
The system SHALL let an Admin set a custom date range for any semester, and date resolution SHALL use the overridden windows.

#### Scenario: Override changes the active set
- **WHEN** the Admin extends semester S4's window to include a date in March
- **THEN** S4 resolves as active on that date

#### Scenario: Overrides reset on restart
- **WHEN** the app restarts
- **THEN** semester windows return to their defaults until overridden again

### Requirement: Timetable visibility follows active semesters
The system SHALL offer a division's timetable for a working date only when the division's semester is active on that date.

#### Scenario: Inactive semester not offered
- **WHEN** the working date is in July and a division belongs to semester S3
- **THEN** that division is not selectable for timetable views on that date
