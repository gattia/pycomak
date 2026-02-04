# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

pycomak is a Python library for biomechanical simulations using the COMAK (Concurrent Optimization of Muscle Activations and Kinematics) framework within OpenSim. It provides wrappers around OpenSim tools for knee joint mechanics and cartilage contact studies.

**Status:** Alpha - APIs may change.

## Development Setup

```bash
conda create -n pycomak python=3.9
conda activate pycomak
pip install -r requirements.txt
pip install -e .
```

### Dependencies

**Required (not in requirements.txt - installed via conda/manual):**
- `opensim` - OpenSim Python bindings (version with COMAK tools: COMAKInverseKinematicsTool, COMAKTool, JointMechanicsTool, ForsimTool)
- `nsosim` - Upstream library for model creation (provides `nsosim.osim_utils`)

**Python packages:**
- `numpy` - Array operations
- `matplotlib` - Plotting
- `h5py` - HDF5 file reading for JamAnalysis
- `pandas` - DataFrame operations in GroupJamAnalysis

## Code Style

Configured in `pyproject.toml`:
- **black**: line-length 100
- **isort**: profile "black", line-length 100

No automated test suite exists yet.

## Architecture

### Class Hierarchy

`COMAKBASE` (in `main.py`) is the foundation class that all workflow tools inherit from. It manages the standardized directory structure:
```
results_dir/
├── inputs/           # Settings files (.xml, .json)
├── logs/             # OpenSim log files
├── comak-inverse-kinematics/
│   ├── Geometry/     # Copied from model
│   ├── *.osim        # Intermediate and final models
│   └── *.xml         # Constraint function files
├── comak-inverse-dynamics/
├── comak/
│   ├── _states.sto
│   ├── _values.sto
│   ├── _force.sto
│   └── _activations.sto
├── joint-mechanics/
│   ├── .h5           # Main output file
│   └── paraview/     # VTP files
└── graphics/
```

### Simulation Workflow Classes

The typical workflow follows this sequence:

1. **`KneeOptimizer`** (`knee_optimizer.py`) - Optional patella position optimization
2. **`COMAKInverseKinematics`** (`comak_ik.py`) - Settle sims, sweep sims, and IK solve
3. **`COMAK`** (`comaktool.py`) - Main COMAK simulation for muscle activations
4. **`COMAKInverseDynamics`** (`comak_id.py`) - Joint reaction forces/moments
5. **`JointMechanics`** (`jntmech.py`) - Contact mechanics, ligament/muscle forces

### Analysis Classes

- **`JamAnalysis`** (`jam_analysis.py`) - Single-subject HDF5 analysis from JointMechanicsTool output
- **`GroupJamAnalysis`** (`group_analysis.py`) - Multi-subject group-level analysis with statistical summaries
- **`plotting_utils.py`** - Standardized plotting for kinematics, forces, contact mechanics

### Key Supporting Modules

- **`defaults.py`** - Default parameters: coordinates, ligament reference strains, muscle weights, secondary coordinate definitions (including meniscus coordinates)
- **`forsim.py`** - Forward simulation wrapper (`COMAKforsim`) used in optimization loops
- **`dict_converter.py`** - Format conversion utilities for slack length, reference strain, and current length
- **`utils.py`** - Utilities including `run_with_timeout()` and `copy_file_names_with_strings()`

## Key Class APIs

### COMAKInverseKinematics
```python
comak_ik = COMAKInverseKinematics(
    base_model_path, results_dir, stop_time_ik, start_time_ik, markerset_file,
    settle_sim_reps=5,  # Total settles = settle_sim_reps (N-1 in settle + 1 in sweep)
    secondary_coordinates=SECONDARY_COORDINATES,  # from defaults.py
)
comak_ik.perform_settle_sim()        # Does (settle_sim_reps - 1) iterations
comak_ik.perform_sweep_sim()         # Does 1 more settle + sweep
comak_ik.perform_inverse_kinematics()

# Key attributes:
comak_ik.final_model_path                  # Path to model after settle+sweep
comak_ik.settle_sim_intermed_model_filepath  # Intermediate model path
comak_ik.ref_force_info                    # Ligament/muscle reference lengths
```

### COMAK
```python
comaktool = COMAK(
    results_dir, forceset_file, model_path, external_loads_file,
    start_time, stop_time,
    muscle_weights_dict=muscle_weights_dict,  # Optional, from defaults.py
    # IPOPT parameters (defaults usually work)
    ipopt_max_iterations=500,
    ipopt_convergence_tolerance=1e-4,
    contact_energy_weight=500,
)
comaktool.run()
```

