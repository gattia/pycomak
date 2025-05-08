import os
import json
import opensim as osim
from pycomak import COMAKBASE

from pycomak.defaults import prescribed_coordinates as PRESCRIBED_COORDINATES
from pycomak.defaults import primary_coordinates as PRIMARY_COORDINATES
from pycomak.defaults import secondary_coordinates as SECONDARY_COORDINATES


def get_muscle_weights(dict_muscle_weights, model):
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
        settle_threshold=1e-3,
        settle_accuracy=1e-2,
        settle_internal_step_limit=10_000,
        max_iterations=25,
        udot_tolerance=1,
        udot_worse_case_tolerance=50,
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
        print("Starting COMAK Tool!")
        self.comak.run()
        print('Finished COMAK Tool!')







# def comaktool_function(settings):#results_basename,model_file,primary_coord_file, secondary_coord_file,prescribed_coord_file,model_dir,comak_result_dir,ik_result_dir,subj_dir,external_loads_file,start_time,stop_time):
#     # coordinates_file = settings.ik_result_dir + '/comak_ik.mot'
#     # forceset_file = settings.model_dir + '/lenhart2015_reserve_actuators.xml'
#     # save_xml_path = settings.subj_dir + '/inputs/comak_settings.xml'
    
#     # with open(settings.prescribed_coord_file,'r') as f:
#     #     prescribed_coordinates = json.load(f)

#     # with open(settings.primary_coord_file, 'r') as f:
#     #     primary_coordinates = json.load(f)

#     # with open(settings.secondary_coord_file, 'r') as f:
#     #     secondary_coordinates = json.load(f)

#     # Settings
#     start_pad = 0.0

#     comak = osim.COMAKTool();
#     comak.set_model_file(settings.upd_model_file);
#     comak.set_coordinates_file(coordinates_file);
#     comak.set_external_loads_file(settings.external_loads_file);
#     comak.set_results_directory(settings.comak_result_dir);
#     comak.set_results_prefix(settings.results_basename);
#     comak.set_replace_force_set(False);
#     comak.set_force_set_file(forceset_file);
#     comak.set_start_time(settings.start_time_comak - start_pad);
#     comak.set_stop_time(settings.stop_time_comak);
#     comak.set_time_step(0.01);
#     comak.set_lowpass_filter_frequency(6);
#     comak.set_print_processed_input_kinematics(False);

#     for coordinate_number, path in prescribed_coordinates.items():
#         comak.set_prescribed_coordinates(int(coordinate_number), path)

#     for coord_number, path in primary_coordinates.items():
#         comak.set_primary_coordinates(int(coord_number), path)

#     secondary_coord_set = osim.COMAKSecondaryCoordinateSet();
#     secondary_coord = osim.COMAKSecondaryCoordinate();

#     for coord, dict_ in secondary_coordinates.items():
#         secondary_coord.setName(coord)
#         secondary_coord.set_max_change(dict_['max_change']);
#         secondary_coord.set_coordinate(dict_['coordinate']);
#         secondary_coord_set.cloneAndAppend(secondary_coord);

#     comak.set_COMAKSecondaryCoordinateSet(secondary_coord_set);

#     comak.set_settle_secondary_coordinates_at_start(True);
#     comak.set_settle_threshold(1e-3);
#     comak.set_settle_accuracy(1e-2);
#     comak.set_settle_internal_step_limit(10000);
#     comak.set_print_settle_sim_results(True);
#     comak.set_settle_sim_results_directory(settings.comak_result_dir);
#     comak.set_settle_sim_results_prefix("motion_settle_sim");
#     comak.set_max_iterations(25);
#     comak.set_udot_tolerance(1);
#     comak.set_udot_worse_case_tolerance(50);
#     comak.set_unit_udot_epsilon(1e-6);
#     comak.set_optimization_scale_delta_coord(1);
#     comak.set_ipopt_diagnostics_level(3);
#     comak.set_ipopt_max_iterations(500);
#     comak.set_ipopt_convergence_tolerance(1e-4);
#     comak.set_ipopt_constraint_tolerance(1e-4);
#     comak.set_ipopt_limited_memory_history(200);
#     comak.set_ipopt_nlp_scaling_max_gradient(10000);
#     comak.set_ipopt_nlp_scaling_min_value(1e-8);
#     comak.set_ipopt_obj_scaling_factor(1);
#     comak.set_activation_exponent(2);
#     comak.set_contact_energy_weight(CONTACT_ENERGY_WEIGHT);
#     comak.set_non_muscle_actuator_weight(1000);
#     comak.set_model_assembly_accuracy(1e-12);
#     comak.set_use_visualizer(False);

#     comak.setDebugLevel(1);
#     comak.printToXML(save_xml_path);

#     print("Starting COMAK Tool!")
#     comak.run()
#     print('Finished COMAK Tool!')