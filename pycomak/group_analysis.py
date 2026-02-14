"""
Group-level JAM Analysis Module

This module provides classes and functions for performing group-level analysis
of Joint and Articular Mechanics (JAM) simulation results. It builds on top
of the JamAnalysis class to enable:
  - Multi-subject analysis
  - Group comparisons (e.g., healthy vs OA)
  - Statistical summaries (mean, std, individual traces)
  - Standardized plotting
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import opensim as osim
from typing import Dict, List, Tuple, Optional, Union
from .jam_analysis import JamAnalysis


def extract_opensim_constraint_functions(constraint_function_file: str) -> Dict[str, Dict[str, np.ndarray]]:
    """
    Extract constraint functions from OpenSim FunctionSet XML file.
    
    These are typically secondary coordinate constraint functions from COMAK IK.
    
    Args:
        constraint_function_file: Path to the constraint functions XML file
        
    Returns:
        Dictionary with constraint names as keys, each containing 'X' and 'Y' arrays
    """
    func_set = osim.FunctionSet(constraint_function_file)
    constraint_funcs = {}
    
    for i in range(func_set.getSize()):
        func = osim.SimmSpline.safeDownCast(func_set.get(i))
        name = func.getName()
        
        X = np.zeros(func.getNumberOfPoints())
        Y = np.zeros(func.getNumberOfPoints())
        
        for pt_idx in range(func.getNumberOfPoints()):
            X[pt_idx] = func.getX(pt_idx)
            Y[pt_idx] = func.getY(pt_idx)
        
        constraint_funcs[name] = {
            'X': X,
            'Y': Y
        }
    
    return constraint_funcs


def extract_opensim_table(table) -> pd.DataFrame:
    """
    Convert OpenSim TimeSeriesTable to pandas DataFrame.
    
    Args:
        table: OpenSim TimeSeriesTable object
        
    Returns:
        Pandas DataFrame with time as first column
    """
    data_array = table.getMatrix().to_numpy()
    colnames = table.getColumnLabels()
    time = np.asarray(table.getIndependentColumn())
    
    df = pd.DataFrame()
    df['time'] = time
    for idx, col_name in enumerate(colnames):
        df[col_name] = data_array[:, idx]
    
    return df


class GroupJamAnalysis:
    """
    Manager for group-level JAM analysis across multiple subjects.
    
    This class organizes multiple subjects into groups (e.g., healthy, OA, progressors)
    and provides methods to extract and visualize data across groups.
    
    Attributes:
        groups: Dictionary of groups, each containing subject info and JamAnalysis objects
        base_results_dir: Base directory containing simulation results
        comak_subfolder: Subfolder name for COMAK results (default: 'comak_results')
    """
    
    def __init__(
        self, 
        base_results_dir: str, 
        comak_subfolder: str = 'comak_results',
        timepoint: str = '00m'
    ):
        """
        Initialize GroupJamAnalysis.
        
        Args:
            base_results_dir: Base directory containing simulation results
            comak_subfolder: Subfolder name for COMAK results (default: 'comak_results')
            timepoint: Timepoint identifier for subject folders (default: '00m')
                      Set to empty string '' if not used in your folder structure
        """
        self.groups = {}
        self.base_results_dir = base_results_dir
        self.comak_subfolder = comak_subfolder
        self.timepoint = timepoint
        
    def add_subject(
        self, 
        subject_id: str, 
        side: str, 
        datetime: str, 
        group: str = 'default',
        run_jam: bool = True,
        results_folder: Optional[str] = None,
        h5_file_path: Optional[str] = None,
        subject_folder_pattern: Optional[str] = None,
        timepoint: Optional[str] = None,
        filter_data: bool = True,
        contact_types: Optional[List[str]] = None,
        cartilages: Optional[List[str]] = None,
        regions: Optional[List[int]] = None,
        contact_outcomes: Optional[List[str]] = None,
        muscle_outcomes: Optional[List[str]] = None,
        ligament_outcomes: Optional[List[str]] = None
    ):
        """
        Add a subject to the analysis.
        
        Args:
            subject_id: Subject identifier (e.g., '9003175')
            side: Limb side ('LEFT' or 'RIGHT')
            datetime: Datetime string for the simulation run
            group: Group name (e.g., 'healthy', 'OA', 'progressors')
            run_jam: Whether to run JAM analysis immediately
            results_folder: Direct path to results folder (overrides automatic construction)
            h5_file_path: Direct path to .h5 file (overrides everything else)
            subject_folder_pattern: Custom pattern for subject folder. Use {subject_id}, {side}, 
                                   and {timepoint} as placeholders. 
                                   Default: '{subject_id}_{timepoint}_{side}'
            timepoint: Timepoint identifier (overrides class default). Use '' for no timepoint.
            filter_data: If True, filter JAM data to reduce memory usage (default: True).
                        This is critical for large datasets - without filtering, pickle files
                        can be 100+ GB instead of ~500 MB.
            contact_types: Contact types to keep (default: ['tf_contact'])
            cartilages: Cartilage surfaces to keep (default: ['tibia_cartilage'])
            regions: Region indices to keep (default: [4, 5] for medial/lateral tibia)
            contact_outcomes: Contact outcomes to keep (default: regional pressures, area, force)
            muscle_outcomes: Muscle outcomes to keep (default: ['actuation']).
                           Set to None to keep all muscle outcomes.
            ligament_outcomes: Ligament outcomes to keep (default: None = keep all).
            
        Returns:
            True if successful, False if simulation files not found
            
        Examples:
            # Standard structure (automatic with default timepoint '00m'):
            add_subject('9003175', 'RIGHT', '2025-08-21_21-33-10')
            # Uses: base_results/9003175_00m_RIGHT/comak_results/2025-08-21_21-33-10/
            
            # Different timepoint:
            add_subject('9003175', 'RIGHT', '2025-08-21_21-33-10', timepoint='12m')
            # Uses: base_results/9003175_12m_RIGHT/...
            
            # No timepoint:
            add_subject('9003175', 'RIGHT', '2025-08-21_21-33-10', timepoint='')
            # Uses: base_results/9003175_RIGHT/...
            
            # Custom subject folder pattern:
            add_subject('9003175', 'RIGHT', '2025-08-21_21-33-10',
                       subject_folder_pattern='{side}_{subject_id}')
            
            # Direct results folder path:
            add_subject('9003175', 'RIGHT', '2025-08-21_21-33-10',
                       results_folder='/path/to/my/custom/results/folder')
            
            # Direct h5 file path (most flexible):
            add_subject('9003175', 'RIGHT', 'run1', 
                       h5_file_path='/path/to/my/file.h5')
            
            # Without filtering (WARNING: large memory usage):
            add_subject('9003175', 'RIGHT', 'run1', filter_data=False)
            
            # Include patellofemoral contact data:
            add_subject('9003175', 'RIGHT', 'run1',
                       contact_types=['tf_contact', 'pf_contact'],
                       cartilages=['tibia_cartilage', 'patella_cartilage'])
        """
        # Use provided timepoint or fall back to class default
        if timepoint is None:
            timepoint = self.timepoint
        
        # Determine h5 file path
        if h5_file_path is not None:
            # Direct h5 file path provided - use it
            h5_file = h5_file_path
            # Try to infer results folder from h5 path (parent of joint-mechanics)
            if 'joint-mechanics' in h5_file:
                folder_results = os.path.dirname(os.path.dirname(h5_file))
            else:
                folder_results = os.path.dirname(h5_file)
        
        elif results_folder is not None:
            # Direct results folder provided
            folder_results = results_folder
            h5_file = os.path.join(folder_results, 'joint-mechanics', 'joint_mechanics.h5')
            if not os.path.exists(h5_file):
                h5_file = os.path.join(folder_results, 'joint-mechanics', '.h5')  # legacy
        
        else:
            # Auto-construct path using pattern
            if subject_folder_pattern is None:
                # Build default pattern based on timepoint
                if timepoint:
                    subject_folder_pattern = '{subject_id}_{timepoint}_{side}'
                else:
                    subject_folder_pattern = '{subject_id}_{side}'
            
            subject_folder = subject_folder_pattern.format(
                subject_id=subject_id,
                side=side,
                timepoint=timepoint
            )
            
            folder_results = os.path.join(
                self.base_results_dir, 
                subject_folder,
                self.comak_subfolder, 
                datetime
            )
            
            h5_file = os.path.join(folder_results, 'joint-mechanics', 'joint_mechanics.h5')
            if not os.path.exists(h5_file):
                h5_file = os.path.join(folder_results, 'joint-mechanics', '.h5')  # legacy
        
        # Check if h5 file exists
        if not os.path.exists(h5_file):
            print(f"Warning: H5 file not found: {h5_file}")
            return False
        
        # Initialize group if needed
        if group not in self.groups:
            self.groups[group] = {
                'subjects': [],
                'subject_ids': [],
                'jam_list': []
            }
        
        # Store subject info
        subject_info = {
            'subject_id': subject_id,
            'side': side,
            'datetime': datetime,
            'folder_results': folder_results,
            'h5_file': h5_file
        }
        
        self.groups[group]['subjects'].append(subject_info)
        self.groups[group]['subject_ids'].append(f"{subject_id}_{side}")
        
        # Run JAM analysis
        if run_jam:
            jam = JamAnalysis()
            jam.jam_analysis([h5_file])
            
            # Apply filtering to reduce memory usage
            if filter_data:
                self._filter_jam_data(
                    jam,
                    contact_types=contact_types,
                    cartilages=cartilages,
                    regions=regions,
                    contact_outcomes=contact_outcomes,
                    muscle_outcomes=muscle_outcomes,
                    ligament_outcomes=ligament_outcomes
                )
            
            self.groups[group]['jam_list'].append(jam)
        
        return True
    
    def _filter_jam_data(
        self,
        jam: 'JamAnalysis',
        contact_types: Optional[List[str]] = None,
        cartilages: Optional[List[str]] = None,
        regions: Optional[List[int]] = None,
        contact_outcomes: Optional[List[str]] = None,
        muscle_outcomes: Optional[List[str]] = None,
        ligament_outcomes: Optional[List[str]] = None
    ):
        """
        Filter JAM data to reduce memory usage.
        
        This removes unused data from the JAM object, keeping only what's needed
        for typical analyses (contact mechanics, muscle forces, kinematics).
        Without filtering, pickle files can be 100+ GB. With filtering, they're ~500 MB.
        
        Default settings match the OARSI analysis workflow:
        - Contact: tf_contact, tibia_cartilage, regions 4 & 5, pressure/area/force outcomes
        - Muscles: only 'actuation' outcome
        - Ligaments: keep all (total_force is primary outcome)
        - Coordinates: keep all (kinematics data is small)
        
        Args:
            jam: JamAnalysis object to filter
            contact_types: Contact types to keep (default: ['tf_contact'])
            cartilages: Cartilage surfaces to keep (default: ['tibia_cartilage'])
            regions: Region indices to keep (default: [4, 5] for medial/lateral tibia)
            contact_outcomes: Contact outcomes to keep 
                (default: regional_max_pressure, regional_mean_pressure, 
                 regional_contact_area, regional_contact_force)
            muscle_outcomes: Muscle outcomes to keep (default: ['actuation'])
                           Set to None to keep all muscle outcomes.
            ligament_outcomes: Ligament outcomes to keep (default: None = keep all)
        """
        # Set defaults matching previous OARSI analysis
        contact_types = contact_types if contact_types is not None else ['tf_contact']
        cartilages = cartilages if cartilages is not None else ['tibia_cartilage']
        regions = regions if regions is not None else [4, 5]
        contact_outcomes = contact_outcomes if contact_outcomes is not None else [
            'regional_max_pressure', 
            'regional_mean_pressure', 
            'regional_contact_area',
            'regional_contact_force'
        ]
        # Default muscle_outcomes to ['actuation'] - but allow None to skip filtering
        if muscle_outcomes is None:
            muscle_outcomes = ['actuation']
        # ligament_outcomes = None means keep all ligament data (no filtering)
        
        # Filter Smith2018ArticularContactForce (the big memory hog)
        if 'Smith2018ArticularContactForce' in jam.forceset:
            original_contact = jam.forceset['Smith2018ArticularContactForce']
            filtered_contact = {}
            
            for contact_type in contact_types:
                if contact_type not in original_contact:
                    continue
                filtered_contact[contact_type] = {}
                
                for cartilage in cartilages:
                    if cartilage not in original_contact[contact_type]:
                        continue
                    src = original_contact[contact_type][cartilage]
                    filtered_contact[contact_type][cartilage] = {}
                    
                    # Keep total_contact_force if present
                    if 'total_contact_force' in src:
                        filtered_contact[contact_type][cartilage]['total_contact_force'] = src['total_contact_force']
                    
                    # Keep only specified regions and outcomes
                    for region in regions:
                        if region in src:
                            filtered_contact[contact_type][cartilage][region] = {}
                            for outcome in contact_outcomes:
                                if outcome in src[region]:
                                    filtered_contact[contact_type][cartilage][region][outcome] = src[region][outcome]
            
            jam.forceset['Smith2018ArticularContactForce'] = filtered_contact
        
        # Filter Muscle data (keep only specified outcomes)
        if muscle_outcomes and 'Muscle' in jam.forceset:
            original_muscles = jam.forceset['Muscle']
            filtered_muscles = {}
            
            for muscle_name, muscle_data in original_muscles.items():
                filtered_muscles[muscle_name] = {}
                for outcome in muscle_outcomes:
                    if outcome in muscle_data:
                        filtered_muscles[muscle_name][outcome] = muscle_data[outcome]
            
            jam.forceset['Muscle'] = filtered_muscles
        
        # Filter Ligament data (optional - by default keep all)
        if ligament_outcomes and 'Blankevoort1991Ligament' in jam.forceset:
            original_ligaments = jam.forceset['Blankevoort1991Ligament']
            filtered_ligaments = {}
            
            for lig_name, lig_data in original_ligaments.items():
                filtered_ligaments[lig_name] = {}
                for outcome in ligament_outcomes:
                    if outcome in lig_data:
                        filtered_ligaments[lig_name][outcome] = lig_data[outcome]
            
            jam.forceset['Blankevoort1991Ligament'] = filtered_ligaments
        
        # Note: coordinateset is kept in full (kinematics data is relatively small)
    
    def add_subjects_from_list(
        self, 
        subjects_list: List[Tuple[str, str, str]], 
        group: str = 'default'
    ):
        """
        Add multiple subjects from a list.
        
        Args:
            subjects_list: List of (subject_id, side, datetime) tuples
            group: Group name for all subjects
            
        Returns:
            Tuple of (successful_count, failed_subjects_list)
        """
        failed = []
        success_count = 0
        
        for subject_id, side, datetime in subjects_list:
            success = self.add_subject(subject_id, side, datetime, group)
            if success:
                success_count += 1
            else:
                failed.append((subject_id, side, datetime))
        
        print(f"Added {success_count}/{len(subjects_list)} subjects to group '{group}'")
        
        return success_count, failed
    
    def load_secondary_constraints(self):
        """
        Load secondary coordinate constraint functions for all subjects.
        
        This loads the constraint functions from COMAK IK that define secondary
        kinematics as functions of primary coordinates.
        """
        for group_name, group_dict in self.groups.items():
            for subject_idx, subject_info in enumerate(group_dict['subjects']):
                folder_results = subject_info['folder_results']
                ik_result_dir = os.path.join(folder_results, 'comak-inverse-kinematics')
                constraint_file = os.path.join(
                    ik_result_dir, 
                    'secondary_coordinate_constraint_functions_final.xml'
                )
                
                if not os.path.exists(constraint_file):
                    print(f"Warning: Constraint file not found for {subject_info['subject_id']}")
                    continue
                
                constraint_funcs = extract_opensim_constraint_functions(constraint_file)
                
                # Initialize storage on first subject
                if subject_idx == 0:
                    group_dict['secondary_constraints'] = {}
                    for key in constraint_funcs.keys():
                        length = len(constraint_funcs[key]['X'])
                        group_dict['secondary_constraints'][key] = {
                            'X': np.rad2deg(constraint_funcs[key]['X']),
                            'Y': np.zeros((len(group_dict['subjects']), length))
                        }
                
                # Store data
                for key in constraint_funcs.keys():
                    # Convert translations to mm, rotations to degrees
                    if any(trans in key for trans in ['tx', 'ty', 'tz']):
                        group_dict['secondary_constraints'][key]['Y'][subject_idx, :] = \
                            constraint_funcs[key]['Y'] * 1000
                    else:
                        group_dict['secondary_constraints'][key]['Y'][subject_idx, :] = \
                            np.rad2deg(constraint_funcs[key]['Y'])
    
    def get_coordinate_data(
        self, 
        coordinate_name: str, 
        group: Optional[str] = None,
        return_individuals: bool = True
    ) -> Union[Dict, np.ndarray]:
        """
        Extract coordinate data from JAM analysis.
        
        Args:
            coordinate_name: Name of coordinate (e.g., 'knee_flex_r')
            group: Specific group name, or None for all groups
            return_individuals: If True, return individual traces; if False, return stats
            
        Returns:
            If return_individuals=True: array of shape (n_subjects, n_timesteps)
            If return_individuals=False: dict with 'mean', 'std', 'ste', 'time'
        """
        if group is not None:
            groups_to_process = {group: self.groups[group]}
        else:
            groups_to_process = self.groups
        
        results = {}
        
        for group_name, group_dict in groups_to_process.items():
            jam_list = group_dict['jam_list']
            
            if len(jam_list) == 0:
                continue
            
            # Get data shape from first subject
            length = jam_list[0].coordinateset[coordinate_name]['value'].shape[0]
            n_subjects = len(jam_list)
            
            # Extract data
            data = np.zeros((n_subjects, length))
            skipped = []
            
            for i, jam in enumerate(jam_list):
                try:
                    data[i, :] = jam.coordinateset[coordinate_name]['value'][:, 0]
                except KeyError:
                    skipped.append(i)
                    continue
            
            # Remove skipped subjects
            if len(skipped) > 0:
                data = np.delete(data, skipped, axis=0)
                print(f"Skipped {len(skipped)}/{n_subjects} subjects in group '{group_name}'")
            
            if return_individuals:
                results[group_name] = data
            else:
                time = np.linspace(0, 100, length)
                results[group_name] = {
                    'mean': np.mean(data, axis=0),
                    'std': np.std(data, axis=0),
                    'ste': np.std(data, axis=0) / np.sqrt(data.shape[0]),
                    'time': time,
                    'n': data.shape[0]
                }
        
        if group is not None:
            return results[group]
        return results
    
    def get_muscle_data(
        self, 
        muscle_name: str,
        outcome: str = 'actuation',
        group: Optional[str] = None,
        return_individuals: bool = True
    ) -> Union[Dict, np.ndarray]:
        """
        Extract muscle force data from JAM analysis.
        
        Args:
            muscle_name: Name of muscle (e.g., 'recfem_r')
            outcome: Parameter to extract (e.g., 'actuation', 'activation')
            group: Specific group name, or None for all groups
            return_individuals: If True, return individual traces; if False, return stats
            
        Returns:
            If return_individuals=True: array of shape (n_subjects, n_timesteps)
            If return_individuals=False: dict with 'mean', 'std', 'ste', 'time'
        """
        if group is not None:
            groups_to_process = {group: self.groups[group]}
        else:
            groups_to_process = self.groups
        
        results = {}
        
        for group_name, group_dict in groups_to_process.items():
            jam_list = group_dict['jam_list']
            
            if len(jam_list) == 0:
                continue
            
            # Get data shape
            length = jam_list[0].forceset['Muscle'][muscle_name][outcome].shape[0]
            n_subjects = len(jam_list)
            
            # Extract data
            data = np.zeros((n_subjects, length))
            skipped = []
            
            for i, jam in enumerate(jam_list):
                try:
                    data[i, :] = jam.forceset['Muscle'][muscle_name][outcome][:, 0]
                except KeyError:
                    skipped.append(i)
                    continue
            
            # Remove skipped subjects
            if len(skipped) > 0:
                data = np.delete(data, skipped, axis=0)
                print(f"Skipped {len(skipped)}/{n_subjects} subjects in group '{group_name}'")
            
            if return_individuals:
                results[group_name] = data
            else:
                time = np.linspace(0, 100, length)
                results[group_name] = {
                    'mean': np.mean(data, axis=0),
                    'std': np.std(data, axis=0),
                    'ste': np.std(data, axis=0) / np.sqrt(data.shape[0]),
                    'min': np.min(data, axis=0),
                    'max': np.max(data, axis=0),
                    'time': time,
                    'n': data.shape[0]
                }
        
        if group is not None:
            return results[group]
        return results
    
    def get_ligament_data(
        self,
        ligament_base_name: str,
        outcome: str = 'total_force',
        group: Optional[str] = None,
        return_individuals: bool = True
    ) -> Union[Dict, np.ndarray]:
        """
        Extract ligament force data (summed across all fibers).
        
        Args:
            ligament_base_name: Base name of ligament (e.g., 'ACL', 'MCL')
            outcome: Parameter to extract (default: 'total_force')
            group: Specific group name, or None for all groups
            return_individuals: If True, return individual traces; if False, return stats
            
        Returns:
            If return_individuals=True: array of shape (n_subjects, n_timesteps)
            If return_individuals=False: dict with 'mean', 'std', 'ste', 'time'
        """
        if group is not None:
            groups_to_process = {group: self.groups[group]}
        else:
            groups_to_process = self.groups
        
        results = {}
        
        for group_name, group_dict in groups_to_process.items():
            jam_list = group_dict['jam_list']
            
            if len(jam_list) == 0:
                continue
            
            # Find all fibers for this ligament
            fibers = [
                x for x in jam_list[0].forceset['Blankevoort1991Ligament'].keys() 
                if ligament_base_name in x
            ]
            
            if len(fibers) == 0:
                print(f"Warning: No fibers found for ligament '{ligament_base_name}'")
                continue
            
            # Get data shape
            length = jam_list[0].forceset['Blankevoort1991Ligament'][fibers[0]][outcome].shape[0]
            n_subjects = len(jam_list)
            
            # Extract and sum across fibers
            data = np.zeros((n_subjects, length))
            skipped = []
            
            for i, jam in enumerate(jam_list):
                try:
                    for fiber in fibers:
                        data[i, :] += jam.forceset['Blankevoort1991Ligament'][fiber][outcome][:, 0]
                except KeyError:
                    skipped.append(i)
                    continue
            
            # Remove skipped subjects
            if len(skipped) > 0:
                data = np.delete(data, skipped, axis=0)
                print(f"Skipped {len(skipped)}/{n_subjects} subjects in group '{group_name}'")
            
            if return_individuals:
                results[group_name] = data
            else:
                time = np.linspace(0, 100, length)
                results[group_name] = {
                    'mean': np.mean(data, axis=0),
                    'std': np.std(data, axis=0),
                    'ste': np.std(data, axis=0) / np.sqrt(data.shape[0]),
                    'time': time,
                    'n': data.shape[0]
                }
        
        if group is not None:
            return results[group]
        return results
    
    def get_contact_force_data(
        self,
        contact_type: str = 'tf_contact',
        cartilage: str = 'tibia_cartilage',
        outcome: str = 'total_contact_force',
        axis: Union[int, str] = 'norm',
        group: Optional[str] = None,
        return_individuals: bool = True
    ) -> Union[Dict, np.ndarray]:
        """
        Extract contact force data.
        
        Args:
            contact_type: Contact name (e.g., 'tf_contact', 'pf_contact')
            cartilage: Cartilage surface (e.g., 'tibia_cartilage', 'patella_cartilage')
            outcome: Parameter to extract (e.g., 'total_contact_force')
            axis: 0, 1, 2 for x/y/z components, or 'norm' for magnitude
            group: Specific group name, or None for all groups
            return_individuals: If True, return individual traces; if False, return stats
            
        Returns:
            If return_individuals=True: array of shape (n_subjects, n_timesteps)
            If return_individuals=False: dict with 'mean', 'std', 'ste', 'time'
        """
        if group is not None:
            groups_to_process = {group: self.groups[group]}
        else:
            groups_to_process = self.groups
        
        results = {}
        
        for group_name, group_dict in groups_to_process.items():
            jam_list = group_dict['jam_list']
            
            if len(jam_list) == 0:
                continue
            
            # Get data shape
            outcome_data = jam_list[0].forceset['Smith2018ArticularContactForce'][contact_type][cartilage][outcome]
            length = outcome_data.shape[0]
            n_subjects = len(jam_list)
            
            # Extract data
            data = np.zeros((n_subjects, length))
            skipped = []
            
            for i, jam in enumerate(jam_list):
                try:
                    outcome_data = jam.forceset['Smith2018ArticularContactForce'][contact_type][cartilage][outcome]
                    
                    if isinstance(axis, int):
                        data[i, :] = np.squeeze(outcome_data[:, axis])
                    elif axis == 'norm':
                        data[i, :] = np.squeeze(np.linalg.norm(outcome_data, axis=1))
                except KeyError:
                    skipped.append(i)
                    continue
            
            # Remove skipped subjects
            if len(skipped) > 0:
                data = np.delete(data, skipped, axis=0)
                print(f"Skipped {len(skipped)}/{n_subjects} subjects in group '{group_name}'")
            
            if return_individuals:
                results[group_name] = data
            else:
                time = np.linspace(0, 100, length)
                results[group_name] = {
                    'mean': np.mean(data, axis=0),
                    'std': np.std(data, axis=0),
                    'ste': np.std(data, axis=0) / np.sqrt(data.shape[0]),
                    'time': time,
                    'n': data.shape[0]
                }
        
        if group is not None:
            return results[group]
        return results
    
    def get_regional_contact_data(
        self,
        region: int,
        contact_type: str = 'tf_contact',
        cartilage: str = 'tibia_cartilage',
        outcome: str = 'regional_contact_force',
        axis: Union[int, str] = 'norm',
        group: Optional[str] = None,
        return_individuals: bool = True
    ) -> Union[Dict, np.ndarray]:
        """
        Extract regional contact data (force, pressure, or area).
        
        Args:
            region: Region index (typically 4=medial tibia, 5=lateral tibia)
            contact_type: Contact name (e.g., 'tf_contact')
            cartilage: Cartilage surface (e.g., 'tibia_cartilage')
            outcome: 'regional_contact_force', 'regional_max_pressure', 
                    'regional_mean_pressure', 'regional_contact_area'
            axis: 0, 1, 2 for components, 'norm' for magnitude, 'pressure'/'area' for scalars
            group: Specific group name, or None for all groups
            return_individuals: If True, return individual traces; if False, return stats
            
        Returns:
            If return_individuals=True: array of shape (n_subjects, n_timesteps)
            If return_individuals=False: dict with 'mean', 'std', 'ste', 'time'
        """
        if group is not None:
            groups_to_process = {group: self.groups[group]}
        else:
            groups_to_process = self.groups
        
        results = {}
        
        for group_name, group_dict in groups_to_process.items():
            jam_list = group_dict['jam_list']
            
            if len(jam_list) == 0:
                continue
            
            # Get data shape
            outcome_data = jam_list[0].forceset['Smith2018ArticularContactForce'][contact_type][cartilage][region][outcome]
            length = outcome_data.shape[0]
            n_subjects = len(jam_list)
            
            # Extract data
            data = np.zeros((n_subjects, length))
            skipped = []
            
            for i, jam in enumerate(jam_list):
                try:
                    data_ = jam.forceset['Smith2018ArticularContactForce'][contact_type][cartilage][region][outcome]
                    
                    if isinstance(axis, int):
                        data_ = data_[:, axis]
                    elif axis == 'norm':
                        data_ = np.linalg.norm(data_, axis=1)
                    elif axis in ['pressure', 'area']:
                        data_ = data_
                    
                    data[i, :] = np.squeeze(data_)
                except KeyError:
                    skipped.append(i)
                    continue
            
            # Remove skipped subjects
            if len(skipped) > 0:
                data = np.delete(data, skipped, axis=0)
                print(f"Skipped {len(skipped)}/{n_subjects} subjects in group '{group_name}'")
            
            if return_individuals:
                results[group_name] = data
            else:
                time = np.linspace(0, 100, length)
                results[group_name] = {
                    'mean': np.mean(data, axis=0),
                    'std': np.std(data, axis=0),
                    'ste': np.std(data, axis=0) / np.sqrt(data.shape[0]),
                    'time': time,
                    'n': data.shape[0]
                }
        
        if group is not None:
            return results[group]
        return results
    
    def get_summary_dataframe(self) -> pd.DataFrame:
        """
        Get a summary DataFrame with all subjects and their group assignments.
        
        Returns:
            DataFrame with columns: subject_id, side, datetime, group
        """
        rows = []
        
        for group_name, group_dict in self.groups.items():
            for subject_info in group_dict['subjects']:
                rows.append({
                    'subject_id': subject_info['subject_id'],
                    'side': subject_info['side'],
                    'datetime': subject_info['datetime'],
                    'group': group_name
                })
        
        return pd.DataFrame(rows)
    
    def remove_subjects(
        self,
        subject_ids: List[str] = None,
        subject_indices: List[int] = None,
        group: str = None
    ):
        """
        Remove subjects from the analysis.
        
        Args:
            subject_ids: List of subject IDs to remove (format: 'subject_id_side', e.g., '9003175_RIGHT')
            subject_indices: List of subject indices within a group to remove (0-based)
            group: Group name to remove subjects from (required if using subject_indices)
            
        Example:
            # Remove by subject ID (works across all groups)
            group_analysis.remove_subjects(subject_ids=['9003175_RIGHT', '9007456_LEFT'])
            
            # Remove by index within a specific group
            group_analysis.remove_subjects(subject_indices=[0, 3], group='healthy')
            
            # Remove outliers identified by identify_outlier_subjects()
            outliers = group_analysis.identify_outlier_subjects(region=4, time_range=(95,100))
            for group_name, outlier_info in outliers.items():
                if len(outlier_info['outlier_indices']) > 0:
                    group_analysis.remove_subjects(
                        subject_indices=outlier_info['outlier_indices'],
                        group=group_name
                    )
        """
        if subject_ids is not None:
            # Remove by subject ID across all groups
            for group_name, group_dict in self.groups.items():
                indices_to_remove = []
                
                for idx, subject_info in enumerate(group_dict['subjects']):
                    subj_id = f"{subject_info['subject_id']}_{subject_info['side']}"
                    if subj_id in subject_ids:
                        indices_to_remove.append(idx)
                        print(f"Removing {subj_id} from group '{group_name}'")
                
                # Remove in reverse order to maintain indices
                for idx in sorted(indices_to_remove, reverse=True):
                    del group_dict['subjects'][idx]
                    del group_dict['subject_ids'][idx]
                    del group_dict['jam_list'][idx]
        
        elif subject_indices is not None:
            # Remove by index within specific group
            if group is None:
                raise ValueError("Must specify 'group' when using subject_indices")
            
            if group not in self.groups:
                raise ValueError(f"Group '{group}' not found")
            
            group_dict = self.groups[group]
            
            # Remove in reverse order to maintain indices
            for idx in sorted(subject_indices, reverse=True):
                if idx < len(group_dict['subjects']):
                    subject_info = group_dict['subjects'][idx]
                    subj_id = f"{subject_info['subject_id']}_{subject_info['side']}"
                    print(f"Removing subject {idx} ({subj_id}) from group '{group}'")
                    
                    del group_dict['subjects'][idx]
                    del group_dict['subject_ids'][idx]
                    del group_dict['jam_list'][idx]
                else:
                    print(f"Warning: Index {idx} out of range for group '{group}'")
        else:
            raise ValueError("Must specify either 'subject_ids' or 'subject_indices'")
        
        # Update summary
        print(f"\nRemaining subjects per group:")
        for group_name, group_dict in self.groups.items():
            print(f"  {group_name}: {len(group_dict['subjects'])} subjects")
    
    def extract_values_at_time(
        self,
        var_type: str,
        var_name: str,
        time_point: float,
        time_window: Optional[float] = None,
        var_params: Optional[Dict] = None,
        group: Optional[str] = None
    ) -> Dict[str, Dict[str, np.ndarray]]:
        """
        Extract variable values at a specific timepoint or time window.
        
        Useful for scatter plot analysis and correlation studies.
        
        Args:
            var_type: Type of variable ('coordinate', 'muscle', 'ligament', 'contact')
            var_name: Name of the variable (e.g., 'knee_flex_r', 'recfem_r', 'ACL')
            time_point: Time point in % stance (0-100)
            time_window: Optional window size (e.g., 5 means ±2.5% around time_point)
                        If None, extracts exact timepoint; if provided, returns mean in window
            var_params: Additional parameters (e.g., {'outcome': 'actuation'} for muscles,
                       {'region': 4, 'outcome': 'regional_contact_force', 'axis': 'norm'} for contact)
            group: Optional group name to extract from (None = all groups)
            
        Returns:
            Dictionary with group names as keys, each containing:
                - 'values': 1D array of values (one per subject)
                - 'subject_ids': List of subject IDs
                - 'time_actual': Actual time point(s) used
        """
        if var_params is None:
            var_params = {}
        
        # Get the full time series data
        if var_type == 'coordinate':
            data_dict = self.get_coordinate_data(var_name, group=group, return_individuals=True)
        elif var_type == 'muscle':
            outcome = var_params.get('outcome', 'actuation')
            data_dict = self.get_muscle_data(var_name, outcome=outcome, group=group, return_individuals=True)
        elif var_type == 'ligament':
            data_dict = self.get_ligament_data(var_name, group=group, return_individuals=True)
        elif var_type == 'contact':
            region = var_params.get('region', 4)
            outcome = var_params.get('outcome', 'regional_contact_force')
            axis = var_params.get('axis', 'norm')
            data_dict = self.get_regional_contact_data(
                region=region, outcome=outcome, axis=axis, group=group, return_individuals=True
            )
        else:
            raise ValueError(f"Unknown var_type: {var_type}")
        
        # If single group requested, wrap in dict
        if group is not None and not isinstance(data_dict, dict):
            data_dict = {group: data_dict}
        
        results = {}
        
        for group_name, data in data_dict.items():
            # data is shape (n_subjects, n_timesteps)
            n_timesteps = data.shape[1]
            time_array = np.linspace(0, 100, n_timesteps)
            
            # Find the timepoint index/indices
            if time_window is None:
                # Extract single timepoint
                idx = np.argmin(np.abs(time_array - time_point))
                values = data[:, idx]
                time_actual = time_array[idx]
            else:
                # Extract window and take mean
                half_window = time_window / 2
                window_mask = (time_array >= time_point - half_window) & \
                             (time_array <= time_point + half_window)
                values = np.mean(data[:, window_mask], axis=1)
                time_actual = time_array[window_mask]
            
            # Get subject IDs
            if group_name in self.groups:
                subject_ids = self.groups[group_name]['subject_ids']
            else:
                subject_ids = [f"subject_{i}" for i in range(data.shape[0])]
            
            results[group_name] = {
                'values': values,
                'subject_ids': subject_ids,
                'time_actual': time_actual
            }
        
        return results
    
    def identify_outlier_subjects(
        self,
        coordinate_name: str = None,
        muscle_name: str = None,
        ligament_name: str = None,
        region: int = None,
        outcome: str = 'regional_max_pressure',
        time_range: Tuple[float, float] = (95, 100),
        threshold_std: float = 2.0,
        group: Optional[str] = None
    ) -> Dict[str, List]:
        """
        Identify subjects with outlier values in a specific time range.
        
        This is useful for detecting simulation errors or abnormal behavior,
        especially at the end of simulations.
        
        Args:
            coordinate_name: Name of coordinate to check (e.g., 'knee_flex_r')
            muscle_name: Name of muscle to check (e.g., 'recfem_r')
            ligament_name: Name of ligament to check (e.g., 'ACL')
            region: Region index for contact data (e.g., 4 for medial tibia)
            outcome: Outcome for contact data (e.g., 'regional_max_pressure')
            time_range: Tuple of (start_pct, end_pct) to analyze (default: last 5%)
            threshold_std: Number of standard deviations for outlier detection
            group: Specific group to analyze (None = all groups)
            
        Returns:
            Dictionary with group names as keys, each containing:
                - 'outlier_indices': List of subject indices that are outliers
                - 'outlier_ids': List of subject IDs that are outliers
                - 'mean_values': Mean value in time range for each subject
                - 'group_mean': Overall group mean
                - 'group_std': Overall group std
                
        Example:
            # Find subjects with extreme knee flexion at end of stance
            outliers = group_analysis.identify_outlier_subjects(
                coordinate_name='knee_flex_r',
                time_range=(95, 100)
            )
        """
        results = {}
        
        # Determine which data type to analyze
        if coordinate_name is not None:
            data_dict = self.get_coordinate_data(coordinate_name, group=group, return_individuals=True)
        elif muscle_name is not None:
            data_dict = self.get_muscle_data(muscle_name, group=group, return_individuals=True)
        elif ligament_name is not None:
            data_dict = self.get_ligament_data(ligament_name, group=group, return_individuals=True)
        elif region is not None:
            data_dict = self.get_regional_contact_data(
                region=region, outcome=outcome, axis='pressure' if 'pressure' in outcome else 'norm',
                group=group, return_individuals=True
            )
        else:
            raise ValueError("Must specify one of: coordinate_name, muscle_name, ligament_name, or region")
        
        # Analyze each group
        for group_name, data in data_dict.items():
            n_subjects, n_timesteps = data.shape
            
            # Determine time range indices
            time_pct = np.linspace(0, 100, n_timesteps)
            mask = (time_pct >= time_range[0]) & (time_pct <= time_range[1])
            
            # Calculate mean value in time range for each subject
            mean_values = np.mean(data[:, mask], axis=1)
            
            # Calculate group statistics
            group_mean = np.mean(mean_values)
            group_std = np.std(mean_values)
            
            # Identify outliers (beyond threshold_std standard deviations)
            outlier_mask = np.abs(mean_values - group_mean) > (threshold_std * group_std)
            outlier_indices = np.where(outlier_mask)[0].tolist()
            
            # Get subject IDs for outliers
            outlier_ids = []
            for idx in outlier_indices:
                subject_info = self.groups[group_name]['subjects'][idx]
                outlier_ids.append(f"{subject_info['subject_id']}_{subject_info['side']}")
            
            results[group_name] = {
                'outlier_indices': outlier_indices,
                'outlier_ids': outlier_ids,
                'mean_values': mean_values,
                'group_mean': group_mean,
                'group_std': group_std,
                'threshold': threshold_std
            }
            
            # Print summary
            if len(outlier_indices) > 0:
                print(f"\n{group_name} group: Found {len(outlier_indices)} outlier(s)")
                print(f"  Group mean ± std: {group_mean:.2f} ± {group_std:.2f}")
                print(f"  Outlier threshold: >{threshold_std} std from mean")
                for idx, subj_id in zip(outlier_indices, outlier_ids):
                    print(f"    - {subj_id}: value={mean_values[idx]:.2f} "
                          f"(z-score={(mean_values[idx]-group_mean)/group_std:.2f})")
            else:
                print(f"\n{group_name} group: No outliers detected")
        
        return results
    
    # ==================================================================================
    # NOTE FOR FUTURE DEVELOPMENT: Cross-Variable Analysis
    # ==================================================================================
    # TODO: Add functionality for analyzing relationships between variables
    # 
    # Potential features:
    # 1. Correlation analysis between muscle forces and contact mechanics
    #    - e.g., correlate vastus lateralis force with lateral contact pressure
    #    - time-series correlation or peak value correlation
    # 
    # 2. Regression models predicting contact mechanics from kinematics/kinetics
    #    - e.g., predict regional pressure from knee adduction angle and moment
    #    - could use linear regression, PLS, or ML approaches
    # 
    # 3. Statistical parametric mapping (SPM) for time-series comparisons
    #    - identify time regions where groups differ significantly
    #    - account for temporal correlation in the data
    # 
    # 4. Principal component analysis (PCA) or clustering
    #    - identify patterns across multiple variables
    #    - group subjects by movement/loading patterns
    # 
    # Example API:
    # ```python
    # # Correlate muscle force with contact pressure
    # corr_results = group_analysis.correlate_variables(
    #     var1_type='muscle', var1_name='vaslat_r', var1_outcome='actuation',
    #     var2_type='contact', var2_region=5, var2_outcome='regional_max_pressure',
    #     method='pearson'  # or 'spearman', 'time_series'
    # )
    # 
    # # Predict contact mechanics from kinematics
    # model = group_analysis.predict_contact_from_kinematics(
    #     predictors=['knee_add_r', 'knee_rot_r', 'knee_flex_r'],
    #     target_region=4, target_outcome='regional_max_pressure',
    #     model_type='linear'  # or 'ridge', 'pls', 'random_forest'
    # )
    # ```
    # ==================================================================================

