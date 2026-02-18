# Plan: Test Suite Overhaul — Remove Trivial Tests, Add Failure-Mode Tests

## Context

The existing test suite (131 tests) was AI-generated as the first test suite for pycomak.
A thorough review identified ~15 trivial tests that add noise without value, and ~21 real
failure modes that are untested. This plan removes the trivial tests and adds tests that
target how the code can *actually break* in production.

**Philosophy:** We write tests for how the code *should* work, not how it *currently* works.
If the test fails because of a code bug, we fix the code *later*. The test defines the
contract.

**Two-phase approach:**
1. **This plan (now):** Write all the tests. Remove trivial tests. Many new tests WILL FAIL
   because the code doesn't yet handle these cases. That's expected and intentional.
2. **Future work (separate agent/session):** Fix the code so that failing tests pass. The
   tests tell you exactly what's wrong — just make them green.

**Prior work:**
- `.claude/plans/completed/pycomak-test-suite_COMPLETED.md` — original test suite creation
- `.claude/plans/fix-bugs-and-critical-test-gaps.md` — bug fixes + 8 additional tests
  (Bug 1: identify_outlier_subjects crash — FIXED; Bug 2: skipped subjects — changed to
  raise KeyError; Tests 3-8: various gap tests — ADDED)

**What this plan does NOT cover:**
- Modules requiring OpenSim (comaktool.py, comak_id.py, jntmech.py, knee_optimizer.py,
  comak_ik.py beyond the strain update methods, dict_converter.py, forsim.py beyond
  criteria functions)
- The `_process_frametransformsset_fast` method (has `NotImplementedError` by design)

---

## Part 1: Remove Trivial Tests

Remove the following tests. For each, the rationale is given.

### test_main.py

| Test to Remove | Rationale |
|---|---|
| `test_standard_filenames_defined` | Tests that hardcoded string literals equal themselves. These are constants, not computed values. If someone changes them, the test must also change — it catches nothing. |
| `test_results_dir_attribute` | Tests `self.results_dir = results_dir`, a plain attribute assignment. |

**Keep:** `test_creates_all_expected_subdirectories` (core contract), `test_idempotent` (real scenario)

### test_cleanup.py

| Test to Remove | Rationale |
|---|---|
| `TestFormatSize.test_bytes` | Formatter display function, not depended on by any logic. |
| `TestFormatSize.test_kilobytes` | Same — pure display. |
| `TestFormatSize.test_megabytes` | Same — pure display. |
| `TestFormatSize.test_fractional_kb` | Same — pure display. |

**Keep:** `test_zero` (edge case), `test_gigabytes` (verifies loop terminates at right unit).
Keep all `TestFindJointMechanicsDirs`, `TestDeleteFilesInDir`, `TestCleanupLegacyVtpFiles`.

### test_jam_analysis.py

| Test to Remove | Rationale |
|---|---|
| `TestSingleFileShapes.test_regional_scalar_area_shape` | Identical code path as `test_regional_scalar_pressure_shape`. Both test the same branch in `_process_contact_fast` for regional scalar datasets. |
| `TestSingleFileShapes.test_num_time_steps_set` | Tests `self.num_time_steps = len(self.time)`. Trivial assignment. |
| `TestLegacyHelpers` (all 4 tests) | Tests backward-compat functions (`get_h5_output`, `get_h5_type`, `get_h5_groups_datasets`) that have WARNING deprecation notes in source. These functions open/close the file per call and are being moved away from. If we want to remove these functions eventually, the tests encourage keeping dead code. |

### test_plotting_utils.py

