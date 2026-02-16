# Integration Report: JointMechanics Output Filtering

**Date:** 2026-02-05
**Library:** pycomak
**File Modified:** `pycomak/jntmech.py`

## Summary

The `JointMechanics` class has been updated with new default behavior that reduces output from ~1 GB to ~100 MB per subject. This is a **breaking change in output files** but maintains full backward compatibility via optional parameters.

## What Changed

### New Default Behavior

The `JointMechanics` class now defaults to minimal VTP output:

| Parameter | Old Default | New Default |
|-----------|-------------|-------------|
| `ligaments` | `'all'` | `'none'` |
| `muscles` | `'all'` | `'none'` |
| `attached_geometry_bodies` | `'all'` | `'none'` |

### Storage Impact

| Configuration | Files | Size |
|--------------|-------|------|
| **New defaults** | ~800 VTPs + H5 | ~100 MB/subject |
| Legacy (all VTPs) | ~30,000 VTPs + H5 | ~1 GB/subject |
| H5 only | 1 file | ~35 MB/subject |

### What's Still Written by Default

- **H5 file (~35 MB):** Contains ALL numerical data (kinematics, muscle forces, ligament forces, contact pressures, etc.) - unchanged
- **Contact surface VTPs (~800 files, ~65 MB):** Cartilage visualization for ParaView - unchanged

### What's No Longer Written by Default

- Ligament VTPs (~9,600 files) - data still in H5
- Muscle VTPs (~4,500 files) - data still in H5
- Body geometry VTPs (~15,500 files) - can regenerate later

## Integration Instructions

### For `comak_2_comak_simulation.py`

**No changes required** - the new defaults will automatically apply. Existing code will produce minimal output.

If you were previously passing filtering parameters explicitly, you can now remove them:

```python
# BEFORE (explicit minimal output)
joint_mechanics = JointMechanics(
    results_dir=results_dir,
    model_path=model_path,
    start_time=start_time,
    end_time=end_time,
    ligaments='none',
    muscles='none',
    attached_geometry_bodies='none',
)

# AFTER (same result with new defaults)
joint_mechanics = JointMechanics(
    results_dir=results_dir,
    model_path=model_path,
    start_time=start_time,
    end_time=end_time,
)
```

### If Legacy Behavior Is Needed

Pass explicit parameters to restore full VTP output:

```python
joint_mechanics = JointMechanics(
    results_dir=results_dir,
    model_path=model_path,
    start_time=start_time,
    end_time=end_time,
    ligaments='all',
    muscles='all',
    attached_geometry_bodies='all',
)
```

### If Bone Visualization Is Needed

For specific subjects where you want to visualize bones in ParaView:

```python
joint_mechanics = JointMechanics(
    results_dir=results_dir,
    model_path=model_path,
    start_time=start_time,
    end_time=end_time,
    attached_geometry_bodies='femur_r tibia_r patella_r',
)
```

## Key Points

1. **H5 file is unaffected** - all numerical data for analysis is still written
2. **VTP files can be regenerated** - just re-run JointMechanics with different parameters
3. **Existing analysis code is unaffected** - JamAnalysis reads from H5, not VTPs
4. **For 700 subjects:** ~70 GB total vs ~700 GB with old defaults

## New API Signature

Two types of output are controlled **independently**:

1. **H5 file** (~35 MB): Numerical data for analysis (kinematics, forces, pressures).
   Controlled by: `contact_outputs`, `ligament_outputs`, `muscle_outputs`
   Default: `'all'` for each (keeps full data for JamAnalysis).

2. **VTP files**: ParaView visualization meshes (one file per component per timestep).
   Controlled by: `contacts`, `ligaments`, `muscles`, `attached_geometry_bodies`
   Default: Only contact surfaces (`'all'` for contacts, `'none'` for others).

```python
class JointMechanics(COMAKBASE):
    def __init__(
        self,
        results_dir,
        model_path,
        start_time,
        end_time,
        debug_level=0,
        # --- VTP file controls (ParaView visualization) ---
        contacts='all',                    # Contact surface VTPs (KEEP 'all')
        ligaments='none',                  # Ligament VTPs - NEW DEFAULT (was 'all')
        muscles='none',                    # Muscle VTPs - NEW DEFAULT (was 'all')
        attached_geometry_bodies='none',   # Body geometry VTPs - NEW DEFAULT (was 'all')
        # --- H5 data controls (analysis data) ---
        contact_outputs='all',             # Contact data in H5 (keep 'all')
        ligament_outputs='all',            # Ligament data in H5 (keep 'all')
        muscle_outputs='all',              # Muscle data in H5 (keep 'all')
        contact_mesh_properties='none',
        # --- Global output controls ---
        write_vtp_files=True,
        write_h5_file=True,
    ):
```

## Testing Recommendation

After integrating, verify:
1. H5 file is created and contains expected data
2. Contact surface VTPs are created in `joint-mechanics/paraview/`
3. No ligament/muscle/body geometry VTPs are created (unless explicitly requested)
4. Downstream analysis (JamAnalysis, GroupJamAnalysis) works unchanged
