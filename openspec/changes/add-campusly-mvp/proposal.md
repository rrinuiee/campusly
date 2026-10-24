# Proposal

## Why

Schools and colleges lose teaching time when a teacher is absent and no substitute is found in time — coordinators currently juggle spreadsheets and phone calls under time pressure. Campusly is a hackathon MVP that demonstrates deterministic, constraint-based substitute allocation with a coordinator approval workflow, replacing ad-hoc manual scheduling.

## What Changes

- Streamlit dashboard preloaded with fictional institution data (teachers, subjects, rooms, classes, weekly timetable) so the demo runs locally with zero setup.
- Teacher absence reporting: mark a teacher absent for a date and see which of their scheduled periods need coverage.
- Deterministic substitute allocation engine that assigns a substitute teacher and room per affected period using subject suitability, availability, workload fairness, and hard scheduling constraints; periods with no suitable substitute are flagged as uncovered.
- Conflict prevention: a substitute cannot be double-booked in the same period, cannot teach a class they already conflict with, and rooms cannot be double-booked.
- Coordinator review queue: proposed substitutions must be approved or rejected before the timetable is updated.
- Published outputs after approval: updated timetable view, notices for affected classes, substitute workload summary, and CSV export of the approved changes.

## Capabilities

### New Capabilities

- `absence-reporting`: Recording teacher absences and deriving the set of scheduled periods that require substitute coverage.
- `substitute-allocation`: Deterministic, constraint-based assignment of substitute teachers and rooms to uncovered periods, including fairness scoring and uncovered-class flagging.
- `timetable-review`: Coordinator review, approval, or rejection of proposed substitutions before any timetable change is applied.
- `schedule-views`: Read-only published outputs — updated timetable, notices, substitute workload summary, and CSV export.

### Modified Capabilities

<!-- None: greenfield project, no existing specs. -->

## Impact

- **New codebase**: Python package + Streamlit app, fictional seed data, pytest tests. No existing code is affected.
- **Dependencies**: `streamlit`, `pytest`; standard library otherwise. No paid APIs, no network calls; runs locally.
- **Out of scope**: authentication/roles, persistence beyond session state + in-memory/seed data, notifications to real email/SMS, optimization for multiple days at once, college-specific extras beyond the adaptable data model.
