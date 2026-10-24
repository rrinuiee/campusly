# Spec Delta

## Purpose

Tracks division project groups and their assigned faculty supervisors, scheduling supervision meetings as timetable slots so they appear in timetable views and interact correctly with absence handling.

## ADDED Requirements

### Requirement: Project groups per division
The system SHALL let an Admin or the division's department coordinator create project groups within a division, each with a title and an assigned faculty supervisor who MAY come from any department.

#### Scenario: Project group created
- **WHEN** a coordinator creates project group "Smart Grid" for division ECE-S6-B with a faculty supervisor
- **THEN** the group is listed under that division with its supervisor

### Requirement: Supervision meetings are timetable slots
Each project group SHALL have a weekly supervision slot (day, period, room) that appears on both the supervisor's timetable and the division's timetable, and the slot MUST NOT double-book the supervisor or the room.

#### Scenario: Supervision slot visible
- **WHEN** a project group has a Friday period-5 supervision slot
- **THEN** that slot appears in the supervisor's timetable and the division's timetable

#### Scenario: Conflicting supervision slot rejected
- **WHEN** the chosen supervision time collides with the supervisor's existing teaching
- **THEN** the slot is rejected with the conflict shown

### Requirement: Supervisor reassignment
Changing a project group's supervisor SHALL update the supervision slot's attribution on the affected timetables.

#### Scenario: New supervisor sees the slot
- **WHEN** a project's supervisor is changed
- **THEN** the supervision slot leaves the old supervisor's timetable and appears on the new one's

### Requirement: Supervisor absences flag supervision slots
When a supervisor is absent on a date containing a supervision slot, that slot SHALL appear among the uncovered periods, flagged for manual handling rather than automatic substitute allocation.

#### Scenario: Absent supervisor
- **WHEN** a supervisor is reported absent on their supervision day
- **THEN** the supervision slot is listed as uncovered and marked as needing manual handling
