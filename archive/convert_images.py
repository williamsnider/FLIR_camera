from pathlib import Path
import shutil
from PIL import Image
from tqdm import tqdm
import threading
from queue import Queue
import time

image_dir = Path('/home/oconnorlab/Data/cameras/test_videos/0/renamed')
save_dir = Path(*image_dir.parts[:-1], "png")

save_dir.mkdir(parents=True, exist_ok=True)

def convert_image(old_path):
    """Converts image from tiff to png"""

    # Load image
    img = Image.open(old_path)

    # Save as png
    new_path = Path(save_dir, old_path.name)
    img.save(new_path.with_suffix('.png'))

def thread_function(image_queue):
    """Function for each thread that converts image as long as there are images in the queue."""
    while not image_queue.empty():
        convert_image(image_queue.get())

# Convert images to png
tiff_list = list(image_dir.glob('*.tiff'))
tiff_list.sort()

# Add images to queue (thread safe)
image_queue = Queue()
for tiff in tiff_list:
    image_queue.put(tiff)


# Create threads
THREAD_COUNT = 10
thread_list = []
for _ in range(THREAD_COUNT):
    thread = threading.Thread(target=thread_function, args=(image_queue,))
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

print("All images converted.")