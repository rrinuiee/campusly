# Proposal

## Why

Campusly's timetable today is entirely seeded or hand-built one slot at a time through `add_offering`. Administrators need to prepare next academic year's timetables — with per-division weekly subject hours, faculty assignments, and clash checking — while the current year's published timetables stay active.

## What Changes

- **Automatic timetable generation**: an Admin selects a target academic year, semester, and division; reviews/edits required weekly subject hours; and generates a draft timetable from the subject catalog, faculty qualifications, and rooms using the existing deterministic teacher-matching approach.
- **Draft → published lifecycle**: generated timetables are drafts scoped to (academic_year, division). Drafts never touch the published timetable. Publishing revalidates all hard conflicts, refuses when the draft's academic period is not yet in session or when safe publication cannot be guaranteed, and replaces the division's existing subject slots. Discarding drops the draft.
- **Curriculum configuration**: weekly subject-hour requirements per division are explicit generator input, defaulted from the department mix used by the seed, editable before generation. Faculty assignments may be given explicitly or left to automatic qualified-teacher matching.
- **Constraint reporting**: unallocated subject hours and unsatisfied mandatory constraints are reported as violations on the draft; a draft with unresolved mandatory violations cannot be treated as valid. Room and laboratory constraints are enforced where the data supports them (optional room kind / lab requirement fields).
- **Conflict scope**: clash checks span all divisions in the same semester parity, matching the existing availability rules used by substitutions, exchanges, and supervision slots.

## Capabilities

### New Capabilities

- `timetable-generation`: Administrator-driven draft timetable generation for a target academic year, semester, and division, including curriculum (weekly-hours) input, automatic faculty/room matching, mandatory-constraint enforcement with violation reporting, preview, and the draft → published/discarded lifecycle.

### Modified Capabilities

- None. Room/laboratory typing and publication semantics are introduced as part of the new `timetable-generation` capability; no existing requirement changes.

## Impact

- **Code**: `campusly/models.py` (GeneratedTimetable, lifecycle constants, optional Room.kind / Subject.lab fields), `campusly/generator.py` (new deterministic generator), `campusly/data.py` (shared `default_requirements`, lab-room seed typing), `campusly/store.py` (draft lifecycle + publish revalidation), `app.py` (Admin "Generate New Timetable" workflow), `tests/` (new generator/lifecycle tests).
- **Dependencies**: none new — still `streamlit`, `pytest`, stdlib.
- **Compatibility**: base timetable, substitutions, exchanges, and project supervision are preserved; publication of a future-year draft is blocked until its semester window is active so existing workflows keep operating on the current timetable.
- **Out of scope**: multi-division batch generation (one division at a time for V1), teacher preferences, workload optimization, persistence across restarts.
