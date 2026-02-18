# Plan: Post-Review Cleanup

## Context

After a thorough review of the AI agent's refactoring work (test suite + code fixes across
4 sessions), we identified several issues: duplicated code patterns, an uncaught exception
gap, dead speculative comments, and a missing test for the most-used API entry point. This
plan addresses the concrete action items from that review.

---

## Changes

### 1. DRY up the `get_*_data` KeyError pattern in `group_analysis.py`

**File:** `pycomak/group_analysis.py`

**Problem:** Five methods (`get_coordinate_data`, `get_muscle_data`, `get_ligament_data`,
`get_contact_force_data`, `get_regional_contact_data`) all repeat this identical 7-line
try/except/re-raise pattern with copy-pasted error messages:

```python
try:
    data[i, :] = <access jam data>
except KeyError as e:
    subject_id = group_dict['subject_ids'][i]
    raise KeyError(
        f"Subject '{subject_id}' (index {i}) in group '{group_name}' "
        f"is missing <type> '{name}': {e}. "
        f"Fix the data upstream or remove this subject with remove_subjects()."
    ) from e
```

**Fix:** Extract a private helper method:

```python
@staticmethod
def _extract_subject_value(jam, accessor, i, subject_id, group_name):
    """Extract a 1D timeseries from a single JAM object, re-raising KeyError with context."""
    try:
        return accessor(jam)
    except KeyError as e:
        raise KeyError(
            f"Subject '{subject_id}' (index {i}) in group '{group_name}': {e}"
        ) from e
```

Each method passes a lambda or small function as `accessor`:
- `get_coordinate_data`: `lambda jam: jam.coordinateset[name]['value'][:, 0]`
- `get_muscle_data`: `lambda jam: jam.forceset['Muscle'][name][outcome][:, 0]`
- `get_ligament_data`: loops fibers inside the accessor (sum pattern)
- `get_contact_force_data`: accessor returns the axis-selected 1D array
- `get_regional_contact_data`: accessor returns the axis-selected 1D array

The 5-line comment block ("NOTE: We intentionally raise on KeyError...") in
`get_coordinate_data` moves to the helper's docstring. The "see get_coordinate_data for
rationale" comments in the other 4 methods are deleted.

**Also fix:** `get_muscle_data` (line 678-679) includes `'min'` and `'max'` in its stats
dict but the other 4 methods don't. Remove `'min'`/`'max'` from `get_muscle_data` for
consistency, OR add them to all 5 methods. Decision: remove from `get_muscle_data` — the
test at line 230-231 of `test_group_analysis.py` checks for `'min'` and `'max'`, so that
test needs updating too.

**Tests affected:** `TestGetMuscleData.test_return_stats` — remove assertions for `'min'`
and `'max'` keys. All other existing tests should pass unchanged since the behavior
(raise on missing data) is identical.

---

### 2. Catch `RuntimeError` in `run_with_timeout` callers

**Problem:** `run_with_timeout()` now raises `RuntimeError` on subprocess crash (exit
code != 0), but the two production callers only catch `TimeoutError`:

| Caller | File | Line | Current catch |
|--------|------|------|--------------|
| `COMAKforsim.run_forsim()` | `forsim.py` | 575 | `TimeoutError` only |
| `KneeOptimizer.optimize_patella_location()` | `knee_optimizer.py` | 188 | `TimeoutError` only |

A subprocess crash (e.g., OpenSim segfault, Python exception in the forked process)
raises `RuntimeError` which bubbles up uncaught, killing the pipeline script.

**Fix:**

**forsim.py** (~line 575): Add `RuntimeError` to the except clause:
```python
try:
    run_with_timeout(run_forsim, self.max_forsim_time, **kwargs)
    print('Forsim Tool completed successfully')
    self.forsim_completed = True
    return True
except TimeoutError:
    print('Forsim Tool timed out... took longer than allowed time')
    return False
except RuntimeError as e:
    print(f'Forsim Tool crashed: {e}')
    return False
```

