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
    """
    def __init__(
        self,
        results_dir,
        model_path,
        start_time,
        end_time,
        debug_level=0,
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
        """
        super().__init__(results_dir)
        save_xml_path = os.path.join(self.inputs_dir, 'joint_mechanics_settings.xml')
    

        ## Perform Joint Mechanics Analysis
        self.jnt_mech = osim.JointMechanicsTool()
        self.jnt_mech.set_model_file(model_path)
        self.jnt_mech.set_input_states_file(os.path.join(self.comak_result_dir, '_states.sto'))
        self.jnt_mech.set_input_forces_file(os.path.join(self.comak_result_dir, '_force.sto'))
        self.jnt_mech.set_input_activations_file(os.path.join(self.comak_result_dir,  '_activations.sto'))
        self.jnt_mech.set_use_muscle_physiology(False)
        # self.jnt_mech.set_results_file_basename(settings.results_basename)
        self.jnt_mech.set_results_directory(self.jnt_mech_result_dir)
        self.jnt_mech.set_start_time(start_time)
        self.jnt_mech.set_stop_time(end_time)
        self.jnt_mech.set_resample_step_size(-1)
        self.jnt_mech.set_normalize_to_cycle(True)
        self.jnt_mech.set_lowpass_filter_frequency(-1)
        self.jnt_mech.set_print_processed_kinematics(False)
        self.jnt_mech.set_contacts(0,'all')
        self.jnt_mech.set_contact_outputs(0,'all')
        self.jnt_mech.set_contact_mesh_properties(0,'none')
        self.jnt_mech.set_ligaments(0,'all')
        self.jnt_mech.set_ligament_outputs(0,'all')
        self.jnt_mech.set_muscles(0,'all')
        self.jnt_mech.set_muscle_outputs(0,'all')

        self.jnt_mech.set_attached_geometry_bodies(0,'all')

        self.jnt_mech.set_output_orientation_frame('ground')
        self.jnt_mech.set_output_position_frame('ground')
        self.jnt_mech.set_write_vtp_files(True)
        self.jnt_mech.set_vtp_file_format('binary')
        self.jnt_mech.set_write_h5_file(True)
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