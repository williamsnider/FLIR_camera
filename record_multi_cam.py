import PySpin
import psutil
import threading
import queue
import time
from pathlib import Path
import datetime
from record_multi_cam_params import (
    CAMERA_PARAMS_COLOR,
    CAMERA_PARAMS_MONO,
    CAMERA_NAMES_DICT_COLOR,
    CAMERA_NAMES_DICT_MONO,
    CAMERA_SPECIFIC_DICT,
    SAVE_LOCATION,
    SAVE_PREFIX,
    GRAB_TIMEOUT,
    NUM_THREADS_PER_CAM,
    # FILETYPE,
    MIN_BATCH_INTERVAL,
    VIDEO_FPS,
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
)
import cv2
import numpy as np


############################################
### Global variables used across threads ###
############################################

KEEP_ACQUIRING_FLAG = True  # Flag for halting acquisition of images; triggered by ctrl+c
SAVING_DONE_FLAG = False  # Flag for signaling that all queued images have been saved

# Images are grouped into batches. New batches are created when a new image is acquired more than MIN_BATCH_INTERVAL from the previous image.
prev_image_timestamp = time.time()  # Timestamp of previous image
curr_image_timestamp = time.time()  # Timestamp of current image
batch_dir_name = datetime.datetime.fromtimestamp(curr_image_timestamp).strftime("%Y-%m-%d_%H-%M-%S_%f")
lock = threading.Lock()  # Used to lock the batch_dir_name variable when it is being updated


################################
### Initialization functions ###
################################


def find_cameras():
    """
    Finds cameras connected to the system.

    Cameras whose serial numbers are not in `CAMERA_NAMES_DICT` are removed from the list of cameras. Change these serial numbers in parameters.py.
    """
    # serial_id_list = []
    # for serial_id in CAMERA_NAMES_DICT_COLOR.keys():
    #     serial_id_list.append(serial_id)
    # for serial_id in CAMERA_NAMES_DICT_MONO.keys():
    #     serial_id_list.append(serial_id)

    # Factory reset cameras to ensure nodes are rewritable (necessary if they were not properly closed)
    print("Resetting cameras...")
    system = PySpin.System.GetInstance()
    cam_list = system.GetCameras()

    # device_ids_in_cam_list = [cam.TLDevice.DeviceSerialNumber.GetValue() for cam in cam_list]
    # device_ids_to_remove = [device_id for device_id in device_ids_in_cam_list if device_id not in serial_id_list]
    # for device_id in device_ids_to_remove:
    #     cam_list.RemoveBySerial(device_id)

    for cam in cam_list:

        # # Skip if not in serial_id_list
        # if cam.TLDevice.DeviceSerialNumber.GetValue() not in serial_id_list:
        #     continue

        # Reset camera
        cam.Init()
        cam.DeviceReset()
        del cam

    # Wait until cameras are reconnected
    time.sleep(5)
    cam_list = system.GetCameras()

    # for device_id in device_ids_to_remove:
    #     cam_list.RemoveBySerial(device_id)

    # old_cam_list = system.GetCameras()
    # cam_list = [cam for cam in old_cam_list if cam.TLDevice.DeviceSerialNumber.GetValue() in serial_id_list]
    # old_cam_list.Clear()

    # # Remove cameras from cam_list if they are not in serial_id_list

    # for cam in cam_list:

    #     # Ensure is in camera dict
    #     device_serial_number = cam.TLDevice.DeviceSerialNumber.GetValue()
    #     if (device_serial_number not in CAMERA_NAMES_DICT_COLOR.keys()) and (
    #         device_serial_number not in CAMERA_NAMES_DICT_MONO.keys()
    #     ):
    #         cam_list.RemoveBySerial(device_serial_number)
    #     if (
    #         cam.TLDevice.DeviceSerialNumber.GetValue() in CAMERA_NAMES_DICT_COLOR.keys()
    #         or cam.TLDevice.DeviceSerialNumber.GetValue() in CAMERA_NAMES_DICT_MONO.keys()
    #     ):
    #         cam.Init()
    #         cam.DeviceReset()
    #         del cam

    # Wait until cameras are reconnected
    # while True:
    #     print("Waiting for cameras to reconnect...")
    #     time.sleep(1)

    #     # Find cameras
    #     system = PySpin.System.GetInstance()
    #     cam_list = system.GetCameras()

    #     if len(cam_list) == num_previously_connected_cameras:
    #         break

    # # Remove cameras from cam_list if they are not in CAMERA_NAMES_DICT
    # serial_numbers = [cam.TLDevice.DeviceSerialNumber.GetValue() for cam in cam_list]
    # for serial_number in serial_numbers:
    #     if (serial_number not in CAMERA_NAMES_DICT_COLOR.keys()) and (
    #         serial_number not in CAMERA_NAMES_DICT_MONO.keys()
    #     ):
    #         cam_list.RemoveBySerial(serial_number)

    # Print camera serials and names
    num_cameras = len(cam_list)
    print("Cameras to be used: ", num_cameras)
    for cam in cam_list:
        serial_number = cam.TLDevice.DeviceSerialNumber.GetValue()
        if serial_number in CAMERA_NAMES_DICT_COLOR.keys():
            print(serial_number, CAMERA_NAMES_DICT_COLOR[serial_number])
        elif serial_number in CAMERA_NAMES_DICT_MONO.keys():
            print(serial_number, CAMERA_NAMES_DICT_MONO[serial_number])

    # Release system if no cameras are found
    if num_cameras == 0:
        print("No cameras found. System is being released.")
        release_cameras(cam_list, system)

    return cam_list, system, num_cameras


