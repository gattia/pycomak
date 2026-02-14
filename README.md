```bash
# create environment
conda create -n pycomak python=3.9
conda activate pycomak

pip install -r requirements.txt

pip install -e .
```

### Additional Dependencies (not pip-installable)

- **opensim** - This project requires the [opensim-jam](https://github.com/opensim-jam-org/opensim-core) fork of OpenSim (by Colin Smith), which includes COMAK tools (`COMAKInverseKinematicsTool`, `COMAKTool`, `JointMechanicsTool`, `ForsimTool`). This must be built from source; the standard `opensim` pip package does not include these tools.
- **nsosim** - Upstream library for subject-specific model creation (provides `nsosim.osim_utils`).

## Project Status

This project is currently in **Alpha** stage. It is under active development, and APIs might change.

## Purpose / Motivation

The `pycomak` library provides a Python interface and a suite of convenience functions for working with the COMAK (Concurrent Optimization of Muscle Activations and Kinematics) version of OpenSim. It aims to streamline the process of setting up, running, and analyzing COMAK-based simulations, particularly for knee joint mechanics and cartilage contact studies. The library wraps core OpenSim tools like COMAKTool, COMAKInverseKinematics, InverseDynamicsTool, ForsimTool, and JointMechanicsTool, offering a higher-level API and helper utilities for common tasks in a biomechanical simulation workflow.

## Key Features

*   **COMAK Workflow Management:** Simplifies setting up and executing the full COMAK pipeline, including inverse kinematics, inverse dynamics, and the main COMAK simulation.
*   **OpenSim Tool Wrappers:** Provides Python classes (`COMAK`, `COMAKInverseKinematics`, `COMAKInverseDynamics`, `JointMechanics`, `COMAKforsim`) that encapsulate the functionality of underlying OpenSim tools, managing their complex configurations.
*   **Automated Directory Structure:** The `COMAKBASE` class establishes a standardized directory structure for inputs, logs, and results.
*   **Parameter Management:** Utilizes default parameter sets (e.g., for coordinates, ligament properties, muscle weights) stored in `defaults.py`, which can be customized by the user.
*   **Joint Mechanics Analysis:** Includes the `JamAnalysis` class for in-depth post-processing of simulation outputs (primarily from HDF5 files), focusing on forces, kinematics, and contact mechanics.
*   **Knee-Specific Optimization:** Offers a `KneeOptimizer` class to iteratively adjust knee model parameters (e.g., patella position) based on simulation results and predefined criteria.
*   **Utility Functions:** Provides helper functions for tasks such as running processes with timeouts and managing output files.

## Overview

The `pycomak` library is designed to facilitate biomechanical simulations using the COMAK framework within OpenSim. It is structured into several modules, each addressing a specific part of the simulation and analysis workflow:

*   **`main.py` (`COMAKBASE`)**: Establishes the foundational class for managing file paths and standardized directory structures for all COMAK-related analyses.
*   **`comaktool.py` (`COMAK`)**: Wraps the main `COMAKTool` from OpenSim, allowing users to configure and run simulations that concurrently optimize muscle activations and kinematics.
*   **`comak_ik.py` (`COMAKInverseKinematics`)**: Manages the COMAK Inverse Kinematics (IK) process. This includes settling simulations to adjust model parameters (e.g., ligament slack lengths), sweep simulations to generate constraint functions, and the IK solve itself. It also contains utilities for updating model properties like ligament and muscle lengths.
*   **`comak_id.py` (`COMAKInverseDynamics`)**: Provides a wrapper for OpenSim's `InverseDynamicsTool`, tailored for use within the COMAK workflow to calculate net joint moments.
*   **`jntmech.py` (`JointMechanics`)**: Wraps OpenSim's `JointMechanicsTool` for detailed post-simulation analysis of joint forces, contact pressures, ligament tensions, muscle contributions, and kinematics.
*   **`jam_analysis.py` (`JamAnalysis`)**: Contains tools for advanced analysis of joint and articular mechanics, primarily by parsing and processing HDF5 output files from `JointMechanicsTool`. It facilitates the extraction and visualization of detailed biomechanical data.
*   **`group_analysis.py` (`GroupJamAnalysis`)**: Provides a high-level interface for multi-subject, group-level analysis. Enables loading multiple subjects into groups (e.g., healthy, OA, progressors), extracting data across subjects (kinematics, muscle forces, ligament forces, contact mechanics), computing statistical summaries (mean, std, STE), and accessing individual subject traces for detailed analysis or statistical testing.
*   **`plotting_utils.py`**: Contains standardized plotting functions for common JAM analysis visualizations including multi-panel kinematic plots, muscle force comparisons, and contact mechanics figures. Supports both group-mean plots with uncertainty bands and individual trace visualizations.
*   **`forsim.py` (`COMAKforsim`)**: Provides classes and functions to run forward simulations using OpenSim's `ForsimTool`. This module is often used for sensitivity analyses, evaluating specific kinematic conditions, or as part of optimization loops (like in `knee_optimizer.py`). It includes utilities for creating input files and evaluating simulation outputs against specific criteria.
*   **`knee_optimizer.py` (`KneeOptimizer`)**: Implements an optimization routine specifically for knee models, focusing on adjusting parameters like the patella's default position. It uses an iterative approach, running COMAK IK and Forsim simulations, and evaluating results to refine the model.
*   **`utils.py`**: A collection of helper functions for common tasks such as file operations (e.g., copying Paraview outputs) and running functions with timeouts to prevent indefinite execution.
*   **`defaults.py`**: Stores default configurations and parameter values used across the library, such as coordinate definitions for COMAK, reference ligament strains, muscle lengths, and muscle weights for the COMAK cost function. These defaults can be overridden by the user.
*   **`__init__.py`**: Initializes the `pycomak` package, making key classes and sub-modules easily accessible.

## Basic Workflow / Usage Examples

A typical workflow using the `pycomak` library for a knee simulation, as exemplified in usage scripts, might involve the following conceptual steps:

1.  **Setup and Configuration:**
    *   Define subject-specific information, paths to the base OpenSim model (.osim), motion capture data (e.g., marker .trc files, external loads .xml files), and the desired main results directory.
    *   It is common practice to copy the base OpenSim model to a new file path within the subject's results directory (e.g., `model_to_optimize.osim`). This new model path will be used for subsequent optimization and IK steps, preserving the original.
    *   Optionally, customize default parameters (e.g., `slack_length_dict` for ligament reference strains, `muscle_weights_dict` for COMAK cost function) by modifying copies of dictionaries imported from `pycomak.defaults`.

2.  **Knee Model Optimization (Optional, e.g., Patella Position using `KneeOptimizer` from `knee_optimizer.py`):**
    *   This step is often performed if subject-specific adjustments to knee geometry, like the patella's default anterior-posterior or superior-inferior position, are required before running the full gait simulation.
    *   Inputs include the path to the model that will be updated (e.g., `model_to_optimize.osim`), a dedicated results directory for this optimization sub-process, the markerset file (for internal IK settle simulations), and often predefined kinematics, muscle activations, and evaluation criteria (e.g., `forsim_patella_optimization_kinematics`, `patella_optimization_criteria` from `pycomak.defaults`).
    *   The `KneeOptimizer` iteratively performs the following internal loop:
        *   Adjusts the specified model parameter (e.g., the patella body's default y-translation in the parent frame).
        *   Runs a COMAK IK settle simulation (via `COMAKInverseKinematics.perform_settle_sim`) to update ligament properties (e.g., slack lengths) based on the newly adjusted geometry.
        *   Executes a `COMAKforsim` forward simulation using the settled model and the predefined test kinematics/activations.
        *   Evaluates the `COMAKforsim` results (e.g., patellofemoral contact forces, ligament forces, patellar kinematics) against the specified criteria.
    *   The loop continues until the criteria are met or a maximum number of updates is reached. The primary output of this step is the modified OpenSim model file (e.g., `model_to_optimize.osim` is updated in place).

3.  **COMAK Inverse Kinematics (using `COMAKInverseKinematics` from `comak_ik.py`):**
    *   Inputs: The OpenSim model file (this should be the `model_to_optimize.osim` that was potentially modified by the `KneeOptimizer`), the marker data file (.trc), and the desired time range for the IK solution.
    *   The `COMAKInverseKinematics` tool then typically executes:
        *   `perform_settle_sim()`: A settling simulation that further refines model parameters, particularly ligament slack lengths based on the (now patella-optimized) model's initial pose or a reference state. This ensures the model is in a reasonable equilibrium before tracking motion.
        *   `perform_sweep_sim()`: Sweep simulations that generate constraint functions for the model's secondary coordinates, based on the settled model from the previous step.
        *   `perform_inverse_kinematics()`: The final IK solve that computes joint kinematics (output as a .mot file, typically `comak_ik.mot`) to best track the experimental marker data, while respecting the model's (now settled and constrained) mechanics.
    *   This step outputs the `final_model_path` (the model after settle and sweep, used for the main COMAK simulation) and the computed joint kinematics.

4.  **COMAK Simulation (using `COMAK` from `comaktool.py`):**
    *   Inputs: The `final_model_path` from the `COMAKInverseKinematics` step, the IK-derived kinematics .mot file, the external loads file, and any necessary force set files (e.g., for reserve actuators).
    *   Configure COMAK tool parameters: time range (often a sub-interval of the IK solution), optimization settings, coordinate definitions (prescribed, primary, secondary), and muscle weights for the cost function.
    *   Run the COMAK simulation (`comaktool.run()`). This solves for muscle activations and can make small adjustments to kinematics to achieve dynamic consistency and satisfy the objectives of the COMAK cost function (e.g., minimizing muscle effort, contact energy).

5.  **Inverse Dynamics (using `COMAKInverseDynamics` from `comak_id.py`):**
    *   Inputs: The `final_model_path` from `COMAKInverseKinematics`, the kinematics file from the *COMAK simulation results* (e.g., `_values.sto`, which contains the COMAK-solved motion), and the external loads file.
    *   Run inverse dynamics (`comak_id.run()`) to calculate the net joint reaction forces and moments consistent with the COMAK-solved motion and applied external loads.

6.  **Joint Mechanics Analysis (using `JointMechanics` from `jntmech.py`):**
    *   Inputs: The `final_model_path` from `COMAKInverseKinematics`, and the comprehensive simulation results from the COMAK step (specifically, the states, forces, and activations .sto files).
    *   Configure the `JointMechanicsTool` to output desired quantities: contact forces/pressures on specified meshes, ligament forces, muscle forces, fiber lengths, activations, body transforms, etc.
    *   Run the analysis (`joint_mechanics.run()`). This generates detailed output, commonly including HDF5 files (for rich numerical data) and VTP files (for visualizing geometries, contact patches, etc. in tools like Paraview).

7.  **Detailed Post-Processing and Visualization:**
    *   **HDF5 Data Analysis (using `JamAnalysis` from `jam_analysis.py`):**
        *   Load the HDF5 file(s) generated by the `JointMechanics` step into the `JamAnalysis` object.
        *   Utilize its methods to extract specific data arrays (e.g., regional contact pressures on cartilage surfaces, time histories of ligament forces, specific coordinate trajectories).
        *   Use the library's plotting utilities or export data for custom plotting and statistical analysis in other environments.
    *   **VTP File Visualization:**
        *   The VTP files (e.g., `_contact_femur_cartilage*.vtp`) generated by `JointMechanicsTool` can be loaded into visualization software like Paraview to inspect contact regions, pressure distributions, and animated mesh movements.
        *   The `pycomak.utils.copy_file_names_with_strings` function can be useful for gathering specific VTP files into a dedicated `paraview` subdirectory for easier access.

### Multi-Subject Group Analysis (New)

For analyzing multiple subjects across different groups (e.g., healthy vs OA), use the `GroupJamAnalysis` class:

```python
from pycomak import GroupJamAnalysis
from pycomak.plotting_utils import plot_kinematics_panel, create_publication_figure

# Initialize group analysis
group_analysis = GroupJamAnalysis(
    base_results_dir='/path/to/results',
    comak_subfolder='comak_results'
)

# Add subjects to groups
group_analysis.add_subject('9003175', 'RIGHT', '2025-08-21_21-33-10', group='healthy')
group_analysis.add_subject('9009999', 'LEFT', '2025-08-22_14-00-00', group='OA')

# Extract data across groups
knee_kinematics = group_analysis.get_coordinate_data('knee_flex_r', return_individuals=False)
contact_forces = group_analysis.get_regional_contact_data(region=4, outcome='regional_max_pressure')

# Create publication-ready figures
fig, axes = plot_kinematics_panel(group_analysis, ['knee_flex_r', 'knee_add_r', 'knee_rot_r'])
fig, axes = create_publication_figure(group_analysis, regions=[4, 5], outcome_type='max_pressure')

# Export data for statistical analysis
summary_df = group_analysis.get_summary_dataframe()
summary_df.to_csv('subjects_summary.csv')
```

See `examples/group_jam_analysis_example.ipynb` for a comprehensive demonstration.

### CLI Tools

#### pycomak-cleanup

Remove legacy VTP files from `joint-mechanics/` directories. Previously, `JointMechanics` output ~30,000 VTP files per subject (~1 GB). The new defaults output only ~800 contact surface files (~100 MB). This tool cleans up legacy files from existing results.

**Files deleted:** `_ligament_*.vtp`, `_muscle_*.vtp`, `_mesh_*.vtp`
**Files kept:** `_contact_*.vtp`, `*.h5`, `*.sto`

```bash
# Dry run (default) - shows what would be deleted
pycomak-cleanup --path /path/to/results

# Actually delete files
pycomak-cleanup --path /path/to/results --execute

# With more parallel workers for faster processing
pycomak-cleanup --path /path/to/results --execute --workers 16
```

Programmatic usage:

```python
from pycomak import cleanup_legacy_vtp_files

# Dry run
result = cleanup_legacy_vtp_files('/path/to/results')
print(f"Would delete {result['files_deleted']} files, freeing {result['size_freed']} bytes")

# Execute
result = cleanup_legacy_vtp_files('/path/to/results', execute=True)
```

*(Note: For detailed API usage, specific function arguments, and file naming conventions, please refer to the docstrings within each Python module and example implementation scripts.)*

## License

This project is licensed under the MIT License. (Assuming MIT, please update if different or add a LICENSE file).
