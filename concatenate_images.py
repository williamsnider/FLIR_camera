from pathlib import Path
from PIL import Image
from tqdm import tqdm
import threading
from queue import Queue
import time
import cv2

# Directories for reading/writing images
FILETYPE = ".tiff"
batch_dir = Path(
    "/home/oconnorlab/Data/cameras/test_calibration/2023-07-12_11-54-19_332591"
)
concat_dir = Path(batch_dir, "concatenated")
concat_dir.mkdir(parents=True, exist_ok=True)

cam_name_list = [p.name for p in batch_dir.glob("cam-*")]


def concat_img(img_queue):
    while img_queue.empty() == False:
        img_path_list = img_queue.get()

        # Check that all images have the same img id
        id_set = {p.stem.split("-")[-1] for p in img_path_list}
        assert len(id_set) == 1, "Images do not have the same id."

        # Load images
        img_list = [cv2.imread(str(p)) for p in img_path_list]

        # Concatenate vertically
        im_v = cv2.vconcat(img_list)

        # Save concatenated image
        dummy_img = img_path_list[0]
        img_num = dummy_img.stem.split("-")[-1]
        concat_name = Path(concat_dir, "concat-" + img_num).with_suffix(FILETYPE)
        cv2.imwrite(str(concat_name), im_v)


# Make list of image paths
cam_images_list = []
for cam_name in cam_name_list:
    cam_dir = Path(batch_dir, cam_name)
    cam_images = list(cam_dir.glob("*" + FILETYPE))
    cam_images.sort()

    cam_images_list.append(cam_images)

# Zip so that images from each camera are in the same list
all_img_path_lists = list(zip(*cam_images_list))

# Add image_path_lists to queue (thread safe)
image_queue = Queue()
for group in all_img_path_lists:
    image_queue.put(group)

# Create threads
THREAD_COUNT = 10
thread_list = []
for _ in range(THREAD_COUNT):
    thread = threading.Thread(target=concat_img, args=(image_queue,))
    thread_list.append(thread)

# Start threads
for thread in thread_list:
    thread.start()

while not image_queue.empty():
    print("Queue size: ", image_queue.qsize(), "            ", end="\r")
    time.sleep(0.5)


# Join threads
for thread in thread_list:
    thread.join()

print("All images concatenated.")
