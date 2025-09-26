"""
Example showing how to use the new reference strain update methods
in the COMAKInverseKinematics class.
"""

from pycomak import COMAKInverseKinematics


def example_update_reference_strains():
    """Example of updating ligament reference strains before running COMAK IK"""
    
    # Initialize COMAK IK
    comak_ik = COMAKInverseKinematics(
        base_model_path="path/to/your/model.osim",
        results_dir="path/to/results",
        stop_time_ik=1.0,
        start_time_ik=0.0,
        markerset_file="path/to/markers.trc",
        settle_sim_reps=3
    )
    
    # View current ligament reference strains
    print("Current ligament reference strains:")
    current_strains = comak_ik.get_ligament_reference_strains()
    for ligament, strain in current_strains.items():
        print(f"  {ligament}: {strain}")
    
    # Update a single ligament reference strain
    comak_ik.update_ligament_reference_strain('MCLd1', 0.06)
    
    # Update multiple ligaments at once
    strain_updates = {
        'ACLpl1': 0.04,
        'PCLal1': 0.02,
        'PT1': 0.025
    }
    comak_ik.update_multiple_ligament_reference_strains(strain_updates)
    
    # View updated strains
    print("\nUpdated ligament reference strains:")
    updated_strains = comak_ik.get_ligament_reference_strains()
    for ligament, strain in updated_strains.items():
        if ligament in ['MCLd1', 'ACLpl1', 'PCLal1', 'PT1']:
            print(f"  {ligament}: {strain} (UPDATED)")
        else:
            print(f"  {ligament}: {strain}")
    
    # Run the COMAK IK process with updated reference strains
    comak_ik.perform_settle_sim()
    comak_ik.perform_sweep_sim()
    comak_ik.perform_inverse_kinematics()
    
    # Reset to defaults if needed
    # comak_ik.reset_to_default_reference_strains()


def example_parameter_sweep():
    """Example of running COMAK IK with different reference strain values"""
    
    # Test different PT reference strain values
    pt_strain_values = [0.015, 0.020, 0.025, 0.030]
    
    for pt_strain in pt_strain_values:
        print(f"\n=== Running with PT strain = {pt_strain} ===")
        
        comak_ik = COMAKInverseKinematics(
            base_model_path="path/to/your/model.osim",
            results_dir=f"results_pt_strain_{pt_strain}",
            stop_time_ik=1.0,
            start_time_ik=0.0,
            markerset_file="path/to/markers.trc",
            settle_sim_reps=2
        )
        
        # Update all PT ligament strains
        pt_updates = {f'PT{i}': pt_strain for i in range(1, 7)}
        comak_ik.update_multiple_ligament_reference_strains(pt_updates)
        
        # Run simulation
        comak_ik.perform_settle_sim()
        # ... continue with sweep and IK as needed


if __name__ == "__main__":
    # Run examples
    print("Reference strain update examples:")
    # example_update_reference_strains()
    # example_parameter_sweep()
    print("Examples complete!")



