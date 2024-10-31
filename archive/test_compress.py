# Compare compression for text files

from pathlib import Path
import gzip
import h5py
import time
import lzma
import json
import numpy as np


txt_dir = Path("/home/oconnorlab/Desktop/test_compress")


txt_list = list(txt_dir.glob("*.txt"))

for txt_file in txt_list:

    # Get file size
    txt_file_size = txt_file.stat().st_size
    print(f"File size: {txt_file_size}")
    start_time = time.time()
    with open(txt_file, "rb") as f:
        txt = f.read()
    stop_time = time.time()
    print(f"Read time: {stop_time - start_time}")

    # Compress file with gzip
    start_time = time.time()
    with open(txt_file, "rb") as f:
        with gzip.open(txt_file.with_suffix(".txt.gz"), "wb") as g:
            g.writelines(f)
    stop_time = time.time()

    # Get compressed file size
    compressed_file = txt_file.with_suffix(".txt.gz")
    compressed_file_size = compressed_file.stat().st_size
    print(f"GZip Compressed file size: {compressed_file_size}")
    print(f"Compression time: {stop_time - start_time}")

    start_time = time.time()
    with gzip.open(txt_file.with_suffix(".json.gz"), "rb") as f:
        txt = f.read()
    stop_time = time.time()
    print(f"Read time: {stop_time - start_time}")
    print("*" * 5)

    # # Compare with lzma
    # start_time = time.time()
    # with open(txt_file, "rb") as f:
    #     with lzma.open(txt_file.with_suffix(".json.xz"), "wb") as g:
    #         g.writelines(f)
    # stop_time = time.time()

    # # Get compressed file size
    # compressed_file = txt_file.with_suffix(".json.xz")
    # compressed_file_size = compressed_file.stat().st_size
    # print(f"LZMA Compressed file size: {compressed_file_size}")
    # print(f"Compression time: {stop_time - start_time}")

    # start_time = time.time()
    # with lzma.open(txt_file.with_suffix(".json.xz"), "rb") as f:
    #     txt = f.read()
    # stop_time = time.time()

    print(f"Read time: {stop_time - start_time}")
    print("*" * 5)

    with open(txt_file, "r") as f:
        data = [json.loads(line) for line in f]  # Assumes one JSON object per line

    # Assuming 'data' is a list of dictionaries
    with h5py.File("data.h5", "w") as h5f:
        # Iterate over entries and store them as datasets within the HDF5 file
        for idx, entry in enumerate(data):
            group = h5f.create_group(f"entry_{idx}")
            for key, value in entry.items():
                # Store each value with gzip compression
                group.create_dataset(key, data=np.array(value), compression="gzip")
