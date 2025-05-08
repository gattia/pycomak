import shutil
import glob
import os
import multiprocessing


def copy_file_names_with_strings(str_list, path):
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