import os
import json
import opensim as osim
import glob
import shutil

import datetime
from pycomak.defaults import prescribed_coordinates as PRESCRIBED_COORDINATES
from pycomak.defaults import primary_coordinates as PRIMARY_COORDINATES
from pycomak.defaults import secondary_coordinates as SECONDARY_COORDINATES
from pycomak.defaults import slack_length_dict as SLACK_LENGTH
from pycomak.defaults import muscle_length_dict as MUSCLE_LENGTH
from pycomak import COMAKBASE

def update_slack_lengths(model, new_model_file=None, slack_length_dict=SLACK_LENGTH, muscle_length_dict=MUSCLE_LENGTH):
    if isinstance(model, str):
        model = osim.Model(model)
    
    forces_upd = model.upd_ForceSet()

    state = model.initSystem()
    
    # Modifying ligaments & muscles
    for i in range(forces_upd.getSize()):
        force_ = forces_upd.get(i)
            
        if force_.getConcreteClassName() == 'Millard2012EquilibriumMuscle':
            # get the muscle
            muscle = osim.Millard2012EquilibriumMuscle.safeDownCast(force_)
            # calculate the scale factor
            scale_factor = muscle.getLength(state) / muscle_length_dict[muscle.getName()]
            # update the optimal fiber length
            optimal_ = muscle.getOptimalFiberLength()
            optimal_ *= scale_factor
            muscle.setOptimalFiberLength(optimal_)
            
            # update the tendon slack length
            slack_ = muscle.getTendonSlackLength()
            slack_ *= scale_factor
            muscle.setTendonSlackLength(slack_)
        elif force_.getConcreteClassName() == 'Blankevoort1991Ligament':
            ligament = osim.Blankevoort1991Ligament.safeDownCast(force_)
            ligament.setSlackLengthFromReferenceStrain(slack_length_dict[ligament.getName()], state)
    
    # Add logic to also update muscle parameters? Slack length, and optimal fiber length?

    print('Updated Ligament & Tendon Slack Lengths and Muscle Optimal Fiber Lengths')

    if new_model_file is not None:
        model.printToXML(new_model_file)
        print('Saved Updated Model:', new_model_file)

    return model

def modifyCoordinates(model_update, ik_result_dir, newmodel, slack_length_dict=SLACK_LENGTH, muscle_length_dict=MUSCLE_LENGTH): 
    
    # Setting the State
    table = osim.TimeSeriesTable(os.path.join(ik_result_dir, '_secondary_constraint_settle_states.sto'))
    column_labels = table.getColumnLabels()
    
    ##Insert joint name labels here
    data_values = [table.getDependentColumn(column_label)[0] for column_label in column_labels]

    coord_values = [0 for i in range(int(len(data_values)/2))]
    joint_names = [0 for i in range(int(len(data_values)/2))]
    coord_names = [0 for i in range(int(len(data_values)/2))]

    for i in range(0,len(data_values)):
        if (i%2) == 0:
            coord_values[int(i/2)] = data_values[i]
            splitName = column_labels[i].split('/')
            joint_names[int(i/2)] = splitName[len(splitName)-3]
            coord_names[int(i/2)] = splitName[len(splitName)-2]    
    
    for i in range(0,len(joint_names)):
        joint_name = joint_names[i]

        joint_upd = model_update.getJointSet().get(joint_name)

        if joint_upd.numCoordinates() == 1:
            coordinate_index = 0
        else:
            for j in range(0,joint_upd.numCoordinates()):
                if joint_upd.get_coordinates(j).getSpeedName().split('/')[0] == coord_names[i]:
                    coordinate_index = j
                    break
        if coord_values[i] < joint_upd.get_coordinates(coordinate_index).getRangeMin():
            joint_upd.get_coordinates(coordinate_index).setDefaultValue(joint_upd.get_coordinates(coordinate_index).getRangeMin())
       
        elif coord_values[i] > joint_upd.get_coordinates(coordinate_index).getRangeMax():
            joint_upd.get_coordinates(coordinate_index).setDefaultValue(joint_upd.get_coordinates(coordinate_index).getRangeMax())
        else:
            joint_upd.get_coordinates(coordinate_index).setDefaultValue(coord_values[i])

    update_slack_lengths(model_update, new_model_file=newmodel, slack_length_dict=slack_length_dict, muscle_length_dict=muscle_length_dict)
    
    
