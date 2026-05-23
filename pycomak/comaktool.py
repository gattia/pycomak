import os
import re
import json
import opensim as osim
from pycomak import COMAKBASE

from pycomak.defaults import prescribed_coordinates as PRESCRIBED_COORDINATES
from pycomak.defaults import primary_coordinates as PRIMARY_COORDINATES
from pycomak.defaults import secondary_coordinates as SECONDARY_COORDINATES


def _filter_coordinates_to_model(coordinate_dict, model_path):
    """Drop secondary-coordinate entries whose coordinate is absent from the model.

    Keeps the COMAK secondary-coordinate list model-driven: a model built
    without the menisci (or any optional body) simply contributes fewer
    secondary coordinates instead of failing when a hardcoded coordinate path
    cannot be resolved. No-op when every coordinate is present, or when the
    model file cannot be read.
    """
    if not model_path or not os.path.exists(model_path):
        return coordinate_dict
    with open(model_path) as f:
        present = set(re.findall(r'<Coordinate\s+name="([^"]+)"', f.read()))
    filtered = {
        name: spec for name, spec in coordinate_dict.items()
        if spec['coordinate'].rsplit('/', 1)[-1] in present
    }
    dropped = [n for n in coordinate_dict if n not in filtered]
    if dropped:
        print(f"[comaktool] secondary coordinates not in model, skipping: {dropped}")
    return filtered


def get_muscle_weights(dict_muscle_weights, model):
    """
    Creates a COMAKCostFunctionParameterSet with muscle-specific weights.

    Iterates through the muscles in the provided model and sets their weights
    in the cost function parameter set. If a muscle is found in `dict_muscle_weights`,
    its weight is set to the specified value; otherwise, it defaults to 1.

    Args:
        dict_muscle_weights (dict): A dictionary mapping muscle names (str) to
            their desired weights (float or int).
        model (osim.Model): The OpenSim model object containing the muscles.

    Returns:
        osim.COMAKCostFunctionParameterSet: The configured set of cost function
            parameters with muscle weights.
    """
    weighted_muscle_names = list(dict_muscle_weights.keys())
    
    cost_fun_param_set = osim.COMAKCostFunctionParameterSet()
    cost_fun_param = osim.COMAKCostFunctionParameter()
    
    muscles = model.getMuscles()
    for muscle_idx in range(muscles.getSize()):
        muscle = muscles.get(muscle_idx)
        muscle_name = muscle.getName()
                
        cost_fun_param.setName(muscle_name)
        cost_fun_param.set_actuator(f'/forceset/{muscle_name}')
        cost_fun_param.set_desired_activation(osim.Constant(0.0))
        cost_fun_param.set_activation_lower_bound(osim.Constant(0.01))
        cost_fun_param.set_activation_upper_bound(osim.Constant(1.0))
        
        if muscle_name in weighted_muscle_names:
            print(f'Setting {muscle_name} muscle weight to: {dict_muscle_weights[muscle_name]}')
            cost_fun_param.set_weight(osim.Constant(dict_muscle_weights[muscle_name]))
        else:
            cost_fun_param.set_weight(osim.Constant(1))
        cost_fun_param_set.cloneAndAppend(cost_fun_param)
    
    return cost_fun_param_set
    
    

