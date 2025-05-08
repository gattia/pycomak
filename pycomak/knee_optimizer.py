import copy
import numpy as np
import os
import xml.etree.ElementTree as ET

# 'LOC_SDF_CACHE' to environment variables
os.environ['LOC_SDF_CACHE'] = ''

from pycomak.forsim import COMAKforsim
from pycomak import COMAKInverseKinematics
from pycomak.utils import run_with_timeout
from nsosim.comak_osim_update import update_patella_location


def get_patella_location(path_model):
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)) # keep comments
    tree = ET.parse(path_model, parser)
    root = tree.getroot()[0]
        
    jointset = root.find('JointSet')[0]
    pf_r = jointset.findall("./CustomJoint[@name='pf_r']")[0]
    pf_r_tx = pf_r.findall("./coordinates/Coordinate[@name='pf_tx_r']/default_value")[0].text 
    pf_r_ty = pf_r.findall("./coordinates/Coordinate[@name='pf_ty_r']/default_value")[0].text 
    pf_r_tz = pf_r.findall("./coordinates/Coordinate[@name='pf_tz_r']/default_value")[0].text 

    pf_r_position = np.array([float(pf_r_tx), float(pf_r_ty), float(pf_r_tz)])
    
    return pf_r_position

def update_patella_location_(path_model, path_save_model, update):
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)) # keep comments
    tree = ET.parse(path_model, parser)
    root = tree.getroot()[0]
    
    # get current patella location
    
    patella_location = get_patella_location(path_model)

    new_patella_location = patella_location + update

    update_patella_location(root, new_patella_location)

    tree.write(path_save_model, encoding='utf8',method='xml')
    
class KneeOptimizer:
    def __init__(self, path_model_to_update, results_dir, markerset_file, dict_kinematics, dict_muscles, dict_criteria, settle_sim_reps=2, patella_position_update=np.asarray([0, -0.001, 0]), max_duration=45, max_updates=10):
        self.path_model_to_update = path_model_to_update
        self.results_dir = results_dir
        self.markerset_file = markerset_file
        self.dict_kinematics = dict_kinematics
        self.dict_muscles = dict_muscles
        self.dict_criteria = dict_criteria
        self.patella_position_update = patella_position_update
        self.max_duration = max_duration
        self.max_updates = max_updates
        self.settle_sim_reps = settle_sim_reps
        self._n_updates = 0
        self._list_eval_results = []
        self.settle_sim_intermed_filename = "patella_optimize_settle_sim_intermediate.osim"

    def optimize_patella_location(self):
        success = False
        while ((not success) and (self._n_updates < self.max_updates)):
            # Update ligament slack lengths
            
            comak_ik = COMAKInverseKinematics(
                base_model_path=self.path_model_to_update,
                results_dir=self.results_dir,
                stop_time_ik=0,
                start_time_ik=0,
                markerset_file=self.markerset_file,
                settle_sim_reps=self.settle_sim_reps,
            )
            
            comak_ik.settle_sim_intermed_filename = self.settle_sim_intermed_filename
            comak_ik.settle_sim_intermed_model_filepath = os.path.join(comak_ik.ik_result_dir, self.settle_sim_intermed_filename)
            comak_ik.setup_generic_comakik_settings()
            
            try:
                # Set timer for settle sim to 5 minutes
                run_with_timeout(comak_ik.perform_settle_sim, 60*5)
            except TimeoutError:
                update_patella_location_(self.path_model_to_update, self.path_model_to_update, self.patella_position_update)
                self._n_updates += 1
                self._list_eval_results.append('settle_sim_timeout')
                continue

            print('=' * 72)
            print('n_updates:', self._n_updates)
            print('=' * 72)

            # Run the forsim simulation to see if it "passes"
            comak_forsim = COMAKforsim(
                path_model=comak_ik.settle_sim_intermed_model_filepath,
                dict_kinematics=self.dict_kinematics,
                dict_muscles=self.dict_muscles,
                folder_save_results=self.results_dir
            )

            forsim_success = comak_forsim.run_forsim(max_forsim_time=self.max_duration)

            if not forsim_success:
                # Update model to move patella down 1mm & continue...
                update_patella_location_(self.path_model_to_update, self.path_model_to_update, self.patella_position_update)
                self._n_updates += 1
                self._list_eval_results.append('forsim_timeout')
                continue

            # Evaluate simulation
            comak_forsim.run_joint_mechanics_tool()
            jam_eval_success = comak_forsim.jam_evaluation(self.dict_criteria)

            self._list_eval_results.append(comak_forsim.evaluation_results)

            if not jam_eval_success:
                # Update model to move patella down 1mm & continue...
                update_patella_location_(self.path_model_to_update, self.path_model_to_update, self.patella_position_update)
                self._n_updates += 1
                continue
            else:
                success = True
        
        # patella_opt_max_updates
        # settle_sim_timeout
        
        if not success:
            if isinstance(self._list_eval_results[-1], str):
                return self._list_eval_results[-1]
            else:
                return 'patella_opt_max_updates'
        return

    @property
    def list_eval_results(self):
        return copy.deepcopy(self._list_eval_results)

    @property
    def n_updates(self):
        return self._n_updates