class COMAKInverseKinematics(COMAKBASE):
    def __init__(
        self,
        base_model_path,
        results_dir,
        stop_time_ik,
        start_time_ik,
        markerset_file,
        start_pad=0.0,
        stop_pad=0.0,
        settle_sim_reps=5,
        secondary_constraint_sim_sweep_time=3.0,
        secondary_coupled_coordinate_stop_value=100,
        secondary_coupled_coordinate='/jointset/knee_r/knee_flex_r',
        secondary_constraint_sim_settle_threshold=1e-4,
        secondary_constraint_sim_integrator_accuracy=1e-3,
        secondary_constraint_sim_internal_step_limit=10_000,
        constraint_function_num_interpolation_points=60,
        print_secondary_constraint_sim_results=True,
        report_errors=True,
        report_marker_locations=False,
        ik_constraint_weight=100,
        ik_accuracy=1e-5,
        prescribed_coordinates=PRESCRIBED_COORDINATES,
        primary_coordinates=PRIMARY_COORDINATES,
        secondary_coordinates=SECONDARY_COORDINATES,
        log_level="Trace",
        slack_length_dict=SLACK_LENGTH,
        muscle_length_dict=MUSCLE_LENGTH
    ):
        # define folders to save results
        super().__init__(results_dir)
                
        self.base_model_path = base_model_path
        self.markerset_file = markerset_file
        self.start_time_ik = start_time_ik
        self.stop_time_ik = stop_time_ik
        
        
        
        # setup logging
        self.date_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        osim.Logger.setLevelString(log_level)
        osim.Logger.removeFileSink()
        osim.Logger.addFileSink(os.path.join(self.log_dir, f'comakIKlog_{self.date_time}.log'))
        
        # store settings
        self.start_pad = start_pad
        self.stop_pad = stop_pad
        self.settle_sim_reps = settle_sim_reps
        self.secondary_constraint_sim_sweep_time = secondary_constraint_sim_sweep_time
        self.secondary_coupled_coordinate_stop_value = secondary_coupled_coordinate_stop_value
        self.secondary_coupled_coordinate = secondary_coupled_coordinate
        self.secondary_constraint_sim_settle_threshold = secondary_constraint_sim_settle_threshold
        self.secondary_constraint_sim_integrator_accuracy = secondary_constraint_sim_integrator_accuracy
        self.secondary_constraint_sim_internal_step_limit = secondary_constraint_sim_internal_step_limit
        self.constraint_function_num_interpolation_points = constraint_function_num_interpolation_points
        self.print_secondary_constraint_sim_results = print_secondary_constraint_sim_results
        self.report_errors = report_errors
        self.report_marker_locations = report_marker_locations
        self.ik_constraint_weight = ik_constraint_weight
        self.ik_accuracy = ik_accuracy
        self.prescribed_coordinates = prescribed_coordinates
        self.primary_coordinates = primary_coordinates
        self.secondary_coordinates = secondary_coordinates
        
        # define file names to save results
        
        self.save_xml_path = os.path.join(self.inputs_dir, 'comak_inverse_kinematics_settings.xml')
        
        self.comak_ik = osim.COMAKInverseKinematicsTool()
        self.comak_ik.set_results_directory(self.ik_result_dir)
        
        # Set settle sim path
        self.settle_sim_intermed_model_filepath = os.path.join(
            self.ik_result_dir, 
            self.settle_sim_intermed_filename
        )
        
        # final model file path
        self.final_model_path = os.path.join(
            self.ik_result_dir,
            self.settle_and_sweep_sim_filename
        )
        
        self.slack_length_dict = slack_length_dict
        self.muscle_length_dict = muscle_length_dict
        
        self.setup_generic_comakik_settings()
        
        # aggregate all the settings in a dictionary and save it
        # as a json file in the inputs directory
        settings_dict = {
            "base_model_path": self.base_model_path,
            "markerset_file": self.markerset_file,
            "start_time_ik": self.start_time_ik,
            "stop_time_ik": self.stop_time_ik,
            "start_pad": self.start_pad,
            "stop_pad": self.stop_pad,
            "settle_sim_reps": self.settle_sim_reps,
            "secondary_constraint_sim_sweep_time": self.secondary_constraint_sim_sweep_time,
            "secondary_coupled_coordinate_stop_value": self.secondary_coupled_coordinate_stop_value,
            "secondary_coupled_coordinate": self.secondary_coupled_coordinate,
            "secondary_constraint_sim_settle_threshold": self.secondary_constraint_sim_settle_threshold,
            "secondary_constraint_sim_integrator_accuracy": self.secondary_constraint_sim_integrator_accuracy,
            "secondary_constraint_sim_internal_step_limit": self.secondary_constraint_sim_internal_step_limit,
            "constraint_function_num_interpolation_points": self.constraint_function_num_interpolation_points,
            "print_secondary_constraint_sim_results": self.print_secondary_constraint_sim_results,
            "report_errors": self.report_errors,
            "report_marker_locations": self.report_marker_locations,
            "ik_constraint_weight": self.ik_constraint_weight,
            "ik_accuracy": self.ik_accuracy,
            "prescribed_coordinates": self.prescribed_coordinates,
            "primary_coordinates": self.primary_coordinates,
            "secondary_coordinates": self.secondary_coordinates,
            "log_level": log_level,
            "slack_length_dict": self.slack_length_dict,
            "muscle_length_dict": self.muscle_length_dict
        }
        
        with open(os.path.join(self.inputs_dir, 'comak_inverse_kinematics_settings.json'), 'w') as f:
            json.dump(settings_dict, f, indent=4)
    
    def setup_generic_comakik_settings(self, secondary_coupled_coordinate=None):
        if secondary_coupled_coordinate is not None:
            self.secondary_coupled_coordinate = secondary_coupled_coordinate
        
        self.comak_ik.set_secondary_coupled_coordinate(self.secondary_coupled_coordinate)
        for idx, (coord, dict_) in enumerate(self.secondary_coordinates.items()):
            self.comak_ik.set_secondary_coordinates(int(idx), dict_['coordinate'])
        
        self.comak_ik.set_secondary_constraint_sim_settle_threshold(self.secondary_constraint_sim_settle_threshold)
        self.comak_ik.set_secondary_constraint_sim_integrator_accuracy(self.secondary_constraint_sim_integrator_accuracy)
        self.comak_ik.set_secondary_constraint_sim_internal_step_limit(self.secondary_constraint_sim_internal_step_limit)
        self.comak_ik.set_constraint_function_num_interpolation_points(self.constraint_function_num_interpolation_points)
        self.comak_ik.set_print_secondary_constraint_sim_results(self.print_secondary_constraint_sim_results)
        
        self.comak_ik.set_marker_file(self.markerset_file)
        self.comak_ik.set_output_motion_file(self.comak_ik_filename)
        self.comak_ik.set_time_range(0, self.start_time_ik-self.start_pad)
        self.comak_ik.set_time_range(1, self.stop_time_ik+self.stop_pad)
        self.comak_ik.set_report_errors(self.report_errors)
        self.comak_ik.set_report_marker_locations(self.report_marker_locations)
        self.comak_ik.set_ik_constraint_weight(self.ik_constraint_weight)
        self.comak_ik.set_ik_accuracy(self.ik_accuracy)
        self.comak_ik.set_use_visualizer(False)
        
        # ik_task_set = self.comak_ik.get_IKTaskSet()
        ik_task_set = osim.IKTaskSet()
        # ik_task = osim.IKMarkerTask()
        self.comak_ik.set_IKTaskSet(ik_task_set)
        self.comak_ik.printToXML(self.save_xml_path)
    
    def perform_settle_sim(self):
        self.comak_ik.set_perform_secondary_constraint_sim(True)
        self.comak_ik.set_secondary_constraint_sim_sweep_time(0)
        self.comak_ik.set_secondary_coupled_coordinate_start_value(0)
        self.comak_ik.set_secondary_coupled_coordinate_stop_value(0)
        self.comak_ik.set_perform_inverse_kinematics(False)

        self.comak_ik.set_constrained_model_file(
            os.path.join(self.ik_result_dir, self.settle_sim_constrained_model_filename)
        )
        self.comak_ik.set_secondary_constraint_function_file(
            os.path.join(self.ik_result_dir, self.settle_sim_secondary_constraint_function_filename)
        )
        
        for count in range(self.settle_sim_reps - 1):
            print(f'Starting Settle Sim {count+1}...')
            if count == 0:
                print('First settle sim step - so, initializing slack lengths...')
                # get file to load
                # model_file =   # THIS ISNT CURRENTLY USED
                # create new model file - to save updated slack lengths
                

                update_slack_lengths(
                    model=self.base_model_path, # load in the original model once
                    new_model_file=self.settle_sim_intermed_model_filepath,
                    slack_length_dict=self.slack_length_dict,
                    muscle_length_dict=self.muscle_length_dict
                )
                
                # copy geometry files to the new model folder
                # find geometry folder in the original model folder
                model_folder = os.path.dirname(self.base_model_path)
                geometry_folder = os.path.join(model_folder, 'Geometry')
                assert os.path.exists(geometry_folder), f'Geometry folder not found in {model_folder}'
                # copy geometry_folder to the comak inverse kinematics folder
                shutil.copytree(geometry_folder, os.path.join(self.ik_result_dir, 'Geometry'), dirs_exist_ok=True)
                
                print('Finished Initializing Slack Lengths')
                print('\tUpdated Model:', self.settle_sim_intermed_model_filepath)

                # update model file path so all new steps use the updated model
                # self.model_path = self.settle_sim_intermed_model_filepath

            # Run COMAK IK
            self.comak_ik.set_model_file(self.settle_sim_intermed_model_filepath)
            print('Running COMAKInverseKinematicsTool - Settle Sim Only...')
            # TODO: Update to use: performIKSecondaryConstraintSimulation() instead of run()
            self.comak_ik.run()

            # Load the model 
            model_update_1 = osim.Model(self.settle_sim_intermed_model_filepath)

            # Pose the model in the settle sim position, then update the tendon slack lengths
            modifyCoordinates(model_update_1, self.ik_result_dir, self.settle_sim_intermed_model_filepath, slack_length_dict=self.slack_length_dict, muscle_length_dict=self.muscle_length_dict)

    def perform_sweep_sim(self):
        self.comak_ik.set_perform_inverse_kinematics(False)
        self.comak_ik.set_perform_secondary_constraint_sim(True)

        # create new model file name
        self.comak_ik.set_model_file(self.settle_sim_intermed_model_filepath)
        
        self.comak_ik.set_constrained_model_file(
            os.path.join(self.ik_result_dir, self.sweep_sim_constrained_model_filename)
        )
        self.comak_ik.set_secondary_constraint_function_file(
            os.path.join(self.ik_result_dir, self.sweep_sim_secondary_constraint_function_filename)
        )

        
        self.comak_ik.set_secondary_constraint_sim_sweep_time(self.secondary_constraint_sim_sweep_time)
        self.comak_ik.set_secondary_coupled_coordinate_start_value(0)
        self.comak_ik.set_secondary_coupled_coordinate_stop_value(self.secondary_coupled_coordinate_stop_value)
        print('Running COMAKInverseKinematicsTool - Final Settle Sim & Sweep Sim...')
        # TODO: Update to use: performIKSecondaryConstraintSimulation() instead of run()
        self.comak_ik.run()
        
        model_update_1 = osim.Model(self.settle_sim_intermed_model_filepath)
        
        modifyCoordinates(model_update_1, self.ik_result_dir, self.final_model_path, slack_length_dict=self.slack_length_dict, muscle_length_dict=self.muscle_length_dict)
    
    def perform_inverse_kinematics(self):
        
        self.comak_ik.set_constrained_model_file(
            os.path.join(self.ik_result_dir, self.sweep_sim_constrained_model_filename)
        )
        self.comak_ik.set_secondary_constraint_function_file(
            os.path.join(self.ik_result_dir, self.sweep_sim_secondary_constraint_function_filename)
        )
        
        self.comak_ik.set_perform_inverse_kinematics(True)
        self.comak_ik.set_perform_secondary_constraint_sim(False)
        self.comak_ik.set_model_file(self.final_model_path)
        print('Running COMAKInverseKinematicsTool - Inverse Kinematics...')
        # TODO: Update to use: performIK() instead of run()
        self.comak_ik.run()