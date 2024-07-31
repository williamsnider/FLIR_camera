# Compress mp4 files
from pathlib import Path
import subprocess
import time
import datetime
import cv2
import os
from tqdm import tqdm
import multiprocessing
from record_multi_cam_params import SAVE_LOCATION


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
    output_name = Path(mp4_filename.parent, mp4_filename.stem[:5] + mp4_filename.suffix)
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


def worker(filename_queue):

    while filename_queue.qsize() > 0:
        print(filename_queue.qsize())
        mp4_filename = filename_queue.get()
        compress_mp4(mp4_filename, cq=CQ)


# Find mp4 files that are  not changing in size

if __name__ == "__main__":

    CQ = 30

    YYYY_MM_DD = datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d")

    TRIALS_DIR = Path(SAVE_LOCATION, YYYY_MM_DD, "cameras")

    while True:
        time.sleep(1)

        unchanged_files = find_unchanged_mp4s(TRIALS_DIR)
        unchanged_files.sort()  # Sort by time

        # Compress mp4 files
        for mp4_filename in tqdm(unchanged_files):
            compress_mp4(mp4_filename, cq=CQ)

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