def set_camera_params(cam_list):
    """
    Initializes the cameras and sets camera parameters (e.g. exposure time, gain, etc.). Change these values in parameters.py
    """

    result = True

    for cam in cam_list:
        # Initialize
        cam.Init()

        # Test if mono or color
        if cam.DeviceID() in CAMERA_NAMES_DICT_COLOR.keys():
            CAMERA_PARAMS = CAMERA_PARAMS_COLOR
        elif cam.DeviceID() in CAMERA_NAMES_DICT_MONO.keys():
            CAMERA_PARAMS = CAMERA_PARAMS_MONO
        else:
            print("Error: Camera serial number not in CAMERA_NAMES_DICT_COLOR or CAMERA_NAMES_DICT_MONO.")
            return False

        # Set imaging parameters
        for [param, value] in CAMERA_PARAMS:
            # Split param strings by period to handle nested attributes. This helps the program handle updating parameters like "TLStream.StreamBufferCountMode"
            attr_list = param.split(".")

            # Update the nested attribute pointer until we have reached the final attribute.
            nested_attr = cam
            for attr in attr_list:
                nested_attr = getattr(nested_attr, attr)

            # Set the value
            try:
                nested_attr.SetValue(value)
            except PySpin.SpinnakerException as ex:
                print("Error: %s" % ex)
                print(
                    "This may have been caused by not properly closing the cameras. The cameras need to be reset (or unplugged)."
                )
                result = False

        # Set camera specific parameters (e.g. cropping)
        crop_params = CAMERA_SPECIFIC_DICT[cam.DeviceID()]
        for [param, value] in crop_params:
            attr_list = param.split(".")
            nested_attr = cam
            for attr in attr_list:
                nested_attr = getattr(nested_attr, attr)

            try:
                nested_attr.SetValue(value)
            except PySpin.SpinnakerException as ex:
                print("Error: %s" % ex)
                print(
                    "This may have been caused by not properly closing the cameras. The cameras need to be reset (or unplugged)."
                )
                result = False

        # Set trigger mode back to True
        cam.TriggerMode.SetValue(True)

        # Set DeviceUserID (e.g. cam-A) based on serial number
        for [serial, name] in CAMERA_NAMES_DICT_COLOR.items():
            if serial == cam.DeviceID():
                cam.DeviceUserID.SetValue(name)

                # Set DeviceUserID (e.g. cam-A) based on serial number
        for [serial, name] in CAMERA_NAMES_DICT_MONO.items():
            if serial == cam.DeviceID():
                cam.DeviceUserID.SetValue(name)

    return result


def release_cameras(cam_list, system):
    """
    Cleanly releases the cameras and system.

    This is important to do when the program closes or else you might need to reset (unplug) the cameras.
    """
    # cam_list = system.GetCameras()

    # # Remove cams by ID
    # serial_id_list = []
    # for cam in cam_list:
    #     serial_id_list.append(cam.TLDevice.DeviceSerialNumber.GetValue())

    # for serial_id in serial_id_list:
    #     cam_list.RemoveBySerial(serial_id)

    cam_list.Clear()
    del cam_list
    system.ReleaseInstance()
    print("\nCameras and system released.")


