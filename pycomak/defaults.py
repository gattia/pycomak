import numpy as np
prescribed_coordinates = {
    "0" : "/jointset/gnd_pelvis/pelvis_tx",
    "1" : "/jointset/gnd_pelvis/pelvis_ty",
    "2" : "/jointset/gnd_pelvis/pelvis_tz",
    "3" : "/jointset/gnd_pelvis/pelvis_tilt",
    "4" : "/jointset/gnd_pelvis/pelvis_list",
    "5" : "/jointset/gnd_pelvis/pelvis_rot",
    "6" : "/jointset/subtalar_r/subt_angle_r",
    "7" : "/jointset/mtp_r/mtp_angle_r",
    "8" : "/jointset/hip_l/hip_flex_l",
    "9" : "/jointset/hip_l/hip_add_l",
    "10" : "/jointset/hip_l/hip_rot_l",
    "11" : "/jointset/pf_l/pf_l_r3",
    "12" : "/jointset/pf_l/pf_l_tx",
    "13" : "/jointset/pf_l/pf_l_ty",
    "14" : "/jointset/knee_l/knee_flex_l",
    "15" : "/jointset/ankle_l/ankle_flex_l",
    "16" : "/jointset/subtalar_l/subt_angle_l",
    "17" : "/jointset/mtp_l/mtp_angle_l",
    "18" : "/jointset/pelvis_torso/lumbar_ext",
    "19" : "/jointset/pelvis_torso/lumbar_latbend",
    "20" : "/jointset/pelvis_torso/lumbar_rot",
    "21" : "/jointset/torso_neckhead/neck_ext",
    "22" : "/jointset/torso_neckhead/neck_latbend",
    "23" : "/jointset/torso_neckhead/neck_rot",
    "24" : "/jointset/acromial_r/arm_add_r",
    "25" : "/jointset/acromial_r/arm_flex_r",
    "26" : "/jointset/acromial_r/arm_rot_r",
    "27" : "/jointset/elbow_r/elbow_flex_r",
    "28" : "/jointset/radioulnar_r/pro_sup_r",
    "29" : "/jointset/radius_hand_r/wrist_flex_r",
    "30" : "/jointset/acromial_l/arm_add_l",
    "31" : "/jointset/acromial_l/arm_flex_l",
    "32" : "/jointset/acromial_l/arm_rot_l",
    "33" : "/jointset/elbow_l/elbow_flex_l",
    "34" : "/jointset/radioulnar_l/pro_sup_l",
    "35" : "/jointset/radius_hand_l/wrist_flex_l"
}

primary_coordinates = {
    "0": "/jointset/hip_r/hip_flex_r",
    "1": "/jointset/hip_r/hip_add_r",
    "2": "/jointset/hip_r/hip_rot_r",
    "3": "/jointset/knee_r/knee_flex_r",
    "4": "/jointset/ankle_r/ankle_flex_r"
}

secondary_coordinates = {
    # Knee kinematics (rotations and translations)
    "knee_add_r": {"max_change": 0.005, "coordinate": "/jointset/knee_r/knee_add_r"},
    "knee_rot_r": {"max_change": 0.005, "coordinate": "/jointset/knee_r/knee_rot_r"},
    "knee_tx_r": {"max_change": 0.001, "coordinate": "/jointset/knee_r/knee_tx_r"},
    "knee_ty_r": {"max_change": 0.001, "coordinate": "/jointset/knee_r/knee_ty_r"},
    "knee_tz_r": {"max_change": 0.001, "coordinate": "/jointset/knee_r/knee_tz_r"},
    # Patella kinematics (rotations and translations)
    "pf_flex_r": {"max_change": 0.005, "coordinate": "/jointset/pf_r/pf_flex_r"},
    "pf_rot_r": {"max_change": 0.005, "coordinate": "/jointset/pf_r/pf_rot_r"},
    "pf_tilt_r": {"max_change": 0.005, "coordinate": "/jointset/pf_r/pf_tilt_r"},
    "pf_tx_r": {"max_change": 0.001, "coordinate": "/jointset/pf_r/pf_tx_r"},
    "pf_ty_r": {"max_change": 0.001, "coordinate": "/jointset/pf_r/pf_ty_r"},
    "pf_tz_r": {"max_change": 0.001, "coordinate": "/jointset/pf_r/pf_tz_r"},
    # Medial meniscus kinematics (rotations and translations)
    "meniscus_medial_flex_r": {"max_change": 0.005, "coordinate": "/jointset/meniscus_medial_r/meniscus_medial_flex_r"},
    "meniscus_medial_rot_r": {"max_change": 0.005, "coordinate": "/jointset/meniscus_medial_r/meniscus_medial_rot_r"},
    "meniscus_medial_add_r": {"max_change": 0.005, "coordinate": "/jointset/meniscus_medial_r/meniscus_medial_add_r"},
    "meniscus_medial_tx_r": {"max_change": 0.001, "coordinate": "/jointset/meniscus_medial_r/meniscus_medial_tx_r"},
    "meniscus_medial_ty_r": {"max_change": 0.001, "coordinate": "/jointset/meniscus_medial_r/meniscus_medial_ty_r"},
    "meniscus_medial_tz_r": {"max_change": 0.001, "coordinate": "/jointset/meniscus_medial_r/meniscus_medial_tz_r"},
    # Lateral meniscus kinematics (rotations and translations)
    "meniscus_lateral_flex_r": {"max_change": 0.005, "coordinate": "/jointset/meniscus_lateral_r/meniscus_lateral_flex_r"},
    "meniscus_lateral_rot_r": {"max_change": 0.005, "coordinate": "/jointset/meniscus_lateral_r/meniscus_lateral_rot_r"},
    "meniscus_lateral_add_r": {"max_change": 0.005, "coordinate": "/jointset/meniscus_lateral_r/meniscus_lateral_add_r"},
    "meniscus_lateral_tx_r": {"max_change": 0.001, "coordinate": "/jointset/meniscus_lateral_r/meniscus_lateral_tx_r"},
    "meniscus_lateral_ty_r": {"max_change": 0.001, "coordinate": "/jointset/meniscus_lateral_r/meniscus_lateral_ty_r"},
    "meniscus_lateral_tz_r": {"max_change": 0.001, "coordinate": "/jointset/meniscus_lateral_r/meniscus_lateral_tz_r"},
    
}


