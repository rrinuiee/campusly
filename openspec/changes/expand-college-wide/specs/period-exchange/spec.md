# Spec Delta

## Purpose

Lets two faculty members swap scheduled teaching periods through a propose → accept → coordinator-approve workflow, so timetable changes initiated by faculty still pass through department review.

## ADDED Requirements

### Requirement: Propose a period exchange
A faculty member SHALL propose exchanging one of their own scheduled slots with one scheduled slot taught by another faculty member, creating a pending exchange; the system MUST reject a proposal whose swap would double-book either participant.

#### Scenario: Proposal created
- **WHEN** Faculty A selects their Tuesday period-4 slot and Faculty B's Thursday period-2 slot and submits
- **THEN** a pending exchange naming both faculty and both slots is recorded for Faculty B to answer

#### Scenario: Conflicting swap rejected upfront
- **WHEN** Faculty B already teaches at the day and period of Faculty A's offered slot
- **THEN** the proposal is rejected with the conflict shown and nothing is recorded as pending

### Requirement: Counterparty accepts or declines
Only the counterparty faculty member SHALL respond to a pending exchange; accepting forwards it to coordinator review, declining closes it with no effect, and the proposer MAY cancel it before the counterparty responds.

#### Scenario: Acceptance forwards to coordinator
- **WHEN** Faculty B accepts a pending exchange
- **THEN** it is marked accepted and awaits department coordinator approval

#### Scenario: Decline closes the request
- **WHEN** Faculty B declines a pending exchange
- **THEN** the exchange is closed and both timetables remain unchanged

#### Scenario: Proposer cancels before answer
- **WHEN** Faculty A cancels an exchange Faculty B has not yet answered
- **THEN** the exchange is closed with no timetable change

### Requirement: Coordinator approval applies the swap
The coordinator of the proposing faculty's department SHALL approve or reject an accepted exchange; approval MUST swap the two slots' faculty atomically in both timetables, and rejection MUST leave both timetables unchanged.

#### Scenario: Approval updates both timetables
- **WHEN** the coordinator approves an accepted exchange of A's slot and B's slot
- **THEN** A's timetable shows B teaching A's former slot and B's timetable shows A teaching B's former slot

#### Scenario: Rejection leaves timetables unchanged
- **WHEN** the coordinator rejects an accepted exchange
- **THEN** both timetables still show the original faculty

### Requirement: No timetable change before approval
The system MUST NOT alter either effective timetable while an exchange is pending or merely accepted.

#### Scenario: Accepted but unapproved exchange invisible
- **WHEN** an exchange is accepted but not yet approved
- **THEN** both timetables still show the original faculty for both slots

### Requirement: Approval re-validates conflicts
Before applying an approved exchange, the system MUST verify neither resulting assignment conflicts with substitutions or other changes approved since the proposal; a conflicting approval SHALL be refused with a warning.

#### Scenario: Late conflict blocks approval
- **WHEN** a substitution approved after the exchange was proposed would make the swap double-book Faculty B
- **THEN** the approval is refused and the coordinator sees the conflict
