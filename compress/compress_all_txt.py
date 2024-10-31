import gzip
from pathlib import Path
import tqdm
from concurrent.futures import ThreadPoolExecutor
import os


def compress_txt_file(txt_file):
    try:
        # Read the original file in binary mode
        with open(txt_file, "rb") as f:
            txt = f.read()

        # Compress the file with gzip
        with gzip.open(txt_file.with_suffix(".txt.gz"), "wb") as g:
            g.write(txt)

        # Load the compressed file to verify integrity
        with gzip.open(txt_file.with_suffix(".txt.gz"), "rb") as f:
            txt_compressed = f.read()

        # Compare original and compressed content for consistency
        assert txt == txt_compressed, f"Integrity check failed for {txt_file}"

        # Optionally, delete the original file
        txt_file.unlink()

    except Exception as e:
        print(f"Error processing {txt_file}: {e}")


def compress_all_files_in_parallel(txt_list, max_workers=4):
    # Use ThreadPoolExecutor for multithreading
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Display progress bar with tqdm
        list(tqdm.tqdm(executor.map(compress_txt_file, txt_list), total=len(txt_list)))


if __name__ == "__main__":
    txt_dir = Path("/mnt/Data4TB")

    # Get a list of all .txt files
    txt_list = [f for f in txt_dir.rglob("*.txt") if "robot_state_data" in f.parts]

    # Compress all files in parallel using multiple threads
    max_workers = os.cpu_count() * 1
    print(f"Using {max_workers} workers.")
    compress_all_files_in_parallel(txt_list, max_workers=max_workers)  # Adjust max_workers based on your CPU
