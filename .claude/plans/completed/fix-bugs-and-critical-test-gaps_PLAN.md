# Plan: Fix Bugs & Critical Test Gaps

## Context

After reviewing all source files, all existing tests, and the main simulation script
(`comak_2_comak_simulation.py`), we identified **2 real bugs** and **6 critical test gaps**
that could cause silent wrong scientific results or runtime crashes in the pipeline.

The existing test suite (~80 tests) does a good job covering H5 parsing shapes and
basic happy paths. This plan targets the gaps that the AI agent missed.

---

## Part A: Fix Real Bugs (Code Changes)

### Bug 1: `identify_outlier_subjects(group=X)` crashes with AttributeError

**File:** `pycomak/group_analysis.py`
**Line:** ~1100
**Severity:** Runtime crash when analyzing a single group

**Problem:** When `group='healthy'` is passed, the internal `get_coordinate_data(..., group='healthy', return_individuals=True)` returns a raw `ndarray`, not a dict. Then:
```python
for group_name, data in data_dict.items():  # AttributeError: ndarray has no .items()
```

**Compare with** `extract_values_at_time` (line ~1002) which correctly guards:
```python
if group is not None and not isinstance(data_dict, dict):
    data_dict = {group: data_dict}
```

**Fix:** Add the same guard at the top of `identify_outlier_subjects`, after the data is fetched (around line 1098):
```python
# If single group requested, wrap in dict
if group is not None and not isinstance(data_dict, dict):
    data_dict = {group: data_dict}
```

**Test to add** (`test_group_analysis.py::TestIdentifyOutlierSubjects`):
```python
def test_single_group_does_not_crash(self, make_jam):
    """Passing group= explicitly should not raise AttributeError."""
    ga = self._build_uniform_ga(make_jam, n_subjects=5)
    jam = ga.groups["healthy"]["jam_list"][4]
    jam.coordinateset["knee_flex_r"]["value"][:] = 999.0
    outliers = ga.identify_outlier_subjects(
        coordinate_name="knee_flex_r", threshold_std=2.0, group="healthy"
    )
    assert "healthy" in outliers
    assert 4 in outliers["healthy"]["outlier_indices"]
```

---

### Bug 2: Skipped subjects corrupt subject-to-data mapping

**File:** `pycomak/group_analysis.py`
**Lines:** All `get_*_data` methods (~506-519, ~574-588, ~656-669, ~730-749, ~813-835)
**Severity:** Silent wrong subject labels on scatter plots and statistical analyses

**Problem:** When a subject raises `KeyError` (missing coordinate/muscle/etc.), the method:
1. Records the index in `skipped`
2. Removes those rows from `data` via `np.delete`
3. Returns the trimmed array

But the caller has **no way to know which subjects remain**. If they use
`group_analysis.groups[group]['subject_ids'][i]` to label `data[i]`, every subject
after the first skip gets the wrong label.

Downstream impact: `extract_values_at_time` uses `subject_ids` directly from the group
dict (line ~1028) without accounting for skips.

**Fix options (pick one):**

**Option A (Minimal - warn loudly):** When subjects are skipped, print which ones and
raise a warning. This at least makes the issue visible:
```python
if len(skipped) > 0:
    data = np.delete(data, skipped, axis=0)
    skipped_ids = [group_dict['subject_ids'][i] for i in skipped]
    import warnings
    warnings.warn(
        f"Skipped {len(skipped)}/{n_subjects} subjects in group '{group_name}': "
        f"{skipped_ids}. Returned array rows no longer align with subject_ids.",
        UserWarning
    )
```

**Option B (Better - return aligned data):** Return a dict that includes the valid
subject IDs alongside the data:
```python
if return_individuals:
    valid_ids = [group_dict['subject_ids'][i] for i in range(n_subjects) if i not in skipped]
    results[group_name] = {'data': data, 'subject_ids': valid_ids}
```
This is a breaking API change. Downstream code that does `data = get_coordinate_data(...)`
would need updating.

**Option C (Safest - no skip, just error):** Raise an error instead of silently skipping.
If a subject is missing data, that's a data integrity issue that should be fixed upstream.

