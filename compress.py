# Workflow to compare compression and quality
from pathlib import Path
import subprocess
import os
import time
import cv2
import tqdm
import select
import sys
import datetime

COMPRESSION_LEVEL = 34


def get_input():
    readable, _, _ = select.select([sys.stdin], [], [], 0)
    if readable:
        input_line = sys.stdin.readline()
        return input_line.strip()  # Remove the newline at the end
    return None  # Return None if no input is available


def compress_dir(input_dir, FPS, input_format, output_name, overwrite_existing=False):

    assert input_format in [".bmp", ".jpg"], "Input format must be .bmp or .jpg"

    # # Make output directory
    output_name.parent.mkdir(exist_ok=True, parents=True)

    # Check that input_dir contains images of the requested type
    file_list = list(input_dir.glob(f"*{input_format}"))
    assert len(file_list) > 0, f"No {input_format} files found in {input_dir}"

    # Overwrite check
    if overwrite_existing == False:
        if output_name.exists():
            print(f"File already exists: {output_name}")
            return

    # # Compress using ffmpeg at lowest process priority (19)
    # # encoder = "libx264"
    # encoder = "h264_nvenc"
    # cmd_string_CPU = f"nice -n 19 ffmpeg -y -framerate {FPS} -pattern_type glob -i '{input_dir}/*{input_format}' -c:v {encoder} -vf format=yuv420p -crf {COMPRESSION_LEVEL} {output_name}"

    # cmd_string_GPU = f"nice -n 19 /usr/bin/ffmpeg -hwaccel cuda -y -framerate {FPS} -pattern_type glob -i '{input_dir}/*{input_format}' -c:v h264_nvenc -preset default -cq {COMPRESSION_LEVEL} {output_name}"
    cmd_string_GPU = f"nice -n 19 /usr/bin/ffmpeg -hwaccel cuda -y -framerate {FPS} -pattern_type glob -i '{input_dir}/*{input_format}' -c:v h264_nvenc -preset default -cq {COMPRESSION_LEVEL} {output_name}"

    # Alter env to ensure that base ffmpeg, not conda's, is used.
    env = os.environ.copy()

    # Modify the PATH environment variable
    # Prepend the directory of the desired FFmpeg executable to ensure it's chosen first
    env["PATH"] = "/usr/bin:" + env["PATH"]

    print(cmd_string_GPU)
    out = subprocess.run(
        cmd_string_GPU,
        shell=True,
        check=True,
        env=env,
    )
    print(out.stdout)

    # Check that conversion was successful
    if out.returncode != 0:
        print(out.stderr)
        return False
    else:
        return True

    # process = subprocess.Popen(cmd_string, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # # Iterate over and print each line of output as it comes
    # while True:
    #     output = process.stdout.readline()
    #     if output == "" and process.poll() is not None:
    #         break
    #     if output:
    #         print(output.strip())

    # # Check if there were any errors
    # err = process.stderr.read()
    # if err:
    #     print("Error:\n", err.strip())

    # # Check the return code
    # if process.returncode == 0:
    #     print("Command executed successfully")
    # else:
    #     print("Command failed with return code", process.returncode)

    # Test if successful
    # assert out.returncode == 0, f"Compression failed: {out.stderr}"
    # print(cmd_string)


def write_file_list(input_dir, input_format, output_name):

    assert input_format in [".bmp", ".jpg"], "Input format must be .bmp or .jpg"

    # Get file list
    file_list = list(input_dir.glob(f"*{input_format}"))
    file_list.sort()

    # Write to txt file
    assert output_name.suffix == ".txt", "Output name must have .txt suffix"
    with open(output_name, "w") as f:
        msg = ""
        for i, fname in enumerate(file_list):
            msg += f"{i}, '{fname}'\n"
        f.write(msg)


def delete_images(input_dir, input_format):
    # file_list = list(input_dir.glob(f"*{input_format}"))

    # for file in file_list:
    #     file.unlink()

    # Create rm command as this cleans up faster than unlink
    cmd_string = f"rm {input_dir}/*{input_format}"
    out = subprocess.run(cmd_string, shell=True, check=True)


def compress_and_delete(input_dir, FPS, input_format, output_prefix, overwrite_existing=False):

    # Count number of .txt, .mp4, .input_format files in input_dir
    num_txt = len(list(input_dir.glob("*.txt")))
    num_mp4 = len(list(input_dir.glob("*.mp4")))
    num_files = len(list(input_dir.glob(f"*{input_format}")))

    # Check if compression already done
    compression_done = check_correct_num_frames(input_dir, input_format)

    if compression_done == False:

        # Write file list
        txt_filename = output_prefix.with_suffix(".txt")
        write_file_list(input_dir, input_format, txt_filename)

        # Execute command
        mp4_filename = output_prefix.with_suffix(".mp4")
        compression_done = compress_dir(
            input_dir, FPS, input_format, mp4_filename, overwrite_existing=overwrite_existing
        )

    # Delete files if compression successful
    if compression_done:
        delete_images(input_dir, input_format)
    else:
        print(f"Compression failed for {input_dir}")

    # # Delete originals if mp4 exists
    # if mp4_filename.exists() and successful_compression:
    #     delete_images(input_dir, input_format)


