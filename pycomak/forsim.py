import numpy as np
import opensim as osim
import os
import copy
import matplotlib.pyplot as plt
from pycomak.utils import run_with_timeout
from pycomak.jam_analysis import JamAnalysis


UNCONSTRAINED_COORDINATES = [
    '/jointset/knee_r/knee_add_r',
    '/jointset/knee_r/knee_rot_r',
    '/jointset/knee_r/knee_tx_r',
    '/jointset/knee_r/knee_ty_r',
    '/jointset/knee_r/knee_tz_r',
    '/jointset/pf_r/pf_flex_r',
    '/jointset/pf_r/pf_rot_r',
    '/jointset/pf_r/pf_tilt_r',
    '/jointset/pf_r/pf_tx_r',
    '/jointset/pf_r/pf_ty_r',
    '/jointset/pf_r/pf_tz_r',
    '/jointset/meniscus_medial_r/meniscus_medial_flex_r',
    '/jointset/meniscus_medial_r/meniscus_medial_rot_r',
    '/jointset/meniscus_medial_r/meniscus_medial_add_r',
    '/jointset/meniscus_medial_r/meniscus_medial_tx_r',
    '/jointset/meniscus_medial_r/meniscus_medial_ty_r',
    '/jointset/meniscus_medial_r/meniscus_medial_tz_r',
    '/jointset/meniscus_lateral_r/meniscus_lateral_flex_r',
    '/jointset/meniscus_lateral_r/meniscus_lateral_rot_r',
    '/jointset/meniscus_lateral_r/meniscus_lateral_add_r',
    '/jointset/meniscus_lateral_r/meniscus_lateral_tx_r',
    '/jointset/meniscus_lateral_r/meniscus_lateral_ty_r',
    '/jointset/meniscus_lateral_r/meniscus_lateral_tz_r',
]

ATTACHED_GEOMETRY_BODIES = [
    '/bodyset/femur_distal_r',
    '/bodyset/tibia_proximal_r',
    '/bodyset/patella_r',
    '/bodyset/meniscus_medial_r',
    '/bodyset/meniscus_lateral_r',
]

SECONDARY_COORDINATES = [
    'knee_flex_r', 'knee_add_r', 'knee_rot_r',
    'knee_tx_r', 'knee_ty_r', 'knee_tz_r',
    'pf_flex_r', 'pf_rot_r', 'pf_tilt_r',
    'pf_tx_r','pf_ty_r','pf_tz_r',
    'meniscus_medial_flex_r', 'meniscus_medial_rot_r', 'meniscus_medial_add_r',
    'meniscus_medial_tx_r', 'meniscus_medial_ty_r', 'meniscus_medial_tz_r',
    'meniscus_lateral_flex_r', 'meniscus_lateral_rot_r', 'meniscus_lateral_add_r',
    'meniscus_lateral_tx_r', 'meniscus_lateral_ty_r', 'meniscus_lateral_tz_r',
]

LIGAMENTS = [
    # 'MCLd','MCLs',
    'MCL',
    'LCL',
    # 'ACLam', 'ACLpl',
    'ACL',
    # 'PCLal', 'PCLpm',
    'PCL',
    'PT',
    'ITB',
    'mPFL',
    'lPFL'
]

# SECONDARY_COORD_CRITERIA = {
#     'max_range': {
#         'coords': {
#             'pf_tx_r': 0.005, # 5mm maximum range in x-axis (AP direction)
#         # 'pf_ty_r': 
#         },
#         'ligaments': {
#             'PT': 1100, # 1100N maximum force in PT ligament
#             'ACL': 300, # 300N maximum force in ACL ligament
#         }
#     },
#     'max': {
#         'ligaments': {
#             'PT': 1100, # 1100N maximum force in PT ligament
#             'ACL': 300, # 300N maximum force in ACL ligament
#         }
#     }
# }

