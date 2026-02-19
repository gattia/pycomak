# Completed: Codebase Bug Fixes & Hardening

**Plan:** `.claude/plans/codebase-bugfixes-hardening_PLAN.md`
**Date:** 2026-02-18
**Branch:** menisci

## Summary

All 5 parts executed. 171 tests pass (up from 151 before).

---

## Part 1: Silent-Wrong-Result Bugs — All Done

| Item | Status | Notes |
|------|--------|-------|
| 1a. `add_subject` list sync | Done | Moved appends to after JAM success |
| 1b. `contact_accessor` None return | Done | Added ValueError for unrecognized axis in both accessors |
| 1c. `analyze_criteria` mutates dict | Done | Added `copy.deepcopy()` at top |
| 1d. NaN passes criteria | Done | Added NaN/Inf check before `np.ptp()` |
| 1e. `load_secondary_constraints` init | Done | Changed to `if key not in dict` |
| 1f. Zero-fill for skipped subjects | Done | Changed to `np.full(..., np.nan)` |
| 1g. `jam_analysis` first file init | Done | Changed to `if not hasattr(self, 'num_time_steps')` |
| 1h. Empty file list | Done | Added `raise ValueError` |

## Part 2: Plotting & Unit Fixes — All Done

| Item | Status | Notes |
|------|--------|-------|
| 2a. Radians plotted as degrees | Done | Added `np.rad2deg()` in both comparison and individuals functions |
| 2b. Dead `show_range` code | Done | Replaced with `show_ste`/`show_std` parameters |
| 2c. Translation label `(mm)` vs `(m)` | Done | Changed to `(m)` for translations, `(rad)` for rotations |
| 2d. Redundant ste handling | Done | Simplified to single line |

## Part 3: Dead Code & Docstring Fixes — All Done

| Item | Status | Notes |
|------|--------|-------|
| 3a. Remove `convert_to_radians` | Done | Removed param, commented code, and call site |
| 3b. Docstring "0.25" → "0.6" | Done | |
| 3c. `list_musccles` typo | Done | Renamed to `list_muscles` |
| 3d. Bare `Exception` types | Done | Changed to `TypeError` and `ValueError` |
| 3e. `muscle_outcomes` docstring | Done | Fixed contradiction |

## Part 4: Defensive Hardening — All Done

| Item | Status | Notes |
|------|--------|-------|
| 4a. Uninitialized `coordinate_index` | Done | Added default + warning |
| 4b. `jam_evaluation` 1D axes | Done | Added `np.atleast_2d(ax)` |
| 4c. Forsim failure reason | Done — **deviated from plan** | Instead of renaming to `'forsim_failed'`, added `self.failure_reason` attribute to `COMAKforsim` (`'forsim_timeout'` or `'forsim_crash'`). Optimizer now uses `comak_forsim.failure_reason` for accurate recording. |
| 4d. `get_*_data` KeyError guard | Done | Added to all 5 methods |

### 4c deviation detail
The plan proposed simply renaming the string from `'forsim_timeout'` to `'forsim_failed'`. User rejected this twice — they wanted the actual failure reason preserved. Solution: `COMAKforsim.run_forsim()` now sets `self.failure_reason` to either `'forsim_timeout'` (TimeoutError) or `'forsim_crash'` (RuntimeError), and the optimizer records whichever value it is.

### Additional fix discovered during testing
The `regional_accessor` in `get_regional_contact_data` needed `axis='pressure'` and `axis='area'` to be treated as pass-through values (scalar data, no axis indexing needed). The initial fix from 1b was too aggressive — it rejected these valid axis values. Fixed to only raise ValueError for truly unrecognized values.

## Part 5: Test Additions — All Done

| Item | Status | New tests |
|------|--------|-----------|
| 5a. NaN detection for remaining methods | Done | 3 tests: ligament, contact force, regional contact |
| 5b. No min/max in muscle stats | Done | 1 test |
| 5c. Failed JAM doesn't corrupt lists | Done | 1 test |
| 5d. Bad axis raises ValueError | Done | 2 tests (contact force + regional contact) |
| 5e. Empty file list raises | Done | 1 test |
| 5f. `analyze_criteria` NaN detection | Done | 2 tests (ligament + coord) |
| 5g. `analyze_criteria` no mutation | Done | 1 test |
| Bonus: empty jam_list KeyError | Done | 5 tests (one per get_*_data method) |

Also fixed 2 existing tests in `test_plotting_utils.py` that expected old labels `(deg)` and `(mm)`.

## Files Modified

| File | Changes |
|------|---------|
| `pycomak/group_analysis.py` | 1a, 1b, 1e, 1f, 3e, 4d, regional_accessor fix |
| `pycomak/forsim.py` | 1c, 1d, 3a, 4b, 4c (failure_reason attribute) |
| `pycomak/jam_analysis.py` | 1g, 1h, 3d |
| `pycomak/plotting_utils.py` | 2a, 2b, 2c, 2d |
| `pycomak/defaults.py` | 3b, 3c |
| `pycomak/comak_ik.py` | 4a |
| `pycomak/knee_optimizer.py` | 4c (uses failure_reason) |
| `tests/test_group_analysis.py` | 5a, 5b, 5c, 5d, empty jam_list tests |
| `tests/test_jam_analysis.py` | 5e |
| `tests/test_forsim_criteria.py` | 5f, 5g |
| `tests/test_plotting_utils.py` | Fixed label assertions for 2c |

## Test Results

```
171 passed, 0 failed, 3 warnings
```

## Future Considerations

- The `regional_accessor` axis handling could be documented more explicitly — the current `'pressure'`/`'area'` pass-through is implicit behavior
- `KneeOptimizer.list_eval_results` now contains a mix of strings (`'forsim_timeout'`, `'forsim_crash'`) and dicts (from `jam_evaluation`) — downstream code checking `== 'forsim_timeout'` will still work, code checking `== 'forsim_failed'` would need updating
- Consider adding `'settle_sim_crash'` to CLAUDE.md breaking changes table (already listed)
