import os

class COMAKBASE:
    def __init__(self, results_dir):
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
        
        
        
    