SECONDARY_COORD_CRITERIA = {
    'ligaments': {
        'PT': {'max_range': 1100, 'max': 1100},
        'ACL': {'max_range': 300, 'max': 300},
        'MCL': {},
        'LCL': {},
        'PCL': {},
        'mPFL': {},
        'lPFL': {},
        
    },
    'coords': {
        'pf_tx_r': {'max_range': 0.005, 'max': 0.005},
        'pf_ty_r': {},
        'pf_tz_r': {},
        'pf_flex_r': {},
        'pf_rot_r': {},
        'pf_tilt_r': {},
    }
}
    
def create_save_sto(
    dict_data,
    path_save,
    convert_to_radians=False,
):
    """
    Creates an OpenSim TimeSeriesTable from a dictionary of data and saves it as a .sto file.

    Args:
        dict_data (dict): A dictionary where keys are column labels (str) and values are
            1D numpy arrays of data. Must include a 'time' key with the time vector.
        path_save (str): The full path (including filename) to save the .sto file.
            Must end with '.sto'.
        convert_to_radians (bool, optional): Whether to convert angular coordinates from degrees to radians.
            Defaults to False.

    Raises:
        AssertionError: If 'time' key is missing in `dict_data` or if `path_save`
            does not end with '.sto'.
        AssertionError: If input types for TimeSeriesTable are incorrect.
    """
    assert 'time' in dict_data.keys(), 'Time data is missing'
    assert path_save.endswith('.sto'), 'File extension must be .sto'
    
    # create data array to hold dataset
    data = np.zeros((len(dict_data['time']), len(dict_data.keys())-1))
    labels = osim.StdVectorString()
    
    idx = 0
    for key, array in dict_data.items():
        if key == 'time':
            continue
        else:
            # if convert_to_radians:
            #     data[:, idx] = np.deg2rad(array)
            # else:
            
            data[:, idx] = array
                
            labels.append(key)
            idx += 1
    
    data_matrix = osim.Matrix.createFromMat(data)
    
    # make sure inputs to TimeSeriesTable are the correct types
    assert isinstance(dict_data['time'], np.ndarray), 'Time data must be a numpy array'
    assert isinstance(data_matrix, osim.Matrix), 'Data matrix must be an osim.Matrix'
    assert isinstance(labels, osim.StdVectorString), 'Labels must be an osim.StdVectorString'
    
    table = osim.TimeSeriesTable(dict_data['time'], data_matrix, labels)
    
    sto = osim.STOFileAdapter()
    sto.write(table, path_save)

def run_forsim(
    path_model,
    folder_save_results,
    integrator_accuracy=1e-2,
    constant_muscle_control=0.02,
    override_default_muscle_activation=0.02,
    use_activation_dynamics=False,
    use_tendon_compliance=False,
    use_muscle_physiology=True,
    unconstrained_coordinates=UNCONSTRAINED_COORDINATES,
):
    """
    Runs a forward simulation using OpenSim's ForsimTool.

    Configures and executes ForsimTool with specified model, kinematics, muscle controls,
    and simulation settings. Saves ForsimTool settings to an XML file.

    Args:
        path_model (str): Path to the OpenSim model file (.osim).
        folder_save_results (str): Directory to save the simulation results and settings file.
        integrator_accuracy (float, optional): Accuracy for the integrator. Defaults to 1e-2.
            (Note: Recommended 1e-6 for research).
        constant_muscle_control (float, optional): Constant control value for all muscles
            if not overridden by actuator input file or default activation. Defaults to 0.02.
        override_default_muscle_activation (float, optional): Value to override default muscle activation.
            Defaults to 0.02.
        use_activation_dynamics (bool, optional): Whether to use activation dynamics for muscles.
            Defaults to False.
        use_tendon_compliance (bool, optional): Whether to use tendon compliance for muscles.
            Defaults to False.
        use_muscle_physiology (bool, optional): Whether to use full muscle physiology (activation dynamics,
            pennation, force-length-velocity). Defaults to True.
        unconstrained_coordinates (list, optional): List of unconstrained coordinate paths for the simulation.
            Defaults to UNCONSTRAINED_COORDINATES from module constants.
    """
    ## Perform Simulation with ForsimTool
    forsim = osim.ForsimTool()
    forsim.set_model_file(path_model)
    forsim.set_results_directory(folder_save_results)
    # forsim.set_results_file_basename(results_basename)
    forsim.set_start_time(-1)
    forsim.set_stop_time(-1)
    forsim.set_integrator_accuracy(integrator_accuracy) # Note this should be 1e-6 for research
    forsim.set_constant_muscle_control(constant_muscle_control) # Set all muscles to 2% activation to represent passive state
    forsim.set_override_default_muscle_activation(override_default_muscle_activation)
    forsim.set_use_activation_dynamics(use_activation_dynamics)
    forsim.set_use_tendon_compliance(use_tendon_compliance)
    forsim.set_use_muscle_physiology(use_muscle_physiology)
    
    for idx, coord in enumerate(unconstrained_coordinates):
        forsim.set_unconstrained_coordinates(idx, coord)
    
    forsim.set_prescribed_coordinates_file(os.path.join(folder_save_results, 'kinematics.sto'))
    forsim.set_actuator_input_file(os.path.join(folder_save_results, 'muscles.sto'))
    forsim.printToXML(os.path.join(folder_save_results, 'forsim_settings.xml'))
    
    print('Running Forsim Tool...')
    forsim.run()

