# Plan: Codebase Bug Fixes & Hardening

## Context

After a comprehensive 6-agent codebase review of pycomak (menisci branch), we identified
~25 issues across severity tiers. The library has been through 4 AI refactoring sessions
(test suite, test overhaul, code fixes, cleanup). This plan addresses all remaining
actionable issues before the user runs full integration tests and begins adding new features.

User decisions on domain questions:
- **MCL grouping**: Keep `startswith('MCL')` matching MCLd+MCLs+MCLp — intentional.
- **H5 units**: Radians for rotations, meters for translations. Plotting labels are wrong.
- **convert_to_radians**: Remove dead code. ForsimTool reads degrees directly.

---

## Part 1: Silent-Wrong-Result Bugs (highest priority)

### 1a. `add_subject` list sync on exception
**File:** `pycomak/group_analysis.py:275-298`

**Problem:** `subjects` and `subject_ids` are appended (L275-276) before `jam.jam_analysis()`
runs (L281). If JAM analysis or validation raises, the three parallel lists go out of sync —
every subsequent subject gets off-by-one mapping.

**Fix:** Move the `subjects.append` and `subject_ids.append` calls to after the successful
`jam_list.append`. Wrap the JAM analysis block so that on any exception, the subject info is
not left in the lists.

```python
# Build subject_info dict (unchanged)
# Run JAM analysis FIRST
if run_jam:
    jam = JamAnalysis()
    jam.jam_analysis([h5_file])
    if filter_data:
        self._filter_jam_data(jam, ...)
    self._validate_jam_consistency(jam, group)
    # Only append AFTER all of the above succeeded
    self.groups[group]['subjects'].append(subject_info)
    self.groups[group]['subject_ids'].append(f"{subject_id}_{side}")
    self.groups[group]['jam_list'].append(jam)
else:
    # No JAM, still append metadata
    self.groups[group]['subjects'].append(subject_info)
    self.groups[group]['subject_ids'].append(f"{subject_id}_{side}")
```

### 1b. `contact_accessor` returns None for unrecognized axis
**File:** `pycomak/group_analysis.py:828-833`

**Problem:** If `axis` is neither `int` nor `'norm'`, the function falls through with
implicit `return None`. Downstream assignment `data[i, :] = None` produces cryptic TypeError.

**Fix:** Add `else: raise ValueError(f"Unrecognized axis: {axis!r}. Use int (0/1/2) or 'norm'.")`.

### 1c. `analyze_criteria` mutates caller's dict
**File:** `pycomak/forsim.py:362`

**Problem:** `criteria_dict[criteria_type][name].update(result_dict)` mutates the dict passed
in. In `KneeOptimizer`, `self.dict_criteria` accumulates stale `ptp_/min_/max_` keys across
iterations.

**Fix:** Work on a `copy.deepcopy(criteria_dict)` at the top of `analyze_criteria`, and return
the copy. The original dict is never modified.

### 1d. NaN silently passes all criteria in `analyze_criteria`
**File:** `pycomak/forsim.py:341-343`

**Problem:** `np.ptp(NaN)` = NaN, and `NaN > threshold` is always `False`. A simulation with
NaN data silently passes all criteria, and the optimizer declares success.

**Fix:** Add a NaN check at L341:
```python
if np.any(np.isnan(data)) or np.any(np.isinf(data)):
    print(f'{name} - Data contains NaN/Inf values')
    passed = False
    continue
```

### 1e. `load_secondary_constraints` first-subject initialization
**File:** `pycomak/group_analysis.py:530`

**Problem:** Uses `if subject_idx == 0` for initialization. If subject 0's file is missing
(L524 `continue`), initialization never happens → `KeyError` on subject 1.

**Fix:** Replace `if subject_idx == 0` with `if 'secondary_constraints' not in group_dict`.

### 1f. `load_secondary_constraints` zero-fill for skipped subjects
**File:** `pycomak/group_analysis.py:540`

