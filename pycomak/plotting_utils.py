"""
Plotting utilities for JAM analysis visualization.

Provides standardized plotting functions for common JAM analysis visualizations
including kinematics, kinetics, contact forces, and group comparisons.
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Tuple, Union


# Standard coordinate labels
COORDINATE_LABELS = {
    'knee_flex_r': 'Flexion',
    'knee_add_r': 'Adduction',
    'knee_rot_r': 'Internal Rotation',
    'knee_tx_r': 'A-P Translation',
    'knee_ty_r': 'S-I Translation',
    'knee_tz_r': 'M-L Translation',
    'pf_flex_r': 'Pat "Flexion"',
    'pf_rot_r': 'Pat Rotation',
    'pf_tilt_r': 'Pat Tilt',
    'pf_tx_r': 'Pat A-P Translation',
    'pf_ty_r': 'Pat S-I Translation',
    'pf_tz_r': 'Pat M-L Translation'
}

# Standard muscle labels
MUSCLE_LABELS = {
    'vasint_r': 'Vastus Intermedius',
    'vaslat_r': 'Vastus Lateralis',
    'vasmed_r': 'Vastus Medialis',
    'recfem_r': 'Rectus Femoris',
    'bflh_r': 'Biceps Femoris LH',
    'bfsh_r': 'Biceps Femoris SH',
    'semimem_r': 'Semimembranosus',
    'semiten_r': 'Semitendinosus',
    'gasmed_r': 'Gastrocnemius Medialis',
    'gaslat_r': 'Gastrocnemius Lateralis'
}

# Standard ligament labels
LIGAMENT_LABELS = {
    'ACL': 'ACL',
    'PCL': 'PCL',
    'MCL': 'MCL',
    'LCL': 'LCL',
    'PT': 'PT',
    'ITB': 'ITB',
    'pCAP': 'pCAP',
    'mPFL': 'mPFL',
    'lPFL': 'lPFL'
}

# Standard region labels
REGION_LABELS = {
    4: 'Medial Tibia',
    5: 'Lateral Tibia'
}

# Standard group colors
GROUP_COLORS = {
    'healthy': '#1f77b4',  # blue
    'progressors': '#2ca02c',  # green
    'OA': '#d62728',  # red
    'other': '#7f7f7f',  # gray
    'default': '#ff7f0e'  # orange
}

def assign_colors_to_groups(group_names: List[str], color_dict: Optional[Dict] = None) -> Dict[str, str]:
    """
    Assign colors to groups, using predefined colors where available and 
    automatically assigning from color cycle for unknown groups.
    
    This is useful for custom plotting code to ensure each group gets a unique color.
    
    Args:
        group_names: List of group names
        color_dict: Optional dict of predefined group colors (defaults to GROUP_COLORS)
        
    Returns:
        Dict mapping each group name to a color
        
    Example:
        ```python
        from pycomak.plotting_utils import assign_colors_to_groups
        
        data = group_analysis.get_ligament_data('ACL', return_individuals=False)
        colors = assign_colors_to_groups(list(data.keys()))
        
        for group_name, group_data in data.items():
            color = colors[group_name]
            plt.plot(group_data['time'], group_data['mean'], color=color)
        ```
    """
    if color_dict is None:
        color_dict = GROUP_COLORS
    
    # Default matplotlib color cycle
    default_colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
    
    assigned_colors = {}
    color_idx = 0
    
    for group_name in group_names:
        if group_name in color_dict:
            # Use predefined color
            assigned_colors[group_name] = color_dict[group_name]
        else:
            # Assign color from cycle
            assigned_colors[group_name] = default_colors[color_idx % len(default_colors)]
            color_idx += 1
    
    return assigned_colors


# Internal alias for backward compatibility
_assign_colors_to_groups = assign_colors_to_groups


def plot_coordinate_comparison(
    group_data: Dict[str, Dict],
    coordinate_name: str,
    ax: Optional[plt.Axes] = None,
    show_std: bool = True,
    show_ste: bool = False,
    title: Optional[str] = None,
    xlabel: str = '% Stance',
    fontsize: int = 15,
    colors: Optional[Dict] = None,
    legend: bool = True,
    legend_loc: str = 'best',
    translation_units: str = 'm'
) -> plt.Axes:
    """
    Plot coordinate comparison across groups (mean ± std/ste).
    
    Args:
        group_data: Dict of group names to data dicts (with 'mean', 'std', 'ste', 'time')
        coordinate_name: Name of coordinate for labeling
        ax: Matplotlib axes object (creates new if None)
        show_std: Whether to show standard deviation band
        show_ste: Whether to show standard error band (overrides show_std if True)
        title: Plot title (auto-generated if None)
        xlabel: X-axis label
        fontsize: Font size for labels
        colors: Dict mapping group names to colors (uses defaults if None)
        legend: Whether to show legend
        legend_loc: Legend location
        translation_units: Units for translation coordinates ('m' or 'mm')
        
    Returns:
        Matplotlib axes object
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 6))
    
    # Assign colors to groups (automatically assigns different colors to unknown groups)
    group_names = list(group_data.keys())
    if colors is None:
        colors = _assign_colors_to_groups(group_names)
    else:
        # Still apply auto-assignment for any groups not in provided colors
        colors = _assign_colors_to_groups(group_names, colors)
    
    # Determine if this is a translation coordinate
    is_translation = any(trans in coordinate_name for trans in ['tx', 'ty', 'tz'])
    
    # Set ylabel based on coordinate type
    if is_translation:
        ylabel = translation_units
    else:
        ylabel = 'degrees'
    
    # Plot each group
    for group_name, data in group_data.items():
        color = colors[group_name]

        mean = data['mean'].copy()
        time = data['time']

        # Convert units: H5 stores radians for rotations, meters for translations
        if is_translation and translation_units == 'mm':
            mean = mean * 1000
            std_data = data.get('std', np.zeros_like(mean)) * 1000
            ste_data = data.get('ste', np.zeros_like(mean)) * 1000
        elif not is_translation:
            mean = np.rad2deg(mean)
            std_data = np.rad2deg(data.get('std', np.zeros_like(mean)))
            ste_data = np.rad2deg(data.get('ste', np.zeros_like(mean)))
        else:
            std_data = data.get('std', np.zeros_like(mean))
            ste_data = data.get('ste', np.zeros_like(mean))
        
        # Plot mean
        ax.plot(time, mean, label=group_name.capitalize(), color=color, linewidth=2)
        
        # Plot uncertainty band
        if show_ste and 'ste' in data:
            ax.fill_between(time, mean - ste_data, mean + ste_data, 
                           alpha=0.3, color=color)
        elif show_std and 'std' in data:
            ax.fill_between(time, mean - std_data, mean + std_data, 
                           alpha=0.2, color=color)
    
    # Labels and formatting
    if title is None:
        title = COORDINATE_LABELS.get(coordinate_name, coordinate_name)
    
    ax.set_title(title, fontsize=fontsize + 5)
    ax.set_xlabel(xlabel, fontsize=fontsize)
    ax.set_ylabel(ylabel, fontsize=fontsize)
    ax.tick_params(labelsize=fontsize - 2)
    ax.grid(True, alpha=0.3)
    
    if legend:
        ax.legend(fontsize=fontsize - 2, loc=legend_loc)
    
    return ax