########################
### Thread functions ###
########################


def acquire_images(cam, image_queue_list):
    """
    Acquires images from the camera buffer and places them in the image_queue.

    Stops acquiring when the KEEP_ACQUIRING_FLAG is set to False.

    Images are stored in the buffer when the camera receives a hardware trigger.

    """
    # Global variables that are modified
    global prev_image_timestamp, curr_image_timestamp, batch_dir_name

    try:
        # Begin acquiring images
        cam.BeginAcquisition()
        device_user_ID = cam.DeviceUserID()
        frame_idx = 0  # Resets for each batch
        batch_dir_name_prev = batch_dir_name  # Detects when batch_dir_name changes
        print("[{}] Acquiring images...".format(device_user_ID))

        while KEEP_ACQUIRING_FLAG:

            # Add end of batch signal to image_queue
            time_since_last_image = time.time() - curr_image_timestamp
            if (frame_idx > 0) and (time_since_last_image > MIN_BATCH_INTERVAL):
                for q in image_queue_list:
                    q.put(("end_of_batch", "end_of_batch", "end_of_batch"))
                frame_idx = 0  # Reset frame_idx to send "end_of_batch" signal only once

            # Use try/except to handle timeout error (no image found within GRAB_TIMEOUT))
            try:
                # Test if images have filled the camera buffer beyond capacity
                if cam.TransferQueueCurrentBlockCount() > 10:
                    print(
                        ("# of images in {0}'s buffer: {1}").format(
                            device_user_ID, cam.TransferQueueCurrentBlockCount()
                        )
                    )

                # Acquire image if one has been stored on the camera's buffer
                # If no image available within GRAB_TIMEOUT, a timeout exception will cause the loop to restart.
                try:
                    image_result = cam.GetNextImage(GRAB_TIMEOUT)

                    # To group the images into sequential batches (separate image sets spaced apart by MIN_BATCH_INTERVAL), we compare the timestamp of the current image to that of the previous image. If it exceeds MIN_BATCH_INTERVAL, update batch_dir_name (global variable) which will change the directory in which the images are saved. Using the lock is necessary so that only the first thread that detects the change will update the directory name for all threads.
                    with lock:
                        curr_image_timestamp = time.time()
                        if curr_image_timestamp - prev_image_timestamp > MIN_BATCH_INTERVAL:
                            # Update batch_dir_name to reflect the current timestamp
                            batch_dir_name = datetime.datetime.fromtimestamp(curr_image_timestamp).strftime(
                                "%Y-%m-%d_%H-%M-%S_%f"
                            )

                        prev_image_timestamp = curr_image_timestamp

                except PySpin.SpinnakerException:
                    time.sleep(0.001)  # Allow time on other threads
                    continue

                # Detect change in batch_dir_name to update frame_idx
                if batch_dir_name != batch_dir_name_prev:
                    frame_idx = 0  # Reset frame_idx for each batch
                    batch_dir_name_prev = batch_dir_name

                #  Handle incomplete images
                if image_result.IsIncomplete():
                    print(
                        "[{}] Image incomplete with image status {}.".format(
                            device_user_ID, image_result.GetImageStatus()
                        )
                    )
                else:
                    # Add grabbed image to queue, which will be saved by saver threads
                    image_copy = PySpin.Image.Create(image_result)
                    # image_queue.put((frame_idx, image_copy))
                    for q in image_queue_list:
                        q.put((image_copy, frame_idx, batch_dir_name))
                    image_result.Release()
                    frame_idx += 1

            except PySpin.SpinnakerException as ex:
                print("Error: %s" % ex)
                return

        # Stop acquisition once KEEP_ACQUIRING_FLAG is set to False
        cam.EndAcquisition()
        cam.DeInit()

    except PySpin.SpinnakerException as ex:
        print("Error: %s" % ex)
        return


