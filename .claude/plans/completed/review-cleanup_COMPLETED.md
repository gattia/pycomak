# Post-Review Cleanup — COMPLETED

**Plan:** `.claude/plans/completed/review-cleanup_PLAN.md`
**Date completed:** 2026-02-18

## What was done

Reviewed all prior AI agent refactoring work (4 sessions: test suite, test overhaul,
code fixes, bug fixes). Then implemented cleanup based on findings.

### Source code changes

| File | Change |
|------|--------|
| `group_analysis.py` | Added `_extract_subject_value()` static helper for KeyError re-raising |
| `group_analysis.py` | Refactored 5 `get_*_data` methods to use helper (eliminated ~35 lines of duplication) |
| `group_analysis.py` | Removed `'min'`/`'max'` from `get_muscle_data` stats dict (inconsistent with other 4 methods) |
| `group_analysis.py` | Deleted 38-line speculative TODO comment block (lines 1264-1302) |
| `forsim.py` | Added `except RuntimeError` to `run_forsim()` — subprocess crashes now return `False` |
| `knee_optimizer.py` | Added `except RuntimeError` to settle sim call — records `'settle_sim_crash'`, continues loop |

### Test changes

| File | Change |
|------|--------|
| `test_group_analysis.py` | Updated `TestGetMuscleData.test_return_stats` — checks consistent stats keys |
| `test_group_analysis.py` | Added `TestAddSubject` class (4 tests): H5 loading, missing file, filtering, multi-subject |

### Decisions from review

| Topic | Decision |
|-------|----------|
| `removal_history` | **Keep** — user uses it for iterative outlier removal tracking |
| `startswith` vs `in` match_type param | **No change** — `startswith` is correct for OpenSim naming, KISS |
| Plotting smoke tests | **Keep as-is** — catch import/signature breaks, not worth investing more |
| `_get_file_structure` inline comparison | **No change** — minor style issue, not worth the churn |
| Speculative TODO block | **Deleted** — content saved for GitHub issue |

## Final test results

```
151 passed, 0 failed (was 147 before)
```

## Things to consider for the future

1. **NaN/Inf handling** — No tests for NaN values in H5 data. A crashed simulation could
   produce NaN, which silently propagates through `np.mean`/`np.std`. Worth adding a check
   or at least a test documenting the behavior.

2. **`allow_mismatched_files=False` default** — May surprise users who were previously
   combining H5 files with different structures. Error message is clear, but worth noting
   in migration if this code is shared.

3. **`get_muscle_data` min/max removal** — If you were using `min`/`max` from muscle stats
   elsewhere, those calls will now KeyError. All other `get_*_data` methods never had them.

4. **`settle_sim_crash` in knee_optimizer** — New string value in `_list_eval_results`.
   If downstream code checks for specific result strings, it should handle this new value.
