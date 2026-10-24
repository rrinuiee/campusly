# substitute-allocation Specification

## Purpose
Deterministically assigns substitute teachers and rooms to periods left uncovered by absences, respecting hard scheduling constraints and preferring fair, subject-appropriate choices.

## Requirements

### Requirement: Propose a substitute for every uncovered period
When an absence creates periods needing coverage, the system MUST evaluate each period independently and either propose a substitute teacher and room or mark it uncovered.

#### Scenario: Proposal generated per period
- **WHEN** an absence affects 3 scheduled periods
- **THEN** the system produces exactly 3 proposals, each either assigned (teacher + room) or flagged uncovered

### Requirement: Enforce hard scheduling constraints
A proposed substitute MUST be free during that period, MUST NOT be the absent teacher, MUST NOT be assigned to two periods at once, and the assigned room MUST be free during that period.

#### Scenario: Busy teacher never proposed
- **WHEN** a teacher already teaches another class during the uncovered period
- **THEN** that teacher is never proposed for that period

#### Scenario: No double booking
- **WHEN** two uncovered periods occur at the same time and only one suitable teacher exists
- **THEN** at most one of them is assigned to that teacher

#### Scenario: Room conflict prevented
- **WHEN** the room for an uncovered period is occupied at that time
- **THEN** the proposal assigns a different free room or the period is flagged

### Requirement: Prefer suitable and fair assignments
Among valid candidates the system MUST prefer teachers qualified for the subject and MUST prefer teachers with the lower substitute workload so far.

#### Scenario: Subject match preferred
- **WHEN** a mathematics period is uncovered and both a mathematics teacher and a non-mathematics teacher are free
- **THEN** the mathematics teacher is proposed

#### Scenario: Workload fairness tie-break
- **WHEN** two equally suitable teachers are free and one has taken more substitutions this week
- **THEN** the teacher with fewer substitutions is proposed

#### Scenario: Fallback when no subject match
- **WHEN** no subject-qualified teacher is free but another teacher is free
- **THEN** the system proposes the free teacher and marks the proposal as non-subject-matched

### Requirement: Flag periods with no suitable substitute
If no teacher satisfies the hard constraints for a period, the system MUST mark it uncovered and keep it visible to the coordinator.

#### Scenario: Uncovered period flagged
- **WHEN** every qualified teacher is busy during an uncovered period and no fallback is allowed or available
- **THEN** the period is flagged uncovered with the affected class shown for manual handling

### Requirement: Deterministic results
Given identical input data, the allocation engine MUST always produce the same assignments.

#### Scenario: Reproducible allocation
- **WHEN** the same absence is processed twice against the same dataset
- **THEN** both runs produce identical proposals in identical order
