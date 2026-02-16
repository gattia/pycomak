# Specification: JointMechanics Output Filtering

## Overview

Add optional parameters to `pycomak.JointMechanics` to control which geometry/visualization outputs are written, reducing file count from ~30,000 to ~800 per subject.

## Problem Statement

The current `JointMechanics` class outputs VTP files for ALL model components at every timestep:
- 8 contact surfaces × 101 timesteps = 808 files (NEEDED)
- 95 ligament elements × 101 timesteps = 9,595 files
- 45 muscle visualizations × 101 timesteps = 4,545 files
- 154 body geometry meshes × 101 timesteps = 15,554 files

**Total: ~30,500 files (~1 GB) per subject**

For large cohort studies (700+ subjects), this creates millions of small files that are slow to copy, backup, and access.

## Current Implementation

File: `pycomak/jntmech.py`

```python
class JointMechanics(COMAKBASE):
    def __init__(
        self,
        results_dir,
        model_path,
        start_time,
        end_time,
        debug_level=0,
    ):
        # ... setup code ...

        # These are hardcoded to 'all':
        self.jnt_mech.set_contacts(0,'all')
        self.jnt_mech.set_contact_outputs(0,'all')
        self.jnt_mech.set_contact_mesh_properties(0,'none')
        self.jnt_mech.set_ligaments(0,'all')
        self.jnt_mech.set_ligament_outputs(0,'all')
        self.jnt_mech.set_muscles(0,'all')
        self.jnt_mech.set_muscle_outputs(0,'all')
        self.jnt_mech.set_attached_geometry_bodies(0,'all')
        self.jnt_mech.set_write_vtp_files(True)
```

## Proposed API Changes

### New Constructor Signature

```python
class JointMechanics(COMAKBASE):
    def __init__(
        self,
        results_dir: str,
        model_path: str,
        start_time: float,
        end_time: float,
        debug_level: int = 0,
        # NEW PARAMETERS:
        contacts: str = 'all',
        contact_outputs: str = 'all',
        contact_mesh_properties: str = 'none',
        ligaments: str = 'all',
        ligament_outputs: str = 'all',
        muscles: str = 'all',
        muscle_outputs: str = 'all',
        attached_geometry_bodies: str = 'all',
        write_vtp_files: bool = True,
        write_h5_file: bool = True,
    ):
```

### Parameter Descriptions

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `contacts` | str | `'all'` | Which contact geometries to analyze. `'all'`, `'none'`, or specific names. |
| `contact_outputs` | str | `'all'` | Which contact outputs to compute. `'all'` or `'none'`. |
| `contact_mesh_properties` | str | `'none'` | Contact mesh property outputs. `'all'` or `'none'`. |
| `ligaments` | str | `'all'` | Which ligaments to output. `'all'` or `'none'`. |
| `ligament_outputs` | str | `'all'` | Which ligament data to output. `'all'` or `'none'`. |
| `muscles` | str | `'all'` | Which muscles to output. `'all'` or `'none'`. |
| `muscle_outputs` | str | `'all'` | Which muscle data to output. `'all'` or `'none'`. |
| `attached_geometry_bodies` | str | `'all'` | Which body geometries to output. `'all'`, `'none'`, or specific body names. |
| `write_vtp_files` | bool | `True` | Whether to write individual VTP mesh files. |
| `write_h5_file` | bool | `True` | Whether to write consolidated H5 file. |

## Implementation Requirements

### 1. Backward Compatibility (CRITICAL)

All new parameters must have defaults matching current behavior. Existing code using `JointMechanics` without these parameters must work identically.

### 2. Implementation

Replace hardcoded values with parameters:

