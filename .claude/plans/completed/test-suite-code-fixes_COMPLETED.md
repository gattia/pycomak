# Test Suite Code Fixes — COMPLETED

**Plan:** `.claude/plans/test-suite-overhaul.md` (Part 2: "For the future code-fixer")
**Prior work:** `.claude/plans/completed/test-suite-overhaul_COMPLETED.md` (wrote the tests)
**Date completed:** 2026-02-17

## What was done

Fixed all 13 xfail tests from the test suite overhaul, plus improved 4 fragile-but-passing code paths.

### Source code changes (4 files)

| File | Change | Fixes |
|------|--------|-------|
| `jam_analysis.py` | Added `import warnings` | Region warning support |
| `jam_analysis.py` | Added `self._analyzed = False` to `__init__` | Double-call guard |
| `jam_analysis.py` | Added `_get_file_structure(f)` method | Structure validation (reads keys from already-open handle, zero extra I/O) |
| `jam_analysis.py` | Updated `jam_analysis()`: double-call guard, `allow_mismatched_files` param, inline structure validation | Tests 1-3 (mismatched files) + Test 4 (double call) |
| `jam_analysis.py` | `_process_contact_fast()`: `warnings.warn()` when `n_regions > 6` | Test 5 (region count) |
| `jam_analysis.py` | `_process_generic_forceset_fast()`: clear `ValueError` on timestep mismatch | Truncated H5 improvement |
| `forsim.py` | `get_total_ligament_force()`: `if ligament_name in x` → `if x.startswith(ligament_name)` | Test 6 (prefix matching) |
| `group_analysis.py` | `get_ligament_data()`: same `in` → `startswith` change | Test 7 (prefix matching) |
| `group_analysis.py` | Added `self.removal_history = []` to `__init__` | Tests 10-11 (removal history) |
| `group_analysis.py` | `remove_subjects()`: raises `KeyError` for bad IDs, `IndexError` for bad indices, logs to `removal_history` | Tests 8-11 |
| `group_analysis.py` | `extract_values_at_time()`: validates `time_point` within `[0, 100]` | Test 12 (time boundary) |
| `group_analysis.py` | `identify_outlier_subjects()`: guards z-score division against `group_std == 0` | Outlier std=0 improvement |
| `group_analysis.py` | `get_regional_contact_data()`: wrapped initial dict access with helpful KeyError | Filtered contact improvement |
| `utils.py` | `run_with_timeout()`: checks `p.exitcode != 0` after join, raises `RuntimeError` | Test 13 (subprocess exception) |

### Test file changes (4 files)

- Removed all 13 `@pytest.mark.xfail` decorators
- Added `ga.removal_history = []` to 3 test helpers that use `__new__` (bypassing `__init__`)

### Breaking changes

1. **`jam_analysis()` rejects double calls** — calling it twice now raises `RuntimeError`. Users must create a new `JamAnalysis()` instance. This was always the correct usage pattern.

2. **`jam_analysis()` rejects mismatched file structures by default** — pass `allow_mismatched_files=True` to get the old behavior (silent zero-fill).

3. **`remove_subjects()` raises on bad input** — out-of-range indices raise `IndexError`, non-existent IDs raise `KeyError`. Previously silently skipped.

4. **`extract_values_at_time()` rejects out-of-range time points** — `time_point=150.0` now raises `ValueError`. Previously silently clamped to nearest index.

5. **`run_with_timeout()` raises on subprocess crash** — raises `RuntimeError` instead of printing "completed successfully".

6. **Ligament matching uses `startswith` instead of `in`** — `get_total_ligament_force(jam, "PT")` no longer matches a hypothetical fiber named `mPTl1`. All real ligament naming conventions (`ACLam1`, `MCLd1`, `PT1`, etc.) work identically with `startswith`.

### Performance note

The file structure validation in `jam_analysis()` uses the already-open H5 file handle to read key names (cached in memory by h5py). Zero extra file opens — the cost is negligible set comparisons.

## Final test results

```
144 passed, 0 failed, 0 xfailed
```
