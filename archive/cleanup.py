import os
import subprocess
import numpy as np


def get_free_space_gb(folder):
    """Get the free disk space in GB."""
    st = os.statvfs(folder)
    free_space_gb = st.f_bavail * st.f_frsize / 1024**3
    return free_space_gb


def create_large_file(file_path, size_gb):
    """Create a large file of specified size in GB using dd."""
    size_bytes = size_gb * 1024**3
    subprocess.run(["dd", "if=/dev/zero", f"of={file_path}", f"bs=1M", f"count={size_bytes // (1024**2)}"])


drive_path = "/mnt/Data4TB"
file_size = 100  # GB
if __name__ == "__main__":

    all_space_filled = False
    file_count = 0
    while all_space_filled == False:
        free_space_GB = get_free_space_gb(drive_path)
        if free_space_GB < file_size:
            all_space_filled = True
            break
        else:
            file_path = os.path.join(drive_path, f"large_file_{file_count}.dat")
            create_large_file(file_path, file_size)
            file_count += 1
            print(f"Created file {file_path} with size {file_size}GB")
