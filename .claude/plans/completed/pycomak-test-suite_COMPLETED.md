# Plan: pycomak Test Suite

## Context

pycomak currently has **zero tests**. The library processes biomechanical simulation data through complex nested data structures, and bugs in H5 parsing or statistical aggregation produce silently wrong scientific results. As we accelerate development with AI agents, a test suite is the single highest-ROI investment to prevent regressions.

**Scope:** Test pure-Python logic and data processing. Do NOT test OpenSim API wrapper code (class `__init__` methods that just call `osim.*.set_*()`).

**Guiding principle from user:** "Some things like inputting params into a comak/opensim class are probably not needed, but more complex things should maybe be tested — make sure their looping logic makes sense."

---

## Test Directory Structure

```
tests/
    conftest.py                  # Shared fixtures: H5 factory, mock JamAnalysis factory
    test_jam_analysis.py         # Phase 1: H5 parsing (MOST IMPORTANT)
    test_forsim_criteria.py      # Phase 2: criteria evaluation
    test_group_analysis.py       # Phase 3: group-level analysis logic
    test_cleanup.py              # Phase 4: file operations
    test_utils.py                # Phase 4: timeout, file copy
    test_plotting_utils.py       # Phase 5: pure logic + smoke tests
    test_main.py                 # Phase 5: COMAKBASE directory structure
    test_comak_ik_logic.py       # Phase 6: ligament strain update logic
```

Update `pyproject.toml`:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["requires_opensim: test requires opensim Python bindings"]
```

---

## Fixture Strategy (conftest.py)

### Synthetic H5 Factory

Generate H5 files at test time using `h5py` (no checked-in binaries). A `create_h5` factory fixture creates files in `tmp_path` matching the structure that `JamAnalysis._process_*_fast()` expects:

```
/time                                                    # (n_timesteps,)
/model/forceset/Muscle/{name}/{outcome}                  # (n_timesteps,)
/model/forceset/Blankevoort1991Ligament/{name}/{outcome}  # (n_timesteps,)
/model/forceset/Smith2018ArticularContactForce/{contact}/{cartilage}/
    total_contact_force                                  # (n_timesteps, 3) Dataset
    regional_contact_force/{region_idx}                  # (n_timesteps, 3) Group→Dataset
    regional_max_pressure                                # (n_timesteps, n_regions) Dataset
    regional_mean_pressure                               # (n_timesteps, n_regions) Dataset
    regional_contact_area                                # (n_timesteps, n_regions) Dataset