def plot_coordinate_individuals(
    group_data: Dict[str, np.ndarray],
    coordinate_name: str,
    ax: Optional[plt.Axes] = None,
    title: Optional[str] = None,
    xlabel: str = '% Stance',
    fontsize: int = 15,
    colors: Optional[Dict] = None,
    alpha: float = 0.5,
    legend: bool = True,
    translation_units: str = 'm'
) -> plt.Axes:
    """
    Plot individual traces for coordinate data.
    
    Args:
        group_data: Dict of group names to arrays of shape (n_subjects, n_timesteps)
        coordinate_name: Name of coordinate for labeling
        ax: Matplotlib axes object (creates new if None)
        title: Plot title (auto-generated if None)
        xlabel: X-axis label
        fontsize: Font size for labels
        colors: Dict mapping group names to colors
        alpha: Transparency of individual lines
        legend: Whether to show legend
        translation_units: Units for translation coordinates ('m' or 'mm')
        
    Returns:
        Matplotlib axes object
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 6))
    
    # Assign colors to groups (automatically assigns different colors to unknown groups)
    group_names = list(group_data.keys())
    if colors is None:
        colors = _assign_colors_to_groups(group_names)
    else:
        # Still apply auto-assignment for any groups not in provided colors
        colors = _assign_colors_to_groups(group_names, colors)
    
    # Determine if this is a translation coordinate
    is_translation = any(trans in coordinate_name for trans in ['tx', 'ty', 'tz'])
    
    # Set ylabel based on coordinate type
    if is_translation:
        ylabel = translation_units
    else:
        ylabel = 'degrees'
    
    # Plot each group
    for group_name, data in group_data.items():
        color = colors[group_name]
        time = np.linspace(0, 100, data.shape[1])

        # Convert units: H5 stores radians for rotations, meters for translations
        plot_data = data.copy()
        if is_translation and translation_units == 'mm':
            plot_data = plot_data * 1000
        elif not is_translation:
            plot_data = np.rad2deg(plot_data)

        for i in range(plot_data.shape[0]):
            label = group_name.capitalize() if i == 0 else None
            ax.plot(time, plot_data[i, :], color=color, alpha=alpha, label=label)

    # Labels and formatting
    if title is None:
        title = COORDINATE_LABELS.get(coordinate_name, coordinate_name)

    ax.set_title(title, fontsize=fontsize + 5)
    ax.set_xlabel(xlabel, fontsize=fontsize)
    ax.set_ylabel(ylabel, fontsize=fontsize)
    ax.tick_params(labelsize=fontsize - 2)
    ax.grid(True, alpha=0.3, which='both', linestyle='--')
    ax.minorticks_on()
    ax.grid(True, alpha=0.15, which='minor', linestyle=':')

    if legend:
        ax.legend(fontsize=fontsize - 2)

    return ax


def plot_kinematics_panel(
    group_analysis,
    coordinates: List[str],
    plot_type: str = 'mean',
    figsize: Tuple[int, int] = (16, 9),
    fontsize: int = 15,
    suptitle: Optional[str] = None,
    translation_units: str = 'm'
) -> Tuple[plt.Figure, np.ndarray]:
    """
    Create multi-panel plot of kinematic coordinates.
    
    Args:
        group_analysis: GroupJamAnalysis object
        coordinates: List of coordinate names to plot
        plot_type: 'mean' for mean±std/ste, 'individual' for individual traces
        figsize: Figure size
        fontsize: Font size
        suptitle: Super title for entire figure
        translation_units: Units for translation coordinates ('m' or 'mm')
        
    Returns:
        Tuple of (figure, axes_array)
    """
    n_coords = len(coordinates)
    n_rows = (n_coords + 2) // 3  # 3 columns
    n_cols = min(3, n_coords)
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
    if n_coords == 1:
        axes = np.array([axes])
    axes = axes.flatten()
    
    for idx, coord_name in enumerate(coordinates):
        if plot_type == 'mean':
            data = group_analysis.get_coordinate_data(coord_name, return_individuals=False)
            plot_coordinate_comparison(data, coord_name, ax=axes[idx], fontsize=fontsize, 
                                     translation_units=translation_units)
        else:
            data = group_analysis.get_coordinate_data(coord_name, return_individuals=True)
            plot_coordinate_individuals(data, coord_name, ax=axes[idx], fontsize=fontsize,
                                      translation_units=translation_units)
    
    # Hide extra subplots
    for idx in range(n_coords, len(axes)):
        axes[idx].set_visible(False)
    
    if suptitle:
        fig.suptitle(suptitle, fontsize=fontsize + 10)
    
    plt.tight_layout()
    
    return fig, axes


def plot_muscle_comparison(
    group_data: Dict[str, Dict],
    muscle_name: str,
    ax: Optional[plt.Axes] = None,
    show_ste: bool = True,
    show_std: bool = False,
    title: Optional[str] = None,
    xlabel: str = '% Stance',
    ylabel: str = 'Force (N)',
    fontsize: int = 15,
    colors: Optional[Dict] = None,
    legend: bool = True
) -> plt.Axes:
    """
    Plot muscle force comparison across groups.

    Args:
        group_data: Dict of group names to data dicts (with 'mean', 'std', 'ste', 'time')
        muscle_name: Name of muscle
        ax: Matplotlib axes object (creates new if None)
        show_ste: Whether to show standard error band (default: True)
        show_std: Whether to show standard deviation band (overridden by show_ste)
        title: Plot title (auto-generated if None)
        xlabel: X-axis label
        ylabel: Y-axis label
        fontsize: Font size
        colors: Dict mapping group names to colors
        legend: Whether to show legend

    Returns:
        Matplotlib axes object
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 6))
    
    # Assign colors to groups (automatically assigns different colors to unknown groups)
    group_names = list(group_data.keys())
    if colors is None:
        colors = _assign_colors_to_groups(group_names)
    else:
        # Still apply auto-assignment for any groups not in provided colors
        colors = _assign_colors_to_groups(group_names, colors)
    
    # Plot each group
    for group_name, data in group_data.items():
        color = colors[group_name]
        
        mean = data['mean']
        time = data['time']
        
        ax.plot(time, mean, label=group_name.capitalize(), color=color, linewidth=2)

        if show_ste and 'ste' in data:
            ax.fill_between(time, mean - data['ste'], mean + data['ste'], alpha=0.3, color=color)
        elif show_std and 'std' in data:
            ax.fill_between(time, mean - data['std'], mean + data['std'], alpha=0.2, color=color)

    # Labels and formatting
    if title is None:
        title = MUSCLE_LABELS.get(muscle_name, muscle_name)

    ax.set_title(title, fontsize=fontsize + 5)
    ax.set_xlabel(xlabel, fontsize=fontsize)
    ax.set_ylabel(ylabel, fontsize=fontsize)
    ax.tick_params(labelsize=fontsize - 2)
    ax.grid(True, alpha=0.3)

    if legend:
        ax.legend(fontsize=fontsize - 2)

    return ax