**Recommendation:** Option A for now (non-breaking), with a TODO for Option B.

**Tests to add** (`test_group_analysis.py`):
```python
def test_skipped_subject_warns(self, make_jam):
    """When a subject is missing a coordinate, a warning should be raised."""
    ga = _build_group_analysis(make_jam, n_subjects=3)
    # Remove coordinate from subject 1
    del ga.groups["healthy"]["jam_list"][1].coordinateset["knee_flex_r"]
    with pytest.warns(UserWarning, match="Skipped"):
        data = ga.get_coordinate_data("knee_flex_r", group="healthy", return_individuals=True)
    assert data.shape[0] == 2  # 3 subjects minus 1 skipped
```

---

## Part B: Add Missing Critical Tests

### Test 3: Ligament fiber prefix matching ambiguity

**File to test:** `pycomak/forsim.py::get_total_ligament_force`
**File to test:** `pycomak/group_analysis.py::get_ligament_data`

**Risk:** Substring `in` matching means `'PFL'` matches `mPFL*`, `lPFL*`, AND `PFL*`.
While current pipeline uses `'mPFL'`/`'lPFL'` specifically, this is a landmine.

**Tests to add** (`test_forsim_criteria.py::TestGetTotalLigamentForce`):
```python
def test_pfl_prefix_ambiguity(self, make_jam):
    """'lPFL' should NOT match 'mPFL' or 'PFL' fibers."""
    jam = self._make_jam_with_ligaments(
        make_jam,
        {
            "lPFL1": np.array([10.0]),
            "mPFL1": np.array([20.0]),
            "PFL1": np.array([30.0]),
        },
    )
    # lPFL should only sum lPFL fibers
    result_l = get_total_ligament_force(jam, "lPFL")
    np.testing.assert_array_almost_equal(result_l, [10.0])

    # mPFL should only sum mPFL fibers
    result_m = get_total_ligament_force(jam, "mPFL")
    np.testing.assert_array_almost_equal(result_m, [20.0])

def test_pfl_without_prefix_matches_all(self, make_jam):
    """Document that 'PFL' matches lPFL, mPFL, and PFL (substring match)."""
    jam = self._make_jam_with_ligaments(
        make_jam,
        {
            "lPFL1": np.array([10.0]),
            "mPFL1": np.array([20.0]),
            "PFL1": np.array([30.0]),
        },
    )
    result = get_total_ligament_force(jam, "PFL")
    # Currently matches ALL three — this documents the behavior
    np.testing.assert_array_almost_equal(result, [60.0])
```

**IMPORTANT:** The first test (`test_pfl_prefix_ambiguity`) will **FAIL** with the current
implementation because `'lPFL' in 'lPFL1'` is True AND `'PFL' in 'lPFL1'` is also True,
but `'lPFL' in 'mPFL1'` is False. So `lPFL` actually works correctly. But `'mPFL' in 'PFL1'`
is False, and `'PFL' in 'mPFL1'` IS True. So the real issue is only when someone uses the
bare `'PFL'` prefix.

Run the first test to verify current behavior is correct for `lPFL`/`mPFL`, then decide
whether the `'PFL'` matching behavior is acceptable or needs a `startswith` fix.

If a fix is needed:
```python
# In forsim.py get_total_ligament_force:
fibers = [x for x in jam.forceset['Blankevoort1991Ligament'].keys() if x.startswith(ligament_name)]
```
But note: this changes `'MCL'` matching behavior — `'MCLd1'.startswith('MCL')` is True, so
that still works. And `'ACLam1'.startswith('ACL')` is True. This is strictly better.

---

### Test 4: Multi-file stacking with mismatched timestep counts

**File to test:** `pycomak/jam_analysis.py::jam_analysis`

**Risk:** Files with different `n_timesteps` crash with a confusing numpy shape error.
This happens when subjects have different gait cycle lengths.

