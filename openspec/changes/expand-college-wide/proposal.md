# Proposal

## Why

The current MVP proves deterministic substitute allocation for a single flat school timetable (teachers + class groups). To make Campusly a credible college demo it must model the real structure of a college — departments, semesters, divisions, and faculty — including cross-department teaching, faculty-initiated period exchanges, and project supervision, while reusing the proven allocation core and demo flow.

## What Changes

- **College domain model**: departments are introduced; faculty have a home department; class groups become divisions scoped as (department, semester, section). Each department, semester, and division has its own timetable.
- **Academic calendar**: semesters S1–S8 with default windows — odd semesters (S1, S3, S5, S7) run January–June, even semesters (S2, S4, S6, S8) run July–December. Admin can override any semester's date range, and any working date resolves to the active semesters.
- **Subject assignments**: subjects belong to departments; a faculty member is assigned to teach a subject for a division, including cross-department teaching (a faculty member from one department teaching another department's division, visibly flagged).
- **Period exchange**: Faculty A proposes a swap of scheduled periods with Faculty B → Faculty B accepts or declines → the department coordinator approves or rejects → on approval both timetables update.
- **Project supervision**: divisions can have project groups with an assigned faculty supervisor; supervision meetings appear as scheduled slots on the relevant timetables.
- **Absence substitution at college scale**: a faculty absence uncovers every slot that faculty teaches across all departments (including supervision slots and cross-department assignments); the allocator still enforces college-wide hard constraints and now prefers same-department substitutes.
- **Department-scoped review**: the review queue is scoped so a department coordinator approves substitutions and exchanges affecting their own department's divisions.
- **Demo roles**: a role selector offers Admin, Department Coordinator, Faculty, and Student, scoping which pages and actions are visible. This is for demonstration only — no credentials, no real authentication.
- **Shared in-memory storage**: the app keeps one shared store so every role view in the demo sees the same live data. Persistence across restarts remains out of scope.
- **MVP preserved**: the existing absence → allocate → review → publish flow and its tests keep working; the college model generalizes the existing datatypes rather than replacing them.

## Capabilities

### New Capabilities

- `academic-calendar`: Semester definitions (S1–S8), default odd/even semester date windows, admin calendar overrides, and resolving a working date to active semesters.
- `college-structure`: Departments, faculty with home departments, divisions scoped by department + semester + section, and the per-division timetables that aggregate into department and semester views. Includes the college-scale seed dataset.
- `subject-assignment`: Department-owned subjects, subject offerings per division, faculty-to-offering assignment, and cross-department teaching assignments.
- `period-exchange`: Faculty-to-faculty period swap workflow with faculty acceptance and department coordinator approval before timetables update.
- `project-supervision`: Project groups per division, supervisor assignment, and supervision meetings as timetable slots.
- `demo-roles`: Demonstration-only role selection (Admin, Department Coordinator, Faculty, Student) that scopes visible views and permitted actions.

### Modified Capabilities

- `absence-reporting`: Absences are reported for faculty; uncovered periods span every department where the faculty teaches; the seeded demo dataset becomes a college dataset.
- `substitute-allocation`: Candidates and hard constraints apply across the whole college timetable; same-department substitutes are preferred after subject match.
- `timetable-review`: The review queue and approval authority are scoped to the coordinator's own department.
- `schedule-views`: Timetable views are selectable by department, semester, and division, plus per-faculty and per-division (student) views.

## Impact

- **Code**: `campusly/models.py` (Department, Faculty fields, Division scoping, Exchange, ProjectGroup), `campusly/data.py` (college seed data + calendar), `campusly/engine.py` (department-aware ranking), `campusly/store.py` (shared store, exchange workflow, scoped views), `app.py` (role selector, new/extended pages). Existing test scenarios must stay green.
- **Dependencies**: none new — still `streamlit`, `pytest`, and the standard library.
- **Compatibility**: no external API. Internal model fields are additive; the session-local store becomes a shared store (intended demo behavior change).
- **Out of scope**: real authentication/authorization, persistence across restarts, notifications to real channels, global timetable optimization, exam scheduling, attendance tracking, multi-week batch planning.
