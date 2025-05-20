import shutil
import glob
import os
import multiprocessing


def copy_file_names_with_strings(str_list, path):
    """
    Copies files matching a list of string patterns from a source path to a 'paraview' subdirectory.

    For each string pattern in `str_list`, it finds matching files in `path` using `glob.glob`.
    Each found file is then copied to a 'paraview' subdirectory created within `path`.
    If the destination file already exists, a message is printed, and the copy is skipped.

    Args:
        str_list (list of str): A list of string patterns to match filenames (e.g., ['*.vtp', '*_data.sto']).
        path (str): The source directory containing the files to be copied.
    """
    destination = os.path.join(path, 'paraview')
    os.makedirs(destination, exist_ok=True)

    for j in str_list:
        final_list = glob.glob(os.path.join(path, j))
        for source in final_list:
            if not os.path.exists(destination):
                shutil.copy(source, destination)
            else:
                print(f"The file {destination} already exists.")


def run_with_timeout(func, timeout, *args, **kwargs):
    """
    Runs a function in a separate process with a specified timeout.

    If the function execution time exceeds `timeout`, the process is terminated,
    and a TimeoutError is raised.

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