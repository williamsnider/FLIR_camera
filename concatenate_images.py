# This script concatenates images from multiple cameras into a single image.

from pathlib import Path
import threading
from queue import Queue
import time
import cv2

# Define constants and directories for image I/O
FILETYPE = ".bmp"
batch_dir = Path("/home/oconnorlab/Data/cameras/William/2023-09-27_17-28-13_047398")
concat_dir = Path(batch_dir, "concatenated")
concat_dir.mkdir(parents=True, exist_ok=True)

# Generate a list of camera names, ignoring any labeled 'original'
cam_name_list = [p.name for p in batch_dir.glob("cam-*") if "original" not in p.name]


def concat_img(img_queue):
    """Concatenate images vertically and save the resulting image."""
    while not img_queue.empty():
        # Fetch the next group of image paths from the queue
        img_path_list = img_queue.get()

        # Verify that the image IDs match
        id_set = {p.stem.split("-")[-1] for p in img_path_list}
        assert len(id_set) == 1, "Mismatched image IDs."

        # Load all images into memory
        img_list = [cv2.imread(str(p)) for p in img_path_list]

        # Concatenate images vertically
        im_v = cv2.vconcat(img_list)

        # Construct the save path and write the concatenated image
        img_num = img_path_list[0].stem.split("-")[-1]
        concat_name = concat_dir / f"concat-{img_num}{FILETYPE}"
        cv2.imwrite(str(concat_name), im_v)


def concat_img_3x2(img_queue):
    """Concatenate images into a 3x2 grid and save the resulting image."""
    while not img_queue.empty():
        # Fetch the next group of image paths from the queue
        img_path_list = img_queue.get()

        # Verify that the image IDs match
        id_set = {p.stem.split("-")[-1] for p in img_path_list}
        assert len(id_set) == 1, "Mismatched image IDs."

        # Load all images into memory
        img_list = [cv2.imread(str(p)) for p in img_path_list]

        # Prepare the 3x2 grid
        rows = [cv2.hconcat(img_list[i : i + 2]) for i in range(0, len(img_list), 2)]

        # Concatenate the rows to complete the grid
        im_grid = cv2.vconcat(rows)

        # Construct the save path and write the concatenated image
        img_num = img_path_list[0].stem.split("-")[-1]
        concat_name = concat_dir / f"concat-{img_num}{FILETYPE}"
        cv2.imwrite(str(concat_name), im_grid)


# Main execution
def main():
    # Sort image paths for each camera
    cam_images_list = [sorted(list((batch_dir / cam_name).glob(f"*{FILETYPE}"))) for cam_name in cam_name_list]

    # Zip the lists so that each resulting list contains one image from each camera
    all_img_path_lists = list(zip(*cam_images_list))

    # Populate the image queue
    image_queue = Queue()
    for group in all_img_path_lists:
        image_queue.put(group)

    # Spawn threads and assign the concat function
    thread_list = [threading.Thread(target=concat_img_3x2, args=(image_queue,)) for _ in range(10)]  # 10 threads

    # Start all threads
    for thread in thread_list:
        thread.start()

    # Monitor the queue size until it's empty
    while not image_queue.empty():
        print(f"Queue size: {image_queue.qsize()}           ", end="\r")
        time.sleep(0.5)

    # Ensure all threads have completed
    for thread in thread_list:
        thread.join()

    print("All images concatenated.")


if __name__ == "__main__":
    main()
