import os
import time


def write_large_file(file_name, size):
    with open(file_name, "wb") as file:
        file.write(os.urandom(size))


def write_many_small_files(folder_name, file_count, size):
    os.makedirs(folder_name, exist_ok=True)
    for i in range(file_count):
        file_name = os.path.join(folder_name, f"file_{i}.bin")
        write_large_file(file_name, size)


def measure_time(func, *args):
    start_time = time.time()
    func(*args)
    return time.time() - start_time


# File sizes and counts
one_mb = 1024 * 1024  # 1MB
one_gb = one_mb * 1024  # 1GB
num_files = 1000

# Measure and print time for writing 1GB file
time_1gb = measure_time(write_large_file, "one_gb_file.bin", one_gb)
print(f"Time to write 1GB file: {time_1gb} seconds")

# Measure and print time for writing 1000 1MB files
time_1000x1mb = measure_time(write_many_small_files, "small_files", num_files, one_mb)
print(f"Time to write 1000 1MB files: {time_1000x1mb} seconds")

# Measure and print time for writing 1000000 1KB files
time_1000000x1kb = measure_time(write_many_small_files, "small_files", num_files * 1000, 1024)