def save_mp4(cam_name, image_queue, save_location):
    """Saves images that are in the image_queue to a mp4 file."""

    # Video parameters
    codec = "mp4v"
    FPS = VIDEO_FPS
    WIDTH = VIDEO_WIDTH
    HEIGHT = VIDEO_HEIGHT

    while (KEEP_ACQUIRING_FLAG == True) or (image_queue.qsize() > 0):

        frame_count = -1
        while True:

            # Get frame from image_queue
            try:
                frame_copy, frame_idx, batch_dir = image_queue.get(block=False)

                frame_count += 1
            except:
                time.sleep(0.001)  # Allow other threads to run
                continue

            # Handle different types of values sent to queue
            if type(frame_copy) == type(None):
                break  # Exit loop if "None" is received
            elif type(frame_copy) == type("end_of_batch"):
                out.release()
                break
            elif type(frame_copy) == PySpin.ImagePtr:

                # Convert to numpy array
                frame = frame_copy.GetNDArray()  # Convert to numpy array

                # Debayer
                if cam_name in CAMERA_NAMES_DICT_COLOR.values():
                    frame = cv2.cvtColor(frame, cv2.COLOR_BayerRG2RGB)
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

            else:
                raise ValueError("Frame is not None, 'end_of_batch', or PySpin.Image")

            # If first frame, create video writer
            if frame_count == 0:
                time_start = time.time()

                fourcc = cv2.VideoWriter_fourcc(*codec)
                savename = Path(save_location, batch_dir[:10], "cameras", batch_dir, f"{cam_name}.mp4")
                savename.parent.mkdir(parents=True, exist_ok=True)
                out = cv2.VideoWriter(str(savename), fourcc, FPS, (WIDTH, HEIGHT), isColor=False)

            # Add frame to video
            if type(frame) == np.ndarray:
                out.write(frame)

            # # If last frame, release video writer
            # if type(frame) == type("end_of_batch"):

            #     if frame == "end_of_batch":
            #         out.release()
            #         print(f"Saved {frame_count} frames in {time.time() - time_start} s")
            #     else:
            #         raise ValueError("Frame is not 'end_of_batch' or np.ndarray")

            #     # Exit loop at end of batch
            #     break


# def save_images_as_video(cam_name, image_queue, save_location):
#     """
#     Saves images that are in the image_queue.
#     """
#     import cv2

#     while True:

#         # Add images to mp4
#         VIDEO_FPS = 100.0
#         width = 960
#         height = 960
#         video_path = Path(save_location, "cam-" + cam_name + ".mp4")
#         fourcc = cv2.VideoWriter_fourcc(*"mp4v")
#         video_writer = cv2.VideoWriter(str(video_path), fourcc, VIDEO_FPS, (width, height))

#         # Collect frames
#         frame_list = []

#         while True:

#             try:
#                 frame_idx, image = image_queue.get()
#             except:
#                 time.sleep(0.005)
#                 continue

#             if image == "end_of_trial":
#                 break
#             elif image == None:
#                 stop_flag = True

#             # Exit loop if "None" is received
#             if image is None:
#                 break


# def save_images_as_video(cam_name, image_queue, save_location):
#     """Saves images as an mp4 video."""

#     continue_saving_flag = True
#     while continue_saving_flag:

#         # Add images to mp4
#         VIDEO_FPS = 100.0
#         width = 960
#         height = 960
#         fourcc = cv2.VideoWriter_fourcc(*"mp4v")

#         # Get images from queue until "Last-of-batch" is received
#         frame_idx_list = []
#         image_list = []
#         while True:


#             try:
#                 frame_idx, image = image_queue.get()
#             except:
#                 time.sleep(0.005)
#                 continue

#             # Exit loop if "None" is received
#             if image is None:
#                 continue_saving_flag = False
#                 break
#             elif image == "Last-of-batch":

#                 break

#             # Add image to list
#             frame_idx_list.append(frame_idx)
#             image_list.append(image)


def save_images(cam_name, image_queue, save_location):
    """
    Saves images that are in the image_queue.

    Loops infinitely until it receives a "None" in the queue, then returns.
    """

    while True:
        try:
            frame_idx, image = image_queue.get()
        except:
            time.sleep(0.001)  # Allow time on other threads
            continue

        # Exit loop if "None" is received
        if image is None:  # No more images
            break

        # Construct filename
        # frame_id = str(image.GetFrameID())
        frame_id = str(frame_idx)  # Resets for each batch, unlike image.GetFrameID()
        frame_id = frame_id.zfill(6)  # pad frame id with zeros to order correctly
        filename = SAVE_PREFIX + "-" + cam_name + "-" + frame_id + FILETYPE

        # Construct batch/camera directory
        date_dir = batch_dir_name[:10] + "/cameras"
        cam_dir_path = Path(save_location, date_dir, batch_dir_name, cam_name)
        cam_dir_path.mkdir(parents=True, exist_ok=True)

        # Construct full filepath
        filepath = Path(cam_dir_path, filename)

        # Save image

        # output = image.GetNDArray()
        # cv2.imwrite(str(filepath), output)

        # output = image.GetNDArray()
        # img = Image.fromarray(output)
        # img.save(filepath)

        image.Save(str(filepath))