def run_joint_mechanics_tool(
    path_model,
    folder_save_results,
    use_activation_dynamics=False,
    use_tendon_compliance=False,
    use_muscle_physiology=True,
    attached_geometry_bodies=ATTACHED_GEOMETRY_BODIES,
    write_vtp_files=False,
):
    """
    Runs OpenSim's JointMechanicsTool to analyze simulation results.

    Configures and executes JointMechanicsTool to compute various biomechanical outputs
    (contact forces, ligament forces, muscle outputs, etc.) from a forward simulation.
    Saves JointMechanicsTool settings to an XML file and results to a subdirectory.

    Args:
        path_model (str): Path to the OpenSim model file (.osim).
        folder_save_results (str): Directory containing the input states file ('_states.sto')
            and where the joint mechanics results will be saved in a 'joint_mechanics' subdirectory.
        use_activation_dynamics (bool, optional): Corresponds to ForsimTool setting. Defaults to False.
        use_tendon_compliance (bool, optional): Corresponds to ForsimTool setting. Defaults to False.
        use_muscle_physiology (bool, optional): Corresponds to ForsimTool setting. Defaults to True.
        attached_geometry_bodies (list, optional): List of body names with attached geometry for analysis.
            Defaults to ATTACHED_GEOMETRY_BODIES from module constants.
        write_vtp_files (bool, optional): Whether to write VTP files for visualization. Defaults to False.
    """
    jnt_mech = osim.JointMechanicsTool()
    jnt_mech.set_model_file(path_model)
    jnt_mech.set_input_states_file(os.path.join(folder_save_results, '_states.sto'))
    jnt_mech.set_results_file_basename('joint_mechanics')
    results_dir = os.path.join(folder_save_results, 'joint_mechanics')
    if not os.path.exists(results_dir):
        os.makedirs(results_dir, exist_ok=True)
    jnt_mech.set_results_directory(results_dir)
    jnt_mech.set_use_activation_dynamics(use_activation_dynamics)
    jnt_mech.set_use_tendon_compliance(use_tendon_compliance)
    jnt_mech.set_use_muscle_physiology(use_muscle_physiology)
    jnt_mech.set_start_time(-1)
    jnt_mech.set_stop_time(-1)
    jnt_mech.set_normalize_to_cycle(False)
    jnt_mech.set_contacts(0,'all')
    jnt_mech.set_ligaments(0,'all')
    jnt_mech.set_muscles(0,'all')
    jnt_mech.set_muscle_outputs(0,'all')
    for idx, body in enumerate(attached_geometry_bodies):
        jnt_mech.set_attached_geometry_bodies(idx, body)
    jnt_mech.set_output_orientation_frame('ground')
    jnt_mech.set_output_position_frame('ground')
    jnt_mech.set_write_vtp_files(write_vtp_files)
    jnt_mech.set_write_h5_file(True)
    jnt_mech.set_h5_kinematics_data(True)
    jnt_mech.set_h5_states_data(True)
    jnt_mech.printToXML(os.path.join(folder_save_results, "joint_mechanics_settings.xml"))
    
    print('Running Joint Mechanics Tool...')
    jnt_mech.run()