| Test to Remove | Rationale |
|---|---|
| `TestAssignColorsToGroups.test_mixed_known_unknown` | Redundant — covered by `test_known_groups_get_predefined_colors` + `test_unknown_groups_get_cycle_colors`. |
| `TestAssignColorsToGroups.test_empty_list` | Edge case that can never happen in practice (GroupJamAnalysis always has at least one group). |
| `TestAssignColorsToGroups.test_custom_dict_overrides` | Tests basic Python dict lookup. |
| `TestGetVariableLabel.test_muscle_actuation_label` | String formatting on lookup dict — tests MUSCLE_LABELS dict values, not logic. |
| `TestGetVariableLabel.test_ligament_label` | Same. |
| `TestGetVariableLabel.test_contact_pressure_label` | Same. |
| `TestGetVariableLabel.test_contact_area_label` | Same. |
| `TestGetVariableLabel.test_contact_force_label` | Same. |

**Keep:** `test_coordinate_rotation_label` (tests deg vs mm logic branch),
`test_coordinate_translation_label` (tests the other branch), `test_unknown_type_returns_name`
(fallback behavior). Keep all `TestPlotSmoke` tests.

### Summary of removals

**Total tests removed: ~15**

Files to edit:
- `tests/test_main.py` — remove 2 tests
- `tests/test_cleanup.py` — remove 4 tests
- `tests/test_jam_analysis.py` — remove 6 tests (1 shape + 1 trivial + 4 legacy)
- `tests/test_plotting_utils.py` — remove 8 tests

---

## Part 2: Add Failure-Mode Tests

**IMPORTANT NOTE FOR IMPLEMENTER:** Write ALL of these tests now. Many will FAIL with the
current code. That is expected and intentional. Do NOT modify the source code to make them
pass — that is a separate future task. Mark tests that are expected to fail with
`@pytest.mark.xfail(reason="...")` so the test suite stays green while documenting the
expected behavior.

When the code is later fixed, remove the `xfail` markers. If a test marked `xfail`
unexpectedly passes (meaning the code already handles it), pytest will report an
`xpass` — investigate and remove the marker.

### Overview of new tests

| # | Failure Mode | File | New Tests |
|---|---|---|---|
| 1 | JamAnalysis: mismatched structure across H5 files | test_jam_analysis.py | 3 |
| 2 | JamAnalysis: corrupted/truncated H5 data | test_jam_analysis.py | 1 |
| 3 | JamAnalysis: calling jam_analysis() twice | test_jam_analysis.py | 1 |
| 4 | JamAnalysis: contact regions > 6 or < 6 | test_jam_analysis.py | 2 |
| 5 | Ligament matching: prefix vs substring | test_forsim_criteria.py + test_group_analysis.py | 3 |
| 6 | GroupJamAnalysis: single-subject statistics | test_group_analysis.py | 2 |
| 7 | GroupJamAnalysis: remove_subjects edge cases + history | test_group_analysis.py | 4 |
| 8 | GroupJamAnalysis: extract_values_at_time boundary | test_group_analysis.py | 2 |
| 9 | GroupJamAnalysis: filter then access non-existent data | test_group_analysis.py | 1 |
| 10 | run_with_timeout: exception not propagated | test_utils.py | 1 |
| 11 | analyze_criteria: reuse across subjects | test_forsim_criteria.py | 1 |
| **Total** | | | **~21 new tests** |

---

### Test 1: JamAnalysis — mismatched H5 file structures (3 tests)

**Where:** `tests/test_jam_analysis.py`, new class `TestMismatchedFiles`

**Background:** `GroupJamAnalysis` has `_validate_jam_consistency()` with
`allow_mismatched_models` flag, but `JamAnalysis.jam_analysis()` has NO validation
when loading multiple H5 files. File A might have muscles `[recfem_r, vaslat_r]` and
file B only `[recfem_r]`. The pre-allocated array for `vaslat_r` gets zeros in column 1
instead of raising an error. This is silent data corruption.

**How the code SHOULD work:** By default, `jam_analysis()` should raise a clear error
when files have different structures (different muscles, ligaments, coordinates, or
contact surfaces). An explicit flag (like `allow_mismatched_files=True`) should be
required to allow combining files with different structures.

**Tests to write:**