slack_length_dict = {'MCLd1':0.04,'MCLd2':-0.04,'MCLd3':0.0,'MCLd4':0.04,'MCLd5':0.04,
                    'MCLs1':0.04,'MCLs2':0.04,'MCLs3':0.05,'MCLs4':0.05,'MCLs5':0.05,'MCLs6':0.05,
                    'ACLpl1':0.03,'ACLpl2':0.01,'ACLpl3':-0.05,'ACLpl4':-0.12,'ACLpl5':-0.02,'ACLpl6':-0.03,
                    'ACLam1':-0.14,'ACLam2':-0.05,'ACLam3':-0.08,'ACLam4':-0.14,'ACLam5':-0.14,'ACLam6':-0.12,
                    'PCLal1':0.03,'PCLal2':-0.1,'PCLal3':0.03,'PCLal4':-0.04,'PCLal5':-0.02,
                    'PCLpm1':-0.05,'PCLpm2':-0.12,'PCLpm3':-0.08,'PCLpm4':-0.12,'PCLpm5':-0.1,
                    'LCL1':0.06,'LCL2':0.06,'LCL3':0.06,'LCL4':0.06,
                    
                    'PT1':0.02,
                    'PT2':0.02,
                    'PT3':0.02,
                    'PT4':0.02,
                    'PT5':0.02,
                    'PT6':0.02,
                    
                    'lPFL1':0.01,'lPFL2':-0.1,'lPFL3':0.01,'lPFL4':-0.12,'lPFL5':0.01,'lPFL6':0.01,'lPFL7':-0.08,'lPFL8':-0.08,
                    'mPFL1':-0.05,'mPFL2':0.01,'mPFL3':0.01,'mPFL4':-0.06,'mPFL5':-0.03,'mPFL6':0.01,
                    'MCLp1':0.05,'MCLp2':0.05,'MCLp3':0.02,'MCLp4':-0.02,'MCLp5':0.05,
                    'PFL1':0.01,'PFL2':-0.12,'PFL3':-0.03,'PFL4':-0.14,'PFL5':-0.1,
                    'pCAP1':0.04,'pCAP2':0.04,'pCAP3':0.04,'pCAP4':0.03,'pCAP5':0.04,'pCAP6':0.04,'pCAP7':0.04,'pCAP8':0.04,
                    'ITB1':0.02} 

