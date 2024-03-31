# Debayer, compress to mp4, transfer to NAS, and delete on disk

import time
from pathlib import Path
import subprocess
from debayer_images import debayer_images_in_dir
from record_multi_cam_params import CAMERA_NAMES_DICT_COLOR, CAMERA_NAMES_DICT_MONO




# Saves to NAS
if __name__ == "__main__":

    # Set base directory
    YYYYMMDD = time.strftime("%Y-%m-%d")
    YYYYMMDD = "2024-02-12"
    BASE_DIR = Path("/home/oconnorlab/Data", YYYYMMDD)

    uncompressed_dir = Path(BASE_DIR, "cameras")
    trial_list = list(uncompressed_dir.glob("*"))
    cams_to_debayer = [c for c in CAMERA_NAMES_DICT_COLOR.values()]
    cam_list = cams_to_debayer
    cam_list.extend([c for c in CAMERA_NAMES_DICT_MONO.values()])

    trial = trial_list[0]

    # Debayer
    # dirs_to_debayer = [Path(trial, cam) for cam in cam_list]
    # for cam in dirs_to_debayer:
    #     debayer_images_in_dir(cam)

    # Compress
    cam_list_debayered = [c for c in CAMERA_NAMES_DICT_MONO.values()]
    cam_list_debayered.extend([c + "-debayered" for c in CAMERA_NAMES_DICT_COLOR.values()])
    for cam in cam_list_debayered:
        compress_dir(Path(trial, cam))

    # for trial in trial_list:

    #     dirs_to_debayer = [Path(trial, cam) for cam in cams_to_debayer]

    #     # # Debayer all images
    #     # for cam in dirs_to_debayer:
    #     #     debayer_images_in_dir(cam)

    # # COMPRESS IMAGES
    # trial_list = list(uncompressed_dir.glob("*"))
    # for trial in trial_list:
    #     cam_list = list(trial.glob("*"))
    #     # print(cam_list)

    #     # Converts all images into compressed mp4 files
    #     for cam in cam_list:

    #         # Skip the color camera directories that are not debayered
    #         if cam.stem in CAMERA_NAMES_DICT_COLOR.values():
    #             continue

    #         print(cam)
    #         compress_dir(cam)