```
test_mismatched_muscles_raises_by_default
    File A: muscles=[recfem_r, vaslat_r], File B: muscles=[recfem_r]
    Expected: Raises ValueError with a message listing the structural difference
    Rationale: Silent zeros in a data column is unacceptable for scientific data

test_mismatched_ligaments_raises_by_default
    File A: ligaments=[ACLam1, ACLpl1], File B: ligaments=[ACLam1]
    Expected: Raises ValueError
    Rationale: Same as above — missing ligament fiber silently becomes zeros

test_mismatched_files_allowed_with_flag
    Same setup as above, but call with allow_mismatched_files=True (or equivalent)
    Expected: No error. vaslat_r column 1 is zeros.
    Rationale: Sometimes combining different models IS intentional (like GroupJamAnalysis
    supports with allow_mismatched_models). The user should explicitly opt in.
```

**What the future code fix should do:** Add validation to `JamAnalysis.jam_analysis()` that
compares the structure of each file against the first file. Add an `allow_mismatched_files`
parameter (default `False`). Model after `GroupJamAnalysis._validate_jam_consistency()`.

---

### Test 2: JamAnalysis — corrupted/truncated H5 data (1 test)

**Where:** `tests/test_jam_analysis.py`, add to `TestEdgeCases`

**Background:** A simulation crash can produce an H5 file where `/time` has 101
timesteps but a muscle dataset has only 50. The numpy broadcasting error message is
opaque.

**How the code SHOULD work:** When a dataset's length doesn't match `/time`, raise a
clear error: "Dataset 'Muscle/recfem_r/actuation' has 50 timesteps but /time has 101
in file /path/to/file.h5".

**Test to write:**

```
test_truncated_dataset_raises_clear_error
    Create H5 file where /time has 101 entries but a muscle dataset has 50
    Expected: Raises ValueError with message containing the dataset path and both lengths
    Rationale: Opaque numpy errors waste hours of debugging time
```

**What the future code fix should do:** In `_process_generic_forceset_fast` and similar
methods, check `data.shape[0] == self.num_time_steps` before assignment. Raise
descriptive ValueError if they don't match.

---

### Test 3: JamAnalysis — calling jam_analysis() twice on same object (1 test)

**Where:** `tests/test_jam_analysis.py`, add to `TestEdgeCases`

**Background:** `JamAnalysis.__init__` initializes `self.names = []`. If someone calls
`jam.jam_analysis([file_a])` then `jam.jam_analysis([file_b])`, `self.names` gets
appended to (not reset), `forceset`/`coordinateset` dicts are mutated in-place, and
`num_files` is overwritten. Silent state corruption.

**How the code SHOULD work:** Raise an error if called twice. User should create
a new `JamAnalysis()` instance.

**Test to write:**

```
test_calling_jam_analysis_twice_raises
    Call jam.jam_analysis([file_a])
    Call jam.jam_analysis([file_b]) again
    Expected: Raises RuntimeError with message like "jam_analysis() has already been
    called. Create a new JamAnalysis() instance."
    Rationale: Silently corrupting state is worse than erroring
```

**What the future code fix should do:** At the top of `jam_analysis()`, check if
`self.h5_file_list` is non-empty. If so, raise RuntimeError.

---

### Test 4: JamAnalysis — contact regions > 6 or < 6 (2 tests)

**Where:** `tests/test_jam_analysis.py`, add to `TestEdgeCases`

**Background:** The code hardcodes `{x: {} for x in range(6)}` for contact mesh
initialization and `for region_idx in range(min(6, n_regions))` for regional scalar
data. >6 regions = silent data truncation. <6 regions = empty dicts for non-existent
regions.

**How the code SHOULD work:**
- >6 regions: warn that regions beyond 5 are being dropped
- <6 regions: empty region dicts should not cause confusing errors downstream

**Tests to write:**

