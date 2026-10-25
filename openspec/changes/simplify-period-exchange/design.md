# Design

## Context

`Store.propose_exchange` already simulates the swap and refuses double-booking; `approve_exchange` re-validates before applying overrides. Gaps: no duplicate check on slots already in an open exchange, no subject-qualification check, supervision slots are exchangeable (which would orphan `ProjectGroup.supervisor`), approval on a removed slot raises `KeyError`, and the faculty UI lists every slot in the college rather than feasible options.

## Goals / Non-Goals

**Goals:**

- One shared eligibility check (`_exchange_reasons`) used by `propose_exchange`, the new `exchange_options` helper, and effectively enforced again at approval.
- Faculty UI that selects an own slot → shows only eligible counterparty slots → proposes, with both periods and the next action always visible.

**Non-Goals:**

- Changing the exchange lifecycle (propose → accept → approve stays), room swapping, date-specific exchanges, or notification mechanics.
- Per-semester curriculum and lab-subject data — audited and reported as missing, not invented.

## Decisions

- **Reasons, not exceptions, for eligibility**: `_exchange_reasons(proposer, sa, sb)` returns a list of human-readable blockers (double-booking, self-swap, supervision, open exchange on either slot, missing qualification). `propose_exchange` raises only when the list is non-empty, preserving existing error substrings (`"double-book"`, `"yourself"`, `"not taught by the proposer"`); `exchange_options` reuses it to filter the candidate list, so UI eligibility and store validation cannot drift apart.
- **Supervision blocked, not qualified-checked**: supervision slots are refused outright; the qualification check applies to real subjects only.
- **Approval unchanged in shape**: existing re-validation stays; `_slot` failures during approval are converted to a clean `ValueError` instead of `KeyError`.
- **Eligible-options filter mirrors the old UI filter** (same parity, not own slot, not overridden) plus the new reasons check; the UI shows a count of excluded options rather than hiding that they exist.

## Risks / Trade-offs

- Tighter rules can refuse swaps users previously made (unqualified teaching) → deliberate per the new spec; the refusal message names the reason.
- `exchange_options` scans the whole timetable per own-slot selection → ~2,500 rows, trivial for the demo's in-memory data.