### KneeOptimizer
```python
optimizer = KneeOptimizer(
    path_model_to_update, results_dir, markerset_file,
    dict_kinematics=forsim_patella_optimization_kinematics,  # from defaults.py
    dict_muscles=forsim_patella_optimization_muscle_activations,
    dict_criteria=patella_optimization_criteria,
    settle_sim_reps=2,  # Use main_ik_settle_reps + 1
    dict_reference_strain_update=None,  # Optional strain updates
)
result = optimizer.optimize_patella_location()
# Returns: None (success), 'settle_sim_timeout', 'forsim_timeout', 'patella_opt_max_updates'

optimizer.intermediate_model_path  # Path to equilibrated model with optimized patella
optimizer.n_updates                # Number of patella adjustments made
optimizer.list_eval_results        # Evaluation results from each iteration
```

### JamAnalysis (Optimized for Performance)
```python
jam = JamAnalysis()
jam.jam_analysis(['/path/to/file.h5'])  # Opens each H5 file only ONCE (~50x faster)

# Access data:
jam.time                                    # Time vector
jam.coordinateset['knee_flex_r']['value']   # Coordinate values (n_timesteps, n_files)
jam.forceset['Muscle']['recfem_r']['actuation']
jam.forceset['Blankevoort1991Ligament']['ACLam1']['total_force']
jam.forceset['Smith2018ArticularContactForce']['tf_contact']['tibia_cartilage']['total_contact_force']
jam.forceset['Smith2018ArticularContactForce']['tf_contact']['tibia_cartilage'][4]['regional_max_pressure']  # Region 4 = medial tibia
```

### GroupJamAnalysis
```python
group_analysis = GroupJamAnalysis(base_results_dir, comak_subfolder='comak_results')

# Add subjects with automatic memory filtering
group_analysis.add_subject('9003175', 'RIGHT', '2025-08-21_21-33-10', group='healthy',
                          filter_data=True)  # Critical for memory - reduces pickle from 100GB to 500MB

# Get data for plotting
data = group_analysis.get_coordinate_data('knee_flex_r', return_individuals=False)
# Returns: {'healthy': {'mean': array, 'std': array, 'ste': array, 'time': array, 'n': int}}

data = group_analysis.get_ligament_data('ACL', return_individuals=True)
# Returns: {'healthy': array of shape (n_subjects, n_timesteps)}

data = group_analysis.get_regional_contact_data(region=4, outcome='regional_max_pressure', axis='pressure')
```

### COMAKforsim (for patella optimization)
```python
forsim = COMAKforsim(
    path_model, dict_kinematics, dict_muscles, folder_save_results,
    max_forsim_time=120,  # 2 minute timeout
)
success = forsim.run_forsim()  # Returns True/False
forsim.run_joint_mechanics_tool()
passed = forsim.jam_evaluation(dict_criteria)
```

## Key Data Structures in defaults.py

### Coordinate Definitions
```python
prescribed_coordinates  # Dict[str, str]: Index -> OpenSim coordinate path (36 coordinates)
primary_coordinates     # Dict[str, str]: Index -> hip/knee/ankle coordinates (5 coordinates)
secondary_coordinates   # Dict[str, Dict]: Name -> {'max_change': float, 'coordinate': str}
                       # Includes knee, patella, and menisci (24 coordinates total)
```

### Ligament Reference Strains (slack_length_dict)
```python
slack_length_dict = {
    'MCLd1': 0.04, 'MCLd2': -0.04, ...  # MCL deep fibers
    'ACLam1': -0.14, ...                 # ACL anteromedial
    'ACLpl1': 0.03, ...                  # ACL posterolateral
    'PT1': 0.02, ...                     # Patellar tendon (6 fibers)
    # ... all fiber-level reference strains
}
```

### COMAK Muscle Weights (muscle_weights_dict)
Based on Colin Smith's thesis - used to tune muscle activations:
```python
muscle_weights_dict = {
    'gasmed_r': 4, 'gaslat_r': 7,  # Gastrocnemius
    'soleus_r': 0.9,
    'recfem_r': 3,                  # Rectus femoris
    'glmed1_r': 0.9, ...            # Gluteus medius
}
```

### Patella Optimization Defaults
```python
# Prescribed kinematics for forsim (0.2s simulation, 0-5 deg knee flexion)
forsim_patella_optimization_kinematics = {'time': array, 'knee_flex_r': array, 'pelvis_tilt': 90}

# Muscle activations (linear ramp 0 to 0.6)
forsim_patella_optimization_muscle_activations = {'time': array, 'recfem_r_activation': array, ...}

# Evaluation criteria
patella_optimization_criteria = {
    'ligaments': {'PT': {}, 'ACL': {}, ...},
    'coords': {'pf_tx_r': {'max_range': 0.004}, ...}
}
```

