import datetime
import os



class COMAK:
    def __init__(
        self,
        base_results_dir,
        basename,
        model_dir,
        mocap_dir,
        subjID,
        model_file,
        markerset_file,
        external_loads_file,
        start_time_ik,
        stop_time_ik,
        start_time_comak,
        stop_time_comak,
        scaling="AB",
        settleSimRep=1,
        settleSimUpd=True,
        modelWrap=True
    ):
        current_date = datetime.datetime.now()
        #format Month-day-year, spell month - include time if needed
        current_date = current_date.strftime("%B-%d-%Y_%H-%M-%S")
        
        ## Subject Information ##
        self.results_basename = basename
        self.subjID = subjID

        ## File Organization ##
        self.model_dir = model_dir
        self.mocap_dir = mocap_dir
        self.subj_dir =  os.path.join(base_results_dir, subjID)      # Subject Directory to House Results
        self.result_dir = os.path.join(self.subj_dir,  f'results_{current_date}')
        self.path_log = os.path.join(self.result_dir, 'logs')
        self.inputs_dir = os.path.join(self.result_dir, 'inputs')
        
        self.ik_result_dir = os.path.join(self.result_dir, 'comak-inverse-kinematics')
        self.comak_result_dir = os.path.join(self.result_dir, 'comak')
        self.id_result_dir = os.path.join(self.result_dir, 'comak-inverse-dynamics')
        self.jnt_mech_result_dir = os.path.join(self.result_dir, 'joint-mechanics')

        # Settings
        self.scaling = scaling # "AB" = Exactly same as AddBiomechanics, "LA" = Femur/Tibia separately using long-axis, "WA" = Femur/Tibia same 0 using weighted average of femur/tibia long-axis scaling
        self.settleSimRep = settleSimRep # Number of times SettleSim is repeated
        self.settleSimUpd = settleSimUpd # Are the coordinates updated each time
        self.modelWrap = modelWrap

        self.model_file = model_file
        self.markerset_file = markerset_file
        self.external_loads_file = external_loads_file
        
        self.primary_coord_file = os.path.join(mocap_dir, 'primary_coordinates.json')
        self.secondary_coords_file = os.path.join(mocap_dir, 'secondary_coordinates.json')
        self.prescribed_coord_file = os.path.join(mocap_dir, 'prescribed_coordinates.json')
        self.upd_model_file = os.path.join(model_dir, f'scaled_lenhart_model_updWrap_updSlack_{subjID}.osim')
        print(self.upd_model_file)
        
        self.primary_coord_file = os.path.join(mocap_dir, 'primary_coordinates.json')
        self.secondary_coord_file = os.path.join(mocap_dir, 'secondary_coordinates.json')
        self.prescribed_coord_file = os.path.join(mocap_dir, 'prescribed_coordinates.json')
        
        # iterate over all of the directories related to "results" and make sure they 
        # exist, if not, create them. 
        results_dirs = [self.subj_dir, self.result_dir, self.path_log, self.inputs_dir,
                        self.ik_result_dir, self.comak_result_dir, self.id_result_dir, 
                        self.jnt_mech_result_dir]
        for dir in results_dirs:
            os.makedirs(dir, exist_ok=True)        

        self.start_time_ik = start_time_ik
        self.stop_time_ik = stop_time_ik
        self.start_time_comak = start_time_comak
        self.stop_time_comak = stop_time_comak