```
test_fewer_than_6_regions_accessible
    Create H5 with 3 regions of contact data
    Load it. Access region 0, 1, 2 — should have data.
    Access region 3 — should be an empty dict (keys 0-5 always initialized).
    Verify that region 3 is an empty dict (documenting this behavior).

test_more_than_6_regions_warns
    Create H5 with 8 regions of regional scalar data (n_timesteps, 8)
    Load it. Verify regions 0-5 have correct data from the first 6 columns.
    Expected: A warning is raised about regions 6-7 being dropped.
    Rationale: Silent truncation of scientific data is unacceptable.
```

**What the future code fix should do:** Add `warnings.warn()` when `n_regions > 6`.
Consider making the region count dynamic instead of hardcoded.

---

### Test 5: Ligament matching — prefix vs substring (3 tests)

**Where:** `tests/test_forsim_criteria.py` and `tests/test_group_analysis.py`

**Background:** Both `get_total_ligament_force()` (forsim.py) and `get_ligament_data()`
(group_analysis.py) use `ligament_name in fiber_name` which is substring matching.
This means `"PT"` would also match a hypothetical fiber named `"mPTl1"`, and `"PFL"`
matches `"mPFL1"`, `"lPFL1"`, AND `"PFL1"`.

**How the code SHOULD work:** Use `startswith` matching. This is strictly better:
- All current ligament names work identically (`"ACLam1".startswith("ACL")` → True)
- Eliminates substring false positives

**Tests to write:**

```
# test_forsim_criteria.py::TestGetTotalLigamentForce
test_prefix_matching_not_substring
    Fibers: PT1, PT2, mPTl1
    Call get_total_ligament_force(jam, "PT")
    Expected: Only sums PT1 + PT2. mPTl1 is NOT included.
    Rationale: "PT" should match fibers that START with "PT", not contain "PT".

test_pfl_prefix_specificity
    Fibers: lPFL1, mPFL1
    Call get_total_ligament_force(jam, "lPFL")
    Expected: Only sums lPFL1.
    Call get_total_ligament_force(jam, "mPFL")
    Expected: Only sums mPFL1.
    Rationale: These are different ligaments.

# test_group_analysis.py::TestGetLigamentData
test_ligament_data_uses_prefix_matching
    Build GA with fibers: MCLd1, MCLs1, LCL1.
    Call get_ligament_data("CL").
    Expected: Raises ValueError ("no fibers found") because no fiber STARTS with "CL".
    Currently "CL" in "MCLd1" is True (substring match) — this is wrong.
```

**What the future code fix should do:**
1. `forsim.py` line ~297: Change `if ligament_name in x` to `if x.startswith(ligament_name)`
2. `group_analysis.py` line ~721: Same change

---

### Test 6: GroupJamAnalysis — single-subject group statistics (2 tests)

**Where:** `tests/test_group_analysis.py`, new class `TestSingleSubjectEdgeCases`

**Background:** With n=1 subject, `identify_outlier_subjects` computes `group_std = 0`,
and the z-score print does `(value - group_mean) / group_std` → division by zero.

**How the code SHOULD work:**
- `get_coordinate_data` with 1 subject: returns std=0, ste=0, n=1 (mathematically correct)
- `identify_outlier_subjects` with 1 subject: returns empty outliers, no crash

**Tests to write:**

```
test_single_subject_stats_no_crash
    Build GA with 1 subject. Call get_coordinate_data(return_individuals=False).
    Expected: Dict with mean, std=0, ste=0, n=1. No crash.

test_single_subject_outlier_detection_no_crash
    Build GA with 1 subject. Call identify_outlier_subjects().
    Expected: Empty outlier list. No division-by-zero crash.
```

**What the future code fix should do:** In `identify_outlier_subjects`, guard against
`group_std == 0` before computing `outlier_mask`.

---

### Test 7: GroupJamAnalysis — remove_subjects edge cases + removal history (4 tests)

**Where:** `tests/test_group_analysis.py`, extend `TestRemoveSubjects`

