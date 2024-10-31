import gzip
import bz2
import lzma
import zlib
import time
import os
import pandas as pd


# Function to read the content of the text file
def read_file(file_path):
    with open(file_path, "rb") as f:
        return f.read()


# Function to write compressed content to a file (for gzip, bz2, lzma)
def write_compressed(file_path, content, mode="wb"):
    with open(file_path, mode) as f:
        f.write(content)


# Compression and time tracking function for each tool
def compress_and_measure(data, compressor, filename_ext):
    start_time = time.time()

    # Perform compression based on the selected tool
    if compressor == "gzip":
        compressed_data = gzip.compress(data)
    elif compressor == "bz2":
        compressed_data = bz2.compress(data)
    elif compressor == "lzma":
        compressed_data = lzma.compress(data)
    elif compressor == "zlib":
        compressed_data = zlib.compress(data)
    else:
        raise ValueError("Unsupported compressor")

    elapsed_time = time.time() - start_time

    # Save the compressed file to disk
    compressed_file = f"test_compressed.{filename_ext}"
    write_compressed(compressed_file, compressed_data)

    # Measure the size of the compressed file
    compressed_size = os.path.getsize(compressed_file)

    return compressed_size, elapsed_time


# Main comparison function
def compare_compression_tools(file_path):
    data = read_file(file_path)
    original_size = len(data)

    # Define the compressors to compare
    compressors = [("gzip", "gz"), ("bz2", "bz2"), ("lzma", "xz"), ("zlib", "zlib")]

    # Store results for comparison
    results = []

    # Iterate over each compressor and collect statistics
    for compressor, ext in compressors:
        compressed_size, elapsed_time = compress_and_measure(data, compressor, ext)
        compression_ratio = compressed_size / original_size
        results.append(
            {
                "Compressor": compressor,
                "Compressed Size (bytes)": compressed_size,
                "Compression Ratio": compression_ratio,
                "Time (seconds)": elapsed_time,
            }
        )

    # Display the comparison table
    df = pd.DataFrame(results)
    print(df)


# Run the comparison (replace 'your_file.txt' with the actual file path)
from pathlib import Path

compare_compression_tools(Path("/home/oconnorlab/Desktop/test_compress", "2024-09-05_15-22-45_state.txt"))