class COMAK(COMAKBASE):
    """
    A class to set up and run the Concurrent Optimization of Muscle Activations and Kinematics 
    (COMAK) tool.

    This class configures the COMAKTool with various parameters related to the model,
    input kinematics, external loads, time settings, filter frequencies, optimization
    parameters (including IPOPT settings), and coordinate definitions (prescribed,
    primary, secondary). It also handles muscle weighting for the cost function.

    The settings are saved to XML and JSON files, and a `run` method is provided
    to execute the COMAK analysis.
    """
    def __init__(
        self,
        results_dir, #settings.model_dir + '/lenhart2015_reserve_actuators.xml'
        forceset_file,
        model_path,
        external_loads_file,
        start_time,
        stop_time,
        time_step=0.01,
        low_pass_cutoff=6,
        settle_threshold=1e-3,  #1e-4
        settle_accuracy=1e-2,  #1e-3
        settle_internal_step_limit=10_000,
        max_iterations=25,
        udot_tolerance=1,
        udot_worse_case_tolerance=50,
        convergence_criterion='udot',
        generalized_force_tolerance=1.0,
        generalized_force_worse_case_tolerance=50.0,
        unit_udot_epsilon=1e-6,
        optimization_scale_delta_coord=1,
        ipopt_diagnostics_level=3,
        ipopt_max_iterations=500,
        ipopt_convergence_tolerance=1e-4,
        ipopt_constraint_tolerance=1e-4,
        ipopt_limited_memory_history=200,
        ipopt_nlp_scaling_max_gradient=10_000,
        ipopt_nlp_scaling_min_value=1e-8,
        ipopt_obj_scaling_factor=1,
        activation_exponent=2,
        contact_energy_weight=500,
        non_muscle_actuator_weight=1_000,
        model_assembly_accuracy=1e-12,
        debug_level=1,        
        primary_coordinates=PRIMARY_COORDINATES,
        secondary_coordinates=SECONDARY_COORDINATES,
        prescribed_coordinates=PRESCRIBED_COORDINATES,
        muscle_weights_dict=None,
    ):
        """
        Initializes the COMAK class.

        Args:
            results_dir (str): Directory to save results and intermediate files.
            forceset_file (str): Path to the ForceSet XML file (e.g., reserve actuators).
            model_path (str): Path to the OpenSim model file (.osim).
            external_loads_file (str): Path to the external loads file.
            start_time (float): Start time for the COMAK analysis.
            stop_time (float): Stop time for the COMAK analysis.
            time_step (float, optional): Time step for the analysis. Defaults to 0.01.
            low_pass_cutoff (float, optional): Cutoff frequency for low-pass filtering input kinematics.
                Defaults to 6.
            settle_threshold (float, optional): Threshold for settling secondary coordinates.
                Defaults to 1e-3.
            settle_accuracy (float, optional): Accuracy for settling secondary coordinates.
                Defaults to 1e-2.
            settle_internal_step_limit (int, optional): Internal step limit for settling simulation.
                Defaults to 10_000.
            max_iterations (int, optional): Maximum COMAK iterations. Defaults to 25.
            udot_tolerance (float, optional): Tolerance for coordinate derivative (udot).
                Defaults to 1.
            udot_worse_case_tolerance (float, optional): Worst-case tolerance for udot.
                Defaults to 50.
            convergence_criterion (str, optional): COMAK convergence criterion.
                'udot' (default) reproduces the historical behavior exactly.
                'generalized_force' gates on the diagonal-scaled residual
                M_kk*|Delta udot| (Lever 4 — coordinate-fair, moment-scaled).
            generalized_force_tolerance (float, optional): Per-coordinate
                tolerance (N or N*m) used when convergence_criterion is
                'generalized_force'. Defaults to 1.0.
            generalized_force_worse_case_tolerance (float, optional):
                Worst-case per-coordinate tolerance (N or N*m) used when
                convergence_criterion is 'generalized_force'. Defaults to 50.0.
            unit_udot_epsilon (float, optional): Epsilon for unit udot. Defaults to 1e-6.
            optimization_scale_delta_coord (float, optional): Scaling factor for delta coordinates
                in optimization. Defaults to 1.
            ipopt_diagnostics_level (int, optional): IPOPT diagnostics level. Defaults to 3.
            ipopt_max_iterations (int, optional): Maximum IPOPT iterations. Defaults to 500.
            ipopt_convergence_tolerance (float, optional): IPOPT convergence tolerance.
                Defaults to 1e-4.
            ipopt_constraint_tolerance (float, optional): IPOPT constraint tolerance.
                Defaults to 1e-4.
            ipopt_limited_memory_history (int, optional): IPOPT limited memory history size.
                Defaults to 200.
            ipopt_nlp_scaling_max_gradient (float, optional): IPOPT NLP scaling max gradient.
                Defaults to 10_000.
            ipopt_nlp_scaling_min_value (float, optional): IPOPT NLP scaling min value.
                Defaults to 1e-8.
            ipopt_obj_scaling_factor (float, optional): IPOPT objective scaling factor.
                Defaults to 1.
            activation_exponent (float, optional): Exponent for muscle activation in the cost function.
                Defaults to 2.
            contact_energy_weight (float, optional): Weight for contact energy in the cost function.
                Defaults to 500.
            non_muscle_actuator_weight (float, optional): Weight for non-muscle actuators in the cost function.
                Defaults to 1_000.
            model_assembly_accuracy (float, optional): Accuracy for model assembly. Defaults to 1e-12.
            debug_level (int, optional): Debug level for COMAKTool. Defaults to 1.
            primary_coordinates (dict, optional): Dictionary of primary coordinates.
                Defaults to PRIMARY_COORDINATES from pycomak.defaults.
            secondary_coordinates (dict, optional): Dictionary of secondary coordinates.
                Defaults to SECONDARY_COORDINATES from pycomak.defaults.
            prescribed_coordinates (dict, optional): Dictionary of prescribed coordinates.
                Defaults to PRESCRIBED_COORDINATES from pycomak.defaults.
            muscle_weights_dict (dict, optional): Dictionary of muscle weights for the cost function.
                If None, default weights (1) are used for all muscles. Defaults to None.
        """
        super().__init__(results_dir)
        
        coordinates_file = os.path.join(self.ik_result_dir, 'comak_ik.mot')
        save_xml_path = os.path.join(self.inputs_dir, 'comak_settings.xml')
        
        self.comak = osim.COMAKTool()
        self.comak.set_model_file(model_path)
        self.comak.set_coordinates_file(coordinates_file)
        self.comak.set_external_loads_file(external_loads_file)
        self.comak.set_results_directory(self.comak_result_dir)
        # self.comak.set_results_prefix(settings.results_basename)
        self.comak.set_replace_force_set(False)
        self.comak.set_force_set_file(forceset_file)
        self.comak.set_start_time(start_time)
        self.comak.set_stop_time(stop_time)
        self.comak.set_time_step(time_step)
        self.comak.set_lowpass_filter_frequency(low_pass_cutoff)
        self.comak.set_print_processed_input_kinematics(False)
        
        if muscle_weights_dict is not None:
            model_ = osim.Model(model_path)
            self.cost_fun_param_set = get_muscle_weights(muscle_weights_dict, model_)
            self.comak.set_COMAKCostFunctionParameterSet(self.cost_fun_param_set)

        for coordinate_number, path in prescribed_coordinates.items():
            self.comak.set_prescribed_coordinates(int(coordinate_number), path)

        for coord_number, path in primary_coordinates.items():
            self.comak.set_primary_coordinates(int(coord_number), path)

        secondary_coordinates = _filter_coordinates_to_model(
            secondary_coordinates, model_path)

        secondary_coord_set = osim.COMAKSecondaryCoordinateSet()
        secondary_coord = osim.COMAKSecondaryCoordinate()

        for coord, dict_ in secondary_coordinates.items():
            secondary_coord.setName(coord)
            secondary_coord.set_max_change(dict_['max_change'])
            secondary_coord.set_coordinate(dict_['coordinate'])
            secondary_coord_set.cloneAndAppend(secondary_coord)

        self.comak.set_COMAKSecondaryCoordinateSet(secondary_coord_set)
       
        
        self.comak.set_settle_secondary_coordinates_at_start(True)
        self.comak.set_settle_threshold(settle_threshold)
        self.comak.set_settle_accuracy(settle_accuracy)
        self.comak.set_settle_internal_step_limit(settle_internal_step_limit)
        self.comak.set_print_settle_sim_results(True)
        self.comak.set_settle_sim_results_directory(self.comak_result_dir)
        self.comak.set_settle_sim_results_prefix("motion_settle_sim")
        self.comak.set_max_iterations(max_iterations)
        self.comak.set_udot_tolerance(udot_tolerance)
        self.comak.set_udot_worse_case_tolerance(udot_worse_case_tolerance)
        # Lever 4 — coordinate-specific, moment-scaled convergence criterion.
        # 'udot' reproduces the historical behaviour exactly; 'generalized_force'
        # gates on the diagonal-scaled residual M_kk*|Delta udot|.
        self.comak.set_convergence_criterion(convergence_criterion)
        self.comak.set_generalized_force_tolerance(generalized_force_tolerance)
        self.comak.set_generalized_force_worse_case_tolerance(
            generalized_force_worse_case_tolerance)
        self.comak.set_unit_udot_epsilon(unit_udot_epsilon)
        self.comak.set_optimization_scale_delta_coord(optimization_scale_delta_coord)
        self.comak.set_ipopt_diagnostics_level(ipopt_diagnostics_level)
        self.comak.set_ipopt_max_iterations(ipopt_max_iterations)
        self.comak.set_ipopt_convergence_tolerance(ipopt_convergence_tolerance)
        self.comak.set_ipopt_constraint_tolerance(ipopt_constraint_tolerance)
        self.comak.set_ipopt_limited_memory_history(ipopt_limited_memory_history)
        self.comak.set_ipopt_nlp_scaling_max_gradient(ipopt_nlp_scaling_max_gradient)
        self.comak.set_ipopt_nlp_scaling_min_value(ipopt_nlp_scaling_min_value)
        self.comak.set_ipopt_obj_scaling_factor(ipopt_obj_scaling_factor)
        self.comak.set_activation_exponent(activation_exponent)
        self.comak.set_contact_energy_weight(contact_energy_weight)
        self.comak.set_non_muscle_actuator_weight(non_muscle_actuator_weight)
        self.comak.set_model_assembly_accuracy(model_assembly_accuracy)
        self.comak.set_use_visualizer(False)

        self.comak.setDebugLevel(debug_level)
        self.comak.printToXML(save_xml_path)
        
        # aggregate all the settings in a dictionary and save it
        # as a json file in the inputs directory
        
        settings_dict = {
            'results_dir': results_dir,
            'forceset_file': forceset_file,
            'model_path': model_path,
            'external_loads_file': external_loads_file,
            'start_time': start_time,
            'stop_time': stop_time,
            'time_step': time_step,
            'low_pass_cutoff': low_pass_cutoff,
            'settle_threshold': settle_threshold,
            'settle_accuracy': settle_accuracy,
            'settle_internal_step_limit': settle_internal_step_limit,
            'max_iterations': max_iterations,
            'udot_tolerance': udot_tolerance,
            'udot_worse_case_tolerance': udot_worse_case_tolerance,
            'convergence_criterion': convergence_criterion,
            'generalized_force_tolerance': generalized_force_tolerance,
            'generalized_force_worse_case_tolerance': generalized_force_worse_case_tolerance,
            'unit_udot_epsilon': unit_udot_epsilon,
            'optimization_scale_delta_coord': optimization_scale_delta_coord,
            'ipopt_diagnostics_level': ipopt_diagnostics_level,
            'ipopt_max_iterations': ipopt_max_iterations,
            'ipopt_convergence_tolerance': ipopt_convergence_tolerance,
            'ipopt_constraint_tolerance': ipopt_constraint_tolerance,
            'ipopt_limited_memory_history': ipopt_limited_memory_history,
            'ipopt_nlp_scaling_max_gradient': ipopt_nlp_scaling_max_gradient,
            'ipopt_nlp_scaling_min_value': ipopt_nlp_scaling_min_value,
            'ipopt_obj_scaling_factor': ipopt_obj_scaling_factor,
            'activation_exponent': activation_exponent,
            'contact_energy_weight': contact_energy_weight,
            'non_muscle_actuator_weight': non_muscle_actuator_weight,
            'model_assembly_accuracy': model_assembly_accuracy,
            'debug_level': debug_level,
            'primary_coordinates': primary_coordinates,
            'secondary_coordinates': secondary_coordinates,
            'prescribed_coordinates': prescribed_coordinates,
            'muscle_weights_dict': muscle_weights_dict
        }
        
        with open(os.path.join(self.inputs_dir, 'comak_settings.json'), 'w') as f:
            json.dump(settings_dict, f, indent=4)

    def run(self):
        """
        Runs the COMAK analysis.

        Prints messages indicating the start and completion of the COMAKTool execution.
        """
        print("Starting COMAK Tool!")
        self.comak.run()
        print('Finished COMAK Tool!')