def queue_counter(image_queues):
    """
    Counts the size of each image queue and displays it in the terminal.

    Queues should be nearly empty at all times. If they are not, then the saving threads are not keeping up with the acquisition threads.
    """
    while SAVING_DONE_FLAG is False:
        time.sleep(0.25)
        # queue_lengths = [
        #     " Queue #" + str(idx) + ": " + str(q.qsize()).zfill(5)
        #     for idx, q in enumerate(image_queues)
        # ]
        # print(" Image queue lengths:" + "".join(queue_lengths), end="\r")
        msg = ""
        for idx, q in enumerate(image_queues):
            if q.qsize() > 50:
                msg += " Queue #" + str(idx) + ": " + str(q.qsize()).zfill(5)
        if msg != "":
            print(" Image queue lengths:" + msg, end="\r")


def print_previous_batch_size(cam_names):
    """
    Prints the number of files saved in a batch directory once the batch is complete.

    This function is useful to monitor that images are being saved successfully.
    """

    # List of batch_dir_names that have had a status printed (prevent duplicate printing)
    batches_already_reported = []

    while SAVING_DONE_FLAG is False:
        time.sleep(0.25)

        # Get full path of current batch directory
        date_dir = batch_dir_name[:10] + "/cameras"
        batch_dir_path = Path(SAVE_LOCATION, date_dir, batch_dir_name)

        # Print status if (1) MIN_BATCH_INTERVAL has passed since the last image was acquired. (2) batch_dir_name has not already had its status printed. (3) batch_dir_path exists i.e. the batch directory has been created and images were saved.
        if (
            (time.time() - curr_image_timestamp > MIN_BATCH_INTERVAL)
            and (batch_dir_name not in batches_already_reported)
            and (batch_dir_path.exists())
        ):

            # Give time for mp4 to be written fully
            time.sleep(0.25)

            # Construct output message listing the number of images saved for each camera.
            output = "\n"
            output += "*" * 30
            output += "\nBatch: " + batch_dir_name

            # # Append the number of images saved for each camera
            # for cam_name in CAMERA_NAMES_DICT_COLOR.values():
            #     cam_subdir = Path(batch_dir_path, cam_name)
            #     file_list = list(cam_subdir.iterdir())
            #     num_files = len(file_list)
            #     output += "\n" + cam_name + ": " + str(num_files) + " images saved."

            # # Append the number of images saved for each camera
            # for cam_name in CAMERA_NAMES_DICT_MONO.values():
            #     cam_subdir = Path(batch_dir_path, cam_name)
            #     file_list = list(cam_subdir.iterdir())
            #     num_files = len(file_list)
            #     output += "\n" + cam_name + ": " + str(num_files) + " images saved."

            # Append the number of images saved for each mp4
            for cam_name in cam_names:
                mp4_path = Path(batch_dir_path, cam_name + ".mp4")
                # Open mp4 file and get number of frames
                cap = cv2.VideoCapture(str(mp4_path))
                num_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                cap.release()
                output += "\n" + cam_name + ": " + str(num_frames) + " images saved."

            # # Append estimated framerate
            # file_list.sort()
            # num_files = len(file_list)
            # first_file_savetime = file_list[0].stat().st_mtime
            # last_file_savetime = file_list[-1].stat().st_mtime
            # estimated_framerate = num_files / (last_file_savetime - first_file_savetime)
            # output += "\nEstimated framerate: " + str(round(estimated_framerate, 1)) + " fps"
            print(output)

            # Print remaining space on hard drive
            check_hard_drive_space()

            # Update for subsequent loops
            batches_already_reported.append(batch_dir_name)


