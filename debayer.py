import cv2
from pathlib import Path

img_dir = Path("/home/oconnorlab/Desktop/images_for_poster/")


def debayer_image(filename):
    # Load the raw Bayer image (as a single-channel grayscale image)
    raw_img = cv2.imread(str(filename), cv2.IMREAD_GRAYSCALE)

    # Perform debayering
    debayered_img = cv2.cvtColor(raw_img, cv2.COLOR_BayerBG2BGR)  # Adjust the pattern

    # Convert to grayscale
    grayscale_img = cv2.cvtColor(debayered_img, cv2.COLOR_BGR2GRAY)

    # Save or display the debayered image

    # Display the debayered image
    # cv2.imshow('Debayered Image', grayscale_img)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()
    # cv2.imwrite('debayered_image.png', debayered_img)
    return grayscale_img


if __name__ == "__main__":
    images_to_debayer = []
    for key in ["cam-A", "cam-B"]:
        images_to_debayer.extend(list(img_dir.glob(f"*{key}*.bmp")))

    save_dir = Path(str(img_dir).replace(".", "-debayered."))
    save_dir.mkdir(parents=True, exist_ok=True)

    for filename in images_to_debayer:
        debayered = debayer_image(filename)

        savename = Path(save_dir, filename.name.replace(".", "-debayered."))
        cv2.imwrite(str(savename), debayered)

## FFMPEG command to convert .bmp to .png