**Background:** The user frequently removes subjects iteratively and has no way to
track what was removed. Out-of-range indices and non-existent IDs are silently ignored.

**How the code SHOULD work:**
- Out-of-range indices: raise IndexError
- Non-existent IDs: raise KeyError (or return a list of not-found IDs)
- All removals logged in `self.removal_history` for reproducibility

**Tests to write:**

```
test_out_of_range_index_raises
    GA with 3 subjects. remove_subjects(subject_indices=[10], group='healthy').
    Expected: Raises IndexError ("Index 10 out of range, group has 3 subjects")

test_nonexistent_id_raises
    GA with 3 subjects. remove_subjects(subject_ids=['nonexistent_RIGHT']).
    Expected: Raises KeyError listing the not-found IDs

test_removal_history_tracked
    GA with 3 subjects. Remove subject 1 by ID. Remove subject 0 by index.
    Expected: ga.removal_history is a list of 2 entries, each containing:
      - 'subject_id': the full subject_id_side string
      - 'group': which group they were in
      - 'method': 'by_id' or 'by_index'
      - 'index_in_group': index at time of removal

test_removal_history_initialized_empty
    Fresh GA (using __new__ pattern from existing tests).
    Expected: ga.removal_history == []
```

**What the future code fix should do:**
1. Add `self.removal_history = []` to `__init__`
2. Log removals before deleting
3. Raise on out-of-range index instead of printing warning
4. Raise on non-existent ID instead of silently skipping

---

### Test 8: GroupJamAnalysis — extract_values_at_time boundary behavior (2 tests)

**Where:** `tests/test_group_analysis.py`, extend `TestExtractValuesAtTime`

**Background:** `time_point=150.0` (beyond 0-100 range) silently returns the value
at the last index. The user asked for a timepoint that doesn't exist.

**How the code SHOULD work:** Raise ValueError for out-of-range time points.

**Tests to write:**

```
test_out_of_range_time_point_raises
    Call extract_values_at_time(time_point=150.0)
    Expected: Raises ValueError ("time_point 150.0 is outside range [0, 100]")

test_boundary_time_points_work
    Call extract_values_at_time(time_point=0.0) and time_point=100.0
    Expected: Both return valid data without error
```

**What the future code fix should do:** Add range check at top of time-index calculation.

---

### Test 9: GroupJamAnalysis — filter then access non-existent contact type (1 test)

**Where:** `tests/test_group_analysis.py`, new class `TestFilterThenGetData`

**Background:** If `_filter_jam_data` keeps only `pf_contact` but the H5 only had
`tf_contact`, the filtered dict is empty. Downstream `get_regional_contact_data()`
KeyErrors with an opaque message.

**How the code SHOULD work:** `get_regional_contact_data` should re-raise with a
helpful message listing available contact types/cartilages/regions.

**Test to write:**

```
test_get_data_after_filtering_wrong_contact_type
    Filter with contact_types=['pf_contact'] on data that only has tf_contact.
    Build GA with this filtered JAM.
    Call get_regional_contact_data(contact_type='pf_contact', region=4).
    Expected: KeyError with message listing available contact types.
```

**What the future code fix should do:** Wrap the deep dict access in try/except,
re-raise with context about what's available.

---

### Test 10: run_with_timeout — subprocess exception not propagated (1 test)

**Where:** `tests/test_utils.py`, extend `TestRunWithTimeout`

**Background:** If the function raises an exception, `p.is_alive()` is False and the
code prints "Function completed successfully" — but the function actually crashed.
`p.exitcode` is nonzero but never checked.

**How the code SHOULD work:** After join, if `p.exitcode != 0`, raise RuntimeError.

**Test to write:**

```
test_function_exception_detected
    def bad_func():
        raise ValueError("model broke")
    run_with_timeout(bad_func, timeout=5)
    Expected: Raises RuntimeError (not TimeoutError) indicating the function crashed
```

**What the future code fix should do:** After `p.join(timeout)`, check `p.exitcode`.