def plot_muscle_individuals(
    group_data: Dict[str, np.ndarray],
    muscle_name: str,
    ax: Optional[plt.Axes] = None,
    title: Optional[str] = None,
    xlabel: str = '% Stance',
    ylabel: str = 'Force (N)',
    fontsize: int = 15,
    colors: Optional[Dict] = None,
    alpha: float = 0.5,
    legend: bool = True
) -> plt.Axes:
    """
    Plot individual traces for muscle force data.
    
    Args:
        group_data: Dict of group names to arrays of shape (n_subjects, n_timesteps)
        muscle_name: Name of muscle for labeling
        ax: Matplotlib axes object (creates new if None)
        title: Plot title (auto-generated if None)
        xlabel: X-axis label
        ylabel: Y-axis label
        fontsize: Font size for labels
        colors: Dict mapping group names to colors
        alpha: Transparency of individual lines
        legend: Whether to show legend
        
    Returns:
        Matplotlib axes object
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 6))
    
    # Assign colors to groups (automatically assigns different colors to unknown groups)
    group_names = list(group_data.keys())
    if colors is None:
        colors = _assign_colors_to_groups(group_names)
    else:
        # Still apply auto-assignment for any groups not in provided colors
        colors = _assign_colors_to_groups(group_names, colors)
    
    # Plot each group
    for group_name, data in group_data.items():
        color = colors[group_name]
        time = np.linspace(0, 100, data.shape[1])
        
        for i in range(data.shape[0]):
            label = group_name.capitalize() if i == 0 else None
            ax.plot(time, data[i, :], color=color, alpha=alpha, label=label)
    
    # Labels and formatting
    if title is None:
        title = MUSCLE_LABELS.get(muscle_name, muscle_name)
    
    ax.set_title(title, fontsize=fontsize + 5)
    ax.set_xlabel(xlabel, fontsize=fontsize)
    ax.set_ylabel(ylabel, fontsize=fontsize)
    ax.tick_params(labelsize=fontsize - 2)
    ax.grid(True, alpha=0.3, which='both', linestyle='--')
    ax.minorticks_on()
    ax.grid(True, alpha=0.15, which='minor', linestyle=':')
    
    if legend:
        ax.legend(fontsize=fontsize - 2)
    
    return ax


def plot_muscles_panel(
    group_analysis,
    muscles: List[str],
    outcome: str = 'actuation',
    plot_type: str = 'mean',
    figsize: Tuple[int, int] = (16, 9),
    fontsize: int = 15,
    suptitle: Optional[str] = None,
    title_fontsize: Optional[int] = None
) -> Tuple[plt.Figure, np.ndarray]:
    """
    Create multi-panel plot of muscle forces.
    
    Args:
        group_analysis: GroupJamAnalysis object
        muscles: List of muscle names
        outcome: Muscle parameter to plot
        plot_type: 'mean' for mean±range, 'individual' for individual traces
        figsize: Figure size
        fontsize: Font size for labels and axes
        suptitle: Super title
        title_fontsize: Font size for subplot titles (if None, uses fontsize)
        
    Returns:
        Tuple of (figure, axes_array)
    """
    n_muscles = len(muscles)
    n_rows = (n_muscles + 4) // 5  # 5 columns
    n_cols = min(5, n_muscles)
    
    # Use title_fontsize if provided, otherwise use fontsize (no +5 to avoid overlap)
    if title_fontsize is None:
        title_fontsize = fontsize
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
    if n_muscles == 1:
        axes = np.array([axes])
    axes = axes.flatten()
    
    for idx, muscle_name in enumerate(muscles):
        if plot_type == 'mean':
            data = group_analysis.get_muscle_data(muscle_name, outcome, return_individuals=False)
            plot_muscle_comparison(data, muscle_name, ax=axes[idx], fontsize=fontsize)
        else:
            data = group_analysis.get_muscle_data(muscle_name, outcome, return_individuals=True)
            plot_muscle_individuals(data, muscle_name, ax=axes[idx], fontsize=fontsize)
        
        # Override the title with wrap-friendly formatting
        title = MUSCLE_LABELS.get(muscle_name, muscle_name)
        # Wrap long titles to two lines
        if len(title) > 18:
            words = title.split()
            if len(words) > 1:
                mid = len(words) // 2
                title = ' '.join(words[:mid]) + '\n' + ' '.join(words[mid:])
        axes[idx].set_title(title, fontsize=title_fontsize)
    
    # Hide extra subplots
    for idx in range(n_muscles, len(axes)):
        axes[idx].set_visible(False)
    
    if suptitle:
        fig.suptitle(suptitle, fontsize=fontsize + 10, y=0.995)
    
    plt.tight_layout()
    
    return fig, axes


def plot_ligament_comparison(
    group_data: Dict[str, Dict],
    ligament_name: str,
    ax: Optional[plt.Axes] = None,
    show_range: bool = False,
    show_ste: bool = True,
    title: Optional[str] = None,
    xlabel: str = '% Stance',
    ylabel: str = 'Force (N)',
    fontsize: int = 15,
    colors: Optional[Dict] = None,
    legend: bool = True
) -> plt.Axes:
    """
    Plot ligament force comparison across groups.
    
    Args:
        group_data: Dict of group names to data dicts (with 'mean', 'ste', 'time')
        ligament_name: Name of ligament
        ax: Matplotlib axes object (creates new if None)
        show_range: Whether to show min-max range
        show_ste: Whether to show standard error band
        title: Plot title (auto-generated if None)
        xlabel: X-axis label
        ylabel: Y-axis label
        fontsize: Font size
        colors: Dict mapping group names to colors
        legend: Whether to show legend
        
    Returns:
        Matplotlib axes object
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 6))
    
    # Assign colors to groups (automatically assigns different colors to unknown groups)
    group_names = list(group_data.keys())
    if colors is None:
        colors = _assign_colors_to_groups(group_names)
    else:
        # Still apply auto-assignment for any groups not in provided colors
        colors = _assign_colors_to_groups(group_names, colors)
    
    # Plot each group
    for group_name, data in group_data.items():
        color = colors[group_name]
        
        mean = data['mean']
        time = data['time']
        
        ax.plot(time, mean, label=group_name.capitalize(), color=color, linewidth=2)
        
        if show_ste and 'ste' in data:
            ax.fill_between(time, mean - data['ste'], mean + data['ste'], alpha=0.3, color=color)
        elif show_range and 'min' in data and 'max' in data:
            ax.fill_between(time, data['min'], data['max'], alpha=0.2, color=color)
    
    # Labels and formatting
    if title is None:
        title = LIGAMENT_LABELS.get(ligament_name, ligament_name)
    
    ax.set_title(title, fontsize=fontsize + 5)
    ax.set_xlabel(xlabel, fontsize=fontsize)
    ax.set_ylabel(ylabel, fontsize=fontsize)
    ax.tick_params(labelsize=fontsize - 2)
    ax.grid(True, alpha=0.3)
    
    if legend:
        ax.legend(fontsize=fontsize - 2)
    
    return ax


