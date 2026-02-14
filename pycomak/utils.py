import shutil
import glob
import os
import multiprocessing


def copy_file_names_with_strings(str_list, path, overwrite=False):
    """
    Copies files matching a list of string patterns from a source path to a 'paraview' subdirectory.

    For each string pattern in `str_list`, it finds matching files in `path` using `glob.glob`.
    Each found file is then copied to a 'paraview' subdirectory created within `path`.
    If the destination file already exists and overwrite is False, a message is printed and the copy is skipped.

    Args:
        str_list (list of str): A list of string patterns to match filenames (e.g., ['*.vtp', '*_data.sto']).
        path (str): The source directory containing the files to be copied.
        overwrite (bool, optional): If True, overwrite existing files. If False, skip existing files. Defaults to False.
    """
    destination_dir = os.path.join(path, 'paraview')
    os.makedirs(destination_dir, exist_ok=True)

    for j in str_list:
        final_list = glob.glob(os.path.join(path, j))
        for source in final_list:
            filename = os.path.basename(source)
            destination_file = os.path.join(destination_dir, filename)
            
            if os.path.exists(destination_file) and not overwrite:
                print(f"The file {destination_file} already exists. Skipping.")
            else:
                shutil.copy(source, destination_file)
                if overwrite:
                    print(f"Overwritten {destination_file} with {source}")
                else:
                    print(f"Copied {source} to {destination_file}")


def run_with_timeout(func, timeout, *args, **kwargs):
    """
    Runs a function in a separate process with a specified timeout.

    If the function execution time exceeds `timeout`, the process is terminated,
    and a TimeoutError is raised.

    Warning:
        Uses multiprocessing.Process, so the function runs in a **separate process**.
        Any in-memory state changes (e.g., model object modifications) will NOT be
        reflected in the calling process. Only use this for functions that persist
        their results to disk (e.g., settle sims, forsim).

    Args:
        func (callable): The function to execute.
        timeout (int or float): The maximum time (in seconds) to allow for function execution.
        *args: Positional arguments to pass to `func`.
        **kwargs: Keyword arguments to pass to `func`.

    Raises:
        TimeoutError: If the function execution exceeds the `timeout`.

    Prints:
        "Function timed out" if timeout occurs.
        "Function completed successfully" if completed within timeout.
    """
    # Create a separate process
    p = multiprocessing.Process(target=func, args=args, kwargs=kwargs)
    p.start()

    # Wait for the process to complete or the timeout
    p.join(timeout)

    if p.is_alive():
        p.terminate()  # Terminate the process if it exceeds the timeout
        print("Function timed out")
        raise TimeoutError("Function timed out.. it took too long to complete")
    else:
        print("Function completed successfully")