def display_images_in_queues(image_queues_display):

    IMG_WIDTH = 960
    IMG_HEIGHT = 960

    while KEEP_ACQUIRING_FLAG:

        # Allow time on other threads
        time.sleep(0.05)

        last_image_list = []

        # Wait until first image is received in each queue
        all_queues_nonempty = True
        for q in image_queues_display:
            if q.qsize() == 0:
                all_queues_nonempty = False

        if all_queues_nonempty == False:
            continue

        # Get last image from each queue
        for q in image_queues_display:

            while True:
                try:
                    frame_copy, frame_idx, batch_dir = q.get(block=False)
                except:
                    break

            # Exit loop if "None" is received
            if frame_copy is None:
                break
            elif type(frame_copy) == type("end_of_batch"):
                break
            elif type(frame_copy) == PySpin.ImagePtr:
                frame = frame_copy.GetNDArray()
            else:
                raise ValueError("Frame is not None, 'end_of_batch', or PySpin.Image")

            last_image_list.append(frame)

        # Resize images
        new_height = IMG_HEIGHT // 3
        new_width = IMG_WIDTH // 3
        for idx, image in enumerate(last_image_list):
            last_image_list[idx] = cv2.resize(image, (new_width, new_height))

        # Display images
        tiled_image = np.zeros((new_height * 2, new_width * 3), dtype=np.uint8)
        for idx, image in enumerate(last_image_list):
            row = idx // 3
            col = idx % 3
            tiled_image[row * new_height : (row + 1) * new_height, col * new_width : (col + 1) * new_width] = image

        tiled_image = tiled_image.astype(np.uint8)

        # Use cv2 to plot random static image
        # static_image = np.random.randint(0, 255, (IMG_HEIGHT, IMG_WIDTH)).astype(np.uint8)
        # cv2.imshow("Static image", static_image)

        cv2.imshow("4FPS Stream", tiled_image)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cv2.destroyAllWindows()
    print("Display tile thread joined")


#####################
### Main Function ###
#####################


def record_high_bandwidth_video(cam_list, system):
    """
    Records images from multiple cameras.

    This function creates a separate acquisition thread for each camera, as well as multiple saving threads for each camera.

    Automatically release cameras and system when finished or when an exception is thrown.
    """
    global KEEP_ACQUIRING_FLAG
    global SAVING_DONE_FLAG

    try:
        ##########################
        ### Initialize threads ###
        ##########################

        # Create lists for acquisition threads, saving threads, and image queues
        acquisition_threads = []
        saving_threads = []
        image_queues_saving = []
        image_queues_display = []

        cam_names = []

        for cam in cam_list:

            # Get camera name
            serial = cam.TLDevice.DeviceSerialNumber.GetValue()
            if serial in CAMERA_NAMES_DICT_COLOR.keys():
                cam_names.append(CAMERA_NAMES_DICT_COLOR[serial])
            elif serial in CAMERA_NAMES_DICT_MONO.keys():
                cam_names.append(CAMERA_NAMES_DICT_MONO[serial])
            else:
                print("WARNING: Camera serial number not in CAMERA_NAMES_DICT_COLOR or CAMERA_NAMES_DICT_MONO.")

            # Add a new image_queue
            image_queues_saving.append(queue.Queue())  # Save and display
            image_queues_display.append(queue.Queue())

            # # Create multiple saving threads for each camera, targeting the most recent image_queue
            # for _ in range(NUM_THREADS_PER_CAM):
            #     saving_thread = threading.Thread(
            #         target=save_images,
            #         args=(cam.DeviceUserID(), image_queues[-1], SAVE_LOCATION),
            #     )
            #     saving_thread.start()
            #     saving_threads.append(saving_thread)

            # Create single saving thread for each camera as mp4
            saving_thread = threading.Thread(
                target=save_mp4, args=(cam.DeviceUserID(), image_queues_saving[-1], SAVE_LOCATION)
            )
            saving_thread.start()
            saving_threads.append(saving_thread)

            # Create an acquisition thread for each camera, which places images into the most recent image_queue
            acquisition_thread = threading.Thread(
                target=acquire_images, args=(cam, [image_queues_saving[-1], image_queues_display[-1]])
            )
            # acquisition_thread = threading.Thread(target=acquire_images, args=(cam, [image_queues_saving[-1]]))
            acquisition_thread.start()
            acquisition_threads.append(acquisition_thread)

        # Create display thread
        display_thread = threading.Thread(target=display_images_in_queues, args=(image_queues_display,))
        display_thread.start()

        # Create the queue counter, which prints the size of each image queue
        time.sleep(0.5)
        queue_counter_thread = threading.Thread(target=queue_counter, args=([image_queues_saving]))
        queue_counter_thread.start()

        # Create the print_previous_batch_size thread, which prints the number of saved images in each batch
        print_previous_batch_size_thread = threading.Thread(target=print_previous_batch_size, args=(cam_names,))
        print_previous_batch_size_thread.start()

        ######################################################
        ### Loop until ctrl+c indicates the end of acquisition ###
        ######################################################

        while KEEP_ACQUIRING_FLAG:
            try:
                time.sleep(0.1)

            except KeyboardInterrupt:
                KEEP_ACQUIRING_FLAG = False
                continue

        #########################
        ### Shut down threads ###
        #########################

        for at in acquisition_threads:
            at.join()
        print(" " * 80)
        print("Finished acquiring images...")
        del cam  # Release the reference to the camera. Important according to FLIR docs.

        # # Cleanly stop and release cameras
        # release_cameras(cam_list, system)

        # Pass None to image queues to signal the end of saving
        for q in image_queues_saving:
            for _ in range(NUM_THREADS_PER_CAM):
                q.put((None, None, None))

        # This block prevents ctrl+c from closing the program before images have finished saving.
        while SAVING_DONE_FLAG is False:
            try:
                for pt in saving_threads:
                    pt.join()

                # Mark saving as done, end the queue_counter
                SAVING_DONE_FLAG = True
                queue_counter_thread.join()
                print_previous_batch_size_thread.join()

            except KeyboardInterrupt:
                print("KeyboardInterrupt rejected. Be patient, images are still being saved.")
                continue

        print(" " * 80)
        print("Finished saving images.")
        print(" " * 80)

        display_thread.join()

    except PySpin.SpinnakerException as ex:
        print("Error: %s" % ex)

        # # Cleanly stop and release cameras
        # release_cameras(cam_list, system)
        return


