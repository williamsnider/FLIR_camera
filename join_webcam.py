# Append webcam mp4 videos together, as well as txt files

from pathlib import Path
import subprocess
import time
import re


def natural_sort_key(path):
    # Extract numbers from the path and convert them to integers
    return [int(text) if text.isdigit() else text.lower() for text in re.split("(\d+)", str(path))]


YYYY_MM_DD = time.strftime("%Y-%m-%d")
SAVE_DIR = Path("/mnt/Data4TB", YYYY_MM_DD, "webcam")

# Get list of all subdirs
subdirs = SAVE_DIR.glob("*")
subdirs = [s for s in subdirs if s.is_dir()]
subdirs.sort()

# Append videos
combined_vid = Path(SAVE_DIR, f"{YYYY_MM_DD}_webcam.mp4")
combined_vid.parent.mkdir(parents=True, exist_ok=True)
combined_txt = Path(SAVE_DIR, f"{YYYY_MM_DD}_webcam.txt")

# Get list of all txt files
txt_files = []
for subdir in subdirs:
    txt_files += list(subdir.glob("*.txt"))

# Sorting the paths naturally
txt_files = sorted(txt_files, key=natural_sort_key)

# Write the txt files to a combined txt file
with open(combined_txt, "w") as outfile:
    for txt_file in txt_files:
        with open(txt_file, "r") as infile:
            outfile.write(infile.read())

# Get list of all video files
vid_files = []
for subdir in subdirs:
    vid_files += list(subdir.glob("*.mp4"))
vid_files = sorted(vid_files, key=natural_sort_key)

# Append the videos together
i_list = ["file " + str(vid_file) + " " for vid_file in vid_files]
i_string = "\n".join(i_list)
file_list = Path(SAVE_DIR, "file_list.txt")
file_list.write_text(i_string)


cmd_string = f"/usr/bin/ffmpeg -hwaccel cuda -f concat -safe 0 -i {file_list} -c copy -c:v h264_nvenc -cq 1 -preset slow {combined_vid}"
subprocess.run(
    cmd_string,
    shell=True,
)

# Confirm that the video contains same number of frames as txt

# # Get the number of frames in the video
# cmd_string = f"/usr/bin/ffprobe -v error -select_streams v:0 -show_entries stream=nb_frames -of default=nokey=1:noprint_wrappers=1 {combined_vid}"
# result = subprocess.run(
#     cmd_string,
#     shell=True,
#     capture_output=True,
#     text=True,
# )
# num_frames_vid = int(result.stdout)

# # Get the number of lines in the txt file
# num_lines_txt = sum(1 for line in open(combined_txt))

# # Check if the number of frames in the video matches the number of lines in the txt file
# if num_frames_vid != num_lines_txt:
#     print(f"Number of frames in video ({num_frames_vid}) does not match number of lines in txt file ({num_lines_txt})")
# else:
#     # Delete the input videos and txt files
#     for subdir in subdirs:
#         cmd_string = f"rm -r {subdir}"
#         subprocess.run(
#             cmd_string,
#             shell=True,
#         )

#     # Delete file list
#     cmd_string = f"rm {file_list}"
#     subprocess.run(
#         cmd_string,
#         shell=True,
#     )

#     print("Videos and txt files deleted")
