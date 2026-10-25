# Proposal

## Why

The period-exchange workflow works but is hard to use correctly: the proposal form lists every slot in the college instead of eligible options, the store accepts duplicate proposals on the same slot and swaps that put faculty into subjects they are not qualified to teach, and supervision meetings can be exchanged away from their project supervisor. Cards do not make each proposal's status or next action obvious.

## What Changes

- **Eligible-option selection**: after a faculty member picks one of their slots, the exchange form lists only slots that can actually be swapped (same parity, no double-booking, mutually qualified faculty, not already in an open exchange or an approved swap); excluded slots are summarized by reason.
- **Stricter exchange rules**: proposals are refused when either slot is a supervision meeting, either participant is unqualified for the other's subject, or either slot already belongs to an open exchange. Approval on a slot that no longer exists is refused cleanly instead of raising an internal error.
- **Clear status and next action**: exchange cards show both periods (day, period time, subject, division, faculty) and the next required action — who must respond, which coordinator must approve, or that the swap is applied/closed.
- **Curriculum validation**: generator regression coverage is extended to every department × semester × section division, asserting exact weekly hours and parity-scoped clash freedom. Missing curriculum data (per-semester hours, lab/practical subjects, faculty availability) is reported, not invented.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `period-exchange`: proposals now require eligible counterparty slots (parity, qualification, no open exchange on either slot, no supervision meetings); the UI presents eligible options and clear next actions. (`period-exchange` is defined by the `expand-college-wide` delta; this change amends its requirements.)

## Impact

- **Code**: `campusly/store.py` (shared `_exchange_reasons`, `exchange_options`, stricter `propose_exchange`, clean `approve_exchange` refusal), `app.py` (faculty exchange page rework, coordinator card detail), `campusly/data.py` (`default_requirements` guard), `tests/` (sweep + exchange regression tests).
- **Dependencies**: none.
- **Compatibility**: previously accepted unqualified or supervision swaps are now refused — a deliberate tightening; substitution, generation, and publication safeguards are unchanged.
- **Out of scope**: per-semester curriculum data, lab-subject definitions, faculty availability windows (reported as missing information).
