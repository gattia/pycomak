import os
import opensim as osim

from pycomak import COMAKBASE


class JointMechanics(COMAKBASE):
    """
    A class to set up and run OpenSim's JointMechanicsTool, typically after a COMAK simulation.

    This class configures the JointMechanicsTool to analyze forces, activations, and kinematics
    from a COMAK simulation. It sets input files (states, forces, activations from COMAK results),
    output directory, time range, and various analysis options (contacts, ligaments, muscles,
    geometry output, etc.).

    The settings are saved to an XML file, and a `run` method is provided to execute
    the joint mechanics analysis.

    Output Filtering:
        Two types of output are controlled **independently**:

        1. **H5 file** (~35 MB): Numerical data for analysis (kinematics, forces, pressures).
           Controlled by: ``contact_outputs``, ``ligament_outputs``, ``muscle_outputs``
           Default: 'all' for each (keeps full data for JamAnalysis).

        2. **VTP files**: ParaView visualization meshes (one file per component per timestep).
           Controlled by: ``contacts``, ``ligaments``, ``muscles``, ``attached_geometry_bodies``
           Default: Only contact surfaces ('all' for contacts, 'none' for others).

        With defaults: ~800 VTP files (~65 MB) + H5 (~35 MB) = **~100 MB per subject**

        **To add bone visualization** for specific subjects (e.g., for figures):
            ``JointMechanics(..., attached_geometry_bodies='femur_r tibia_r patella_r')``

        **To output ALL VTPs** (legacy behavior - ~30,000 files, ~1 GB per subject):
            ``JointMechanics(..., ligaments='all', muscles='all', attached_geometry_bodies='all')``

        **H5-only output** (no visualization files, ~35 MB per subject):
            ``JointMechanics(..., write_vtp_files=False)``
    """

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
        ligaments='none',
        ligament_outputs='all',
        muscles='none',
        muscle_outputs='all',
        attached_geometry_bodies='none',
        write_vtp_files=True,
        write_h5_file=True,
    ):
        """
        Initializes the JointMechanics class.

        Args:
            results_dir (str): The base directory where COMAK results are stored and where
                joint mechanics results will be saved (in a 'joint-mechanics' subdirectory).
            model_path (str): Path to the OpenSim model file (.osim).
            start_time (float): Start time for the joint mechanics analysis.
            end_time (float): End time for the joint mechanics analysis.
            debug_level (int, optional): Debug level for JointMechanicsTool. Defaults to 0.
            contacts (str, optional): Which contact geometries to analyze and write VTPs for.
                'all', 'none', or specific contact names. Defaults to 'all'.
                Note: Contact data is always written to the H5 file regardless of VTP settings.
            contact_outputs (str, optional): Which contact outputs to compute.
                'all' or 'none'. Defaults to 'all'.
            contact_mesh_properties (str, optional): Contact mesh property outputs.
                'all' or 'none'. Defaults to 'none'.
            ligaments (str, optional): Which ligaments to write **VTP files** for (ParaView).
                'all' or 'none'. Defaults to 'none' (~9,600 fewer files).
                Note: This only controls VTP visualization files, not H5 data.
            ligament_outputs (str, optional): Which ligament data to write to **H5 file**.
                'all' or 'none'. Defaults to 'all' (keeps force/strain data for analysis).
                Note: Independent of VTP setting above.
            muscles (str, optional): Which muscles to write **VTP files** for (ParaView).
                'all' or 'none'. Defaults to 'none' (~4,500 fewer files).
                Note: This only controls VTP visualization files, not H5 data.
            muscle_outputs (str, optional): Which muscle data to write to **H5 file**.
                'all' or 'none'. Defaults to 'all' (keeps activation/force data for analysis).
                Note: Independent of VTP setting above.
            attached_geometry_bodies (str, optional): Which body geometries to write VTP files for.
                'all', 'none', or space-separated body names (e.g., 'femur_r tibia_r patella_r').
                Defaults to 'none'.
                Set to specific bones for visualization (e.g., 'femur_r tibia_r patella_r')
                or 'all' for complete model visualization (~15,500 extra files).
            write_vtp_files (bool, optional): Whether to write any VTP mesh files.
                Defaults to True. Set to False for H5-only output (~35 MB per subject).
            write_h5_file (bool, optional): Whether to write consolidated H5 file.
                Defaults to True. The H5 file contains all numerical data needed for analysis.
        """
        super().__init__(results_dir)
        save_xml_path = os.path.join(self.inputs_dir, 'joint_mechanics_settings.xml')

        # Perform Joint Mechanics Analysis
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

        # Configurable output filtering (use parameters instead of hardcoded values)
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

    def run(self):
        """
        Runs the JointMechanicsTool analysis.

        Prints messages indicating the start and completion of the JointMechanicsTool execution.
        """
        print('Running JointMechanicsTool...')
        self.jnt_mech.run()
        print('Finished JointMechanicsTool!')