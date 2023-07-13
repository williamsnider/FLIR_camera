# Potentially useful functions that are not used in the main script currently.


def convert_to_video():
    """
    Converts a folder of images into a video avi file. Use the wrapper file to adjust the fps.
    """

    for [_, cam_ID] in CAMERA_NAMES_DICT.items():
        video_name = SAVE_PREFIX + "-" + cam_ID + ".avi"

        cam_subdir = Path(SAVE_LOCATION, cam_ID)
        img_list = list(cam_subdir.glob("*" + FILETYPE))

        # Sort images using natsort; otherwise image-1 grouped with image-10
        # sorted_image_names = natsort.natsorted(os.listdir(cam_subdir))
        # images = [img for img in sorted_image_names if img.endswith(FILETYPE) & img.startswith(SAVE_PREFIX+'-'+cam_ID)]

        if len(img_list) == 0:
            print(
                "No images found for "
                + cam_ID
                + " of type "
                + FILETYPE
                + " so no video was created.\n"
            )
            continue
        else:
            print("Converting images to video format for camera " + cam_ID + ".\n")
            cmd = "ffmpeg -framerate {} -pattern_type glob -i '{}/*{}' -vf format=yuv420p {}/{}.mp4".format(
                VIDEO_FPS, cam_subdir, FILETYPE, cam_subdir, video_name
            )
            os.system(cmd)
        # frame = cv2.imread(os.path.join(cam_subdir, images[0]))
        # height, width, layers = frame.shape
        # fourcc = cv2.VideoWriter_fourcc('M','J','P','G') # TODO: suboptimal because it introduces second round of compression.
        # video = cv2.VideoWriter(video_name, fourcc, VIDEO_FPS, (width,height), True)

        # for image in images:
        #     print(image)
        #     video.write(cv2.imread(os.path.join(cam_subdir, image)))

        # cv2.destroyAllWindows()
        # video.release()

        print("Video saved as " + video_name + " at " + str(VIDEO_FPS) + "fps.\n")

    # TODO: Put in a check on whether the input FPS is plausible given the timestamps of the images.

    # TODO: Ensure that skipped frames are handled properly (black screen)


def rename_images(
    image_folder, initial_prefix_list, target_prefix_list, save_format_extension=".tiff"
):
    """
    Rename the images in the folder given a list of the initial names and target_names. Changes the prefix, so "1947202-01.tiff" becomes "cam-A-01.tiff".
    """
    for [idx, initial_prefix] in enumerate(initial_prefix_list):
        # Make list containing images of correct initial prefix and ending
        image_list = [
            i
            for i in os.listdir(image_folder)
            if i.startswith(initial_prefix) & i.endswith(save_format_extension)
        ]

        if image_list == []:
            print(
                "No images found with prefix {0} and extension {1}.".format(
                    initial_prefix, save_format_extension
                )
            )
        else:
            pass

        # Iterate through images, assigning new names
        for image_name in image_list:
            image_number = image_name.split(initial_prefix)[1].split(
                save_format_extension
            )[0]
            new_prefix = target_prefix_list[idx]
            new_name = new_prefix + image_number + save_format_extension
            os.rename(
                os.path.join(image_folder, image_name),
                os.path.join(image_folder, new_name),
            )
