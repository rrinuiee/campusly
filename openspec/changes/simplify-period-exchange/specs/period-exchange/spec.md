# Spec Delta

## Purpose

Tightens the period-exchange workflow: only eligible counterparty slots may be proposed, and every exchange clearly shows both periods, its status, and the next required action. (The `period-exchange` capability spec is introduced by the `expand-college-wide` change; these requirements extend its proposal rules.)

## ADDED Requirements

### Requirement: Exchange proposals are eligibility-checked

In addition to refusing swaps that double-book a participant, the system MUST refuse a proposal when either faculty member is not qualified for the subject they would take over, when either slot is a project-supervision meeting, or when either slot already belongs to an open or approved exchange.

#### Scenario: Unqualified swap refused

- **WHEN** a faculty member would take over a subject they are not qualified to teach
- **THEN** the proposal is refused with an explanation and nothing is recorded

#### Scenario: Supervision slot refused

- **WHEN** either slot in a proposed exchange is a project-supervision meeting
- **THEN** the proposal is refused because supervision stays tied to the project supervisor

#### Scenario: Duplicate or stale proposal refused

- **WHEN** either slot already belongs to an open (proposed or accepted) exchange
- **THEN** the new proposal is refused and nothing is recorded

### Requirement: Eligible exchange options are presented

After a faculty member selects one of their scheduled slots, the system SHALL present only counterparty slots that can actually be swapped — same semester parity, no double-booking for either participant, mutual subject qualification, and not already part of an exchange — each shown with its day, period, subject, division, and faculty member.

#### Scenario: Options filtered to feasible swaps

- **WHEN** a faculty member picks a slot to offer
- **THEN** only eligible counterparty slots are offered for selection, and ineligible slots are excluded rather than silently failing at submission

### Requirement: Exchange status and next action are explicit

Each exchange SHALL display both periods in full (day, period, subject, division, faculty) and its current status with the next required action, so each participant knows who must act next.

#### Scenario: Proposer sees pending state

- **WHEN** a proposal has been sent but not answered
- **THEN** the proposer sees that the counterparty's response is awaited and may cancel

#### Scenario: Counterparty sees both periods

- **WHEN** a counterparty reviews an incoming proposal
- **THEN** both their own slot and the offered slot are shown in full before they accept or decline

#### Scenario: Coordinator sees approval state

- **WHEN** an exchange is accepted
- **THEN** the proposer's department coordinator sees it as awaiting their approval, and timetables change only after approval
