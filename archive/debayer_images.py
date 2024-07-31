# Removes bayer pattern from raw images (on color cameras) and converts to grayscale.

import cv2
from pathlib import Path
import tqdm





if __name__ == "__main__":
    # Set the input and output directories
    img_dir = Path("/home/oconnorlab/Data/2024-02-28/cameras/2024-02-28_14-38-08_767258/camTR-bayer")

    debayer_images_in_dir(img_dir)
