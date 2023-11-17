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
    FILETYPE,
    MIN_BATCH_INTERVAL,
)


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

    # Factory reset cameras to ensure nodes are rewritable (necessary if they were not properly closed)
    print("Resetting cameras...")
    system = PySpin.System.GetInstance()
    cam_list = system.GetCameras()
    num_previously_connected_cameras = len(cam_list)
    for cam in cam_list:
        cam.Init()
        cam.DeviceReset()
        del cam

    # Wait until cameras are reconnected
    while True:
        print("Waiting for cameras to reconnect...")
        time.sleep(1)

        # Find cameras
        system = PySpin.System.GetInstance()
        cam_list = system.GetCameras()

        if len(cam_list) == num_previously_connected_cameras:
            break

    # Remove cameras from cam_list if they are not in CAMERA_NAMES_DICT
    serial_numbers = [cam.TLDevice.DeviceSerialNumber.GetValue() for cam in cam_list]
    for serial_number in serial_numbers:
        if (serial_number not in CAMERA_NAMES_DICT_COLOR.keys()) and (
            serial_number not in CAMERA_NAMES_DICT_MONO.keys()
        ):
            cam_list.RemoveBySerial(serial_number)

    # Print camera serials and names
    num_cameras = cam_list.GetSize()
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
    cam_list.Clear()
    system.ReleaseInstance()
    print("\nCameras and system released.")


########################
### Thread functions ###
########################


def acquire_images(cam, image_queue):
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
                    image_queue.put((frame_idx, image_copy))
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


def save_images(cam_name, image_queue, save_location):
    """
    Saves images that are in the image_queue.

    Loops infinitely until it receives a "None" in the queue, then returns.
    """

    while True:
        (frame_idx, image) = image_queue.get(block=True)

        # Exit loop if "None" is received
        if image is None:  # No more images
            break

        # Construct filename
        # frame_id = str(image.GetFrameID())
        frame_id = str(frame_idx)  # Resets for each batch, unlike image.GetFrameID()
        frame_id = frame_id.zfill(6)  # pad frame id with zeros to order correctly
        filename = SAVE_PREFIX + "-" + cam_name + "-" + frame_id + FILETYPE

        # Construct batch/camera directory
        cam_dir_path = Path(save_location, batch_dir_name, cam_name)
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
<<<<<<< HEAD:record_multiple_cameras.py
        # queue_lengths = [
        #     " Queue #" + str(idx) + ": " + str(q.qsize()).zfill(5)
        #     for idx, q in enumerate(image_queues)
        # ]
        # print(" Image queue lengths:" + "".join(queue_lengths), end="\r")
        msg = ""
        for idx, q in enumerate(image_queues):
            if q.qsize() > 5:
                msg += " Queue #" + str(idx) + ": " + str(q.qsize()).zfill(5)
        if msg != "":
            print(" Image queue lengths:" + msg, end="\r")
=======
        queue_lengths = [" Queue #" + str(idx) + ": " + str(q.qsize()).zfill(5) for idx, q in enumerate(image_queues)]
        print(" Image queue lengths:" + "".join(queue_lengths), end="\r")
>>>>>>> e813fa8d6188ec870fcac23d5c1a015df06488c1:record_multi_cam.py


def print_previous_batch_size():
    """
    Prints the number of files saved in a batch directory once the batch is complete.

    This function is useful to monitor that images are being saved successfully.
    """

    # List of batch_dir_names that have had a status printed (prevent duplicate printing)
    batches_already_reported = []

    while SAVING_DONE_FLAG is False:
        time.sleep(0.25)

        # Get full path of current batch directory
        batch_dir_path = Path(SAVE_LOCATION, batch_dir_name)

        # Print status if (1) MIN_BATCH_INTERVAL has passed since the last image was acquired. (2) batch_dir_name has not already had its status printed. (3) batch_dir_path exists i.e. the batch directory has been created and images were saved.
        if (
            (time.time() - curr_image_timestamp > MIN_BATCH_INTERVAL)
            and (batch_dir_name not in batches_already_reported)
            and (batch_dir_path.exists())
        ):
            # Construct output message listing the number of images saved for each camera.
            output = "\n"
            output += "*" * 30
            output += "\nBatch: " + batch_dir_name

            # Append the number of images saved for each camera
            for cam_name in CAMERA_NAMES_DICT_COLOR.values():
                cam_subdir = Path(batch_dir_path, cam_name)
                file_list = list(cam_subdir.iterdir())
                num_files = len(file_list)
                output += "\n" + cam_name + ": " + str(num_files) + " images saved."

            # Append the number of images saved for each camera
            for cam_name in CAMERA_NAMES_DICT_MONO.values():
                cam_subdir = Path(batch_dir_path, cam_name)
                file_list = list(cam_subdir.iterdir())
                num_files = len(file_list)
                output += "\n" + cam_name + ": " + str(num_files) + " images saved."

            # Append estimated framerate
            file_list.sort()
            num_files = len(file_list)
            first_file_savetime = file_list[0].stat().st_mtime
            last_file_savetime = file_list[-1].stat().st_mtime
            estimated_framerate = num_files / (last_file_savetime - first_file_savetime)
            output += "\nEstimated framerate: " + str(round(estimated_framerate, 1)) + " fps"
            print(output)

            # Print remaining space on hard drive
            check_hard_drive_space()

            # Update for subsequent loops
            batches_already_reported.append(batch_dir_name)


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
        image_queues = []

        for cam in cam_list:
            # Add a new image_queue
            image_queues.append(queue.Queue())

            # Create multiple saving threads for each camera, targeting the most recent image_queue
            for _ in range(NUM_THREADS_PER_CAM):
                saving_thread = threading.Thread(
                    target=save_images,
                    args=(cam.DeviceUserID(), image_queues[-1], SAVE_LOCATION),
                )
                saving_thread.start()
                saving_threads.append(saving_thread)

            # Create an acquisition thread for each camera, which places images into the most recent image_queue
            acquisition_thread = threading.Thread(target=acquire_images, args=(cam, image_queues[-1]))
            acquisition_thread.start()
            acquisition_threads.append(acquisition_thread)

        # Create the queue counter, which prints the size of each image queue
        time.sleep(0.5)
        queue_counter_thread = threading.Thread(target=queue_counter, args=([image_queues]))
        queue_counter_thread.start()

        # Create the print_previous_batch_size thread, which prints the number of saved images in each batch
        print_previous_batch_size_thread = threading.Thread(target=print_previous_batch_size)
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

        # Cleanly stop and release cameras
        release_cameras(cam_list, system)

        # Pass None to image queues to signal the end of saving
        for q in image_queues:
            for _ in range(NUM_THREADS_PER_CAM):
                q.put((None, None))

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

    except PySpin.SpinnakerException as ex:
        print("Error: %s" % ex)

        # Cleanly stop and release cameras
        release_cameras(cam_list, system)
        return


########################
### Useful functions ###
########################


def get_remaining_space():
    """Returns the remaining space on the hard drive in GB."""
    total_space = psutil.disk_usage("/").total
    used_space = psutil.disk_usage("/").used
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

    # Identify connected cameras
    cam_list, system, num_cameras = find_cameras()

    if num_cameras != 0:
        # Initialize and set imaging parameters
        result = set_camera_params(cam_list)

        # Acquire and save images using multiple threads; loops until ctrl+c
        if result:
            record_high_bandwidth_video(cam_list, system)

    else:
        print("No cameras found. Exiting.")
