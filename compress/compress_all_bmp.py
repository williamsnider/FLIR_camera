import cv2
from pathlib import Path
from compress import get_num_frames
import tqdm
import sys
import select


def convert_bmp_to_mp4(bmp_dir, output_fname, FPS):
    bmp_files = sorted(bmp_dir.glob("*.bmp"))

    if not bmp_files:
        print("No BMP files found.")
        return

    # # Read all BMP frames into memory
    # frames = []
    # for bmp_file in bmp_files:
    #     img = cv2.imread(str(bmp_file))
    #     if img is None:
    #         print(f"Skipping invalid frame: {bmp_file}")
    #         continue
    #     frames.append(img)

    # Read first BMP frame to get dimensions
    img = cv2.imread(str(bmp_files[0]))
    height, width, _ = img.shape

    # Create VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    video = cv2.VideoWriter(str(output_fname), fourcc, FPS, (width, height))

    # Write all frames to the video in one go
    for bmp_file in bmp_files:
        frame = cv2.imread(str(bmp_file))
        if frame is None:
            print(f"Skipping invalid frame: {bmp_file}")
            continue
        video.write(frame)

    video.release()


def delete_bmp_dir(mp4_fname, bmp_dir):
    # Check if video has same number of frames as BMP files
    num_frames_vid = get_num_frames(mp4_fname)
    num_frames_bmp = len(list(bmp_dir.glob("*.bmp")))
    if num_frames_vid == num_frames_bmp:
        # Delete BMP files
        for bmp_file in bmp_dir.glob("*.bmp"):
            bmp_file.unlink()
        bmp_dir.rmdir()
        pass
    else:
        print(f"Number of frames in video ({num_frames_vid}) does not match number of BMP files ({num_frames_bmp}).")
        print("BMP files were not deleted.")


def convert_bmp_dir_to_mp4(bmp_dir):
    output_fname = Path(bmp_dir.parent, bmp_dir.name + "-orig.mp4")

    # Define frames per second
    FPS = 100

    # Assert mp4 does not already exist
    if output_fname.exists():
        print(f"MP4 file already exists: {output_fname}")
        exit(1)

    # Convert BMP files to MP4
    convert_bmp_to_mp4(bmp_dir, output_fname, FPS)

    # Delete BMP files
    delete_bmp_dir(output_fname, bmp_dir)


# Use select to test for enter press
def check_for_enter():

    i, o, e = select.select([sys.stdin], [], [], 0.0001)
    for s in i:
        if s == sys.stdin:
            input_line = sys.stdin.readline()
            return True
    return False


if __name__ == "__main__":

    # # Define input and output directories
    # bmp_dir = Path("/home/oconnorlab/Desktop/2023-11-20_12-17-09_167964/cam-To")

    base_dir = Path("/mnt/data12/William/Data/")
    trial_list = [d for d in base_dir.glob("*/cameras/*/*") if d.is_dir()]

    # Ensure the directories contain .bmp files
    trial_list_copy = []
    for trial in trial_list:
        if list(trial.glob("*.bmp")):
            trial_list_copy.append(trial)
        else:
            print(f"No BMP files found in {trial}")

    # Convert bmp directories to mp4
    print("Press ENTER to exit loop")
    for trial in tqdm.tqdm(trial_list_copy):

        if check_for_enter():
            break

        convert_bmp_dir_to_mp4(trial)