# lenhart2015 osim muscle lengths
muscle_length_dict = {'addbrev_r': 0.14196569529280523,
    'addlong_r': 0.23173330804979062,
    'addmagProx_r': 0.12213388076394897,
    'addmagMid_r': 0.13563520428000195,
    'addmagDist_r': 0.20321321314484678,
    'addmagIsch_r': 0.3080344961751358,
    'bflh_r': 0.37880967257019954,
    'bfsh_r': 0.22398432847854888,
    'edl_r': 0.4409234378087697,
    'ehl_r': 0.40785104855414667,
    'fdl_r': 0.4274734783595246,
    'fhl_r': 0.40807465638869356,
    'gaslat_r': 0.4440216273355755,
    'gasmed_r': 0.4519788482822444,
    'gem_r': 0.06884986382678986,
    'glmax1_r': 0.20077207750300657,
    'glmax2_r': 0.22687570387437456,
    'glmax3_r': 0.22689858797363516,
    'glmed1_r': 0.12489193169744166,
    'glmed2_r': 0.13665693255382516,
    'glmed3_r': 0.11883810637975158,
    'glmin1_r': 0.0816316242615008,
    'glmin2_r': 0.08275663184296343,
    'glmin3_r': 0.08971812932914208,
    'grac_r': 0.4065791175021344,
    'iliacus_r': 0.21783284847135825,
    'pect_r': 0.10631198270106394,
    'perbrev_r': 0.19728868722786433,
    'perlong_r': 0.3891309655551033,
    'pertert_r': 0.18073471337793937,
    'piri_r': 0.15276079396991796,
    'psoas_r': 0.2406669693773934,
    'quadfem_r': 0.0724648700366977,
    'recfem_r': 0.40105048061270326,
    'sart_r': 0.5614783918207071,
    'semimem_r': 0.37920697331727504,
    'semiten_r': 0.4209187887384535,
    'soleus_r': 0.3255053326433204,
    'tfl_r': 0.5225831437146169,
    'tibant_r': 0.3084001442615228,
    'tibpost_r': 0.3224557582356099,
    'vasint_r': 0.17614838512977013,
    'vaslat_r': 0.1905789024047313,
    'vasmed_r': 0.16580181536888208
}



"""
Colin Smith Thesis: 
Chapter 2: Probabilistic Simulation of Knee Mechanics
during Walking using Concurrent Optimization of Muscle 
Activations and Kinematics (COMAK)

Table 3: Nominal muscle weights used in COMAK objective
function. 
med gastroc: 4
lat gastroc: 7
hamstrings: 2
rectus femoris: 3
soleus: 0.9
glut med: 0.9
glut min: 0.9

However, based on the text in this paper, and on the
results from DeMers it seems like: 
- Hamstrings has little effect - and should maybe go
in the < 1 direction
- Soleus has little effect (in the < 1 direction)

Therefore, we use the following scheme. 
"""

muscle_weights_dict = {
    # calves
    'gasmed_r': 4,
    'gaslat_r': 7,
    'soleus_r': 0.9,
    # quads
    'recfem_r': 3,
    # glutes
    'glmed1_r': 0.9,
    'glmed2_r': 0.9,
    'glmed3_r': 0.9,
    'glmin1_r': 0.9,
    'glmin2_r': 0.9,
    'glmin3_r': 0.9,
    # hamstrings
    # 'bflh_r': 0.9,
    # 'bfsh_r': 0.9,
    # 'semiten_r': 0.9,
    # 'semimem_r': 0.9
}

# PATELLA HEIGHT OPTIMIZATION DEFAULTS

# criteria used to determine if patella height
# should be adjusted
patella_optimization_criteria = {
    'ligaments': {
        'PT': {},#{'max_range': 1400, 'max': 1400},
        'ACL': {},#{'max_range': 300, 'max': 300},
        'MCL': {},
        'LCL': {},
        'PCL': {},
        'mPFL': {},
        'lPFL': {},
        
    },
    'coords': {
        'pf_tx_r': {'max_range': 0.004},
        'pf_ty_r': {},
        'pf_tz_r': {},
        'pf_flex_r': {},
        'pf_rot_r': {},
        'pf_tilt_r': {},
    }
}

# DEFAULT FORSIM PRESCRIBED KINEMATICS & MUSCLE ACTIVATIONS
"""
This creates a simulation that is 0.2s long, with a time
step of 0.01s. The knee flexes from 0 to 5 degrees, and
the pelvis is tilted 90 degrees (laying down). The muscle
activations are linearly increased from 0 to 0.25 over
the duration of the simulation.

This is used to prescribe kinematics and muscle activations
for the forsim simulation, and these parameters were shown 
to dislocate the patella in similar ways to what was seen
for dislocations during gait. 
"""

# Create time vector for forsim simulations
duration = 0.2
time_step = 0.01
time_ = np.arange(0, duration + time_step, time_step)

# Create kinematics to prescribe for forsim simulations
max_knee_flex = 5
knee_flex = np.linspace(0, max_knee_flex, len(time_))

pelvis_tilt = np.ones(len(time_)) * 90

forsim_patella_optimization_kinematics = {
    'time': time_,
    'knee_flex_r': knee_flex,
    'pelvis_tilt': pelvis_tilt
}

# Create muscle activations to prescribe for forsim simulations
list_musccles = [
    'recfem_r', 'vasint_r', 'vaslat_r', 'vasmed_r',
    'bflh_r', 'bfsh_r', 'semimem_r', 'semiten_r',
    'sart_r', 'gaslat_r', 'gasmed_r'
]
muscle_parameter = 'activation'
max_activation = 0.6
activation = np.linspace(0, max_activation, len(time_))

forsim_patella_optimization_muscle_activations = {'time': time_}
for muscle in list_musccles:
    forsim_patella_optimization_muscle_activations[f'{muscle}_{muscle_parameter}'] = activation