def plot_ligament_individuals(
    group_data: Dict[str, np.ndarray],
    ligament_name: str,
    ax: Optional[plt.Axes] = None,
    title: Optional[str] = None,
    xlabel: str = '% Stance',
    ylabel: str = 'Force (N)',
    fontsize: int = 15,
    colors: Optional[Dict] = None,
    alpha: float = 0.5,
    legend: bool = True
) -> plt.Axes:
    """
    Plot individual traces for ligament force data.
    
    Args:
        group_data: Dict of group names to arrays of shape (n_subjects, n_timesteps)
        ligament_name: Name of ligament for labeling
        ax: Matplotlib axes object (creates new if None)
        title: Plot title (auto-generated if None)
        xlabel: X-axis label
        ylabel: Y-axis label
        fontsize: Font size for labels
        colors: Dict mapping group names to colors
        alpha: Transparency of individual lines
        legend: Whether to show legend
        
    Returns:
        Matplotlib axes object
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 6))
    
    # Assign colors to groups (automatically assigns different colors to unknown groups)
    group_names = list(group_data.keys())
    if colors is None:
        colors = _assign_colors_to_groups(group_names)
    else:
        # Still apply auto-assignment for any groups not in provided colors
        colors = _assign_colors_to_groups(group_names, colors)
    
    # Plot each group
    for group_name, data in group_data.items():
        color = colors[group_name]
        time = np.linspace(0, 100, data.shape[1])
        
        for i in range(data.shape[0]):
            label = group_name.capitalize() if i == 0 else None
            ax.plot(time, data[i, :], color=color, alpha=alpha, label=label)
    
    # Labels and formatting
    if title is None:
        title = LIGAMENT_LABELS.get(ligament_name, ligament_name)
    
    ax.set_title(title, fontsize=fontsize + 5)
    ax.set_xlabel(xlabel, fontsize=fontsize)
    ax.set_ylabel(ylabel, fontsize=fontsize)
    ax.tick_params(labelsize=fontsize - 2)
    ax.grid(True, alpha=0.3, which='both', linestyle='--')
    ax.minorticks_on()
    ax.grid(True, alpha=0.15, which='minor', linestyle=':')
    
    if legend:
        ax.legend(fontsize=fontsize - 2)
    
    return ax


def plot_ligaments_panel(
    group_analysis,
    ligaments: List[str],
    plot_type: str = 'mean',
    figsize: Tuple[int, int] = (16, 7),
    fontsize: int = 15,
    suptitle: Optional[str] = None,
    title_fontsize: Optional[int] = None
) -> Tuple[plt.Figure, np.ndarray]:
    """
    Create multi-panel plot of ligament forces.
    
    Args:
        group_analysis: GroupJamAnalysis object
        ligaments: List of ligament names
        plot_type: 'mean' for mean±ste, 'individual' for individual traces
        figsize: Figure size
        fontsize: Font size for labels and axes
        suptitle: Super title
        title_fontsize: Font size for subplot titles (if None, uses fontsize)
        
    Returns:
        Tuple of (figure, axes_array)
    """
    n_ligaments = len(ligaments)
    n_rows = (n_ligaments + 4) // 5  # 5 columns
    n_cols = min(5, n_ligaments)
    
    # Use title_fontsize if provided, otherwise use fontsize
    if title_fontsize is None:
        title_fontsize = fontsize
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
    if n_ligaments == 1:
        axes = np.array([axes])
    axes = axes.flatten()
    
    for idx, ligament_name in enumerate(ligaments):
        if plot_type == 'mean':
            data = group_analysis.get_ligament_data(ligament_name, return_individuals=False)
            plot_ligament_comparison(data, ligament_name, ax=axes[idx], fontsize=fontsize)
        else:
            data = group_analysis.get_ligament_data(ligament_name, return_individuals=True)
            plot_ligament_individuals(data, ligament_name, ax=axes[idx], fontsize=fontsize)
        
        # Set title
        title = LIGAMENT_LABELS.get(ligament_name, ligament_name)
        axes[idx].set_title(title, fontsize=title_fontsize)
        
        # Show legend on second subplot (idx == 1)
        if idx == 1:
            axes[idx].legend(fontsize=fontsize - 2)
        else:
            legend = axes[idx].get_legend()
            if legend:
                legend.remove()
    
    # Hide extra subplots
    for idx in range(n_ligaments, len(axes)):
        axes[idx].set_visible(False)
    
    if suptitle:
        fig.suptitle(suptitle, fontsize=fontsize + 10, y=0.995)
    
    plt.tight_layout()
    
    return fig, axes


def plot_regional_contact(
    group_data: Dict[str, Dict],
    region: int,
    outcome_type: str = 'force',
    ax: Optional[plt.Axes] = None,
    title: Optional[str] = None,
    xlabel: str = '% Stance',
    fontsize: int = 15,
    colors: Optional[Dict] = None,
    legend: bool = True,
    ylim: Optional[Tuple] = None
) -> plt.Axes:
    """
    Plot regional contact data (force, pressure, or area).
    
    Args:
        group_data: Dict of group names to data dicts
        region: Region index
        outcome_type: 'force', 'max_pressure', 'mean_pressure', or 'area'
        ax: Matplotlib axes object
        title: Plot title
        xlabel: X-axis label
        fontsize: Font size
        colors: Group colors
        legend: Show legend
        ylim: Y-axis limits
        
    Returns:
        Matplotlib axes object
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 6))
    
    # Assign colors to groups (automatically assigns different colors to unknown groups)
    group_names = list(group_data.keys())
    if colors is None:
        colors = _assign_colors_to_groups(group_names)
    else:
        # Still apply auto-assignment for any groups not in provided colors
        colors = _assign_colors_to_groups(group_names, colors)
    
    # Determine y-label based on outcome type
    ylabel_map = {
        'force': 'Contact Force (N)',
        'max_pressure': 'Max Pressure (MPa)',
        'mean_pressure': 'Mean Pressure (MPa)',
        'area': 'Contact Area (cm²)'
    }
    ylabel = ylabel_map.get(outcome_type, 'Value')
    
    # Plot each group
    for group_name, data in group_data.items():
        color = colors[group_name]
        
        mean = data['mean']
        time = data['time']
        
        # Convert units if needed
        if 'pressure' in outcome_type:
            mean = mean / 1e6  # Pa to MPa
            if 'ste' in data:
                ste = data['ste'] / 1e6
        elif outcome_type == 'area':
            mean = mean * 1e4  # m² to cm²
            if 'ste' in data:
                ste = data['ste'] * 1e4
        else:
            if 'ste' in data:
                ste = data['ste']
        
        ax.plot(time, mean, label=group_name.capitalize(), color=color, linewidth=2)

        if 'ste' in data:
            ax.fill_between(time, mean - ste, mean + ste, alpha=0.3, color=color)
    
    # Labels and formatting
    if title is None:
        title = REGION_LABELS.get(region, f'Region {region}')
    
    ax.set_title(title, fontsize=fontsize + 5)
    ax.set_xlabel(xlabel, fontsize=fontsize)
    ax.set_ylabel(ylabel, fontsize=fontsize)
    ax.tick_params(labelsize=fontsize - 2)
    ax.grid(True, alpha=0.3)
    
    if ylim:
        ax.set_ylim(ylim)
    
    if legend:
        ax.legend(fontsize=fontsize - 2)
    
    return ax