**knee_optimizer.py** (~line 188): Same pattern — catch `RuntimeError` alongside
`TimeoutError` in the settle sim call. Record `'settle_sim_crash'` instead of
`'settle_sim_timeout'`:
```python
try:
    run_with_timeout(comak_ik.perform_settle_sim, 60*10)
except TimeoutError:
    update_patella_location_(...)
    self._n_updates += 1
    self._list_eval_results.append('settle_sim_timeout')
    continue
except RuntimeError:
    update_patella_location_(...)
    self._n_updates += 1
    self._list_eval_results.append('settle_sim_crash')
    continue
```

**Tests:** No new tests needed — the existing `test_function_exception_detected` in
`test_utils.py` already covers `RuntimeError` from `run_with_timeout`. The callers are
OpenSim-dependent code that isn't unit-tested.

---

### 3. Remove speculative TODO comment block from `group_analysis.py`

**File:** `pycomak/group_analysis.py`, lines 1277-1315

**Problem:** 38-line comment block about PCA, SPM, regression, and correlation features
that don't exist. Speculative planning in source code rots.

**Fix:** Delete lines 1277-1315 (the entire `NOTE FOR FUTURE DEVELOPMENT` block).

---

### 4. Add test for `add_subject()` — biggest coverage gap

**File:** `tests/test_group_analysis.py`

**Problem:** `add_subject()` is the primary entry point for `GroupJamAnalysis`. It
constructs paths, opens H5 files, runs filtering, validates consistency. Zero tests.

**What to test:** We can't test the full `add_subject()` path without real H5 files on
disk (it calls `JamAnalysis().jam_analysis([h5_path])`). But we CAN test it using the
`create_h5` fixture from `conftest.py` which creates real H5 files in `tmp_path`.

**Tests to add** (new class `TestAddSubject`):

```
test_add_subject_with_h5_path
    Create an H5 file with create_h5 fixture.
    Call add_subject(..., h5_file_path=path_to_h5).
    Verify: subject appears in group, jam_list has 1 entry, subject_ids correct.

test_add_subject_missing_h5_returns_false
    Call add_subject(..., h5_file_path='/nonexistent/file.h5').
    Verify: returns False, group is empty or subject not added.

test_add_subject_filter_data
    Create H5 with tf_contact + pf_contact.
    Call add_subject(..., h5_file_path=path, filter_data=True, contact_types=['tf_contact']).
    Verify: pf_contact is not in the JAM's forceset after filtering.

test_add_subject_two_subjects_same_group
    Add 2 subjects with different H5 files to same group.
    Verify: group has 2 subjects, jam_list has 2 entries.
```

These test the real code path (H5 → JamAnalysis → filter → validate → store) without
needing OpenSim.

---

## Files Modified

| File | Change |
|------|--------|
| `pycomak/group_analysis.py` | Add `_extract_subject_value` helper, refactor 5 `get_*_data` methods, remove `min`/`max` from `get_muscle_data` stats, delete TODO block |
| `pycomak/forsim.py` | Catch `RuntimeError` in `run_forsim()` |
| `pycomak/knee_optimizer.py` | Catch `RuntimeError` in `optimize_patella_location()` |
| `tests/test_group_analysis.py` | Update `TestGetMuscleData.test_return_stats`, add `TestAddSubject` class |

---

## Verification

```bash
conda run -n comak python -m pytest tests/ -v
```

All 147 existing tests should pass (with the `test_return_stats` assertion update).
New `TestAddSubject` tests should pass.

---

## What this plan does NOT do

- Does not change `removal_history` (user wants to keep it)
- Does not add `match_type` param to `get_total_ligament_force` (KISS — `startswith` is correct)
- Does not strengthen plotting smoke tests (not worth the investment)
- Does not simplify the `_get_file_structure` inline comparison (minor style issue)
