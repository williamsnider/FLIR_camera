# Compress mp4 files
from pathlib import Path
import subprocess
import time
import datetime
import cv2
import os
from tqdm import tqdm
import shutil


def find_unchanged_mp4s(trials_dir):

    # Get list of all mp4 files in subdirectories
    mp4_files = []
    for subdir in trials_dir.glob("*"):
        mp4_files += list(subdir.glob("*-orig.mp4"))

    # Get size of each mp4 file
    size_dict = {}
    for mp4_file in mp4_files:
        size_dict[mp4_file] = mp4_file.stat().st_size

    # Wait 1 second
    time.sleep(1)
    unchanged_files = []
    for mp4_file in mp4_files:
        if mp4_file.stat().st_size == size_dict[mp4_file]:
            unchanged_files.append(mp4_file)

    return unchanged_files


def copy_mp4(mp4_list):

    for mp4_filename in mp4_list:
        output_name = Path(
            mp4_filename.parents[2],
            "cameras_full_res",
            mp4_filename.parts[-2],
            mp4_filename.name.replace("-orig", "_full_res"),
        )
        output_name.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(mp4_filename, output_name)


def get_num_frames(mp4_filename):

    # Get the number of frames in the video
    cmd_string = f"/usr/bin/ffprobe -v error -select_streams v:0 -show_entries stream=nb_frames -of default=nokey=1:noprint_wrappers=1 {mp4_filename}"
    result = subprocess.run(
        cmd_string,
        shell=True,
        capture_output=True,
        text=True,
    )
    num_frames_vid = int(result.stdout)

    return num_frames_vid


def compress_mp4(mp4_filename, cq=34, preset="slow"):
    # Compress mp4 file
    input_name = mp4_filename
    output_name = Path(mp4_filename.parent, mp4_filename.stem.replace("-orig", "") + mp4_filename.suffix)
    # Get
    cmd_string = (
        f"nice -n -19 ffmpeg -y -hwaccel cuda -i {input_name} -c:v h264_nvenc -cq {cq} -preset {preset} {output_name}"
    )

    output = subprocess.run(
        cmd_string,
        shell=True,
        cwd=mp4_filename.parent,
        capture_output=True,
    )

    # Confirm input and output have same number of frames
    attempt_count = 0
    while attempt_count < 10:
        try:
            num_input = get_num_frames(mp4_filename)
            num_output = get_num_frames(output_name)
            if num_input == num_output > 0:
                os.remove(input_name)
                break
        except:
            attempt_count += 1
            time.sleep(0.25)

    # Test if successful deletion
    if input_name.exists():
        print(f"Failed to delete {input_name}")
    # num_input = get_num_frames(mp4_filename)
    # num_output = get_num_frames(output_name)

    # if num_input == num_output > 0:
    #     os.remove(input_name)


import multiprocessing as mp
from tqdm import tqdm


def compress_dir(trial_dir, cq):
    print("Compressing directory: ", trial_dir)
    timestamp_list = [d for d in trial_dir.glob("*") if d.is_dir()]
    timestamp_list.sort()

    # Copy subset of these trials
    gap = 50
    for timestamp in timestamp_list[::gap]:
        mp4_files_to_copy = list(timestamp.rglob("*-orig.mp4"))
        copy_mp4(mp4_files_to_copy)

    # Compress original mp4s in parallel
    unchanged_files = find_unchanged_mp4s(trial_dir)
    unchanged_files.sort()

    # Create a pool of workers
    for mp4_filename in tqdm(unchanged_files):
        compress_mp4(mp4_filename, cq=cq)


# def worker(filename_queue):

#     while filename_queue.qsize() > 0:
#         print(filename_queue.qsize())
#         mp4_filename = filename_queue.get()
#         compress_mp4(mp4_filename, cq=CQ)


# Find mp4 files that are  not changing in size

if __name__ == "__main__":

    CQ = 30
    SAVE_LOCATION = Path("/mnt/Data4TB")

    YYYY_MM_DD_list = [d for d in SAVE_LOCATION.glob("*-*-*")]
    YYYY_MM_DD_list.sort()
    # YYYY_MM_DD_list = [datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d")]

    # Create list of timestamps (all directories)
    for YYYY_MM_DD in YYYY_MM_DD_list:

        TRIALS_DIR = Path(SAVE_LOCATION, YYYY_MM_DD, "cameras")

        compress_dir(TRIALS_DIR, cq=CQ)

    # TRIALS_DIR = Path(SAVE_LOCATION, YYYY_MM_DD, "cameras")
    # print(TRIALS_DIR)
    # # while True:
    # time.sleep(1)

    # unchanged_files = find_unchanged_mp4s(TRIALS_DIR)
    # unchanged_files.sort()  # Sort by time

    # # Copy subset of mp4 files in high res
    # gap = 50
    # mp4_list = unchanged_files[::gap]
    # copy_mp4(mp4_list)

    # # Compress mp4 files
    # for mp4_filename in tqdm(unchanged_files):
    #     compress_mp4(mp4_filename, cq=CQ)
    # # Compress mp4 files
    # filename_queue = multiprocessing.Queue()
    # for mp4_filename in unchanged_files:
    #     filename_queue.put(mp4_filename)

    # num_workers = 8
    # workers = []
    # for i in range(num_workers):
    #     my_worker = multiprocessing.Process(target=worker, args=(filename_queue,))
    #     workers.append(worker)
    #     my_worker.start()

    # for worker in workers:
    #     worker.join()
