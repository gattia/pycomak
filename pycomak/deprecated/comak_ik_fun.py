import os
import json
import opensim as osim
import re
import shutil
import datetime

pt_strain_scale = 1

# Patellar tendon peak strains during gait simulation: 
#   PT1: 3-9%
#   PT2: 1.9-6.9%
#   PT3: -1.8-4.4%
#   PT4: -0.6-5.9%
#   PT5: -1.6-4.6%
#   PT6: 1.9-8.6%


SLACK_LENGTH = {'MCLd1':0.04,'MCLd2':-0.04,'MCLd3':0.0,'MCLd4':0.04,'MCLd5':0.04,
                    'MCLs1':0.04,'MCLs2':0.04,'MCLs3':0.05,'MCLs4':0.05,'MCLs5':0.05,'MCLs6':0.05,
                    'ACLpl1':0.03,'ACLpl2':0.01,'ACLpl3':-0.05,'ACLpl4':-0.12,'ACLpl5':-0.02,'ACLpl6':-0.03,
                    'ACLam1':-0.14,'ACLam2':-0.05,'ACLam3':-0.08,'ACLam4':-0.14,'ACLam5':-0.14,'ACLam6':-0.12,
                    'PCLal1':0.03,'PCLal2':-0.1,'PCLal3':0.03,'PCLal4':-0.04,'PCLal5':-0.02,
                    'PCLpm1':-0.05,'PCLpm2':-0.12,'PCLpm3':-0.08,'PCLpm4':-0.12,'PCLpm5':-0.1,
                    'LCL1':0.06,'LCL2':0.06,'LCL3':0.06,'LCL4':0.06,
                    
                    # 'PT1':0.02 * pt_strain_scale,
                    # 'PT2':0.02 * pt_strain_scale,
                    # 'PT3':0.00 * pt_strain_scale,
                    # 'PT4':0.01 * pt_strain_scale,
                    # 'PT5':0.00 * pt_strain_scale,
                    # 'PT6':0.02 * pt_strain_scale,
                    
                    # 'PT1':0.02 * pt_strain_scale,
                    # 'PT2':0.02 * pt_strain_scale,
                    # 'PT3':0.02 * pt_strain_scale,
                    # 'PT4':0.02 * pt_strain_scale,
                    # 'PT5':0.02 * pt_strain_scale,
                    # 'PT6':0.02 * pt_strain_scale,

                    # 'PT1':0.02 * pt_strain_scale,
                    # 'PT2':0.02 * pt_strain_scale,
                    # 'PT3':0.005 * pt_strain_scale,
                    # 'PT4':0.01 * pt_strain_scale,
                    # 'PT5':0.005 * pt_strain_scale,
                    # 'PT6':0.02 * pt_strain_scale,

                    'PT1':0.02 * pt_strain_scale,
                    'PT2':0.02 * pt_strain_scale,
                    'PT3':0.02 * pt_strain_scale,
                    'PT4':0.02 * pt_strain_scale,
                    'PT5':0.02 * pt_strain_scale,
                    'PT6':0.02 * pt_strain_scale,
                    
                    'lPFL1':0.01,'lPFL2':-0.1,'lPFL3':0.01,'lPFL4':-0.12,'lPFL5':0.01,'lPFL6':0.01,'lPFL7':-0.08,'lPFL8':-0.08,
                    'mPFL1':-0.05,'mPFL2':0.01,'mPFL3':0.01,'mPFL4':-0.06,'mPFL5':-0.03,'mPFL6':0.01,
                    'MCLp1':0.05,'MCLp2':0.05,'MCLp3':0.02,'MCLp4':-0.02,'MCLp5':0.05,
                    'PFL1':0.01,'PFL2':-0.12,'PFL3':-0.03,'PFL4':-0.14,'PFL5':-0.1,
                    'pCAP1':0.04,'pCAP2':0.04,'pCAP3':0.04,'pCAP4':0.03,'pCAP5':0.04,'pCAP6':0.04,'pCAP7':0.04,'pCAP8':0.04,
                    'ITB1':0.02}  


def update_slack_lengths(model, new_model_file=None, slack_length_dict=SLACK_LENGTH):
    if isinstance(model, str):
        model = osim.Model(model)
    
    ligaments_upd = model.upd_ForceSet()

    state = model.initSystem()
    
    # Modifying the ligaments
    for i in range(0,(ligaments_upd.getSize())):
        ligament = osim.Blankevoort1991Ligament.safeDownCast(ligaments_upd.get(i))
        ligament_upd = osim.Blankevoort1991Ligament.safeDownCast(ligaments_upd.get(i))
        if ligament is not None:
            sL = ligament.getName()
            ligament_upd.setSlackLengthFromReferenceStrain(slack_length_dict[sL],state)

    print('Updated Ligament Slack Lengths')

    if new_model_file is not None:
        model.printToXML(new_model_file)
        print('Saved Updated Model:', new_model_file)

    return model