def get_total_ligament_force(jam, ligament_name):
    """
    Calculates the total force for a given ligament from JamAnalysis data.

    Sums the 'total_force' from all fibers belonging to the specified ligament.

    Args:
        jam (JamAnalysis): An instance of the JamAnalysis class containing loaded
            joint mechanics data.
        ligament_name (str): The base name of the ligament (e.g., 'ACL', 'MCL').

    Returns:
        numpy.ndarray: A 1D array of the total force for the ligament over time.

    Raises:
        ValueError: If the ligament is not found in the forceset.
    """
    fibers = [x for x in jam.forceset['Blankevoort1991Ligament'].keys() if x.startswith(ligament_name)]
    if len(fibers) == 0:
        raise ValueError('Ligament not found in forceset')
    data = np.zeros(jam.forceset['Blankevoort1991Ligament'][fibers[0]]['total_force'].shape[0])
    for fiber in fibers:
        data += np.squeeze(jam.forceset['Blankevoort1991Ligament'][fiber]['total_force'])
    return data

def analyze_criteria(jam, criteria_dict, criteria_type, passed=True):
    """
    Analyzes data from JamAnalysis against specified criteria.

    For a given `criteria_type` ('ligaments' or 'coords'), this function retrieves
    the relevant data from the `jam` object. It then checks if the data's peak-to-peak
    range, maximum value, or minimum value exceed thresholds defined in `criteria_dict`.
    Results (ptp, min, max) are added to the `criteria_dict`.

    Args:
        jam (JamAnalysis): An instance of JamAnalysis containing the simulation data.
        criteria_dict (dict): A dictionary defining the criteria to check. Expected structure:
            `{'ligaments': {'LIG_NAME': {'max_range': val, 'max': val, 'min': val}}, ...}`
            `{'coords': {'COORD_NAME': {'max_range': val, 'max': val, 'min': val}}, ...}`
        criteria_type (str): The type of data to analyze, either 'ligaments' or 'coords'.
        passed (bool, optional): The current pass/fail status. If any criterion is not met,
            this will be set to False. Defaults to True.

    Returns:
        tuple: 
            - dict: The updated `criteria_dict` with 'ptp_', 'min_', and 'max_' values added for each item.
            - bool: The updated `passed` status.
    """
    for name, criteria in criteria_dict[criteria_type].items():
        if criteria_type == 'ligaments':
            data = get_total_ligament_force(jam, ligament_name=name)
        elif criteria_type == 'coords':
            data = jam.coordinateset[name]['value']
            # data = get_coordinate_data(jam, coord_name=name)  # Assuming a function to get coordinate data
        
        ptp_ = np.ptp(data)
        min_ = np.min(data)
        max_ = np.max(data)
        if 'max_range' in criteria.keys():
            if ptp_ > criteria['max_range']:
                print(f'{name} - Range: {ptp_:.3f} exceeded max range of {criteria["max_range"]}')
                passed = False
        if 'max' in criteria.keys():
            if max_ > criteria['max']:
                print(f'{name} - Max: {max_:.3f} exceeded max value of {criteria["max"]}')
                passed = False
        if 'min' in criteria.keys():
            if min_ < criteria['min']:
                print(f'{name} - Min: {min_:.3f} exceeded min value of {criteria["min"]}')
                passed = False

        result_dict = {
            'ptp_': ptp_,
            'min_': min_,
            'max_': max_
        }
        criteria_dict[criteria_type][name].update(result_dict)
        
    return criteria_dict, passed

