# Tasks

## 1. Model & data extensions

- [x] 1.1 Add `GeneratedTimetable` dataclass and draft/published/discarded lifecycle constants to `models.py`; add optional `Room.kind` and `Subject.room_kind` fields with backward-compatible defaults.
- [x] 1.2 Factor `_week_mix` into `default_requirements(department)` in `data.py` (seed keeps identical output); type `LAB-*` rooms as `"lab"` and `GYM` as `"gym"` in the seed.
- [x] 1.3 Record `academic_year` on `Store` and expose a semester-window lookup for an arbitrary (academic_year, semester).

## 2. Generator

- [x] 2.1 Create `campusly/generator.py`: deterministic weekly placement of required subject hours for one division, reusing parity-scoped availability and qualified-teacher matching.
- [x] 2.2 Exclude the division's replaceable slots from occupancy; keep its supervision slots and all other divisions' slots as hard constraints; support pinned faculty assignments.
- [x] 2.3 Enforce room kind for lab-marked subjects and prefer consecutive same-day lab blocks; emit warnings when a preference can't be met.
- [x] 2.4 Report every unallocated hour and unsatisfied mandatory constraint as a violation; never emit a slot that violates a mandatory constraint.

## 3. Store lifecycle

- [x] 3.1 `generate_draft(class_group, academic_year, requirements, assignments)` → `GeneratedTimetable` stored as draft; regenerating replaces the existing draft for that key.
- [x] 3.2 `publish_draft(draft_id, on)` → gate on semester window, blocking violations, open proposals/exchanges, and supervision conflicts; revalidate all conflicts against the live timetable; atomically replace the division's non-supervision slots.
- [x] 3.3 `discard_draft(draft_id)` → remove draft without side effects; draft listing helpers for the UI.

## 4. Admin UI

- [x] 4.1 Add a "Generate timetable" tab to the Admin page: academic year, semester, department, division selects; editable weekly hours per subject with optional faculty pin.
- [x] 4.2 Generate → preview in the existing week grid; show violations and warnings; Publish and Discard actions; list existing drafts.

## 5. Tests & validation

- [x] 5.1 New `tests/test_generator.py`: hour allocation, faculty/room/division clash prevention, cross-department conflicts, determinism, infeasible requirements → violations, lab placement, draft isolation, publish/discard, publish gating and revalidation, protection of substitutions/exchanges/supervision.
- [x] 5.2 Full `pytest` run green and `openspec validate auto-timetable-generation --strict` clean; update tasks checkboxes as items complete.
