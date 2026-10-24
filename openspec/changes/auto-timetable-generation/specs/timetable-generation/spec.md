# Spec Delta

## Purpose

Lets an administrator automatically generate a division's weekly timetable for a chosen academic year and semester, preview it, and publish or discard it — without disturbing the currently published timetables or existing substitution, exchange, and supervision workflows.

## ADDED Requirements

### Requirement: Target selection for generation

The system SHALL let an administrator choose a target academic year, a semester (S1–S8), and a division before generating a timetable.

#### Scenario: Select generation target

- **WHEN** the administrator opens timetable generation
- **THEN** they can pick an academic year, a semester, and a division of the chosen department

#### Scenario: Future academic year allowed

- **WHEN** the administrator selects an academic year later than the current one
- **THEN** generation proceeds against the published timetable as it stands, without modifying it

### Requirement: Reviewable weekly subject hours

Before generation, the system SHALL present the required weekly hours per subject for the target division and SHALL let the administrator edit them, including assigning a specific faculty member per subject where desired.

#### Scenario: Default curriculum shown and editable

- **WHEN** a target division is chosen
- **THEN** default weekly hours per subject are shown and the administrator may adjust hours or pin a faculty member before generating

#### Scenario: Requirements are explicit input

- **WHEN** the administrator changes a subject's weekly hours
- **THEN** the generated timetable allocates exactly the configured hours, not a fixed curriculum

### Requirement: Mandatory scheduling constraints

Generation MUST NOT produce a timetable in which a division has two classes in the same period, a faculty member teaches two classes at the same day and period within the semester's parity, a room hosts two classes at the same day and period within the parity, or a faculty member teaches a subject they are not qualified for unless explicitly assigned by the administrator.

#### Scenario: No clashes across the college

- **WHEN** generation places a slot
- **THEN** it never double-books the division, the faculty member, or the room against any existing slot in the same semester parity, in any department

#### Scenario: Laboratory rooms where data exists

- **WHEN** a subject is marked as requiring a laboratory and room kind data exists
- **THEN** the generator places that subject only in a laboratory room and, when consecutive lab periods are required and expressible in the data, places them back-to-back on the same day

### Requirement: Violations are reported, never hidden

The system SHALL report every unallocated subject hour and every unsatisfied mandatory constraint as violations on the draft, and MUST NOT present a draft with unresolved mandatory violations as a valid publishable timetable.

#### Scenario: Infeasible requirements reported

- **WHEN** required hours cannot all be placed (for example demand exceeds the weekly grid or no qualified faculty is free)
- **THEN** the draft lists the unallocated hours with reasons instead of silently dropping them

### Requirement: Deterministic generation

Generation SHALL be deterministic: identical inputs (division, requirements, existing timetable) always produce the same draft.

#### Scenario: Repeat generation identical

- **WHEN** the administrator generates twice with unchanged inputs
- **THEN** both drafts contain identical slots

### Requirement: Draft does not mutate the published timetable

Generating or previewing a draft MUST NOT change the published timetable, proposals, exchanges, project groups, or any view of them.

#### Scenario: Draft is isolated

- **WHEN** a draft has been generated but not published
- **THEN** every timetable, review queue, and faculty view is exactly as before generation

### Requirement: Publication lifecycle

A draft SHALL move through a draft → published or draft → discarded lifecycle. Publishing MUST revalidate all mandatory conflicts against the live timetable at publish time, MUST refuse when the draft's academic period is not yet in session, and on success SHALL atomically replace the division's generated scope. Discarding SHALL remove the draft without side effects.

#### Scenario: Publish blocked before the period begins

- **WHEN** the administrator tries to publish a draft for a semester window that is not active on the working date
- **THEN** publication is refused with an explanation and the published timetable is unchanged

#### Scenario: Publish revalidates

- **WHEN** another change created a conflict after the draft was generated
- **THEN** publication is refused and the conflicting slots are reported

#### Scenario: Discard drops the draft

- **WHEN** the administrator discards a draft
- **THEN** the draft is gone and nothing else changes

### Requirement: Existing workflows preserved

Publishing a draft MUST NOT silently break substitution, period-exchange, or project-supervision workflows; where publication cannot be made safe (for example a referenced supervision slot would be removed), the system SHALL block publication and explain why.

#### Scenario: Supervision slot protects publication

- **WHEN** publishing would remove a slot that a project group's supervision meeting depends on
- **THEN** publication is blocked with an explanatory violation

#### Scenario: Existing flows still work after publication

- **WHEN** a draft is published
- **THEN** absences, substitutions, and exchanges continue to operate on the new published slots
