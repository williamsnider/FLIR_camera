import os
import glob
import matplotlib.pyplot as plt
from PIL import Image
from pathlib import Path
import numpy as np
from matplotlib.animation import FuncAnimation


def find_newest_image(base_path, cam):
    """
    Find the newest image in the specified camera directory.
    """
    newest_date_dir = max(glob.glob(f"{base_path}/*"), key=os.path.getctime)
    list_of_files = list(Path(newest_date_dir).rglob(f"{cam}/*.bmp"))
    if not list_of_files:  # directory might be empty
        return None
    latest_file = max(list_of_files, key=os.path.getctime)
    return latest_file


def update_images(frame, ax, base_path, cameras):
    """
    Update the images in the existing plot.
    """
    images = []
    for cam in cameras:
        newest_image_path = find_newest_image(base_path, cam)
        if newest_image_path:
            img = Image.open(newest_image_path)
            img = np.array(img)  # Convert to numpy array
            images.append(img)

    if len(images) == 6:  # Ensure all 6 images are present
        # Combine images into 2x3 grid
        rows = [np.hstack(images[i : i + 3]) for i in range(0, len(images), 3)]
        im_grid = np.vstack(rows)

        ax.clear()
        ax.imshow(im_grid)
        ax.axis("off")


def main():
    base_path = "/home/oconnorlab/Data/2023-12-13/cameras"
    cameras = ["camTL", "camTo", "camTR", "camBL", "camBo", "camBR"]

    # Initialize plot
    fig, ax = plt.subplots(figsize=(10, 6))

    # find_newest_image(base_path, cameras[0])

    # Create animation
    anim = FuncAnimation(fig, update_images, fargs=(ax, base_path, cameras), interval=250)

    plt.show()


if __name__ == "__main__":
    main()