```python
def __init__(
    self,
    results_dir,
    model_path,
    start_time,
    end_time,
    debug_level=0,
    contacts='all',
    contact_outputs='all',
    contact_mesh_properties='none',
    ligaments='all',
    ligament_outputs='all',
    muscles='all',
    muscle_outputs='all',
    attached_geometry_bodies='all',
    write_vtp_files=True,
    write_h5_file=True,
):
    super().__init__(results_dir)
    save_xml_path = os.path.join(self.inputs_dir, 'joint_mechanics_settings.xml')

    self.jnt_mech = osim.JointMechanicsTool()
    self.jnt_mech.set_model_file(model_path)
    self.jnt_mech.set_input_states_file(os.path.join(self.comak_result_dir, '_states.sto'))
    self.jnt_mech.set_input_forces_file(os.path.join(self.comak_result_dir, '_force.sto'))
    self.jnt_mech.set_input_activations_file(os.path.join(self.comak_result_dir, '_activations.sto'))
    self.jnt_mech.set_use_muscle_physiology(False)
    self.jnt_mech.set_results_directory(self.jnt_mech_result_dir)
    self.jnt_mech.set_start_time(start_time)
    self.jnt_mech.set_stop_time(end_time)
    self.jnt_mech.set_resample_step_size(-1)
    self.jnt_mech.set_normalize_to_cycle(True)
    self.jnt_mech.set_lowpass_filter_frequency(-1)
    self.jnt_mech.set_print_processed_kinematics(False)

    # Use parameters instead of hardcoded values:
    self.jnt_mech.set_contacts(0, contacts)
    self.jnt_mech.set_contact_outputs(0, contact_outputs)
    self.jnt_mech.set_contact_mesh_properties(0, contact_mesh_properties)
    self.jnt_mech.set_ligaments(0, ligaments)
    self.jnt_mech.set_ligament_outputs(0, ligament_outputs)
    self.jnt_mech.set_muscles(0, muscles)
    self.jnt_mech.set_muscle_outputs(0, muscle_outputs)
    self.jnt_mech.set_attached_geometry_bodies(0, attached_geometry_bodies)

    self.jnt_mech.set_output_orientation_frame('ground')
    self.jnt_mech.set_output_position_frame('ground')
    self.jnt_mech.set_write_vtp_files(write_vtp_files)
    self.jnt_mech.set_vtp_file_format('binary')
    self.jnt_mech.set_write_h5_file(write_h5_file)
    self.jnt_mech.set_h5_kinematics_data(True)
    self.jnt_mech.set_h5_states_data(True)
    self.jnt_mech.set_write_transforms_file(True)
    self.jnt_mech.set_output_transforms_file_type('sto')
    self.jnt_mech.set_use_visualizer(False)
    self.jnt_mech.setDebugLevel(debug_level)

    analysis_set = osim.AnalysisSet()
    frc_reporter = osim.ForceReporter()
    frc_reporter.setName('ForceReporter')
    analysis_set.cloneAndAppend(frc_reporter)
    self.jnt_mech.set_AnalysisSet(analysis_set)
    self.jnt_mech.printToXML(save_xml_path)
```

### 3. Docstring Update

Update the class docstring to document all new parameters with examples.

## Example Usage

### Current (unchanged, outputs everything):
```python
joint_mechanics = JointMechanics(
    results_dir=results_dir,
    model_path=model_path,
    start_time=0.0,
    end_time=1.0,
)
```

### New (minimal output - contact surfaces only):
```python
joint_mechanics = JointMechanics(
    results_dir=results_dir,
    model_path=model_path,
    start_time=0.0,
    end_time=1.0,
    ligaments='none',
    muscles='none',
    attached_geometry_bodies='none',
)
```

### New (contact surfaces + ligaments, no muscles or body geometry):
```python
joint_mechanics = JointMechanics(
    results_dir=results_dir,
    model_path=model_path,
    start_time=0.0,
    end_time=1.0,
    muscles='none',
    attached_geometry_bodies='none',
)
```

## Expected Impact

With `ligaments='none', muscles='none', attached_geometry_bodies='none'`:
- **Before:** ~30,500 files, ~1 GB per subject
- **After:** ~808 files, ~65 MB per subject (contact surfaces only)

For 700 subjects: **~700 GB → ~45 GB** (and much faster file operations)

## Testing

1. Verify default parameters produce identical output to current implementation
2. Verify `ligaments='none'` produces no ligament VTP files
3. Verify `muscles='none'` produces no muscle VTP files
4. Verify `attached_geometry_bodies='none'` produces no body geometry VTP files
5. Verify contact surface VTPs are still produced when other outputs are disabled
6. Verify H5 file is still written correctly

## Files to Modify

- `pycomak/jntmech.py` - Main implementation changes

## Related Consumer Code

After this change is made, the following script will be updated to use the new parameters:
- `comak_gait_simulation/run_simulations/scripts/comak_2_comak_simulation.py`