## HDF5 Output Structure (from JointMechanicsTool)

```
/time                                           # (n_timesteps,) float array
/model/
├── forceset/
│   ├── Muscle/
│   │   └── {muscle_name}/
│   │       ├── actuation                       # (n_timesteps,) force in N
│   │       ├── activation
│   │       └── fiber_length
│   ├── Blankevoort1991Ligament/
│   │   └── {ligament_fiber_name}/
│   │       ├── total_force                     # (n_timesteps,)
│   │       └── strain
│   └── Smith2018ArticularContactForce/
│       └── {contact_name}/                     # e.g., tf_contact, pf_contact
│           └── {cartilage_surface}/            # e.g., tibia_cartilage
│               ├── total_contact_force         # (n_timesteps, 3) xyz components
│               └── {region_idx}/               # 0-5 for 6 regions
│                   ├── regional_contact_force  # (n_timesteps, 3)
│                   ├── regional_max_pressure   # (n_timesteps,)
│                   ├── regional_mean_pressure
│                   └── regional_contact_area
└── coordinateset/
    └── {coordinate_name}/
        ├── value                               # (n_timesteps,)
        └── speed
/comak/                                         # Optional COMAK-specific data
```

## Full Simulation Pipeline

pycomak is the **second stage** of a two-stage pipeline:

```
nsosim (model creation) → pycomak (COMAK simulation)
```

### Stage 1: nsosim (upstream)
Creates subject-specific OpenSim knee models from imaging data:
- Fits Neural Shape Models (NSM) to subject bone/cartilage surfaces
- Creates articular contact surfaces (femur, tibia, patella, menisci)
- Fits wrap surfaces (ellipsoid, cylinder) for muscle/ligament paths
- Interpolates ligament attachment points from reference to subject
- Outputs: `{model_name}_nsm_{subject}_{timepoint}_{side}_{version}.osim`

### Stage 2: pycomak (this library)
Runs COMAK simulations on the nsosim-generated model:
- Patella optimization → IK → COMAK → ID → Joint Mechanics
- Outputs: HDF5 files with kinematics, forces, contact mechanics

### nsosim Dependencies

The `menisci` branch depends on `nsosim.osim_utils` for:
- `update_slack_lengths()` - Updates ligament slack lengths in model
- `get_osim_muscle_ligament_reference_lengths()` - Gets current reference lengths
- `update_joint_default_values()` - Updates joint coordinate defaults

## Critical Patterns (Non-Obvious)

### Model Chaining Between Steps
Each workflow step produces a modified model for the next step:
- `KneeOptimizer.intermediate_model_path` → `COMAKInverseKinematics`
- `COMAKInverseKinematics.final_model_path` → `COMAK`, `COMAKInverseDynamics`, `JointMechanics`

### Settle Sim Reps Nuance
- `settle_sim_reps=N` performs `N-1` settles in `perform_settle_sim()`, then 1 in `perform_sweep_sim()`
- **For KneeOptimizer**: Use `settle_sim_reps+1` because it doesn't run sweep sim

### Timeout Handling
Long-running sims should use `run_with_timeout(func, seconds)` from `pycomak.utils`:
```python
run_with_timeout(comak_ik.perform_settle_sim, 60*5)   # 5 min
run_with_timeout(comak_ik.perform_sweep_sim, 60*120)  # 2 hr
run_with_timeout(comaktool.run, 60*180)               # 3 hr
```

### Return Values on Failure
`KneeOptimizer.optimize_patella_location()` returns `None` on success, or error strings:
`'settle_sim_timeout'`, `'forsim_timeout'`, `'patella_opt_max_updates'`

### Updating Ligament Reference Strains
```python
# Single ligament
comak_ik.update_ligament_reference_strain('MCLd1', 0.05)

# Multiple ligaments
comak_ik.update_multiple_ligament_reference_strains({'MCLd1': 0.05, 'ACLpl1': 0.02})
```

### Memory Management for GroupJamAnalysis
**Critical:** Without filtering, pickle files can be 100+ GB. With filtering: ~500 MB.
```python
# Default filtering keeps only essential data:
# - Contact: tf_contact, tibia_cartilage, regions 4 & 5, pressure/area/force
# - Muscles: only 'actuation' outcome
# - Ligaments: all data (relatively small)
# - Coordinates: all data (relatively small)

group_analysis.add_subject(..., filter_data=True)  # Default

# Custom filtering for patellofemoral analysis:
group_analysis.add_subject(...,
    contact_types=['tf_contact', 'pf_contact'],
    cartilages=['tibia_cartilage', 'patella_cartilage'],
    regions=[4, 5])
```

