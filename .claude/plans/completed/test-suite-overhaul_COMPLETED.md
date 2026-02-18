# Test Suite Overhaul — COMPLETED

**Plan:** `.claude/plans/test-suite-overhaul.md`
**Date completed:** 2026-02-17

## What was done

### Part 1: Removed 15 trivial tests

| File | Tests Removed | Count |
|------|--------------|-------|
| `test_main.py` | `test_standard_filenames_defined`, `test_results_dir_attribute` | 2 |
| `test_cleanup.py` | `TestFormatSize`: `test_bytes`, `test_kilobytes`, `test_megabytes`, `test_fractional_kb` | 4 |
| `test_jam_analysis.py` | `test_regional_scalar_area_shape`, `test_num_time_steps_set`, `TestLegacyHelpers` (all 4) | 6 |
| `test_plotting_utils.py` | `TestAssignColorsToGroups`: `test_mixed_known_unknown`, `test_custom_dict_overrides`, `test_empty_list`; `TestGetVariableLabel`: `test_muscle_actuation_label`, `test_ligament_label`, `test_contact_pressure_label`, `test_contact_area_label`, `test_contact_force_label` | 8 |
| **Total** | | **20** |

Note: Plan said ~15 but actual count was 20 (the plotting_utils removals were 8, not 5 as estimated).

### Part 2: Added 21 failure-mode tests

All tests from the plan were written. Summary:

| # | Test Group | File | Tests Added | Status |
|---|-----------|------|-------------|--------|
| 1 | Mismatched H5 structures | `test_jam_analysis.py` | 3 (`TestMismatchedFiles`) | 2 xfail, 1 xfail |
| 2 | Truncated H5 data | `test_jam_analysis.py` | 1 (`TestTruncatedH5Data`) | PASS (numpy catches it) |
| 3 | Double jam_analysis() call | `test_jam_analysis.py` | 1 (`TestDoubleCall`) | xfail |
| 4 | Region count != 6 | `test_jam_analysis.py` | 2 (`TestRegionCounts`) | 1 PASS, 1 xfail |
| 5a | Prefix matching (forsim) | `test_forsim_criteria.py` | 2 (`test_prefix_matching_not_substring`, `test_pfl_prefix_specificity`) | 1 xfail, 1 PASS |
| 5b | Prefix matching (group) | `test_group_analysis.py` | 1 (`TestLigamentPrefixMatching`) | xfail |
| 6 | Single-subject stats | `test_group_analysis.py` | 2 (`TestSingleSubjectEdgeCases`) | both PASS |
| 7 | remove_subjects edge cases | `test_group_analysis.py` | 4 (`TestRemoveSubjectsEdgeCases`) | all xfail |
| 8 | Time boundary validation | `test_group_analysis.py` | 2 (`TestExtractValuesAtTimeBoundary`) | 1 xfail, 1 PASS |
| 9 | Filter + access mismatch | `test_group_analysis.py` | 1 (`TestFilterThenGetData`) | PASS |
| 10 | Subprocess exception | `test_utils.py` | 1 (`test_function_exception_detected`) | xfail |
| 11 | Criteria dict reuse | `test_forsim_criteria.py` | 1 (`test_criteria_dict_reuse_across_calls`) | PASS |
| **Total** | | | **21** | |

## What we encountered

### 4 tests expected to fail actually passed (xpass)

These were marked `@pytest.mark.xfail` but the code already handled them. We removed the markers and updated docstrings to explain why they pass:

1. **`test_pfl_prefix_specificity`** — `"lPFL" in "mPFL1"` is `False`, so substring matching happens to work for this case. The underlying logic is still fragile (substring-based), but this specific test case passes.

2. **`test_single_subject_outlier_detection_no_crash`** — With n=1, `group_std=0`. The z-score division line (`(value - mean) / std`) is inside a loop over outlier indices, but `0 > threshold * 0` is always `False` for non-zero values, so the loop body is never reached. No crash, but the logic is still fragile.

3. **`test_truncated_dataset_raises_error`** — Numpy itself raises a broadcasting/shape error when trying to assign truncated data into pre-allocated arrays. The error message is opaque, but it does raise.

4. **`test_get_data_after_filtering_wrong_contact_type`** — A raw `KeyError` is already raised from the nested dict access. The message is opaque (just the missing key), not a helpful contextual message.

### Test count reconciliation

- Started: 131 tests (but prior commit had already added 12 model consistency tests, so actual starting point was ~143)
- Removed: 20
- Added: 21
- **Final: 144 collected, 131 passed, 13 xfailed**

## Remaining xfail tests (for future code fixer)

These 13 tests document code changes needed:

| xfail Test | Code Fix Needed |
|-----------|----------------|
| `test_mismatched_muscles_raises_by_default` | Add file structure validation to `JamAnalysis.jam_analysis()` |
| `test_mismatched_ligaments_raises_by_default` | Same as above |
| `test_mismatched_files_allowed_with_flag` | Add `allow_mismatched_files` parameter to `jam_analysis()` |
| `test_calling_jam_analysis_twice_raises` | Guard against double-call in `jam_analysis()` |
| `test_more_than_6_regions_warns` | Add `warnings.warn()` when `n_regions > 6` |
| `test_prefix_matching_not_substring` | Change `if ligament_name in x` to `if x.startswith(ligament_name)` in `forsim.py:297` |
| `test_ligament_data_uses_prefix_matching` | Same change in `group_analysis.py:723` |
| `test_out_of_range_index_raises` | Raise `IndexError` in `remove_subjects()` instead of silently skipping |
| `test_nonexistent_id_raises` | Raise `KeyError` in `remove_subjects()` instead of silently ignoring |
| `test_removal_history_tracked` | Add `self.removal_history = []` to `__init__`, log removals |
| `test_removal_history_initialized_empty` | Same as above |
| `test_out_of_range_time_point_raises` | Add range check in `extract_values_at_time()` |
| `test_function_exception_detected` | Check `p.exitcode` in `run_with_timeout()` after `p.join()` |

## Things to consider for the future

- The plan file (`test-suite-overhaul.md`) has detailed "What the future code fix should do" sections for each test group — a future agent should reference both this completed file and that plan.
- The `test_pfl_prefix_specificity` test passes with substring matching by coincidence. When the prefix fix is applied to `forsim.py`, this test should continue to pass — it's a good regression test.
- The `test_single_subject_outlier_detection_no_crash` test passes because the division-by-zero line is inside an unreachable branch. If the outlier detection logic changes, this could start crashing. A proper guard (`if group_std == 0`) is still recommended.