def modifyCoordinates(model_update, ik_result_dir,results_basename,newmodel): 
    
    # Setting the State
    table = osim.TimeSeriesTable(os.path.join(ik_result_dir, f'{results_basename}_secondary_constraint_settle_states.sto'))
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

    update_slack_lengths(model_update, new_model_file=newmodel)


def comak_ik_function(settings):
    # print('Starting COMAK Inverse Kinematics...')
    # osim.Logger.setLevelString('Trace')
    # osim.Logger.removeFileSink()
    # #make a log file with the current date and time
    # date_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    # osim.Logger.addFileSink(os.path.join(settings.path_log, f'comakIKlog_{date_time}.log'))

    # with open(settings.secondary_coord_file,'r') as f:
    #     secondary_coordinates = json.load(f)

    # # Set Output Files
    # secondary_constraint_function_file = os.path.join(settings.ik_result_dir, 'secondary_coordinate_constraint_functions.xml')
    # constrained_model_file = os.path.join(settings.model_dir, f'ik_constrained_model_initial_{settings.subjID}.osim')
    # save_xml_path = os.path.join(settings.inputs_dir, 'comak_inverse_kinematics_settings.xml')
    

    ## Step 1: First Settle Sim & Update Slack Length ##

    # Settings
    start_pad = 0.0
    
    perform_secondary_constraint_sim = True
    secondary_constraint_sim_settle_threshold = 1e-4 #1e-40
    secondary_constraint_sim_sweep_time = 0.00#1.0#3.0
    secondary_coupled_coordinate_start_value = 0
    secondary_coupled_coordinate_stop_value = 0
    secondary_constraint_sim_integrator_accuracy = 1e-3 #1e-2 #1e-3 #1e-2
    secondary_constraint_sim_internal_step_limit = 10_000
    constraint_function_num_interpolation_points = 60
    print_secondary_constraint_sim_results = True
    perform_inverse_kinematics = False #True

    report_errors = True
    report_marker_locations = False
    ik_constraint_weight = 100
    ik_accuracy = 1e-5
    use_visualizer = False
    
    PARAMS = {
        'SLACK_LENGTH': SLACK_LENGTH,
        'perform_secondary_constraint_sim': perform_secondary_constraint_sim,
        'secondary_constraint_sim_settle_threshold': secondary_constraint_sim_settle_threshold,
        'secondary_constraint_sim_sweep_time': secondary_constraint_sim_sweep_time,
        'secondary_coupled_coordinate_start_value': secondary_coupled_coordinate_start_value,
        'secondary_coupled_coordinate_stop_value': secondary_coupled_coordinate_stop_value,
        'secondary_constraint_sim_integrator_accuracy': secondary_constraint_sim_integrator_accuracy,
        'secondary_constraint_sim_internal_step_limit': secondary_constraint_sim_internal_step_limit,
        'constraint_function_num_interpolation_points': constraint_function_num_interpolation_points,
        'print_secondary_constraint_sim_results': print_secondary_constraint_sim_results,
        'perform_inverse_kinematics': perform_inverse_kinematics,
        'ik_constraint_weight': ik_constraint_weight,
        'ik_accuracy': ik_accuracy,
    }
    
    with open(os.path.join(settings.inputs_dir, 'IK_PARAMS.json'), 'w') as f:
        json.dump(PARAMS, f, indent=4)

    # comak_ik = osim.COMAKInverseKinematicsTool();
    # # comak_ik.set_model_file(model_file);
    # comak_ik.set_results_directory(settings.ik_result_dir);
    # comak_ik.set_results_prefix(settings.results_basename);
    # comak_ik.set_perform_secondary_constraint_sim(perform_secondary_constraint_sim);

    # for idx, (coord, dict_) in enumerate(secondary_coordinates.items()):
    #     comak_ik.set_secondary_coordinates(int(idx), dict_['coordinate'])

    # comak_ik.set_secondary_coupled_coordinate('/jointset/knee_r/knee_flex_r');
    # comak_ik.set_secondary_constraint_sim_settle_threshold(secondary_constraint_sim_settle_threshold);
    # comak_ik.set_secondary_constraint_sim_sweep_time(secondary_constraint_sim_sweep_time);
    # comak_ik.set_secondary_coupled_coordinate_start_value(secondary_coupled_coordinate_start_value);
    # comak_ik.set_secondary_coupled_coordinate_stop_value(secondary_coupled_coordinate_stop_value);
    # comak_ik.set_secondary_constraint_sim_integrator_accuracy(secondary_constraint_sim_integrator_accuracy);
    # comak_ik.set_secondary_constraint_sim_internal_step_limit(secondary_constraint_sim_internal_step_limit);
    # comak_ik.set_secondary_constraint_function_file(secondary_constraint_function_file);
    # comak_ik.set_constraint_function_num_interpolation_points(constraint_function_num_interpolation_points);
    # comak_ik.set_print_secondary_constraint_sim_results(print_secondary_constraint_sim_results);
    # comak_ik.set_constrained_model_file(constrained_model_file);
    # comak_ik.set_perform_inverse_kinematics(perform_inverse_kinematics);
    # comak_ik.set_marker_file(settings.markerset_file);
    
    # comak_ik.set_output_motion_file('comak_ik.mot');
    # comak_ik.set_time_range(0, settings.start_time_ik-start_pad);
    # comak_ik.set_time_range(1, settings.stop_time_ik);
    # comak_ik.set_report_errors(report_errors);
    # comak_ik.set_report_marker_locations(report_marker_locations);
    # comak_ik.set_ik_constraint_weight(ik_constraint_weight);
    # comak_ik.set_ik_accuracy(ik_accuracy);
    # comak_ik.set_use_visualizer(use_visualizer);

    # ik_task_set = comak_ik.get_IKTaskSet()

    # ik_task_set = osim.IKTaskSet()
    # ik_task = osim.IKMarkerTask()

    # comak_ik.set_IKTaskSet(ik_task_set)
    # comak_ik.printToXML(save_xml_path)

    count = 0
    # count = 1
    for count in range(settings.settleSimRep):
        print(f'Starting Settle Sim {count+1}...')
        if count == 0:
            print('First settle sim step - so, initializing slack lengths...')
            # get file to load
            model_file = settings.model_file  # THIS ISNT CURRENTLY USED
            # create new model file - to save updated slack lengths
            new_model_file = os.path.join(
                settings.model_dir, 
                f"{settings.subjID}_scaled_lenhart_model_updated_wrap_updSlack_intermediate.osim"
            )

            update_slack_lengths(
                model=model_file, 
                new_model_file=new_model_file, 
            )
            
            print('Finished Initializing Slack Lengths')
            print('\tUpdated Model:', new_model_file)

            # update model file path so all new steps use the updated model
            model_file = new_model_file

        # Run COMAK IK
        comak_ik.set_model_file(model_file)
        print('Running COMAKInverseKinematicsTool...')
        comak_ik.run()

        # Load the model 
        model_update_1 = osim.Model(model_file)

        # Update Coordinates & Ligament Slack Lengths
        if count + 1 == settings.settleSimRep:
            # set the final name for the model (to save)
            new_model_filepath = settings.upd_model_file
        else:
            if settings.settleSimUpd == True:       
                # set the intermediate model name (to save)         
                new_model_filepath = os.path.join(settings.model_dir, f'{settings.subjID}_scaled_lenhart_model_updated_wrap_updSlack_intermediate.osim')
            else:
                # skip - becuase not updating after settle sim - not sure why? 
                continue            
        # Pose the model in the settle sim position, then update the tendon slack lengths
        modifyCoordinates(model_update_1, settings.ik_result_dir, settings.results_basename, new_model_filepath)

    
    
    ## Step 3: Perform SWeep Sim & IK ##

    # Set Input Files
    # model_file = settings.upd_model_file

    # Set Output Files
    # secondary_constraint_function_file = os.path.join(settings.ik_result_dir, 'secondary_coordinate_constraint_functions_final.xml')
    # constrained_model_file = os.path.join(settings.ik_result_dir, f'{settings.subjID}_ik_constrained_model_final.osim')

    # secondary_constraint_sim_sweep_time = 3.0
    # secondary_coupled_coordinate_stop_value = 100 #100 
    # perform_inverse_kinematics = True

    # comak_ik.set_model_file(model_file)
    # comak_ik.set_constrained_model_file(constrained_model_file);
    # comak_ik.set_secondary_constraint_function_file(secondary_constraint_function_file);

    # comak_ik.set_secondary_constraint_sim_sweep_time(secondary_constraint_sim_sweep_time);
    # comak_ik.set_secondary_coupled_coordinate_stop_value(secondary_coupled_coordinate_stop_value);
    # comak_ik.set_perform_inverse_kinematics(perform_inverse_kinematics);

    print('Running COMAKInverseKinematicsTool...')
    comak_ik.run()  
