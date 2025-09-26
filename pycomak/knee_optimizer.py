import copy
import numpy as np
import os
import xml.etree.ElementTree as ET
import opensim as osim
import json
# 'LOC_SDF_CACHE' to environment variables
os.environ['LOC_SDF_CACHE'] = ''

from pycomak.forsim import COMAKforsim
from pycomak import COMAKInverseKinematics
from pycomak.utils import run_with_timeout
# from nsosim.comak_osim_update import update_patella_location
from nsosim.osim_utils import update_joint_default_values, get_osim_muscle_ligament_reference_lengths



def update_patella_location_(path_model, path_save_model, update):
    """
    Updates the default patellofemoral (pf_r) joint translation values in an OpenSim model file.

    Reads an existing .osim model, gets the current default patella location using
    `get_patella_location`, adds the `update` vector to these coordinates, and then
    uses `nsosim.comak_osim_update.update_patella_location` to modify the XML tree.
    The modified model is then saved to `path_save_model`.

    Args:
        path_model (str): Path to the source OpenSim model file (.osim).
        path_save_model (str): Path to save the modified OpenSim model file (.osim).
            Can be the same as `path_model` to overwrite.
        update (numpy.ndarray): A 1D array containing the [dx, dy, dz] changes to be
            applied to the patella's default translational coordinates.
    """

    #load the model 
    model = osim.Model(path_model)
    
    # create patella update dict
    dict_joint_default_values_update = {
        "pf_r": {
            3: update[0],
            4: update[1],
            5: update[2]
        }
    }
    # update the model
    
    update_joint_default_values(model, dict_joint_default_values_update, incremental=True)
    # save the model
    model.printToXML(path_save_model)
    
class KneeOptimizer:
    """
    Optimizes patella location by iteratively adjusting its default position and evaluating
    knee joint mechanics using COMAK IK and Forsim simulations.

    The optimization process involves:
    1. Performing a COMAK IK settle simulation to update ligament slack lengths with the current patella position.
    2. Running a COMAK Forsim simulation with predefined kinematics and muscle activations.
    3. Evaluating the Forsim results (e.g., ligament forces, joint translations) against specified criteria.
    4. If criteria are not met or simulations time out, the patella's default 'ty' (superior-inferior) 
       position is updated (typically moved inferiorly), and the process repeats.

    The optimization stops if criteria are met, a maximum number of updates is reached,
    or simulations consistently time out.

    Attributes:
        path_model_to_update (str): Path to the OpenSim model file to be optimized.
        results_dir (str): Directory to save intermediate results.
        markerset_file (str): Path to the markerset file for COMAK IK.
        dict_kinematics (dict): Prescribed kinematics for Forsim.
        dict_muscles (dict): Prescribed muscle activations for Forsim.
        dict_criteria (dict): Criteria for evaluating Forsim results.
        patella_position_update (numpy.ndarray): Update vector applied to patella position at each step.
        max_duration (int): Max duration for Forsim simulation (seconds).
        max_updates (int): Max number of patella position updates.
        settle_sim_reps (int): Number of repetitions for COMAK IK settle sim.
        _n_updates (int): Current number of patella position updates made.
        _list_eval_results (list): Stores evaluation results from each iteration.
    """
    def __init__(
            self, 
            path_model_to_update, 
            results_dir, 
            markerset_file, 
            dict_kinematics, 
            dict_muscles, 
            dict_criteria, 
            settle_sim_reps=2, 
            patella_position_update=np.asarray([0, -0.001, 0]), 
            max_duration=45, 
            max_updates=10,
            dict_reference_strain_update=None,
        ):
        """
        Initializes the KneeOptimizer.

        Args:
            path_model_to_update (str): Path to the .osim model file that will be iteratively updated.
            results_dir (str): Directory to store results from IK, Forsim, and evaluations.
            markerset_file (str): Path to the markerset file (.xml or .trc) for COMAK IK.
            dict_kinematics (dict): Dictionary of prescribed kinematics for the Forsim simulation
                (see `COMAKforsim` for format).
            dict_muscles (dict): Dictionary of prescribed muscle activations for the Forsim simulation
                (see `COMAKforsim` for format).
            dict_criteria (dict): Dictionary of criteria to evaluate the Forsim simulation results
                (see `forsim.jam_evaluation` for format).
            settle_sim_reps (int, optional): Number of repetitions for the COMAK IK settle simulation.
                Defaults to 2.
            patella_position_update (numpy.ndarray, optional): The [dx, dy, dz] vector to update the
                patella's default position by at each iteration. Defaults to [0, -0.001, 0] (1mm inferiorly).
            max_duration (int, optional): Maximum duration in seconds for each Forsim simulation run.
                Defaults to 45.
            max_updates (int, optional): Maximum number of times the patella position will be updated.
                Defaults to 10.
            dict_reference_strain_update (dict, optional): Dictionary of reference strain updates for the COMAK IK settle simulation.
                Defaults to None.
        """
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
        self.dict_reference_strain_update = dict_reference_strain_update

    def optimize_patella_location(self):
        """
        Runs the iterative patella location optimization process.

        The loop continues until success criteria are met, max_updates is reached, or
        a persistent timeout occurs. 

        The process involves:
        1. COMAK IK settle simulation (with timeout).
        2. COMAK Forsim simulation (with timeout).
        3. Joint mechanics analysis and evaluation against criteria.
        4. If not successful, updates patella location and repeats.

        Returns:
            str or None: 
                - None if optimization was successful.
                - 'settle_sim_timeout' if the COMAK IK settle simulation timed out persistently.
                - 'forsim_timeout' if the COMAK Forsim simulation timed out persistently.
                - 'patella_opt_max_updates' if maximum updates were reached without success.
        """
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
            
            if self.dict_reference_strain_update is not None:
                comak_ik.update_multiple_ligament_reference_strains(self.dict_reference_strain_update)
            
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
        
        # in results_dir, save the total update achieved, by summing all the updates.
        total_update = np.asarray(self.patella_position_update) * self._n_updates
        with open(os.path.join(self.results_dir, 'total_patella_update.json'), 'w') as f:
            json.dump(total_update.tolist(), f)
        
        if not success:
            if isinstance(self._list_eval_results[-1], str):
                return self._list_eval_results[-1]
            else:
                return 'patella_opt_max_updates'
        return

    @property
    def list_eval_results(self):
        """
        Provides a deep copy of the list of evaluation results from each optimization iteration.

        Each element in the list can be a dictionary of evaluation metrics (if evaluation completed)
        or a string indicating a timeout ('settle_sim_timeout', 'forsim_timeout').

        Returns:
            list: A deep copy of the list containing evaluation results or timeout strings.
        """
        return copy.deepcopy(self._list_eval_results)

    @property
    def n_updates(self):
        """
        Returns the number of patella position updates performed during the optimization.

        Returns:
            int: The total count of updates made to the patella's default position.
        """
        return self._n_updates