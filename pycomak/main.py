import os

class COMAKBASE:
    """
    A base class for COMAK-related processing tools (IK, ID, COMAK, JointMechanics).

    This class primarily initializes a standardized directory structure for storing
    inputs, logs, and results for various stages of a COMAK workflow. It also defines
    some standard filenames used by the COMAK tools.

    Attributes:
        results_dir (str): The main directory for all results.
        log_dir (str): Subdirectory for log files.
        ik_result_dir (str): Subdirectory for COMAK Inverse Kinematics results.
        inputs_dir (str): Subdirectory for input settings files.
        id_result_dir (str): Subdirectory for COMAK Inverse Dynamics results.
        comak_result_dir (str): Subdirectory for main COMAK tool results.
        jnt_mech_result_dir (str): Subdirectory for Joint Mechanics tool results.
        jnt_mech_paraview_dir (str): Subdirectory within joint mechanics for Paraview files.
        graphics_dir (str): Subdirectory for generated graphics/plots.
        settle_sim_intermed_filename (str): Standard filename for intermediate model in IK settle sim.
        settle_sim_constrained_model_filename (str): Standard filename for constrained model in IK settle sim.
        settle_sim_secondary_constraint_function_filename (str): Standard filename for constraint functions in IK settle sim.
        sweep_sim_constrained_model_filename (str): Standard filename for constrained model in IK sweep sim.
        sweep_sim_secondary_constraint_function_filename (str): Standard filename for constraint functions in IK sweep sim.
        settle_and_sweep_sim_filename (str): Standard filename for the final model after IK settle and sweep.
        comak_id_results_filename (str): Standard filename for Inverse Dynamics results.
        comak_ik_filename (str): Standard filename for COMAK IK motion output.
    """
    def __init__(self, results_dir):
        """
        Initializes the COMAKBASE class, creating result directories if they don't exist.

        Args:
            results_dir (str): The root directory where all COMAK-related subdirectories
                for results, inputs, and logs will be created.
        """
        # define folders to save results
        self.results_dir = results_dir
        self.log_dir = os.path.join(self.results_dir, 'logs')
        self.ik_result_dir = os.path.join(self.results_dir, 'comak-inverse-kinematics')
        self.inputs_dir = os.path.join(self.results_dir, 'inputs')
        self.id_result_dir = os.path.join(self.results_dir, 'comak-inverse-dynamics')
        self.comak_result_dir = os.path.join(self.results_dir, 'comak')
        self.jnt_mech_result_dir = os.path.join(self.results_dir, 'joint-mechanics')
        self.jnt_mech_paraview_dir = os.path.join(self.jnt_mech_result_dir, 'paraview')
        self.graphics_dir = os.path.join(self.results_dir, 'graphics')
        
        for dir_path in [self.log_dir, self.ik_result_dir, self.inputs_dir, 
                         self.id_result_dir, self.comak_result_dir, 
                         self.jnt_mech_result_dir, self.jnt_mech_paraview_dir,
                         self.graphics_dir]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
        
        
        # Define standard filenames for COMAK IK
        self.settle_sim_intermed_filename = "model_update_slack_intermediate.osim"
        self.settle_sim_constrained_model_filename = 'ik_constrained_model_settle.osim'
        self.settle_sim_secondary_constraint_function_filename = 'secondary_coordinate_constraint_functions_settle.xml'
        
        self.sweep_sim_constrained_model_filename = 'ik_constrained_model_final.osim'
        self.sweep_sim_secondary_constraint_function_filename = 'secondary_coordinate_constraint_functions_final.xml'
        
        self.settle_and_sweep_sim_filename = "model_updated_slack_final.osim"
        
        # Define standard filenames for COMAK ID
        self.comak_id_results_filename = 'inverse-dynamics.sto'
        
        # Setting COMAK stuff
        self.comak_ik_filename = 'comak_ik.mot'
        
        
        
    