/model/coordinateset/{coord}/value                       # (n_timesteps,)
/model/coordinateset/{coord}/speed                       # (n_timesteps,)
/comak/{item}                                            # (n_timesteps,) optional
```

Parameters: `n_timesteps`, `muscles`, `ligaments`, `contacts`, `coordinates`, `data_fill` (`'zeros'`/`'random'`/`'linear'`).

### Mock JamAnalysis Factory

For `test_group_analysis.py` and `test_forsim_criteria.py` — builds a `JamAnalysis` object with pre-populated `.forceset`, `.coordinateset`, `.time` attributes. No H5 files needed.

---

## Critical Files to Modify/Create

| File | Action |
|------|--------|
| `pyproject.toml` | Add pytest config |
| `tests/conftest.py` | Create — H5 factory, mock JamAnalysis factory |
| `tests/test_jam_analysis.py` | Create — ~29 H5 parsing tests |
| `tests/test_forsim_criteria.py` | Create — ~12 criteria evaluation tests |
| `tests/test_group_analysis.py` | Create — ~37 group analysis tests |
| `tests/test_cleanup.py` | Create — ~10 file operation tests |
| `tests/test_utils.py` | Create — ~7 utility tests |
| `tests/test_plotting_utils.py` | Create — ~10 plotting logic tests |
| `tests/test_main.py` | Create — ~4 COMAKBASE tests |
| `tests/test_comak_ik_logic.py` | Create — ~5 ligament strain update tests |

## Implementation Phases

### Phase 1: `test_jam_analysis.py` — H5 Parsing (Most Important)

**Files:** `pycomak/jam_analysis.py`, `tests/conftest.py`

**Entry point validation:**
- Rejects non-list input, non-`.h5` files
- Tracks missing files without crashing
- Default names are string indices

**Single-file shape validation (most critical):**
- Muscle: `(n_timesteps, 1)`, Ligament: `(n_timesteps, 1)`, Coordinate: `(n_timesteps, 1)`
- Contact total_force: `(n_timesteps, 3, 1)`
- Regional scalar (pressure/area): `(n_timesteps, 1)` per region
- Regional vector (force Group): `(n_timesteps, 3, 1)` per region
- COMAK data: `(n_timesteps, 1)` or `{}` if absent

**Multi-file stacking:**
- Two files → last axis is 2, data values land in correct file-index column

**Edge cases:**
- Missing `/model/forceset` group → `jam.forceset` stays `{}`
- 6 region keys (0-5) initialized for each cartilage surface

---

### Phase 2: `test_forsim_criteria.py` — Criteria Evaluation

**File:** `pycomak/forsim.py` — functions `get_total_ligament_force()`, `analyze_criteria()`

- Fiber summation, pattern matching, not-found handling
- Criteria pass/fail for all threshold types (max_range, max, min)
- Dict mutation side effects
- Empty criteria, preserved failure state

---

### Phase 3: `test_group_analysis.py` — Group-Level Analysis

**File:** `pycomak/group_analysis.py`

Uses mock JamAnalysis objects (no H5 files needed).

- `_filter_jam_data()`: filtering by contact types, cartilages, regions, outcomes
- `get_*_data()`: shape validation, mean/std/ste computation, missing key handling
- `remove_subjects()`: by id and by index
- `identify_outlier_subjects()`: known outlier detection, threshold parameter
- `extract_values_at_time()`: exact and window extraction

---

### Phase 4: `test_cleanup.py` + `test_utils.py` — File Operations

**Files:** `pycomak/cleanup.py`, `pycomak/utils.py`

All use `tmp_path` — no real files touched.

- `format_size()`, `find_joint_mechanics_dirs()`, `delete_files_in_dir()`
- `run_with_timeout()`, `copy_file_names_with_strings()`

---

### Phase 5: `test_plotting_utils.py` + `test_main.py`

**Files:** `pycomak/plotting_utils.py`, `pycomak/main.py`

- Pure logic: `assign_colors_to_groups()`, `_get_variable_label()`
- Smoke tests: plot functions return `Axes` without crashing
- `COMAKBASE(tmp_path)` creates all 8 expected subdirectories

---

### Phase 6: `test_comak_ik_logic.py` — Ligament Strain Updates

**File:** `pycomak/comak_ik.py`

- `update_ligament_reference_strain()`, `update_multiple_ligament_reference_strains()`
- Create lightweight object with `ref_force_info` dict (no OpenSim needed)

---

## Verification

```bash
cd /dataNAS/people/aagatti/programming/pycomak
pip install -e .
pytest tests/ -v
```

All tests should pass. Tests marked `@pytest.mark.requires_opensim` will skip if opensim isn't installed.

---

## Summary

| Phase | Tests | Priority | Key Risk Mitigated |
|-------|-------|----------|-------------------|
| 1 | ~29 | **Critical** | Wrong array shapes/values from H5 parsing |
| 2 | ~12 | High | Wrong pass/fail in patella optimization |
| 3 | ~37 | **Critical** | Wrong statistical summaries, memory leaks from bad filtering |
| 4 | ~17 | Medium | File deletion bugs, timeout failures |
| 5 | ~17 | Low | Plot crashes, directory structure drift |
| 6 | ~5 | Medium | Wrong ligament strain updates |
| **Total** | **~117** | | |

Implementation order: **Phase 1 → 2 → 3 → 4 → 5 → 6** (most critical first, then dependencies).

**Note:** After implementation, plan file should be copied to `/dataNAS/people/aagatti/programming/pycomak/.claude/plans/` per project conventions.