---

### Test 11: analyze_criteria — dict reuse across subjects (1 test)

**Where:** `tests/test_forsim_criteria.py`, extend `TestAnalyzeCriteria`

**Background:** `analyze_criteria` mutates `criteria_dict` in place. If reused across
multiple calls (as in KneeOptimizer), the result keys (`ptp_`, `min_`, `max_`) from
the first call persist. The second call should cleanly overwrite them.

**How the code SHOULD work:** Second call overwrites first call's results. This
already works correctly via `.update()` — this test documents that contract.

**Test to write:**

```
test_criteria_dict_reuse_across_calls
    Call analyze_criteria with JAM where PT force range = 500 (passes max_range=1100)
    Verify ptp_ = 500
    Call again with DIFFERENT JAM where PT force range = 2000 (fails)
    Verify ptp_ = 2000 (overwritten, not accumulated)
    Verify passed = False
```

**No code fix needed** — this test documents existing correct behavior.

---

## Part 3: Implementation Instructions

### For the implementer

1. **Remove trivial tests** (Part 1). Run `pytest` to verify remaining tests pass.

2. **Add all new tests** (Part 2). Use `@pytest.mark.xfail(reason="<reason>")` on tests
   that are expected to fail with current code. The `reason` string should briefly explain
   what code change is needed (e.g., `reason="JamAnalysis needs file structure validation"`).

3. **Run `pytest -v`**. You should see:
   - All existing (non-removed) tests: PASS
   - Test 11 (criteria reuse): PASS (documents existing correct behavior)
   - Tests 1-10: XFAIL (expected failures, documenting needed code changes)
   - No unexpected failures

4. **Do NOT modify source code.** That is a separate task for a future session. The tests
   define the contracts; a future agent will make the code satisfy them.

5. **Commit** with message: "Overhaul test suite: remove 15 trivial tests, add 21
   failure-mode tests"

### For the future code-fixer

After this plan is complete, a separate session should:

1. Run `pytest -v` to see all xfail tests
2. For each xfail test, read the `reason` string and the "What the future code fix
   should do" section in this plan
3. Fix the code, remove the `@pytest.mark.xfail` marker
4. Run full suite to verify no regressions
5. Commit per-fix or in logical groups

---

## Verification

```bash
cd /dataNAS/people/aagatti/programming/pycomak
pytest tests/ -v
```

After Part 1 + Part 2:
- Starting: 131 tests
- Removed: ~15
- Added: ~21
- Final: ~137 tests
- All PASS or XFAIL (no unexpected failures)

---

## Summary Table

| # | What | Tests Δ | Test File | Source File (future fix) |
|---|---|---|---|---|
| Part 1 | Remove trivial | -15 | 4 test files | None |
| Test 1 | Mismatched H5 structures | +3 | test_jam_analysis.py | jam_analysis.py |
| Test 2 | Truncated H5 data | +1 | test_jam_analysis.py | jam_analysis.py |
| Test 3 | Double jam_analysis() call | +1 | test_jam_analysis.py | jam_analysis.py |
| Test 4 | Region count != 6 | +2 | test_jam_analysis.py | jam_analysis.py |
| Test 5 | Prefix vs substring matching | +3 | test_forsim_criteria.py, test_group_analysis.py | forsim.py, group_analysis.py |
| Test 6 | Single-subject stats | +2 | test_group_analysis.py | group_analysis.py |
| Test 7 | Removal edge cases + history | +4 | test_group_analysis.py | group_analysis.py |
| Test 8 | Time boundary validation | +2 | test_group_analysis.py | group_analysis.py |
| Test 9 | Filter + access mismatch | +1 | test_group_analysis.py | group_analysis.py |
| Test 10 | Subprocess exception | +1 | test_utils.py | utils.py |
| Test 11 | Criteria dict reuse | +1 | test_forsim_criteria.py | None (already works) |
| **Total** | | **+6 net** | | |