**Problem:** Skipped subjects get all-zero rows, which look like real data.

**Fix:** Use `np.nan` fill instead of `np.zeros` for the Y array initialization. This way
skipped subjects produce NaN rows, which are clearly identifiable and will propagate visibly
in downstream statistics.

### 1g. `jam_analysis()` missing first file crashes on second file
**File:** `pycomak/jam_analysis.py:701`

**Problem:** `self.time` and `self.num_time_steps` are only set when `h5_file_idx == 0`.
If file 0 is missing, file 1 crashes with `AttributeError`.

**Fix:** Change `if h5_file_idx == 0:` to set time from the first *successfully opened* file:
```python
if not hasattr(self, 'num_time_steps'):
    self.time = np.array(f['/time'])
    self.num_time_steps = len(self.time)
```

### 1h. `jam_analysis()` empty file list leaves broken state
**File:** `pycomak/jam_analysis.py:637`

**Problem:** `jam_analysis([])` sets `num_files=0`, loop never executes, `_analyzed=True` but
`time`/`num_time_steps` never set. Any attribute access crashes.

**Fix:** Add early validation: `if len(h5_file_list) == 0: raise ValueError("h5_file_list is empty")`.

---

## Part 2: Plotting & Unit Fixes

### 2a. Rotational coordinates: radians plotted as "degrees"
**Files:** `pycomak/plotting_utils.py:174, 267`

**Problem:** Confirmed: H5 stores radians (OpenSim internal units). `load_secondary_constraints`
converts with `np.rad2deg()`. But `plot_coordinate_comparison` and `plot_coordinate_individuals`
do NOT convert rotational data, yet label the y-axis "degrees".

**Fix in `plot_coordinate_comparison`** (L180+): For non-translation coordinates, convert:
```python
if not is_translation:
    mean = np.rad2deg(mean)
    std_data = np.rad2deg(data.get('std', np.zeros_like(mean)))
    ste_data = np.rad2deg(data.get('ste', np.zeros_like(mean)))
```

**Fix in `plot_coordinate_individuals`** (L275+): Same conversion:
```python
if not is_translation:
    plot_data = np.rad2deg(plot_data)
```

Also fix `plot_kinematics_panel` which calls these — verify it passes through correctly.

### 2b. `plot_muscle_comparison` dead `show_range` code
**File:** `pycomak/plotting_utils.py:406-407`

**Problem:** `show_range` checks for `'min'`/`'max'` keys that `get_muscle_data` no longer
returns. The parameter is dead.

**Fix:** Replace `show_range` behavior with `show_ste`/`show_std` pattern matching
`plot_coordinate_comparison` and `plot_ligament_comparison`:
```python
if show_ste and 'ste' in data:
    ax.fill_between(time, mean - data['ste'], mean + data['ste'], alpha=0.3, color=color)
elif show_std and 'std' in data:
    ax.fill_between(time, mean - data['std'], mean + data['std'], alpha=0.2, color=color)
```

Remove `show_range` parameter. Add `show_ste=True` and `show_std=False` parameters.

### 2c. `_get_variable_label` translations labeled (mm) but data in meters
**File:** `pycomak/plotting_utils.py:1371-1373`

**Problem:** The scatter plot label helper says `(mm)` for translations, but
`extract_values_at_time` returns raw data (meters) with no conversion.

**Fix:** Two options — either convert in `extract_values_at_time`, or fix the label to `(m)`.
Better: fix the label to match what the data actually is. Change ` (mm)` to ` (m)`.
Add a comment noting that `plot_coordinate_comparison` handles its own m→mm conversion.

### 2d. `plot_regional_contact` redundant ste handling
**File:** `pycomak/plotting_utils.py:826-851`

**Problem:** The if/elif/else block at L844-851 is redundant — `ste_plot` is always just `ste`.

**Fix:** Simplify to `ste_plot = ste` (delete the redundant if/elif/else).

---

## Part 3: Dead Code & Docstring Fixes

