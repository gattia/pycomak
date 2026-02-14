"""
Shared fixtures for pycomak test suite.

Provides:
- create_h5: Factory for generating synthetic H5 files matching JamAnalysis expectations
- make_jam: Factory for creating pre-populated JamAnalysis objects (no H5 needed)
"""

import numpy as np
import h5py
import pytest


@pytest.fixture
def create_h5(tmp_path):
    """
    Factory fixture that creates synthetic H5 files matching the structure
    that JamAnalysis._process_*_fast() expects.

    Returns a callable:
        create_h5(
            filename='test.h5',
            n_timesteps=101,
            muscles=None,         # dict of {name: [outcomes]}
            ligaments=None,       # dict of {name: [outcomes]}
            contacts=None,        # dict of {contact_name: {cartilage: n_regions}}
            coordinates=None,     # list of coordinate names
            comak_items=None,     # list of comak dataset names
            data_fill='linear',   # 'zeros', 'random', 'linear', or callable(shape)->array
        ) -> pathlib.Path
    """
    _counter = [0]

    def _create(
        filename=None,
        n_timesteps=101,
        muscles=None,
        ligaments=None,
        contacts=None,
        coordinates=None,
        comak_items=None,
        data_fill="linear",
    ):
        if filename is None:
            filename = f"test_{_counter[0]}.h5"
            _counter[0] += 1

        filepath = tmp_path / filename

        def _fill(shape, seed=None):
            if data_fill == "zeros":
                return np.zeros(shape)
            elif data_fill == "random":
                rng = np.random.default_rng(seed)
                return rng.standard_normal(shape)
            elif data_fill == "linear":
                arr = np.empty(shape)
                lin = np.linspace(0, 1, shape[0])
                # Broadcast linear ramp along first axis
                arr[...] = lin.reshape(shape[0], *([1] * (len(shape) - 1)))
                return arr
            elif callable(data_fill):
                return data_fill(shape)
            else:
                raise ValueError(f"Unknown data_fill: {data_fill}")

        seed_counter = [0]

        def _next_seed():
            seed_counter[0] += 1
            return seed_counter[0]

        with h5py.File(filepath, "w") as f:
            # Time vector
            f.create_dataset("time", data=np.linspace(0, 1, n_timesteps))

            # Muscles
            if muscles:
                for muscle_name, outcomes in muscles.items():
                    for outcome in outcomes:
                        path = f"model/forceset/Muscle/{muscle_name}/{outcome}"
                        f.create_dataset(path, data=_fill((n_timesteps,), _next_seed()))

            # Ligaments
            if ligaments:
                for lig_name, outcomes in ligaments.items():
                    for outcome in outcomes:
                        path = f"model/forceset/Blankevoort1991Ligament/{lig_name}/{outcome}"
                        f.create_dataset(path, data=_fill((n_timesteps,), _next_seed()))

            # Contacts (Smith2018ArticularContactForce)
            if contacts:
                for contact_name, cartilage_dict in contacts.items():
                    for cartilage_name, n_regions in cartilage_dict.items():
                        base = f"model/forceset/Smith2018ArticularContactForce/{contact_name}/{cartilage_name}"

                        # total_contact_force: (n_timesteps, 3) Dataset
                        f.create_dataset(
                            f"{base}/total_contact_force",
                            data=_fill((n_timesteps, 3), _next_seed()),
                        )

                        # regional_contact_force: Group with region sub-datasets
                        for r in range(n_regions):
                            f.create_dataset(
                                f"{base}/regional_contact_force/{r}",
                                data=_fill((n_timesteps, 3), _next_seed()),
                            )

                        # Regional scalar datasets: (n_timesteps, n_regions)
                        for scalar_name in [
                            "regional_max_pressure",
                            "regional_mean_pressure",
                            "regional_contact_area",
                        ]:
                            f.create_dataset(
                                f"{base}/{scalar_name}",
                                data=_fill((n_timesteps, n_regions), _next_seed()),
                            )

            # Coordinates
            if coordinates:
                for coord_name in coordinates:
                    for item in ["value", "speed"]:
                        path = f"model/coordinateset/{coord_name}/{item}"
                        f.create_dataset(path, data=_fill((n_timesteps,), _next_seed()))

            # COMAK
            if comak_items:
                for item_name in comak_items:
                    f.create_dataset(f"comak/{item_name}", data=_fill((n_timesteps,), _next_seed()))

        return filepath

    return _create


@pytest.fixture
def make_jam():
    """
    Factory fixture that creates a JamAnalysis object with pre-populated attributes.
    No H5 files needed — useful for testing group_analysis and forsim criteria.

    Returns a callable:
        make_jam(
            n_timesteps=101,
            muscles=None,       # dict of {name: {outcome: array}}
            ligaments=None,     # dict of {name: {outcome: array}}
            contacts=None,      # nested dict matching forceset structure
            coordinates=None,   # dict of {name: {item: array}}
            comak=None,         # dict of {name: array}
        ) -> JamAnalysis
    """
    from pycomak.jam_analysis import JamAnalysis

    def _make(
        n_timesteps=101,
        muscles=None,
        ligaments=None,
        contacts=None,
        coordinates=None,
        comak=None,
    ):
        jam = JamAnalysis()
        jam.time = np.linspace(0, 1, n_timesteps)
        jam.num_time_steps = n_timesteps
        jam.num_files = 1

        # Build forceset
        if muscles:
            jam.forceset["Muscle"] = {}
            for name, outcomes in muscles.items():
                jam.forceset["Muscle"][name] = {}
                for outcome_name, data in outcomes.items():
                    jam.forceset["Muscle"][name][outcome_name] = data

        if ligaments:
            jam.forceset["Blankevoort1991Ligament"] = {}
            for name, outcomes in ligaments.items():
                jam.forceset["Blankevoort1991Ligament"][name] = {}
                for outcome_name, data in outcomes.items():
                    jam.forceset["Blankevoort1991Ligament"][name][outcome_name] = data

        if contacts:
            jam.forceset["Smith2018ArticularContactForce"] = contacts

        # Build coordinateset
        if coordinates:
            for name, items in coordinates.items():
                jam.coordinateset[name] = {}
                for item_name, data in items.items():
                    jam.coordinateset[name][item_name] = data

        # COMAK
        if comak:
            jam.comak = comak

        return jam

    return _make
