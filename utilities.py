# Contains the functions used in record_multiple_cameras.py

import os
import PySpin
import threading
import queue
import time
from pathlib import Path
import datetime
from PIL import Image
from parameters import (
    CAMERA_PARAMS,
    CAMERA_NAMES_DICT,
    SAVE_LOCATION,
    SAVE_PREFIX,
    GRAB_TIMEOUT,
    NUM_THREADS_PER_CAM,
    FILETYPE,
    MIN_BATCH_INTERVAL,
)

############################################
### Global variables used across threads ###
############################################

KEEP_ACQUIRING_FLAG = (
    True  # Flag for halting acquisition of images; triggered by ctrl+c
)
SAVING_DONE_FLAG = False  # Flag for signaling that all queued images have been saved

# Images are grouped into batches. New batches are created when a new image is acquired more than MIN_BATCH_INTERVAL from the previous image.
prev_image_timestamp = time.time()  # Timestamp of previous image
curr_image_timestamp = time.time()  # Timestamp of current image
batch_dir_name = datetime.datetime.fromtimestamp(curr_image_timestamp).strftime(
    "%Y-%m-%d_%H-%M-%S_%f"
)
lock = (
    threading.Lock()
)  # Used to lock the batch_dir_name variable when it is being updated


################################
### Initialization functions ###
################################


def find_cameras():
    """
    Finds cameras connected to the system.

    Cameras whose serial numbers are not in `CAMERA_NAMES_DICT` are removed from the list of cameras. Change these serial numbers in parameters.py.
    """

    # Retrieve reference to system object
    system = PySpin.System.GetInstance()

    # Get connected cameras
    cam_list = system.GetCameras()

    # Remove cameras from cam_list if they are not in CAMERA_NAMES_DICT
    serial_numbers = [cam.TLDevice.DeviceSerialNumber.GetValue() for cam in cam_list]
    for serial_number in serial_numbers:
        if serial_number not in CAMERA_NAMES_DICT.keys():
            cam_list.RemoveBySerial(serial_number)

    # Print camera serials and names
    num_cameras = cam_list.GetSize()
    print("Cameras to be used: ", num_cameras)
    for cam in cam_list:
        serial_number = cam.TLDevice.DeviceSerialNumber.GetValue()
        print(serial_number, CAMERA_NAMES_DICT[serial_number])

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

        # Set DeviceUserID (e.g. cam-A) based on serial number
        for [serial, name] in CAMERA_NAMES_DICT.items():
            if serial == cam.DeviceID():
                cam.DeviceUserID.SetValue(name)

    return result


def release_cameras(cam_list, system):
    """
    Cleanly releases the cameras and system.

    This is important to do when the program closes or else you might need to reset (unplug) the cameras.
    """
    cam_list.Clear()
    system.ReleaseInstance()
    print("\nCameras and system released.")


########################
### Thread functions ###
########################


def acquire_images(cam, image_queue):
    """
    Acquires images from the camera buffer and places the in the image_queue.

    Stops acquiring when the KEEP_ACQUIRING_FLAG is set to False.

    Images are stored in the buffer when the camera receives a hardware trigger.

    """
    try:
        # Begin acquiring images
        cam.BeginAcquisition()
        device_user_ID = cam.DeviceUserID()
        print("[{}] Acquiring images...".format(device_user_ID))

        # Global variables that are modified
        global prev_image_timestamp, curr_image_timestamp, batch_dir_name

        while KEEP_ACQUIRING_FLAG is True:
            # Use try/except to handle timeout error (no image found within GRAB_TIMEOUT))
            try:
                # Test if images have filled the camera buffer beyond capacity
                if cam.TransferQueueCurrentBlockCount() > 0:
                    print(
                        ("# of images in {0}'s buffer: {1}").format(
                            device_user_ID, cam.TransferQueueCurrentBlockCount()
                        )
                    )

                # Acquire image if one has been stored on camera's buffer
                # If no image available within GRAB_TIMEOUT, a timeout exception will cause the loop to restart.
                try:
                    image_result = cam.GetNextImage(GRAB_TIMEOUT)

                    # To group the images into sequential batches (separate image sets spaced apart by MIN_BATCH_INTERVAL), we compare the timestamp of the current image to that of the previous image. If it exceeds MIN_BATCH_INTERVAL, update batch_dir_name (global variable) which will change the directory in which the images are saved. Using the lock is necessary so that only the first thread that detects the change will update the directory name for all threads.
                    lock.acquire()
                    curr_image_timestamp = time.time()
                    if curr_image_timestamp - prev_image_timestamp > MIN_BATCH_INTERVAL:
                        # Update batch_dir_name to reflect the current timestamp
                        batch_dir_name = datetime.datetime.fromtimestamp(
                            curr_image_timestamp
                        ).strftime("%Y-%m-%d_%H-%M-%S_%f")

                    prev_image_timestamp = curr_image_timestamp
                    lock.release()

                except PySpin.SpinnakerException:
                    continue

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
                    image_queue.put(image_copy)
                    image_result.Release()

            except PySpin.SpinnakerException as ex:
                print("Error: %s" % ex)
                return

        # Stop acquisition once KEEP_ACQUIRING_FLAG is set to False
        cam.EndAcquisition()
        cam.DeInit()

    except PySpin.SpinnakerException as ex:
        print("Error: %s" % ex)
        return

    return