### 3a. Remove `convert_to_radians` dead code
**File:** `pycomak/forsim.py:112, 122, 142-146, 539`

**Fix:** Remove the `convert_to_radians` parameter from `create_save_sto()` and the commented-out
conversion code. Remove `convert_to_radians=True` from the `COMAKforsim.__init__` call.

### 3b. Fix defaults docstring
**File:** `pycomak/defaults.py:228`

**Fix:** Change "0.25" to "0.6" in the docstring.

### 3c. Fix `list_musccles` typo
**File:** `pycomak/defaults.py:255`

**Fix:** Rename to `list_muscles`.

### 3d. Bare `Exception` types
**File:** `pycomak/jam_analysis.py:633, 666`

**Fix:** Change `raise Exception(...)` to `raise TypeError(...)` (L633) and `raise ValueError(...)` (L666).

### 3e. `muscle_outcomes` docstring contradiction
**File:** `pycomak/group_analysis.py:402`

**Fix:** Change docstring from "Set to None to keep all muscle outcomes" to
"Set to None to use default (['actuation']). Pass filter_data=False to keep all outcomes."

---

## Part 4: Defensive Hardening

### 4a. `comak_ik.py` uninitialized `coordinate_index`
**File:** `pycomak/comak_ik.py:64-69`

**Fix:** Initialize `coordinate_index = 0` before the `for j` loop, and add a warning if no
match is found:
```python
coordinate_index = 0  # default to first coordinate
matched = False
for j in range(joint_upd.numCoordinates()):
    if joint_upd.get_coordinates(j).getSpeedName().split('/')[0] == coord_names[i]:
        coordinate_index = j
        matched = True
        break
if not matched:
    print(f"Warning: No matching coordinate found for {coord_names[i]}")
```

### 4b. `jam_evaluation` plotting crash with 1-3 items
**File:** `pycomak/forsim.py:401-418`

**Fix:** Handle 1D axes from `plt.subplots(1, cols)` by reshaping:
```python
if rows == 1:
    ax = ax.reshape(1, -1)
```

Same fix for the ligaments plot block at L427.

### 4c. `knee_optimizer` records 'forsim_timeout' even for crashes
**File:** `pycomak/knee_optimizer.py:220`

**Problem:** `run_forsim()` returns `False` for both timeout and crash. The optimizer always
records `'forsim_timeout'`.

**Fix:** Change the recorded string to `'forsim_failed'` since it covers both cases. The
distinction between timeout and crash isn't critical for the optimizer's decision logic
(both cases trigger a patella update).

### 4d. `get_*_data` raw KeyError when group has no jam_list
**File:** `pycomak/group_analysis.py:636, 700, 779, 854, 943`

**Problem:** When a requested group has `jam_list == []`, the group is skipped in the loop,
`results` stays empty, and `return results[group]` raises raw `KeyError`.

**Fix:** Add after the loop:
```python
if group is not None and group not in results:
    raise KeyError(f"Group '{group}' has no loaded JAM data (0 subjects with JAM).")
```

Apply to all 5 `get_*_data` methods.

---

## Part 5: Test Additions

### 5a. NaN detection for remaining 3 methods
**File:** `tests/test_group_analysis.py` — extend `TestNaNDetection`

Add tests for `get_ligament_data`, `get_contact_force_data`, `get_regional_contact_data`
with NaN in the data, verifying `ValueError` is raised.

### 5b. Assertion that min/max absent from `get_muscle_data`
**File:** `tests/test_group_analysis.py` — `TestGetMuscleData`

Add `test_no_min_max_in_stats` asserting `'min' not in data` and `'max' not in data`.

### 5c. `add_subject` exception leaves lists in sync
**File:** `tests/test_group_analysis.py` — `TestAddSubject`

Add `test_failed_jam_does_not_corrupt_lists`: create H5 that would fail validation with
a second subject, verify that after the exception, `subjects`, `subject_ids`, and `jam_list`
all have the same length.