## Plotting Utilities

### Available Functions
```python
from pycomak.plotting_utils import (
    plot_coordinate_comparison,      # Mean ± std/ste across groups
    plot_coordinate_individuals,     # Individual traces
    plot_kinematics_panel,           # Multi-panel kinematic plots
    plot_muscle_comparison,
    plot_muscle_individuals,
    plot_muscles_panel,
    plot_ligament_comparison,
    plot_ligament_individuals,
    plot_ligaments_panel,
    plot_regional_contact,
    plot_regional_contact_individuals,
    plot_contact_comparison_panel,
    create_publication_figure,
    plot_variable_scatter,           # Scatter plot correlations
    plot_scatter_panel,
    assign_colors_to_groups,         # Color assignment utility
)

# Standard label dictionaries available:
from pycomak.plotting_utils import (
    COORDINATE_LABELS, MUSCLE_LABELS, LIGAMENT_LABELS, REGION_LABELS, GROUP_COLORS
)
```

### Example Usage
```python
# Get data and plot
data = group_analysis.get_coordinate_data('knee_flex_r', return_individuals=False)
plot_coordinate_comparison(data, 'knee_flex_r', translation_units='mm')

# Multi-panel figure
fig, axes = plot_kinematics_panel(
    group_analysis,
    coordinates=['knee_flex_r', 'knee_add_r', 'knee_rot_r'],
    plot_type='mean'
)
```

## Required Input Files

- **Marker file** (`.trc`): Motion capture data
- **External loads file** (`.xml`): Ground reaction forces for COMAK/ID
- **Reserve actuators file** (`.xml`): Force set for COMAK (e.g., `smith2019_reserve_actuators.xml`)
- **Ligament parameters** (`.json`): Optional custom strain/stiffness, format: `{"LIG_NAME": {"strain": float, "stiffness": float}}`

## Output Files

### From COMAKInverseKinematics
- `model_update_slack_intermediate.osim` - After settle sims
- `model_updated_slack_final.osim` - After settle + sweep
- `ik_constrained_model_final.osim` - Constrained model for IK
- `secondary_coordinate_constraint_functions_final.xml` - Constraint functions
- `comak_ik.mot` - IK motion file

### From COMAK
- `_states.sto` - Full state trajectory
- `_values.sto` - Coordinate values
- `_force.sto` - Force outputs
- `_activations.sto` - Muscle activations

### From JointMechanics
- `.h5` - Main HDF5 output with all mechanics data
- `*.vtp` - ParaView visualization files (in paraview/ subdirectory)

## Example Usage

Full pipeline examples (run in order):

1. **nsosim model creation** (Stage 1):
   `/dataNAS/people/aagatti/projects/comak_gait_simulation/stuff/comak_1_update_comak_knee_nsm_OAI_Oct.31.2025_stiff_pt_pfp_contact.py`

2. **pycomak simulation** (Stage 2):
   `/dataNAS/people/aagatti/projects/comak_gait_simulation/stuff/comak_2_comakPipeline_class_Gatti_Nov.20.2025_prefemoral_fatpad.py`

Typical SLURM usage:
```bash
# Stage 1: Model creation (needs GPU)
salloc -c 2 --mem=24gb --gres=gpu:2080ti:1 --time=1-00
python comak_1_...py 9003175 --side RIGHT --model-version 2025-10-19

# Stage 2: COMAK simulation (CPU only)
salloc -c 4 --mem=24gb --time=1-00
python comak_2_...py 9003175 --side RIGHT --model-version 2025-10-19
```

## Troubleshooting

### Timeout Issues
- **settle_sim_timeout**: Model may be unstable. Try adjusting ligament strains or checking model geometry.
- **forsim_timeout**: Increase `max_duration` or simplify the model.

### Memory Issues with GroupJamAnalysis
- Always use `filter_data=True` (default) when adding subjects
- Customize filtering if you need specific data (e.g., patellofemoral)
- Consider processing in batches for very large datasets

### OpenSim Logging
Logs are written to `results_dir/logs/`. Check these for simulation errors.

### Common Errors
- Missing Geometry folder: Ensure model's Geometry folder is accessible
- NaN in outputs: Usually indicates model instability - check settle sim results
- HDF5 file not found: Check `joint-mechanics/` subdirectory naming

## Branch Notes

- **main**: Stable baseline
- **menisci**: Active development with meniscus kinematics support, breaking API changes from main (see commit history for details)