def jam_evaluation(
    path_h5_file,
    folder_save_figs,
    dict_criteria,
    list_kinematics_plot=SECONDARY_COORDINATES,
    list_ligaments_plot=LIGAMENTS,
    fontsize=20
):
    """
    Performs joint mechanics analysis evaluation using JamAnalysis.

    Loads data from an H5 file, generates plots for secondary kinematics and
    ligament forces, and evaluates the data against specified criteria using
    the `analyze_criteria` function.

    Args:
        path_h5_file (str): Path to the H5 file containing joint mechanics results.
        folder_save_figs (str): Directory to save the generated plots.
        dict_criteria (dict): Dictionary defining the criteria for evaluation (passed to `analyze_criteria`).
        list_kinematics_plot (list, optional): List of coordinate names to plot.
            Defaults to SECONDARY_COORDINATES from module constants.
        list_ligaments_plot (list, optional): List of ligament base names to plot.
            Defaults to LIGAMENTS from module constants.
        fontsize (int, optional): Fontsize for plot titles and labels. Defaults to 20.

    Returns:
        tuple:
            - bool: True if all criteria are passed, False otherwise.
            - dict: The `dict_criteria` updated with analysis results (ptp, min, max values).
    """
        
    jam = JamAnalysis()
    jam.jam_analysis([path_h5_file,])
    
    # create kinematics plot & save
    cols = 3
    rows = int(np.ceil(len(list_kinematics_plot)/cols))
    fig, ax = plt.subplots(rows, cols, figsize=(cols*16, rows*12))
    for idx, kinematic_ in enumerate(list_kinematics_plot):
        row_ = idx // cols
        col_ = idx % cols
        data_ = jam.coordinateset[kinematic_]['value']
        ptp_ = np.ptp(data_)
        min_ = np.min(data_)
        max_ = np.max(data_)
        ax[row_, col_].plot(data_, linewidth=5)
        ax[row_, col_].set_title(kinematic_, fontsize=fontsize*3)
        ax[row_, col_].xaxis.set_tick_params(labelsize=fontsize*2)
        ax[row_, col_].yaxis.set_tick_params(labelsize=fontsize*2)
        # print the range, min, and max values
        ax[row_, col_].text(0.5, 0.9, f'Range: {ptp_:.3f}', fontsize=fontsize*2, transform=ax[row_, col_].transAxes)
        ax[row_, col_].text(0.5, 0.8, f'Min: {min_:.3f}', fontsize=fontsize*2, transform=ax[row_, col_].transAxes)
        ax[row_, col_].text(0.5, 0.7, f'Max: {max_:.3f}', fontsize=fontsize*2, transform=ax[row_, col_].transAxes)
    fig.suptitle('Secondary Kinematics', fontsize=fontsize*4)
    fig.tight_layout(rect=[0, 0.03, 1, 0.95])
    fig.savefig(os.path.join(folder_save_figs, 'secondary_kinematics.png'))
    plt.close()
    
    # create ligaments plot & save
    cols = 3
    rows = int(np.ceil(len(list_ligaments_plot)/cols))
    fig, ax = plt.subplots(rows, cols, figsize=(cols*16, rows*12))
    for idx, ligament_ in enumerate(list_ligaments_plot):
        row_ = idx // cols
        col_ = idx % cols
        
        # get data to plot
        data = get_total_ligament_force(jam, ligament_name=ligament_)
        
        ax[row_, col_].plot(data, linewidth=5)
        ax[row_, col_].set_title(ligament_, fontsize=fontsize*3)
        ax[row_, col_].xaxis.set_tick_params(labelsize=fontsize*2)
        ax[row_, col_].yaxis.set_tick_params(labelsize=fontsize*2)
        
        ptp_ = np.ptp(data)
        min_ = np.min(data)
        max_ = np.max(data)
        # print the range, min, and max values
        ax[row_, col_].text(0.5, 0.9, f'Range: {ptp_:.3f}', fontsize=fontsize*2, transform=ax[row_, col_].transAxes)
        ax[row_, col_].text(0.5, 0.8, f'Min: {min_:.3f}', fontsize=fontsize*2, transform=ax[row_, col_].transAxes)
        ax[row_, col_].text(0.5, 0.7, f'Max: {max_:.3f}', fontsize=fontsize*2, transform=ax[row_, col_].transAxes)
        
    fig.suptitle('Ligament Forces', fontsize=fontsize*4)
    fig.tight_layout(rect=[0, 0.03, 1, 0.95])
    fig.savefig(os.path.join(folder_save_figs, 'ligament_forces.png'))
    plt.close()
    
    # compute all the metrics of interest.
    
    # iterate over ligaments, for each ligament get the data
    # and store the max, min, and range of the data
    dict_criteria, passed = analyze_criteria(jam, dict_criteria, criteria_type='ligaments')
    dict_criteria, passed = analyze_criteria(jam, dict_criteria, criteria_type='coords', passed=passed)    

    return passed, dict_criteria