def plot_regional_contact_individuals(
    group_data: Dict[str, np.ndarray],
    region: int,
    outcome_type: str = 'force',
    ax: Optional[plt.Axes] = None,
    title: Optional[str] = None,
    xlabel: str = '% Stance',
    fontsize: int = 15,
    colors: Optional[Dict] = None,
    alpha: float = 0.5,
    legend: bool = True
) -> plt.Axes:
    """
    Plot individual traces for regional contact data.
    
    Args:
        group_data: Dict of group names to arrays of shape (n_subjects, n_timesteps)
        region: Region index
        outcome_type: 'force', 'max_pressure', 'mean_pressure', or 'area'
        ax: Matplotlib axes object (creates new if None)
        title: Plot title (auto-generated if None)
        xlabel: X-axis label
        fontsize: Font size for labels
        colors: Dict mapping group names to colors
        alpha: Transparency of individual lines
        legend: Whether to show legend
        
    Returns:
        Matplotlib axes object
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 6))
    
    # Assign colors to groups (automatically assigns different colors to unknown groups)
    group_names = list(group_data.keys())
    if colors is None:
        colors = _assign_colors_to_groups(group_names)
    else:
        # Still apply auto-assignment for any groups not in provided colors
        colors = _assign_colors_to_groups(group_names, colors)
    
    # Determine y-label based on outcome type
    ylabel_map = {
        'force': 'Contact Force (N)',
        'max_pressure': 'Max Pressure (MPa)',
        'mean_pressure': 'Mean Pressure (MPa)',
        'area': 'Contact Area (cm²)'
    }
    ylabel = ylabel_map.get(outcome_type, 'Value')
    
    # Plot each group
    for group_name, data in group_data.items():
        color = colors[group_name]
        time = np.linspace(0, 100, data.shape[1])
        
        # Convert units if needed (data is in SI units)
        plot_data = data.copy()
        if 'pressure' in outcome_type:
            plot_data = plot_data / 1e6  # Pa to MPa
        elif outcome_type == 'area':
            plot_data = plot_data * 1e4  # m² to cm²
        
        for i in range(plot_data.shape[0]):
            label = group_name.capitalize() if i == 0 else None
            ax.plot(time, plot_data[i, :], color=color, alpha=alpha, label=label)
    
    # Labels and formatting
    if title is None:
        title = REGION_LABELS.get(region, f'Region {region}')
    
    ax.set_title(title, fontsize=fontsize + 5)
    ax.set_xlabel(xlabel, fontsize=fontsize)
    ax.set_ylabel(ylabel, fontsize=fontsize)
    ax.tick_params(labelsize=fontsize - 2)
    ax.grid(True, alpha=0.3, which='both', linestyle='--')
    ax.minorticks_on()
    ax.grid(True, alpha=0.15, which='minor', linestyle=':')
    
    if legend:
        ax.legend(fontsize=fontsize - 2)
    
    return ax


def plot_contact_comparison_panel(
    group_analysis,
    regions: List[int] = [4, 5],
    outcomes: List[str] = ['force', 'max_pressure', 'mean_pressure', 'area'],
    plot_type: str = 'mean',
    contact_type: str = 'tf_contact',
    figsize: Optional[Tuple[int, int]] = None,
    fontsize: int = 15
) -> Tuple[plt.Figure, np.ndarray]:
    """
    Create comprehensive contact mechanics comparison panel.
    
    Args:
        group_analysis: GroupJamAnalysis object
        regions: List of regions to plot (default: [4, 5] for medial/lateral)
        outcomes: List of outcome types to plot
        plot_type: 'mean' for mean±ste, 'individual' for individual traces
        contact_type: Contact type to plot (default: 'tf_contact')
        figsize: Figure size (if None, auto-calculated based on number of rows)
        fontsize: Font size
        
    Returns:
        Tuple of (figure, axes_array)
    """
    n_rows = len(outcomes)
    n_cols = len(regions)
    
    # Auto-calculate figsize if not provided (3.5 inches per row to avoid squishing)
    if figsize is None:
        figsize = (8 * n_cols, 3.5 * n_rows)
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
    if n_rows == 1 and n_cols == 1:
        axes = np.array([[axes]])
    elif n_rows == 1:
        axes = axes.reshape(1, -1)
    elif n_cols == 1:
        axes = axes.reshape(-1, 1)
    
    outcome_map = {
        'force': 'regional_contact_force',
        'max_pressure': 'regional_max_pressure',
        'mean_pressure': 'regional_mean_pressure',
        'area': 'regional_contact_area'
    }
    
    axis_map = {
        'force': 'norm',
        'max_pressure': 'pressure',
        'mean_pressure': 'pressure',
        'area': 'area'
    }
    
    for row_idx, outcome_type in enumerate(outcomes):
        for col_idx, region in enumerate(regions):
            outcome_name = outcome_map[outcome_type]
            axis = axis_map[outcome_type]
            
            # Only show legend on first subplot
            show_legend = (row_idx == 0 and col_idx == 0)
            
            if plot_type == 'mean':
                data = group_analysis.get_regional_contact_data(
                    region=region,
                    contact_type=contact_type,
                    outcome=outcome_name,
                    axis=axis,
                    return_individuals=False
                )
                
                plot_regional_contact(
                    data,
                    region,
                    outcome_type,
                    ax=axes[row_idx, col_idx],
                    fontsize=fontsize,
                    legend=show_legend
                )
            else:
                data = group_analysis.get_regional_contact_data(
                    region=region,
                    contact_type=contact_type,
                    outcome=outcome_name,
                    axis=axis,
                    return_individuals=True
                )
                
                plot_regional_contact_individuals(
                    data,
                    region,
                    outcome_type,
                    ax=axes[row_idx, col_idx],
                    fontsize=fontsize,
                    legend=show_legend
                )
    
    plt.tight_layout()
    
    return fig, axes


def create_publication_figure(
    group_analysis,
    regions: List[int] = [4, 5],
    outcome_type: str = 'max_pressure',
    figsize: Tuple[int, int] = (16, 5),
    fontsize: int = 20,
    ylim: Optional[Tuple] = None
) -> Tuple[plt.Figure, np.ndarray]:
    """
    Create publication-ready figure for contact mechanics.
    
    Args:
        group_analysis: GroupJamAnalysis object
        regions: Regions to plot
        outcome_type: Type of outcome to plot
        figsize: Figure size
        fontsize: Font size
        ylim: Y-axis limits
        
    Returns:
        Tuple of (figure, axes_array)
    """
    fig, axes = plt.subplots(1, len(regions), figsize=figsize)
    if len(regions) == 1:
        axes = [axes]
    
    outcome_map = {
        'force': 'regional_contact_force',
        'max_pressure': 'regional_max_pressure',
        'mean_pressure': 'regional_mean_pressure',
        'area': 'regional_contact_area'
    }
    
    axis_map = {
        'force': 'norm',
        'max_pressure': 'pressure',
        'mean_pressure': 'pressure',
        'area': 'area'
    }
    
    for idx, region in enumerate(regions):
        outcome_name = outcome_map[outcome_type]
        axis = axis_map[outcome_type]
        
        data = group_analysis.get_regional_contact_data(
            region=region,
            outcome=outcome_name,
            axis=axis,
            return_individuals=False
        )
        
        # Only show legend on first subplot
        show_legend = (idx == 0)
        
        plot_regional_contact(
            data,
            region,
            outcome_type,
            ax=axes[idx],
            fontsize=fontsize,
            legend=show_legend,
            ylim=ylim
        )
    
    plt.tight_layout()
    
    return fig, axes


def plot_variable_scatter(
    x_data: Dict[str, np.ndarray],
    y_data: Dict[str, np.ndarray],
    ax: Optional[plt.Axes] = None,
    xlabel: str = 'X Variable',
    ylabel: str = 'Y Variable',
    title: Optional[str] = None,
    fontsize: int = 15,
    colors: Optional[Dict] = None,
    show_legend: bool = True,
    show_stats: bool = True,
    add_trendline: bool = False
) -> plt.Axes:
    """
    Create scatter plot comparing two variables across groups.
    
    Useful for exploratory analysis of relationships between variables
    at specific timepoints.
    
    Args:
        x_data: Dict of group names to 1D arrays of x values
        y_data: Dict of group names to 1D arrays of y values
        ax: Matplotlib axes object (creates new if None)
        xlabel: X-axis label
        ylabel: Y-axis label
        title: Plot title
        fontsize: Font size for labels
        colors: Dict mapping group names to colors
        show_legend: Whether to show legend
        show_stats: Whether to show correlation coefficient
        add_trendline: Whether to add linear trendline
        
    Returns:
        Matplotlib axes object
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 6))
    
    # Assign colors to groups (automatically assigns different colors to unknown groups)
    group_names = list(x_data.keys())
    if colors is None:
        colors = _assign_colors_to_groups(group_names)
    else:
        # Still apply auto-assignment for any groups not in provided colors
        colors = _assign_colors_to_groups(group_names, colors)
    
    # Plot each group
    all_x = []
    all_y = []
    
    for group_name in x_data.keys():
        if group_name not in y_data:
            continue
        
        x = x_data[group_name]
        y = y_data[group_name]
        color = colors[group_name]
        
        ax.scatter(x, y, label=group_name.capitalize(), color=color, 
                  s=80, alpha=0.7, edgecolors='black', linewidths=0.5)
        
        all_x.extend(x)
        all_y.extend(y)
    
    # Add trendline if requested
    if add_trendline and len(all_x) > 1:
        all_x = np.array(all_x)
        all_y = np.array(all_y)
        
        # Remove any NaN values
        mask = ~(np.isnan(all_x) | np.isnan(all_y))
        if mask.sum() > 1:
            coeffs = np.polyfit(all_x[mask], all_y[mask], 1)
            x_line = np.linspace(all_x[mask].min(), all_x[mask].max(), 100)
            y_line = np.polyval(coeffs, x_line)
            ax.plot(x_line, y_line, 'k--', alpha=0.5, linewidth=2, label='Trendline')
    
    # Calculate correlation if requested
    if show_stats and len(all_x) > 1:
        all_x = np.array(all_x)
        all_y = np.array(all_y)
        
        # Remove any NaN values
        mask = ~(np.isnan(all_x) | np.isnan(all_y))
        if mask.sum() > 1:
            corr = np.corrcoef(all_x[mask], all_y[mask])[0, 1]
            ax.text(0.05, 0.95, f'r = {corr:.3f}', 
                   transform=ax.transAxes, fontsize=fontsize-2,
                   verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Labels and formatting
    if title:
        ax.set_title(title, fontsize=fontsize + 5)
    ax.set_xlabel(xlabel, fontsize=fontsize)
    ax.set_ylabel(ylabel, fontsize=fontsize)
    ax.tick_params(labelsize=fontsize - 2)
    ax.grid(True, alpha=0.3)
    
    if show_legend:
        ax.legend(fontsize=fontsize - 2)
    
    return ax


def plot_scatter_panel(
    group_analysis,
    x_var: Dict,
    y_vars: List[Dict],
    time_point: float = 50,
    time_window: Optional[float] = None,
    figsize: Optional[Tuple[int, int]] = None,
    fontsize: int = 15,
    suptitle: Optional[str] = None,
    show_stats: bool = True,
    add_trendline: bool = False,
    n_cols: int = 3
) -> Tuple[plt.Figure, np.ndarray]:
    """
    Create panel of scatter plots comparing one variable against multiple others.
    
    Perfect for exploratory analysis to understand what drives certain outcomes.
    
    Args:
        group_analysis: GroupJamAnalysis object
        x_var: Dictionary defining x variable:
               {'type': 'ligament', 'name': 'mPFL', 'params': {}}
        y_vars: List of dictionaries defining y variables:
                [{'type': 'muscle', 'name': 'recfem_r', 'params': {'outcome': 'actuation'}},
                 {'type': 'coordinate', 'name': 'knee_flex_r', 'params': {}}, ...]
        time_point: Time point in % stance (0-100)
        time_window: Optional window size for averaging
        figsize: Figure size (auto-calculated if None)
        fontsize: Font size
        suptitle: Super title
        show_stats: Show correlation coefficients
        add_trendline: Add linear trendlines
        n_cols: Number of columns in panel
        
    Returns:
        Tuple of (figure, axes_array)
        
    Example:
        ```python
        # Compare mPFL force against various muscles and kinematics
        x_var = {'type': 'ligament', 'name': 'mPFL'}
        y_vars = [
            {'type': 'muscle', 'name': 'recfem_r', 'params': {'outcome': 'actuation'}},
            {'type': 'muscle', 'name': 'vaslat_r', 'params': {'outcome': 'actuation'}},
            {'type': 'coordinate', 'name': 'knee_flex_r'},
            {'type': 'coordinate', 'name': 'knee_add_r'}
        ]
        fig, axes = plot_scatter_panel(group_analysis, x_var, y_vars, time_point=50)
        ```
    """
    # Extract x variable data
    x_data_full = group_analysis.extract_values_at_time(
        var_type=x_var['type'],
        var_name=x_var['name'],
        time_point=time_point,
        time_window=time_window,
        var_params=x_var.get('params', {})
    )
    
    # Convert to simple dict of arrays
    x_data = {group: data['values'] for group, data in x_data_full.items()}
    
    # Setup figure
    n_vars = len(y_vars)
    n_rows = (n_vars + n_cols - 1) // n_cols
    
    if figsize is None:
        figsize = (6 * n_cols, 5 * n_rows)
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
    if n_vars == 1:
        axes = np.array([axes])
    axes = axes.flatten()
    
    # Create label for x variable
    x_label = _get_variable_label(x_var)
    
    # Plot each y variable
    for idx, y_var in enumerate(y_vars):
        # Extract y variable data
        y_data_full = group_analysis.extract_values_at_time(
            var_type=y_var['type'],
            var_name=y_var['name'],
            time_point=time_point,
            time_window=time_window,
            var_params=y_var.get('params', {})
        )
        
        # Convert to simple dict of arrays
        y_data = {group: data['values'] for group, data in y_data_full.items()}
        
        # Create label for y variable
        y_label = _get_variable_label(y_var)
        
        # Plot
        plot_variable_scatter(
            x_data, y_data,
            ax=axes[idx],
            xlabel=x_label,
            ylabel=y_label,
            fontsize=fontsize,
            show_legend=(idx == 0),  # Only show legend on first plot
            show_stats=show_stats,
            add_trendline=add_trendline
        )
    
    # Hide extra subplots
    for idx in range(n_vars, len(axes)):
        axes[idx].set_visible(False)
    
    # Add suptitle with time info
    if suptitle is None:
        if time_window is None:
            suptitle = f'Variable Relationships at {time_point:.0f}% Stance'
        else:
            suptitle = f'Variable Relationships at {time_point:.0f}% Stance (±{time_window/2:.1f}% window)'
    
    fig.suptitle(suptitle, fontsize=fontsize + 10)
    plt.tight_layout()
    
    return fig, axes


def _get_variable_label(var_dict: Dict) -> str:
    """
    Helper function to generate human-readable label for a variable.
    
    Args:
        var_dict: Variable dictionary with 'type', 'name', and optional 'params'
        
    Returns:
        Human-readable label string
    """
    var_type = var_dict['type']
    var_name = var_dict['name']
    var_params = var_dict.get('params', {})
    
    # Get base label
    if var_type == 'coordinate':
        base_label = COORDINATE_LABELS.get(var_name, var_name)
        # Data is in raw H5 units (meters for translations, radians for rotations).
        # Note: plot_coordinate_comparison handles its own unit conversions (m→mm, rad→deg).
        if any(trans in var_name for trans in ['tx', 'ty', 'tz']):
            unit = ' (m)'
        else:
            unit = ' (rad)'
        return base_label + unit
    
    elif var_type == 'muscle':
        base_label = MUSCLE_LABELS.get(var_name, var_name)
        outcome = var_params.get('outcome', 'actuation')
        if outcome == 'actuation':
            return base_label + ' Force (N)'
        else:
            return base_label + f' {outcome}'
    
    elif var_type == 'ligament':
        base_label = LIGAMENT_LABELS.get(var_name, var_name)
        return base_label + ' Force (N)'
    
    elif var_type == 'contact':
        region = var_params.get('region', 4)
        outcome = var_params.get('outcome', 'regional_contact_force')
        region_label = REGION_LABELS.get(region, f'Region {region}')
        
        if 'pressure' in outcome:
            unit = ' (MPa)'
        elif 'area' in outcome:
            unit = ' (cm²)'
        else:
            unit = ' (N)'
        
        outcome_type = outcome.replace('regional_', '').replace('_', ' ').title()
        return f'{region_label} {outcome_type}{unit}'
    
    else:
        return var_name

