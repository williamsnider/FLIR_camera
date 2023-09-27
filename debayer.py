import cv2
from pathlib import Path

img_dir =   Path("/home/oconnorlab/Data/cameras/William/2023-09-27_17-28-13_047398/cam-B-original")

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


    img_list = list(img_dir.glob('*.bmp'))

    save_dir = Path(str(img_dir).replace("-original",""))
    save_dir.mkdir(parents=True, exist_ok=True)

    for filename in img_list:
        debayered = debayer_image(filename)

        savename = Path(save_dir, filename.name)
        cv2.imwrite(str(savename), debayered)


