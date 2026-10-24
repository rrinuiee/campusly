# Spec Delta

## Purpose

Models the college as departments containing faculty and divisions — where a division is a student group scoped by department, semester, and section — so every timetable slot belongs to a department, a semester, and a division.

## ADDED Requirements

### Requirement: Departments organize the college
The system SHALL organize the institution into departments, each with a unique name, that own subjects, faculty, and divisions.

#### Scenario: Seeded departments exist
- **WHEN** the app launches with its seed dataset
- **THEN** five engineering departments (CSE, ECE, EEE, ME, CE) exist with their own faculty and divisions, plus a Basic Science department of service faculty

### Requirement: Faculty have a home department
Every faculty member SHALL belong to exactly one home department, and faculty listings SHALL identify each member's department.

#### Scenario: Faculty grouped by department
- **WHEN** a user browses the faculty list
- **THEN** every faculty member is shown under exactly one home department

### Requirement: Divisions are scoped by department and semester
A division SHALL be a student group identified by its department, its semester (S1–S8), and a section label, and division identifiers SHALL be unique across the college.

#### Scenario: Same section in two departments
- **WHEN** departments CSE and ECE each have a semester-S3 section "A"
- **THEN** they are two distinct divisions with independent timetables

#### Scenario: Sections per department per semester
- **WHEN** the seed dataset is loaded
- **THEN** CSE and ECE have sections A, B, and C in every semester S1–S8, while EEE, ME, and CE have sections A and B

### Requirement: Each division has its own timetable
Every division SHALL have an independent weekly timetable of period slots; a department's timetable SHALL be the aggregate of its divisions' timetables, and a semester's timetable SHALL be the aggregate of all divisions in that semester.

#### Scenario: Department view aggregates divisions
- **WHEN** a user views a department's timetable for a day
- **THEN** it shows the slots of every division belonging to that department for the active semesters

### Requirement: College-wide resource uniqueness
A faculty member or room MUST NOT appear in two timetable slots at the same day and period among divisions whose semesters are in session together (same odd/even parity).

#### Scenario: Cross-department double-booking prevented
- **WHEN** a faculty member is scheduled to teach a division in one department at a given day and period
- **THEN** no slot in any other department's same-parity division can schedule the same faculty member at that day and period

#### Scenario: First-year cross-department teaching
- **WHEN** the timetable for a first-year (S1 or S2) division is generated
- **THEN** Basic Science faculty teach a substantial share of its slots, appearing as cross-department teaching
