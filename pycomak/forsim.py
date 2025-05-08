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
    '/jointset/pf_r/pf_tz_r'
]

ATTACHED_GEOMETRY_BODIES = [
    '/bodyset/femur_distal_r',
    '/bodyset/tibia_proximal_r',
    '/bodyset/patella_r'
]

SECONDARY_COORDINATES = [
    'knee_flex_r', 'knee_add_r', 'knee_rot_r',
    'knee_tx_r', 'knee_ty_r', 'knee_tz_r',
    'pf_flex_r', 'pf_rot_r', 'pf_tilt_r',
    'pf_tx_r','pf_ty_r','pf_tz_r'
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
    path_save
):
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
    unconstrianed_coordinates=UNCONSTRAINED_COORDINATES,
):
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
    
    for idx, coord in enumerate(unconstrianed_coordinates):
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
    fibers = [x for x in jam.forceset['Blankevoort1991Ligament'].keys() if ligament_name in x]
    if len(fibers) == 0:
        raise ValueError('Ligament not found in forceset')
    data = np.zeros(jam.forceset['Blankevoort1991Ligament'][fibers[0]]['total_force'].shape[0])
    for fiber in fibers:
        data += np.squeeze(jam.forceset['Blankevoort1991Ligament'][fiber]['total_force'])
    return data

def analyze_criteria(jam, criteria_dict, criteria_type, passed=True):
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
        unconstrianed_coordinates=UNCONSTRAINED_COORDINATES,
        max_forsim_time=2*60, # 2 minutes
    ):
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
        self.unconstrianed_coordinates = unconstrianed_coordinates
        self.max_forsim_time = max_forsim_time    
        
        create_save_sto(
            dict_kinematics,
            os.path.join(folder_save_results, 'kinematics.sto')
        )
        
        create_save_sto(
            dict_muscles,
            os.path.join(folder_save_results, 'muscles.sto')
        )
        
        self.forsim_completed = False
        self._evaluation_results = None
    
    def run_forsim(self, max_forsim_time=None):
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
            'unconstrianed_coordinates': self.unconstrianed_coordinates,
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
        
        run_joint_mechanics_tool(
            self.path_model,
            self.folder_save_results,
            self.use_activation_dynamics,
            self.use_tendon_compliance,
            self.use_muscle_physiology,
        )
    
    def jam_evaluation(self, dict_criteria):
        
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
        # return a copy of the evaluation results
        return copy.deepcopy(self._evaluation_results)