# Spec Delta

## Purpose

Provides a demonstration-only role selector — Admin, Department Coordinator, Faculty, Student — that scopes which pages and actions the app shows, without implementing real authentication.

## ADDED Requirements

### Requirement: Pick a demo role
The system SHALL let the user switch freely among Admin, Department Coordinator, Faculty, and Student without credentials.

#### Scenario: Switch roles freely
- **WHEN** a user selects a different role
- **THEN** the visible pages and actions update immediately with no sign-in step

### Requirement: Coordinator role picks a department
Selecting the Department Coordinator role SHALL also select which department's coordinator is being demonstrated.

#### Scenario: Coordinator scoped to a department
- **WHEN** a user chooses Department Coordinator for CSE
- **THEN** review and approval actions apply only to CSE divisions

### Requirement: Role-scoped views and actions
The system SHALL show each role only the pages and actions appropriate to it.

#### Scenario: Admin sees management
- **WHEN** the role is Admin
- **THEN** calendar overrides, department and faculty management, subject assignments, and all timetable views are available

#### Scenario: Faculty sees own schedule and exchanges
- **WHEN** the role is Faculty
- **THEN** the faculty member's own timetable, exchange proposals and answers, and supervised project groups are available

#### Scenario: Student sees read-only division view
- **WHEN** the role is Student
- **THEN** the student sees their division's timetable, notices, and project groups with no editing actions

### Requirement: Shared data across roles
All roles SHALL observe the same shared in-memory data, so an action taken under one role is visible under the others.

#### Scenario: Cross-role visibility
- **WHEN** a Faculty proposes a period exchange and the user switches to the coordinator role
- **THEN** that exchange appears in the coordinator's pending items

### Requirement: Role selection is not authentication
Role selection SHALL NOT require, store, or verify credentials; it exists only to demonstrate role-scoped workflows and MUST NOT be presented as access control.

#### Scenario: No credentials requested
- **WHEN** any role is selected
- **THEN** no password, login, or identity check occurs
