# Removes bayer pattern from raw images (on color cameras) and converts to grayscale.

import cv2
from pathlib import Path


def debayer_image(filename):
    """Debayers a raw Bayer image and returns a grayscale image.

    Args:
        filename (Path): Path to the input raw Bayer image.

    Returns:
        ndarray: Debayered grayscale image.
    """
    # Load the raw Bayer image as a single-channel grayscale image
    raw_img = cv2.imread(str(filename), cv2.IMREAD_GRAYSCALE)

    # Perform debayering
    debayered_img = cv2.cvtColor(raw_img, cv2.COLOR_BayerBG2BGR)

    # Convert to grayscale
    grayscale_img = cv2.cvtColor(debayered_img, cv2.COLOR_BGR2GRAY)

    return grayscale_img


def main():
    # Set the input and output directories
    img_dir = Path("/home/oconnorlab/Data/cameras/William/2023-09-27_17-28-13_047398/cam-B-original")
    save_dir = Path(str(img_dir).replace("-original", ""))

    # Create save directory if it doesn't exist
    save_dir.mkdir(parents=True, exist_ok=True)

    # Get list of image files
    img_list = list(img_dir.glob("*.bmp"))

    for filename in img_list:
        # Perform debayering
        debayered = debayer_image(filename)

        # Save the debayered image
        savename = Path(save_dir, filename.name)
        cv2.imwrite(str(savename), debayered)


if __name__ == "__main__":
    main()
