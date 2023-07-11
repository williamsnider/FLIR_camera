from pathlib import Path
import shutil
from PIL import Image

# Rename images

image_dir = Path('/home/oconnorlab/Data/cameras/test_videos/0')
save_dir = Path(image_dir, "renamed")

# Make save_dir if it doesn't exist
save_dir.mkdir(parents=True, exist_ok=True)

# Copy each file with new name
image_list = list(image_dir.glob('*.tiff'))
image_list.sort()


for i, old_path in enumerate(image_list):

    # Pad new name with zeros
    new_name = str(i).zfill(6) + '.tiff'

    # New path
    new_path = Path(save_dir, new_name)

    # Copy file
    shutil.copy2(old_path, new_path)