**Test to add** (`test_jam_analysis.py::TestEdgeCases`):
```python
def test_mismatched_timesteps_raises_clear_error(self, create_h5, tmp_path):
    """Loading H5 files with different timestep counts should fail clearly."""
    h5_a = create_h5(filename="short.h5", n_timesteps=50,
                     muscles={"recfem_r": ["actuation"]})
    h5_b = create_h5(filename="long.h5", n_timesteps=100,
                     muscles={"recfem_r": ["actuation"]})
    jam = JamAnalysis()
    # Currently this crashes with a confusing numpy broadcasting error.
    # This test documents the behavior. If we want graceful handling,
    # JamAnalysis should validate timestep counts match.
    with pytest.raises(Exception):
        jam.jam_analysis([str(h5_a), str(h5_b)])
```

---

### Test 5: `analyze_criteria` with multi-file data (np.ptp over all axes)

**File to test:** `pycomak/forsim.py::analyze_criteria`

**Risk:** `np.ptp(data)` on shape `(n_timesteps, n_files)` computes across files, not
just across time. This would give wrong pass/fail decisions.

**Test to add** (`test_forsim_criteria.py::TestAnalyzeCriteria`):
```python
def test_criteria_on_multifile_coordinate_data(self, make_jam):
    """Criteria should evaluate per-column (per-file), not across all files."""
    # Subject A: pf_tx_r varies 0.000 to 0.001 (small range, should pass)
    # Subject B: pf_tx_r is constant at 0.010 (large value but small range)
    # If np.ptp operates across both columns, ptp = 0.010 which exceeds threshold
    jam = make_jam(
        coordinates={
            "pf_tx_r": {
                "value": np.column_stack([
                    np.linspace(0, 0.001, 10),  # file A: range=0.001
                    np.ones(10) * 0.010,         # file B: range=0.0
                ])
            }
        }
    )
    jam.num_files = 2
    criteria = {"coords": {"pf_tx_r": {"max_range": 0.005}}}
    criteria, passed = analyze_criteria(jam, criteria, "coords")
    # With np.ptp over all axes: ptp = 0.010 > 0.005 → FAIL (wrong!)
    # With np.ptp per file: max ptp = 0.001 < 0.005 → PASS (correct)
    # This test documents current (buggy) behavior:
    assert passed is False  # BUG: should be True if evaluated per-file
```

**Note:** This test documents the existing behavior. In practice, `analyze_criteria` is only
called with single-file JamAnalysis objects (from forsim evaluation), so this bug is latent.
But document it to prevent future issues.

---

### Test 6: All H5 files missing → undefined `jam.time`

**File to test:** `pycomak/jam_analysis.py`

**Risk:** If all files in the list are missing, `self.time` and `self.num_time_steps` are
never set. Downstream code gets `AttributeError`.

**Test to add** (`test_jam_analysis.py::TestEdgeCases`):
```python
def test_all_files_missing_attributes(self, tmp_path):
    """When all files are missing, time/num_time_steps should be safely handled."""
    jam = JamAnalysis()
    jam.jam_analysis([
        str(tmp_path / "missing_a.h5"),
        str(tmp_path / "missing_b.h5"),
    ])
    assert jam.num_missing_files == 2
    assert jam.num_files == 2
    # Verify that accessing time doesn't crash (or crashes with clear error)
    assert not hasattr(jam, 'time') or jam.time is None
    assert not hasattr(jam, 'num_time_steps') or jam.num_time_steps is None
```

If this fails (because `jam.time` is undefined), the fix is to initialize in `__init__`:
```python
self.time = None
self.num_time_steps = None
```

---

### Test 7: `get_ligament_data` fiber discovery from first subject only

**File to test:** `pycomak/group_analysis.py::get_ligament_data`

**Risk:** If subject 0 has fewer ligament fibers than others (different model version),
data from extra fibers is silently ignored.