### 5d. `contact_accessor` ValueError on bad axis
**File:** `tests/test_group_analysis.py` — new test

Add `test_contact_force_bad_axis_raises` passing `axis='pressure'` to `get_contact_force_data`.

### 5e. Empty file list raises
**File:** `tests/test_jam_analysis.py`

Add `test_empty_file_list_raises` passing `[]` to `jam_analysis()`.

### 5f. `analyze_criteria` NaN detection
**File:** `tests/test_forsim_criteria.py`

Add `test_nan_data_fails_criteria` using a JAM with NaN values.

### 5g. `analyze_criteria` does not mutate input
**File:** `tests/test_forsim_criteria.py`

Existing `test_criteria_dict_reuse_across_calls` tests this but with empty criteria. Add
`test_criteria_dict_not_mutated` with actual thresholds, verifying the input dict is unchanged.

---

## Files Modified

| File | Changes |
|------|---------|
| `pycomak/group_analysis.py` | 1a, 1b, 1e, 1f, 3e, 4d |
| `pycomak/forsim.py` | 1c, 1d, 3a, 4b |
| `pycomak/jam_analysis.py` | 1g, 1h, 3d |
| `pycomak/plotting_utils.py` | 2a, 2b, 2c, 2d |
| `pycomak/defaults.py` | 3b, 3c |
| `pycomak/comak_ik.py` | 4a |
| `pycomak/knee_optimizer.py` | 4c |
| `tests/test_group_analysis.py` | 5a, 5b, 5c, 5d |
| `tests/test_jam_analysis.py` | 5e |
| `tests/test_forsim_criteria.py` | 5f, 5g |

---

## Breaking Changes

| Change | Impact | Migration |
|--------|--------|-----------|
| `add_subject` appends after JAM success | None for working H5 files. Failed `add_subject` no longer corrupts state. | No action needed |
| `analyze_criteria` returns copy, not mutated input | `KneeOptimizer.dict_criteria` stays clean between iterations | No action needed |
| `analyze_criteria` fails on NaN data | Previously silently passed | Fix simulation producing NaN |
| `create_save_sto` removes `convert_to_radians` param | Callers passing `convert_to_radians=True` get TypeError | Remove the argument from call sites |
| `plot_muscle_comparison` replaces `show_range` with `show_ste`/`show_std` | Callers using `show_range=True` get TypeError | Change to `show_ste=True` |
| Rotational coordinate plots now in degrees | Visual change — values ~57x larger for typical knee angles | Correct behavior |
| `_get_variable_label` translations now `(m)` not `(mm)` | Scatter plot labels change | Correct behavior |
| `knee_optimizer` records `'forsim_failed'` instead of `'forsim_timeout'` | Code checking `== 'forsim_timeout'` won't match | Change to `== 'forsim_failed'` |
| `load_secondary_constraints` uses NaN fill for missing subjects | NaN instead of zeros for missing data | Filter with `np.isnan()` if needed |

---

## Verification

```bash
conda run -n comak python -m pytest tests/ -v
```

All 151 existing tests should still pass (with adjustments for show_range → show_ste in any
plotting tests). New tests bring total to ~159.

---

## What this plan does NOT do

- Does not change MCL grouping in criteria (user decision: keep current behavior)
- Does not add tests for OpenSim-dependent classes (comak_ik, comaktool, jntmech, comak_id)
- Does not fix `add_subjects_from_list` missing filter params (convenience method, user can use `add_subject` directly)
- Does not change hardcoded COMAK output filenames (comaktool→ID, comaktool→JointMechanics coupling) — these are architectural decisions better addressed when/if the user needs configurability
- Does not fix `jam_evaluation` plotting crash with 0 items (pathological case)
- Does not fix `_process_frametransformsset_fast` dead code (behind `raise NotImplementedError`)
- Does not change `KneeOptimizer` results directory overwriting (by design for optimization loop)