def find_uncompressed_directories(base_dir, input_format):

    # Get nested directories
    subdirs = [p for p in base_dir.rglob("*") if p.is_dir()]
    subdirs.append(base_dir)  # Add base_dir
    subdirs.sort()

    # Find lengths of dirs containing input_format
    uncompressed_dirs_lengths = {}
    for subdir in subdirs:
        file_list = list(subdir.glob(f"*{input_format}"))
        num_files = len(file_list)
        uncompressed_dirs_lengths[subdir] = num_files

    # Pause to allow more files to be written
    time.sleep(0.5)

    # Check again, store unchanged dirs
    uncompressed_dirs = []
    for subdir in subdirs:
        file_list = list(subdir.glob(f"*{input_format}"))
        num_files = len(file_list)
        if (num_files == uncompressed_dirs_lengths[subdir]) & (num_files > 0):
            uncompressed_dirs.append(subdir)

    return uncompressed_dirs


def debayer_image(filename):
    """Debayers a raw Bayer image and returns a grayscale image.

    Args:
        filename (Path): Path to the input raw Bayer image.

    Returns:
        ndarray: Debayered grayscale image.
    """
    # Load the raw Bayer image as a single-channel grayscale image
    raw_img = cv2.imread(str(filename), cv2.IMREAD_GRAYSCALE)

    if type(raw_img) == type(None):
        return None

    # Perform debayering
    debayered_img = cv2.cvtColor(raw_img, cv2.COLOR_BayerBG2BGR)

    # Convert to grayscale
    grayscale_img = cv2.cvtColor(debayered_img, cv2.COLOR_BGR2GRAY)

    return grayscale_img


def debayer_images_in_dir(img_dir, bayer_string="-bayer"):

    # Create save directory if it doesn't exist
    save_dir = Path(str(img_dir).replace(bayer_string, ""))
    save_dir.mkdir(parents=True, exist_ok=True)

    # Get list of image files
    img_list = list(img_dir.glob("*.bmp"))
    img_list.sort()

    # Iterate through images with progress bar
    for filename in img_list:
        # Perform debayering
        debayered = debayer_image(filename)

        # Replace incomplete images with blank
        if debayered is None:
            print(f"Error debayering {filename}")
            debayered = cv2.imread(str(img_list[0])) * 0.0  # Create black image

        # Save debayered image
        savename = str(Path(save_dir, filename.name)).replace(bayer_string, "")
        cv2.imwrite(savename, debayered)

    # Delete original dir
    cmd_string = f"rm -r {img_dir}"
    out = subprocess.run(cmd_string, shell=True, check=True)


def check_correct_num_frames(input_dir, input_format):

    # Test if mp4 file present
    mp4_list = list(input_dir.glob("*.mp4"))
    if len(mp4_list) == 0:
        return False
    else:
        video_path = mp4_list[0]

    # Get number of frames in mp4
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print("Error: Could not open video.")
        return False
    else:
        # Get the number of frames in the video
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    # Get number of frames in txt
    txt_path = list(input_dir.glob("*.txt"))[0]
    with open(txt_path, "r") as f:
        lines = f.readlines()
        num_txt = len(lines)

    # Check if number of frames in txt matches number of frames in video
    if frame_count != num_txt:
        print(f"Number of frames in txt and video do not match in {input_dir}")
        return False

    return True


# def check_finished_dir(img_dir, input_format):

#     # Get number of frames in mp4
#     video_path = list(img_dir.glob("*.mp4"))[0]
#     cap = cv2.VideoCapture(video_path)

#     # Check if video opened successfully
#     if not cap.isOpened():
#         print("Error: Could not open video.")
#         return False
#     else:
#         # Get the number of frames in the video
#         frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

#     # Release the VideoCapture object
#     cap.release()

#     # Get number of frames in txt
#     txt_path = list(img_dir.glob("*.txt"))[0]
#     with open(txt_path, "r") as f:
#         lines = f.readlines()
#         num_txt = len(lines)

#     # Check if number of frames in txt matches number of frames in video
#     if frame_count != num_txt:
#         print(f"Number of frames in txt and video do not match in {img_dir}")
#         return False

#     return True


if __name__ == "__main__":

    # FPS = 100.0
    # BASE_DIR = Path("/mnt/Data4TB/2024-03-05/cameras")
    # IMG_SUFFIX = ".bmp"

    YYYY_MM_DD = datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d")

    FPS = 30.0
    BASE_DIR = Path("/mnt/Data4TB/", YYYY_MM_DD, "webcam")
    IMG_SUFFIX = ".jpg"

    while True:

        time.sleep(5)

        # Find uncompressed directories
        uncompressed_dirs = find_uncompressed_directories(BASE_DIR, IMG_SUFFIX)

        if len(uncompressed_dirs) == 0:
            continue

        # Compress and delete images
        for i, u in enumerate(uncompressed_dirs):
            print("*" * 20)
            print("Press ENTER to exit loop, not CTRL+C!")
            print(u)
            print(i, "/", len(uncompressed_dirs))

            # Debayer if necessary
            if "-bayer" in u.stem:
                debayer_images_in_dir(u)
                u = Path(str(u).replace("-bayer", ""))  # Update to new directory name

            # Construct prefix for saving mp4 and txt file
            output_prefix = Path(u, u.stem + "_" + u.parent.stem)
            compress_and_delete(u, FPS, IMG_SUFFIX, output_prefix, overwrite_existing=True)

            #       # Check for user input
            if get_input() == "":
                print("Enter pressed, exiting loop.")
                break


# Snakeviz command
# snakeviz compress.py