**Test to add** (`test_group_analysis.py::TestGetLigamentData`):
```python
def test_heterogeneous_fiber_counts(self, make_jam):
    """If subjects have different fibers, only first subject's fibers are summed."""
    ga = GroupJamAnalysis.__new__(GroupJamAnalysis)
    ga.groups = {"test": {"subjects": [], "subject_ids": [], "jam_list": []}}
    ga.base_results_dir = "/fake"
    ga.comak_subfolder = "test"
    ga.timepoint = ""

    n = 20
    # Subject 0: only ACLam1
    jam0 = make_jam(ligaments={"ACLam1": {"total_force": np.ones((n, 1)) * 10}})
    # Subject 1: ACLam1 + ACLpl1
    jam1 = make_jam(ligaments={
        "ACLam1": {"total_force": np.ones((n, 1)) * 10},
        "ACLpl1": {"total_force": np.ones((n, 1)) * 5},
    })

    for i, jam in enumerate([jam0, jam1]):
        ga.groups["test"]["subjects"].append(
            {"subject_id": f"s{i}", "side": "R", "datetime": "d",
             "folder_results": "/f", "h5_file": "/f.h5"})
        ga.groups["test"]["subject_ids"].append(f"s{i}_R")
        ga.groups["test"]["jam_list"].append(jam)

    data = ga.get_ligament_data("ACL", group="test", return_individuals=True)
    # Subject 0: only ACLam1 = 10
    # Subject 1: only ACLam1 = 10 (ACLpl1 silently ignored because subject 0 didn't have it)
    np.testing.assert_array_almost_equal(data[0, :], 10.0)
    np.testing.assert_array_almost_equal(data[1, :], 10.0)  # NOT 15.0
    # This documents the "first subject defines the fiber list" behavior
```

---

### Test 8: Filter + get_data integration test

**File to test:** `pycomak/group_analysis.py`

**Risk:** `_filter_jam_data` restructures the contact dict. `get_regional_contact_data`
must navigate the filtered structure correctly. Currently untested end-to-end.

**Test to add** (`test_group_analysis.py`):
```python
class TestFilterThenGetData:
    def test_get_regional_data_after_filtering(self, make_jam):
        """get_regional_contact_data works correctly after _filter_jam_data."""
        n = 20
        contacts = {
            "tf_contact": {
                "tibia_cartilage": {
                    "total_contact_force": np.ones((n, 3, 1)),
                    0: {"regional_max_pressure": np.ones((n, 1)) * 999},
                    4: {"regional_max_pressure": np.ones((n, 1)) * 100},
                    5: {"regional_max_pressure": np.ones((n, 1)) * 200},
                }
            }
        }
        jam = make_jam(n_timesteps=n, contacts=contacts)

        ga = GroupJamAnalysis.__new__(GroupJamAnalysis)
        ga._filter_jam_data(jam, regions=[4, 5])

        # Build a group analysis with the filtered jam
        ga.groups = {"test": {
            "subjects": [{"subject_id": "s0", "side": "R", "datetime": "d",
                         "folder_results": "/f", "h5_file": "/f.h5"}],
            "subject_ids": ["s0_R"],
            "jam_list": [jam],
        }}
        ga.base_results_dir = "/fake"
        ga.comak_subfolder = "test"
        ga.timepoint = ""

        data = ga.get_regional_contact_data(
            region=4, outcome="regional_max_pressure", axis="pressure",
            group="test", return_individuals=True
        )
        np.testing.assert_array_almost_equal(data[0, :], 100.0)

        data5 = ga.get_regional_contact_data(
            region=5, outcome="regional_max_pressure", axis="pressure",
            group="test", return_individuals=True
        )
        np.testing.assert_array_almost_equal(data5[0, :], 200.0)
```

---

## Implementation Order

1. **Bug 1** — Fix `identify_outlier_subjects` + add test (~5 min)
2. **Bug 2** — Add warning for skipped subjects + add test (~10 min)
3. **Test 3** — Ligament prefix matching + decide on `startswith` fix (~15 min)
4. **Test 4** — Mismatched timesteps (~5 min)
5. **Test 5** — `analyze_criteria` multi-file behavior (~5 min)
6. **Test 6** — All files missing + fix `__init__` defaults (~5 min)
7. **Test 7** — Heterogeneous fiber counts (~5 min)
8. **Test 8** — Filter + get_data integration (~10 min)

**Total:** ~60 minutes of implementation

---

## Verification

```bash
cd /dataNAS/people/aagatti/programming/pycomak
pytest tests/ -v
```

All existing tests should still pass. New tests should:
- Tests 1, 2, 6: pass after the corresponding bug fix
- Tests 3, 5, 7: document current (potentially buggy) behavior with clear comments
- Tests 4, 8: pass as-is (testing existing correct behavior or expected errors)