class COMAKforsim:
    """
    A class to manage and run COMAK-specific forward simulations (Forsim) and subsequent
    joint mechanics analysis.

    This class handles:
    - Setting up input files (kinematics.sto, muscles.sto) for ForsimTool.
    - Running ForsimTool, with an optional timeout.
    - Running JointMechanicsTool on the ForsimTool results.
    - Evaluating the joint mechanics results against specified criteria.
    """
    def __init__(
        self,
        path_model,
        dict_kinematics,
        dict_muscles,
        folder_save_results,
        integrator_accuracy=1e-2,
        use_activation_dynamics=False, # control = activation 
        use_tendon_compliance=False, # assume rigid tendons
        use_muscle_physiology=True, # activation dynamics, pennation angle, force-length-velocity. 
        constant_muscle_control=0.02,
        override_default_muscle_activation=0.02,
        unconstrained_coordinates=UNCONSTRAINED_COORDINATES,
        max_forsim_time=2*60, # 2 minutes
    ):
        """
        Initializes the COMAKforsim class.

        Args:
            path_model (str): Path to the OpenSim model file (.osim).
            dict_kinematics (dict): Dictionary of kinematics data to be saved as 'kinematics.sto'.
                Must include a 'time' key.
            dict_muscles (dict): Dictionary of muscle control/activation data to be saved as 'muscles.sto'.
                Must include a 'time' key.
            folder_save_results (str): Directory to save all results and intermediate files.
            integrator_accuracy (float, optional): Integrator accuracy for ForsimTool. Defaults to 1e-2.
            use_activation_dynamics (bool, optional): Whether ForsimTool uses activation dynamics.
                Defaults to False.
            use_tendon_compliance (bool, optional): Whether ForsimTool uses tendon compliance.
                Defaults to False.
            use_muscle_physiology (bool, optional): Whether ForsimTool uses full muscle physiology.
                Defaults to True.
            constant_muscle_control (float, optional): Constant muscle control for ForsimTool.
                Defaults to 0.02.
            override_default_muscle_activation (float, optional): Override default muscle activation
                for ForsimTool. Defaults to 0.02.
            unconstrained_coordinates (list, optional): List of unconstrained coordinates for ForsimTool.
                Defaults to UNCONSTRAINED_COORDINATES from module constants.
            max_forsim_time (int, optional): Maximum allowed time in seconds for the forsim run.
                Defaults to 120 (2 minutes).

        Raises:
            ValueError: If `path_model` does not exist.
        """
        if not os.path.exists(path_model):
            raise ValueError('Model file does not exist')

        if not os.path.exists(folder_save_results):
            os.makedirs(folder_save_results, exist_ok=True)
        
        self.path_model = path_model
        self.dict_kinematics = dict_kinematics
        self.dict_muscles = dict_muscles
        self.folder_save_results = folder_save_results
        self.integrator_accuracy = integrator_accuracy
        self.use_activation_dynamics = use_activation_dynamics
        self.use_tendon_compliance = use_tendon_compliance
        self.use_muscle_physiology = use_muscle_physiology
        self.constant_muscle_control = constant_muscle_control
        self.override_default_muscle_activation = override_default_muscle_activation
        self.unconstrained_coordinates = unconstrained_coordinates
        self.max_forsim_time = max_forsim_time    
        
        create_save_sto(
            dict_kinematics,
            os.path.join(folder_save_results, 'kinematics.sto'),
            convert_to_radians=True
        )
        
        create_save_sto(
            dict_muscles,
            os.path.join(folder_save_results, 'muscles.sto')
        )
        
        self.forsim_completed = False
        self._evaluation_results = None
    
    def run_forsim(self, max_forsim_time=None):
        """
        Runs the ForsimTool simulation with a timeout.

        Args:
            max_forsim_time (int, optional): Maximum allowed time in seconds for the forsim run.
                If None, uses the value set during initialization. Defaults to None.

        Returns:
            bool: True if ForsimTool completes successfully within the timeout, False otherwise.
        """
        if max_forsim_time is not None:
            self.max_forsim_time = max_forsim_time
        
        kwargs = {
            'path_model': self.path_model,
            'folder_save_results': self.folder_save_results,
            'integrator_accuracy': self.integrator_accuracy,
            'constant_muscle_control': self.constant_muscle_control,
            'override_default_muscle_activation': self.override_default_muscle_activation,
            'use_activation_dynamics': self.use_activation_dynamics,
            'use_tendon_compliance': self.use_tendon_compliance,
            'use_muscle_physiology': self.use_muscle_physiology,
            'unconstrained_coordinates': self.unconstrained_coordinates,
        }
        try:
            run_with_timeout(run_forsim, self.max_forsim_time, **kwargs)
            print('Forsim Tool completed successfully')
            self.forsim_completed = True
            return True
        except TimeoutError:
            print('Forsim Tool timed out... took longer than allowed time')
            return False
    
    def run_joint_mechanics_tool(self):
        """
        Runs the JointMechanicsTool on the results of the Forsim simulation.

        Uses the settings (activation dynamics, tendon compliance, muscle physiology)
        defined during the initialization of the COMAKforsim object.
        """
        
        run_joint_mechanics_tool(
            self.path_model,
            self.folder_save_results,
            self.use_activation_dynamics,
            self.use_tendon_compliance,
            self.use_muscle_physiology,
        )
    
    def jam_evaluation(self, dict_criteria):
        """
        Evaluates the joint mechanics results against specified criteria.

        This method should be called after `run_forsim` and `run_joint_mechanics_tool`.
        It uses the `jam_evaluation` function to perform the analysis.

        Args:
            dict_criteria (dict): Dictionary defining the criteria for evaluation.

        Returns:
            bool: True if ForsimTool completed and all criteria are passed, False otherwise.
                       Returns False immediately if ForsimTool did not complete successfully.
        """
        
        if not self.forsim_completed:
            print('Forsim Tool did not complete successfully')
            return False
        
        path_h5_file = os.path.join(self.folder_save_results, 'joint_mechanics', 'joint_mechanics.h5')
        passed, evaluation_results = jam_evaluation(
            path_h5_file,
            self.folder_save_results,
            dict_criteria=dict_criteria
        )
        
        self._evaluation_results = evaluation_results
        
        return passed
    
    # return the evaluation results
    @property
    def evaluation_results(self):
        """
        Provides a deep copy of the evaluation results from the last `jam_evaluation` call.

        Returns:
            dict or None: A deep copy of the dictionary containing evaluation metrics and criteria results,
                          or None if `jam_evaluation` has not been successfully run.
        """
        # return a copy of the evaluation results
        return copy.deepcopy(self._evaluation_results)