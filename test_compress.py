# Compare compression for text files

from pathlib import Path
import gzip
import h5py

txt_dir = Path("/home/oconnorlab/Desktop/test_compress")


txt_list = list(txt_dir.glob("*.txt"))

for txt_file in txt_list:

    # Get file size
    txt_file_size = txt_file.stat().st_size
    print(f"File size: {txt_file_size}")

    # Compress file with gzip
    with open(txt_file, "rb") as f:
        with gzip.open(txt_file.with_suffix(".json.gz"), "wb") as g:
            g.writelines(f)

    # Get compressed file size
    compressed_file = txt_file.with_suffix(".json.gz")
    compressed_file_size = compressed_file.stat().st_size
    print(f"Compressed file size: {compressed_file_size}")

    # Calculate compression ratio
    compression_ratio = txt_file_size / compressed_file_size
    print(f"Compression ratio: {compression_ratio}")

    print("*" * 5)

    # Compare compression for HDF5 files
    with h5py.File(txt_file.with_suffix(".h5"), "w") as f:
        f.create_dataset("data", data="data")

    # Get file size
    hd5_file_size = txt_file.with_suffix(".h5").stat().st_size
    print(f"File size: {hd5_file_size}")

    # Compare compression ratio
    comp_ratio = txt_file_size / hd5_file_size
    print(f"Compression ratio: {comp_ratio}")

    print("*" * 5)
