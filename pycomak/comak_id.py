import os
import json

import opensim as osim
from pycomak import COMAKBASE

class COMAKInverseDynamics(COMAKBASE):
    """
    A class to perform inverse dynamics using OpenSim's InverseDynamicsTool,
    configured for use within the COMAK workflow.

    This class sets up the InverseDynamicsTool with specified parameters,
    saves the settings to XML and JSON files, and provides a method to run
    the inverse dynamics analysis.
    """
    def __init__(
        self,
        results_dir,
        start_time,
        stop_time,
        model_path,
        external_loads_file,
        low_pass_cutoff=6,
        
    ):
        """
        Initializes the COMAKInverseDynamics class.

        Args:
            results_dir (str): Directory to save the results.
            start_time (float): Start time for the analysis.
            stop_time (float): Stop time for the analysis.
            model_path (str): Path to the OpenSim model file (.osim).
            external_loads_file (str): Path to the external loads file.
            low_pass_cutoff (float, optional): Cutoff frequency for the low-pass
                filter applied to coordinates. Defaults to 6.
        """
        super().__init__(results_dir)
        
        save_xml_path = os.path.join(self.inputs_dir, 'comak_inverse_dynamics_settings.xml')
        
        self.start_time = start_time
        self.stop_time = stop_time
        
        self.inverse_dynamics = osim.InverseDynamicsTool()
        self.inverse_dynamics.set_results_directory(self.id_result_dir)
        self.inverse_dynamics.setModelFileName(model_path)
        self.inverse_dynamics.setStartTime(self.start_time)
        self.inverse_dynamics.setEndTime(self.stop_time)
        
        exclude_frc = osim.ArrayStr()
        exclude_frc.append('ALL')

        self.inverse_dynamics.setExcludedForces(exclude_frc)

        self.inverse_dynamics.setExternalLoadsFileName(external_loads_file)
        self.inverse_dynamics.setCoordinatesFileName(os.path.join(self.comak_result_dir, '_values.sto'))
        self.inverse_dynamics.setLowpassCutoffFrequency(low_pass_cutoff)
        self.inverse_dynamics.setOutputGenForceFileName(self.comak_id_results_filename)

        self.inverse_dynamics.printToXML(save_xml_path)

        # aggregate all the settings in a dictionary and save it
        # as a json file in the inputs directory
        settings = {
            'start_time': self.start_time,
            'stop_time': self.stop_time,
            'model_path': model_path,
            'external_loads_file': external_loads_file,
            'low_pass_cutoff': low_pass_cutoff
        }
        with open(os.path.join(self.inputs_dir, 'comak_inverse_dynamics_settings.json'), 'w') as f:
            json.dump(settings, f, indent=4)
            
    def run(self):
        """
        Runs the inverse dynamics analysis.

        Prints a message indicating the start and end times of the analysis
        before executing the OpenSim InverseDynamicsTool's run method.
        """
        print(f"Running Inverse Dynamics from {self.start_time} to {self.stop_time}")
        self.inverse_dynamics.run()
        
        
