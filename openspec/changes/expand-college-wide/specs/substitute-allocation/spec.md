# Spec Delta

## ADDED Requirements

### Requirement: Availability evaluated college-wide
A faculty member SHALL be treated as busy whenever they hold a slot at that day and period in any department, so a substitute MUST NOT be double-booked across departments.

#### Scenario: Busy in another department
- **WHEN** a faculty member teaches an ECE division at the uncovered slot's day and period
- **THEN** that faculty member is never proposed to cover a CSE slot at that time

### Requirement: Prefer same-department substitutes
Among subject-qualified candidates the system MUST prefer a substitute whose home department matches the affected division's department, before weekly workload is compared.

#### Scenario: In-department candidate preferred
- **WHEN** a subject-qualified faculty member of the division's department and a subject-qualified faculty member of another department are both free
- **THEN** the in-department faculty member is proposed

#### Scenario: Cross-department substitute flagged
- **WHEN** the best available substitute belongs to a different department than the division
- **THEN** the proposal carries a cross-department warning shown in the review queue
