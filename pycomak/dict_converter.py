"""
Utility functions to convert between pycomak and nsosim dictionary formats
for the update_slack_lengths function.
"""
import opensim as osim


def convert_to_nsosim_format(model, slack_length_dict, muscle_length_dict):
    """
    Convert pycomak's separate dictionaries to nsosim's unified format.
    
    Args:
        model (osim.Model or str): OpenSim model to get current lengths from
        slack_length_dict (dict): Ligament name -> reference strain mapping
        muscle_length_dict (dict): Muscle name -> reference length mapping
    
    Returns:
        dict: Unified force_length_dict in nsosim format
    """
    if isinstance(model, str):
        model = osim.Model(model)
    
    state = model.initSystem()
    forces = model.getForceSet()
    
    force_length_dict = {}
    
    # Process all forces in the model
    for i in range(forces.getSize()):
        force_ = forces.get(i)
        force_name = force_.getName()
        
        if force_.getConcreteClassName() == 'Millard2012EquilibriumMuscle':
            # Only include muscles that are in our muscle_length_dict
            if force_name in muscle_length_dict:
                muscle = osim.Millard2012EquilibriumMuscle.safeDownCast(force_)
                force_length_dict[force_name] = {
                    'class': 'Millard2012EquilibriumMuscle',
                    'length': muscle_length_dict[force_name],  # Reference length
                    'reference_strain': None,
                    'slack_length': None
                }
                
        elif force_.getConcreteClassName() == 'Blankevoort1991Ligament':
            # Only include ligaments that are in our slack_length_dict
            if force_name in slack_length_dict:
                ligament = osim.Blankevoort1991Ligament.safeDownCast(force_)
                current_length = ligament.getLength(state)
                current_slack_length = ligament.get_slack_length()
                
                force_length_dict[force_name] = {
                    'class': 'Blankevoort1991Ligament',
                    'length': current_length,
                    'reference_strain': slack_length_dict[force_name],
                    'slack_length': current_slack_length
                }
    
    return force_length_dict


def create_nsosim_defaults(model_path):
    """
    Create nsosim-format defaults from current pycomak defaults.
    
    Args:
        model_path (str): Path to OpenSim model file
        
    Returns:
        dict: force_length_dict in nsosim format
    """
    from pycomak.defaults import slack_length_dict, muscle_length_dict
    
    return convert_to_nsosim_format(model_path, slack_length_dict, muscle_length_dict)



