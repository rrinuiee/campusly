# Tasks

## 1. Domain model extension

- [x] 1.1 Extend `campusly/models.py`: add `Department`; add `department` to `Teacher`; add `department`, `semester`, `section` to `ClassGroup` (division identity, e.g. `CSE-S3-A`); add `ProjectGroup`, `Exchange` dataclasses and exchange status constants — verify `pytest` still passes (new fields defaulted or fixtures updated minimally)
- [x] 1.2 Add `campusly/data.py` semester-window model: defaults odd=S1/S3/S5/S7 Jan 1–Jun 30, even=S2/S4/S6/S8 Jul 1–Dec 31; `active_semesters(date)` resolver — verify pytest covers default windows and October-date → even semesters

## 2. College seed data + calendar override

- [x] 2.1 Build the fictional college dataset (6 departments: CSE, ECE, EEE, ME, CE + Basic Science; ~10 faculty per engineering dept, exactly 5 in Basic Science; divisions A–C for CSE/ECE and A–B for EEE/ME/CE across every semester S1–S8; per-division timetables generated per semester parity, with S1/S2 first-year divisions staffed preferentially by Basic Science faculty) — verify pytest asserts referential integrity and zero same-parity faculty/room double-booking
- [x] 2.2 Add admin calendar override on `Store` (set a custom window per semester; overrides reset on restart) — verify pytest shows an overridden semester resolving as active on a date outside its default window

## 3. Subject assignments + project supervision

- [ ] 3.1 Implement subject offerings (division, subject, assigned faculty) that generate division timetable slots, including a cross-department flag when faculty home department ≠ division department; reject assignments that double-book faculty — verify pytest covers offering→slots, reassignment, conflict rejection, cross-department flag
- [ ] 3.2 Implement project groups and weekly supervision slots on supervisor + division timetables, with conflict rejection and supervisor reassignment — verify pytest covers create, reassign, and supervisor-absence flagging (uncovered, manual handling)

## 4. Store: shared state, scoping, exchanges

- [ ] 4.1 Switch the app to one shared `Store` instance (process-level, e.g. `st.cache_resource`) — verify a unit test or two-session manual check shows actions visible across sessions
- [ ] 4.2 Implement the exchange lifecycle in `Store` (propose with swap-feasibility check → accept/decline/cancel → coordinator approve with conflict re-check → atomic effective-timetable overrides on both slots) — verify pytest covers approve, decline, cancel, reject, and late-conflict refusal
- [ ] 4.3 Add department-scoped queries (pending queue filtered to coordinator's department; division→department lookup) and restrict absence reporting to Admin or the absent faculty's department coordinator — verify pytest covers scoping and refused cross-department actions

## 5. Allocation engine updates

- [ ] 5.1 Extend `allocate`: evaluate busy faculty college-wide, rank candidates subject-match → same-department → workload → id, and emit a `cross-department` warning — verify pytest covers cross-department busy exclusion and in-department preference while existing allocation tests stay green
- [ ] 5.2 Exclude supervision slots from automatic substitute assignment (always flag uncovered for manual handling) — verify pytest covers a supervisor absence producing a flagged supervision slot

## 6. Streamlit UI

- [ ] 6.1 Add the demo role selector (Admin / Department Coordinator + department / Faculty / Student) and role-scoped page map — verify each role sees only its pages and switching needs no credentials
- [ ] 6.2 Add Admin pages: semester calendar overrides and subject-offering management — verify an override changes the offered semesters and an assignment updates the division timetable in the UI
- [ ] 6.3 Add exchange UI: faculty propose/respond to exchanges, coordinator approves — verify the full propose→accept→approve→both-timetables-update flow renders correctly
- [ ] 6.4 Extend timetable views: department/semester/division selectors, faculty timetable, student division view, project groups and supervision slots — verify approved substitutions, applied exchanges, and uncovered/cross-department flags all render
- [ ] 6.5 Update `README.md` for the college features (roles, departments, exchanges, calendar) — verify the documented commands still run as written

## 7. Verification

- [ ] 7.1 Run `pytest` — all existing and new tests pass
- [ ] 7.2 Run the full demo end-to-end once: seed → absence → allocate → coordinator approve → faculty exchange lifecycle → per-role timetable views

## Workflow follow-up

- Archive the change after review requirements are satisfied (`openspec archive expand-college-wide`).
- Verify the archived result with `openspec list` / `openspec list --specs`.