########################
### Useful functions ###
########################


def get_remaining_space():
    """Returns the remaining space on the hard drive in GB."""
    total_space = psutil.disk_usage(str(SAVE_LOCATION)).total
    used_space = psutil.disk_usage(str(SAVE_LOCATION)).used
    remaining_space = total_space - used_space
    return round(remaining_space / 1e9, 2)


def check_hard_drive_space():
    """Prints warning if hard drive is low on space."""
    remaining_space_GB = get_remaining_space()
    print(f"Free space on the hard drive: {remaining_space_GB} GB")

    if remaining_space_GB < 100:
        print("WARNING: Less than 100 GB of free space on the hard drive.")


if __name__ == "__main__":
    # Check hard drive space
    check_hard_drive_space()

    # Identify connected cameras and reset them
    cam_list, system, num_cameras = find_cameras()

    # Split cameras into high_speed and overhead
    # CAM_OVERHEAD_SERIAL = "23398261"
    # cam_overhead = cam_list.GetBySerial(CAM_OVERHEAD_SERIAL)
    # cam_high_speed_list = [cam for cam in cam_list if cam.TLDevice.DeviceSerialNumber.GetValue() != CAM_OVERHEAD_SERIAL]

    cam_high_speed_list = []
    for c in cam_list:
        # Test serial number
        serial = c.TLDevice.DeviceSerialNumber.GetValue()
        if serial in CAMERA_NAMES_DICT_COLOR.keys() or serial in CAMERA_NAMES_DICT_MONO.keys():
            cam_high_speed_list.append(c)

    if num_cameras != 0:

        # Initialize and set imaging parameters
        result = set_camera_params(cam_high_speed_list)

        # Acquire and save images using multiple threads; loops until ctrl+c
        if result:

            from record_single_cam import record_overhead
            from queue import Queue

            queue_A = Queue()
            queue_B = Queue()
            stop_event = threading.Event()
            # record_thread = threading.Thread(target=record_overhead, args=(cam_overhead, queue_A, queue_B, stop_event))
            # record_thread.start()

            # overhead_thread = threading.Thread(target=record_overhead, args=(cam_overhead,))
            record_high_bandwidth_video(cam_high_speed_list, system)

            # Stop overhead thread
            stop_event.set()
            queue_A.put(None)
            queue_B.put(None)
            cv2.destroyAllWindows()
            # record_thread.join()

            # # Release overhead camera
            # if cam_overhead.IsValid():
            #     cam_overhead.DeInit()
            #     del cam_overhead

            for cam in cam_high_speed_list:
                cam.DeInit()
                del cam
            del cam_high_speed_list

            for cam in cam_list:
                cam.DeInit()
                del cam

            # TODO: Figure out why overhead_cam is causing errors with releasing camera and system instance.
            release_cameras(cam_list, system)
    else:
        print("No cameras found. Exiting.")