def save_images(cam_name, image_queue, save_location):
    """
    Saves images that are in the image_queue.

    Loops inifinitely until it receives a "None" in the queue, then returns.
    """

    while True:
        image = image_queue.get(block=True)

        # Exit loop if "None" is received
        if image is None:  # No more images
            break

        # Construct filename
        frame_id = str(image.GetFrameID())
        frame_id = frame_id.zfill(9)  # pad frame id with zeros to order correctly
        filename = SAVE_PREFIX + "-" + cam_name + "-" + frame_id + FILETYPE

        # Construct batch/camera directory
        cam_dir_path = Path(save_location, batch_dir_name, cam_name)
        cam_dir_path.mkdir(parents=True, exist_ok=True)

        # Construct full filepath
        filepath = Path(cam_dir_path, filename)

        # Save image
        output = image.GetNDArray()
        img = Image.fromarray(output)
        img.save(filepath)


def queue_counter(image_queues):
    """
    Counts the size of each image queue and displays it in the terminal.

    Queues should be nearly empty at all times. If they are not, then the saving threads are not keeping up with the acquisition threads.
    """
    while SAVING_DONE_FLAG is False:
        time.sleep(0.25)
        queue_lengths = [
            " Queue #" + str(idx) + ": " + str(q.qsize()).zfill(5)
            for idx, q in enumerate(image_queues)
        ]
        print(" Image queue lengths:" + "".join(queue_lengths), end="\r")


def print_previous_batch_size():
    """
    Prints the number of files saved in a batch directory once the batch is complete.

    This function is useful to monitor that images are saved successfully.
    """

    # List of batch_dir_names that have had a status printed (prevent duplicate printing)
    batches_already_reported = []

    while SAVING_DONE_FLAG is False:
        time.sleep(0.25)

        # Get full path of current batch directory
        batch_dir_path = Path(SAVE_LOCATION, batch_dir_name)

        # Print status is (1) MIN_BATCH_INTERVAL has passed since the last image was acquired. (2) batch_dir_name has not already had its status printed. (3) batch_dir_path exists i.e. the batch directory has been created and images were saved.
        if (
            (time.time() - curr_image_timestamp > MIN_BATCH_INTERVAL)
            and (batch_dir_name not in batches_already_reported)
            and (batch_dir_path.exists())
        ):
            # Construct output message listing # of images saved for each camera.
            output = "\n"
            output += "*" * 30
            output += "\nBatch: " + batch_dir_name
            for cam_name in CAMERA_NAMES_DICT.values():
                cam_subdir = Path(batch_dir_path, cam_name)
                num_files = len(list(cam_subdir.iterdir()))
                output += "\n" + cam_name + ": " + str(num_files) + " images saved."

            print(output)

            # Update for subsequent loops
            batches_already_reported.append(batch_dir_name)


############################
### Main Thread Function ###
############################


def record_high_bandwidth_video(cam_list, system):
    """
    Records images from multiple cameras.

    This function creates a separate acqusition thread for each camera, as well as multiple saving threads for each camera.

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
        image_queues = []

        for cam in cam_list:
            # Add new image_queue
            image_queues.append(queue.Queue())

            # Create multiple saving threads for each camera, targetting the most recent image_queue
            for _ in range(NUM_THREADS_PER_CAM):
                saving_thread = threading.Thread(
                    target=save_images,
                    args=(cam.DeviceUserID(), image_queues[-1], SAVE_LOCATION),
                )
                saving_thread.start()
                saving_threads.append(saving_thread)

            # Create acquisition thread for each camera, which places images into the most recent image_queue
            acquisition_thread = threading.Thread(
                target=acquire_images, args=(cam, image_queues[-1])
            )
            acquisition_thread.start()
            acquisition_threads.append(acquisition_thread)

        # Create the queue counter, which prints the size of each image queue
        time.sleep(0.5)
        queue_counter_thread = threading.Thread(
            target=queue_counter, args=([image_queues])
        )
        queue_counter_thread.start()

        # Create the print_previous_batch_size thread, which prints the number of saved images in each batch
        print_previous_batch_size_thread = threading.Thread(
            target=print_previous_batch_size
        )
        print_previous_batch_size_thread.start()

        ######################################################
        ### Loop until ctrl+c indicates end of acquisition ###
        ######################################################

        while KEEP_ACQUIRING_FLAG is True:
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

        del cam  # Release reference to camera. Important according to FLIR docs.

        # Cleanly stop and release cameras
        release_cameras(cam_list, system)

        # Pass None to image queues to signal end of saving
        for q in image_queues:
            for _ in range(NUM_THREADS_PER_CAM):
                q.put(None)

        # This block prevents ctrl+c from closing program before images have finished saving.
        while SAVING_DONE_FLAG is False:
            try:
                for pt in saving_threads:
                    pt.join()

                # Mark saving as done, end the queue_counter
                SAVING_DONE_FLAG = True
                queue_counter_thread.join()
                print_previous_batch_size_thread.join()

            except KeyboardInterrupt:
                print(
                    "KeyboardInterrupt rejected. Be patient, images are still being saved."
                )
                continue

        print(" " * 80)
        print("Finished saving images.")
        print(" " * 80)

    except PySpin.SpinnakerException as ex:
        print("Error: %s" % ex)

        # Cleanly stop and release cameras
        release_cameras(cam_list, system)
        return
    return
