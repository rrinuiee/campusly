# Design

## Context

The working MVP (`campusly/` + `app.py`) models one flat institution: `Teacher`, `ClassGroup`, `Room`, `Subject`, weekly `TimetableSlot`s, and an in-memory `Store` held in `st.session_state`. The expansion generalizes this to a college without replacing the proven pieces. See proposal.md for motivation and scope.

## Goals / Non-Goals

**Goals:**
- Extend, don't rewrite: same layered structure (`models` / `data` / `engine` / `store` / `export` + thin Streamlit UI), same deterministic allocation, same absence → review → publish flow.
- One shared in-memory store so all four demo roles observe the same live data.
- Every existing test keeps passing; new tests cover the college behaviors.

**Non-Goals:**
- Persistence across restarts, real authentication, solver-based optimization, notifications, exam scheduling, attendance (unchanged from MVP).

## Decisions

- **Extend existing datatypes instead of renaming.** `Teacher` gains a `department` field; `ClassGroup` gains `department`, `semester`, `section` fields and is displayed as a "division" (id like `CSE-S3-A`); new `Department`, `ProjectGroup`, and `Exchange` dataclasses are added. Rationale: renaming `Teacher`→`Faculty` and `ClassGroup`→`Division` would churn every test for cosmetic gain; additive fields keep the suite green. "Faculty"/"division" are UI vocabulary over the same types.
- **Shared store via process-level singleton** (e.g. `st.cache_resource`), not `st.session_state`. The demo needs Faculty A's proposal visible to Faculty B and the coordinator across sessions; per-session state would fork the data. Data resets on restart — persistence is deferred by decision, not by accident. Acceptable trade-off: concurrent edits in a real deployment would need locking — irrelevant for the demo.
- **Academic calendar as data, not logic.** A `SemesterWindow {semester, start, end}` table defaults to odd = Jan 1–Jun 30, even = Jul 1–Dec 31 of the configured academic year; admin edits mutate the table. `active_semesters(date)` filters the table. Rationale: overrides become trivial and testable; no special-casing in scheduling code. Note: only one parity (odd or even) is ever in session at once — a division attends classes only while its own semester is active.
- **Division-scoped timetables, aggregated views.** The timetable remains a flat `list[TimetableSlot]`; each slot's `class_group` now identifies a (department, semester, section) division. Department and semester "timetables" are filtered projections, not separate structures — zero new storage, consistent with the MVP.
- **Subject assignments as offerings.** An offering = (division, subject, faculty) and generates that division's weekly slots for the subject; the seed builder produces offerings per division, then slots. Cross-department teaching is an offering whose faculty's home department differs from the division's — flagged, not forbidden. Assignments are validated against faculty double-booking at creation.
- **Exchange as a state machine layered like substitutions.** `Exchange` records (proposer, counterparty, their two slots, status). Lifecycle: `proposed` → (`accepted` → `approved`) with `declined` / `rejected` / `cancelled` terminal states. Validation at proposal time simulates the swap and rejects any that would double-book either faculty; the coordinator of the proposer's home department gives the single approval — confirmed: dual-coordinator approval for cross-department exchanges is deferred, not required. Applied exchanges write per-slot overrides into the same "effective timetable" overlay used by approved substitutions — the base timetable stays immutable, preserving the MVP's review boundary. Re-check conflicts at approval time in case a substitution landed meanwhile.
- **Divisions keep ~4 free periods per week.** The weekly mix schedules 26 of 30 slots, so supervision meetings (and ad-hoc offerings) can be placed without double-booking a division. Rationale: a fully booked division made every supervision slot a conflict by construction.
- **Supervision meetings are timetable slots.** Each project group gets a weekly slot whose subject marker is `supervision`; it appears in division and faculty timetables and in the absent supervisor's uncovered set — but the allocator never auto-assigns a substitute for it, flagging it for manual handling. Rationale: reuses views/workload/uncovered machinery; auto-substituting a project supervisor would be meaningless.
- **Absence reporting authority.** Only Admin or the absent faculty member's home-department coordinator reports absences — confirmed. Faculty self-report is deferred; it can be added later without model changes.
- **Role gating is a view filter.** `st.session_state.role` (+ department selection for the coordinator role) decides which pages render and which actions are offered. No permission enforcement beyond UI scope — explicitly demo-only per proposal.
- **Seed scale:** 6 departments — five engineering (CSE, ECE, EEE, ME, CE) plus Basic Science as a service department. ~10 faculty per engineering department and exactly 5 in Basic Science (~55 total). Divisions cover every semester S1–S8: CSE/ECE get sections A–C per semester, EEE/ME/CE get sections A–B (96 divisions total).
- **Timetables are generated per parity.** Only one semester parity is in session at a time, so odd- and even-semester divisions never compete for the same faculty/room slot; generation and double-booking checks run independently per parity (~48 simultaneous classes vs ~55 faculty). First-year divisions (S1/S2) are staffed preferentially by Basic Science faculty — that is the explicit first-year cross-department teaching requirement.

## Risks / Trade-offs

- [Shared singleton store means stale tabs can act on old state] → Acceptable for a demo; mitigated by deterministic ids and status checks that reject stale actions.
- [Exchange and substitution overlays can conflict (e.g. a slot is exchanged after a substitute was approved for it)] → Re-validate conflicts at approval time; coordinator sees the conflict warning and can reject.
- [Generalizing `ClassGroup` to carry department+semester adds fields every test fixture must supply] → Give new fields defaults or a single fixture helper; only signature-tight tests get touched.
- [College dataset increases timetable size ~4×] → Still a few hundred slots; generation and allocation remain instant and deterministic.
- [Role selector is trivially switchable, so "permissions" are cosmetic] → By design (demo, not auth); stated in spec and UI copy.
