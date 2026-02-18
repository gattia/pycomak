# Fix Bugs & Critical Test Gaps — COMPLETED

**Plan:** `.claude/plans/completed/fix-bugs-and-critical-test-gaps_PLAN.md`
**Date completed:** 2026-02-17

## What the plan proposed

2 real bugs and 6 critical test gaps identified after reviewing all source files, existing tests,
and the main simulation script. The plan targeted gaps that could cause silent wrong scientific
results or runtime crashes.

### Part A: Bug Fixes

**Bug 1:** `identify_outlier_subjects(group=X)` crashes with `AttributeError` because
`get_coordinate_data(..., group='healthy', return_individuals=True)` returns a raw ndarray,
not a dict. The `.items()` call then fails.

**Bug 2:** Skipped subjects in `get_*_data` methods corrupt subject-to-data mapping. When a
subject raises `KeyError` (missing coordinate/muscle/etc.), the method records the index,
removes those rows via `np.delete`, and returns a trimmed array. But the caller has no way to
know which subjects remain, so `subject_ids[i]` labels the wrong subject. Three fix options
were proposed: A (warn loudly), B (return aligned data — breaking API), C (raise error).

### Part B: Tests

| # | What the plan proposed | Risk addressed |
|---|------------------------|---------------|
| Test 3 | PFL prefix ambiguity — `'PFL'` matches `mPFL*`, `lPFL*`, and `PFL*` via substring | Wrong ligament force sums |
| Test 4 | Mismatched timesteps across H5 files — confusing numpy shape error | Opaque crash messages |
| Test 5 | `analyze_criteria` with multi-file data — `np.ptp(data)` on `(n_timesteps, n_files)` computes across files | Wrong pass/fail decisions |
| Test 6 | All H5 files missing — `self.time` and `self.num_time_steps` never set | `AttributeError` downstream |
| Test 7 | Heterogeneous fiber counts — `get_ligament_data` discovers fibers from first subject only | Silently ignored data |
| Test 8 | Filter + get_data integration — `_filter_jam_data` restructures contact dict, `get_regional_contact_data` must navigate filtered structure | Wrong data after filtering |

---

## What was actually done

### Part A: Bug Fixes (both completed in earlier sessions)

| Bug | Plan | Actual | Where |
|-----|------|--------|-------|
| Bug 1 | Add dict wrapping guard (same as `extract_values_at_time`) | **Done as planned.** Added `if group is not None and not isinstance(data_dict, dict): data_dict = {group: data_dict}` | `group_analysis.py:1225-1227` |
| Bug 2 | Option A (warn loudly) recommended, Option C (raise) as alternative | **Done with Option C.** All `get_*_data` methods now raise `KeyError` with subject details instead of silently skipping. Stricter than planned but prevents the silent data corruption entirely. | All `get_*_data` methods in `group_analysis.py` |

### Part B: Tests

| # | Plan | Actual | Notes |
|---|------|--------|-------|
| Test 3 | Add `test_pfl_prefix_ambiguity` and `test_pfl_without_prefix_matches_all` | **Done (differently).** Added `test_bare_pfl_does_not_match_prefixed_variants` — verifies `startswith` correctly isolates `PFL` from `lPFL`/`mPFL`. The `startswith` fix was already applied in code-fixes session, so the substring ambiguity no longer exists. | The plan was written when the code used `in` matching. The `startswith` fix changed the behavior. |
| Test 4 | Add `test_mismatched_timesteps_raises_clear_error` | **Done as planned** (earlier session). | `test_mismatched_timesteps_raises` in test_jam_analysis.py |
| Test 5 | Document `np.ptp` behavior with multi-file data as a latent bug | **Done (differently).** After review, determined this is not a real bug — `analyze_criteria` is always called via `jam_evaluation()` which loads a single H5 file. Added a defensive `if jam.num_files > 1: raise ValueError` guard + `test_multi_file_jam_raises` test instead of documenting buggy behavior. | The plan correctly noted "this bug is latent" — it can't happen through the normal API. |
| Test 6 | Add `test_all_files_missing_attributes` | **Done as planned** (earlier session). | test_jam_analysis.py |
| Test 7 | Add `test_heterogeneous_fiber_counts` documenting "first subject defines fiber list" | **Not needed.** `_validate_jam_consistency()` already prevents heterogeneous fiber counts with a clear `ValueError`. `test_mismatched_ligament_fibers_raises` already tests this. | The plan was written before `_validate_jam_consistency()` existed (added in test-suite-code-fixes session). |
| Test 8 | Add `test_get_regional_data_after_filtering` — success path after `_filter_jam_data` | **Done as planned.** Tests 2 subjects, 2 regions, verifies correct pressure values survive filtering. | Complements existing error-path test `test_get_data_after_filtering_wrong_contact_type`. |

### Source code changes (this session only)

| File | Change |
|------|--------|
| `forsim.py:328` | Added `num_files > 1` guard at top of `analyze_criteria()` |

### Test changes (this session only)

| File | Test added |
|------|-----------|
| `test_forsim_criteria.py` | `test_bare_pfl_does_not_match_prefixed_variants` |
| `test_forsim_criteria.py` | `test_multi_file_jam_raises` |
| `test_group_analysis.py` | `test_get_regional_data_after_filtering` |

---

## Final test results

```
147 passed, 0 failed
```

---

## Things to consider for the future

1. **Bug 2 (Option C) may be too strict.** Raising `KeyError` when a subject is missing a
   coordinate means the entire `get_*_data()` call fails. If a user has one subject with
   slightly different model outputs (e.g., a coordinate renamed between model versions),
   they must `remove_subjects()` before calling `get_*_data()`. The plan's Option B
   (return aligned data with valid subject IDs) would be more flexible but is a breaking
   API change. Consider if users hit this in practice.

2. **`analyze_criteria` guard is defensive.** Nobody currently passes multi-file JAMs to
   `analyze_criteria`, but the guard prevents confusing results if someone refactors
   `jam_evaluation()` or calls `analyze_criteria` directly. Low cost, high clarity.

3. **PFL matching edge case.** With `startswith`, `get_total_ligament_force(jam, "PFL")`
   now only matches fibers starting with `"PFL"` (e.g., `PFL1`), not `lPFL1` or `mPFL1`.
   This is correct behavior — `lPFL` and `mPFL` are distinct ligaments. But if a user
   previously relied on `"PFL"` to sum all PFL variants, they'd need to make separate
   calls for `"lPFL"`, `"mPFL"`, and `"PFL"`.

4. **`_validate_jam_consistency` covers Test 7's concern.** But note it only validates at
   `add_subject()` time. If someone constructs a `GroupJamAnalysis` manually (via `__new__`
   pattern used in tests), they bypass validation. This is fine for tests but worth noting.
