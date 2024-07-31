# Debayer cameras, produce individual videos, and produce concatenated videos
from debayer_images import debayer_images_in_dir
from pathlib import Path
import cv2
import os

CAMS_TO_DEBAYER = ["camBo", "camTR"]
CONCAT_ORDER = [
    "camTL",
    "camTo",
    "camTR",
    "camBL",
    "camBo",
    "camBR",
]


def process_trial(trial_dir):
    # Debayer images
    for cam in CAMS_TO_DEBAYER:
        img_dir = Path(trial_dir, cam)
        debayer_images_in_dir(img_dir)

    # Concatenate images in 2x3 grid
    image_groups = []
    for cam in CONCAT_ORDER:
        if cam in CAMS_TO_DEBAYER:
            img_dir = Path(trial_dir, cam + "-debayered")
        else:
            img_dir = Path(trial_dir, cam)
        img_list = list(img_dir.glob("*.bmp"))
        img_list.sort()
        image_groups.append(img_list)
    image_groups_inv = list(zip(*image_groups))

    # Concatenate images in 2x3 grid
    for i, img_group in enumerate(image_groups_inv):
        # Load all images into memory
        img_list = [cv2.imread(str(p)) for p in img_group]

        # Prepare the 2x3 grid
        rows = [cv2.hconcat(img_list[i : i + 3]) for i in range(0, len(img_list), 3)]
        # Concatenate the rows to complete the grid
        im_grid = cv2.vconcat(rows)

        # Construct the save path and write the concatenated image
        img_num = img_group[0].stem.split("-")[-1]
        concat_name = Path(trial_dir, "concat", f"concat-{img_num}.bmp")
        concat_name.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(concat_name), im_grid)

    # Make videos of concatenated images with ffmpeg (compress)
    img_type_list = (
        [c + "-debayered" for c in CAMS_TO_DEBAYER] + [c for c in CONCAT_ORDER if c not in CAMS_TO_DEBAYER] + ["concat"]
    )
    for fps in [20, 100]:
        for img_type in img_type_list:
            img_dir = Path(trial_dir, img_type)
            vid_dir = Path(trial_dir, "videos")
            vid_dir.mkdir(parents=True, exist_ok=True)
            cmd_string = f"ffmpeg -framerate {fps} -pattern_type glob -i '{img_dir}/*.bmp' -vf format=yuv420p {vid_dir}/{img_type}_{fps}fps.mp4"
            os.system(cmd_string)


if __name__ == "__main__":
    # Set the input and output directories
    trial_dir = Path("/home/oconnorlab/Desktop/2023-11-30_13-32-14_920729")
    process_trial(trial_dir)
