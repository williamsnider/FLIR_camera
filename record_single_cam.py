import cv2
import threading
from pathlib import Path
import time
import datetime
from queue import Queue
import PySpin
import numpy as np


def save_frame_from_queue(queue_A, SAVE_DIR, IMG_WIDTH, IMG_HEIGHT, FPS):

    # Initialize variables to estimate fps
    start_time = time.time()
    frame_count = 0

    # Get list of all subdirs
    subdirs = SAVE_DIR.glob("*")
    subdirs = [s for s in subdirs if s.is_dir()]
    subdirs.sort()
    if len(subdirs) > 0:
        group_number = int(str(subdirs[-1].stem)) + 1
        group_count = 0
    else:
        group_number = 0
        group_count = 0

    # Create mp4 out object
    group_dir = str(group_number).zfill(4)
    mp4_filename = Path(SAVE_DIR, group_dir, f"{group_number}.mp4")
    mp4_filename.parent.mkdir(parents=True, exist_ok=True)
    mp4_out = cv2.VideoWriter(str(mp4_filename), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (IMG_WIDTH, IMG_HEIGHT))

    # Create txt file to save frame times
    txt_filename = Path(SAVE_DIR, group_dir, f"{group_number}.txt")

    try:
        while True:
            # Print size of queue if getting full
            queue_length = queue_A.qsize()
            if queue_length > 0:
                print(f"Queue length: {queue_length}")

            # Get frame from queue
            item = queue_A.get()
            frame, frame_time, _ = item

            # None is signal to stop thread
            if frame is None:
                break
            frame_as_cv2 = cv2.cvtColor(frame.GetNDArray(), cv2.COLOR_BayerRG2BGR)
            mp4_out.write(frame_as_cv2)

            # Save frame_time to txt_file
            with open(txt_filename, "a") as file:
                file.write(frame_time + "\n")

            # Estimate fps
            frame_count += 1
            if frame_count % 15 == 0:
                end_time = time.time()
                fps = frame_count / (end_time - start_time)
                print(f"Estimated FPS of saving: {round(fps,3)}", end="\r")

                # Reset variables
                frame_count = 0
                start_time = time.time()

            # Iterate group number
            group_count += 1
            if group_count > 10000:
                group_number += 1
                group_count = 0

                # Close mp4_out and open new one
                mp4_out.release()

                group_dir = str(group_number).zfill(4)
                mp4_filename = Path(SAVE_DIR, group_dir, f"{group_number}.mp4")
                mp4_filename.parent.mkdir(parents=True, exist_ok=True)
                mp4_out = cv2.VideoWriter(
                    str(mp4_filename), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (IMG_WIDTH, IMG_HEIGHT)
                )

                # Create new txt file
                txt_filename = Path(SAVE_DIR, group_dir, f"{group_number}.txt")

    finally:
        mp4_out.release()

    print("Save thread joined")


def display_frame_from_queues(list_of_queue_lists, window_names_list):
    """Creates windows that display images from queues in real-time."""

    # Create windows
    for window_name in window_names_list:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    # Create list of last frames
    list_of_last_frame_lists = []
    for queue_list in list_of_queue_lists:
        last_frame_list = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(len(queue_list))]
        list_of_last_frame_lists.append(last_frame_list)

    # Loop through each queue
    continue_looping = True
    while continue_looping is True:

        for window_idx, queue_list in enumerate(list_of_queue_lists):
            window_name = window_names_list[window_idx]

            # Skip if no queues
            if len(queue_list) == 0:
                continue

            # Collect frames from queues
            for queue_idx, queue in enumerate(queue_list):

                # Loop until no more frames in queue (prevent display queue from getting too large; we only need to display the most recent frame anyway).
                while True:
                    try:
                        frame, _, _ = queue.get_nowait()

                        # None is signal to stop thread -> exit loop to join thread
                        if frame is None:
                            continue_looping = False
                            break

                        # Convert to numpy
                        frame = cv2.cvtColor(frame.GetNDArray(), cv2.COLOR_BayerRG2BGR)
                        # frame = cv2.resize(frame, (IMG_WIDTH // 2, IMG_HEIGHT // 2))  # Resize to fit on screen
                        list_of_last_frame_lists[window_idx][queue_idx] = frame
                    except:
                        break

            # Stack into one image, converting to two rows if necessary
            img_height, img_width, _ = list_of_last_frame_lists[window_idx][0].shape

            num_queues = len(queue_list)
            MAX_COLS = 3
            num_cols = min(num_queues, MAX_COLS)
            num_rows = np.ceil(num_queues / MAX_COLS).astype(int)

            stacked_frame = np.zeros((img_height * num_rows, img_width * num_cols, 3), dtype=np.uint8)
            for idx, frame in enumerate(list_of_last_frame_lists[window_idx]):
                stacked_frame[
                    img_height * (idx // MAX_COLS) : img_height * ((idx // MAX_COLS) + 1),
                    img_width * (idx % MAX_COLS) : img_width * ((idx % MAX_COLS) + 1),
                ] = frame

            cv2.imshow(window_name, stacked_frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
        time.sleep(0.001)
    print(f"Display thread joined for {window_name}")


def display_frame_from_queue(queue_B, IMG_WIDTH, IMG_HEIGHT, window_name):

    while True:
        frame = queue_B.get()
        if frame is None:
            break

        frame = cv2.cvtColor(frame.GetNDArray(), cv2.COLOR_BayerRG2BGR)
        frame = cv2.resize(frame, (IMG_WIDTH // 2, IMG_HEIGHT // 2))  # Resize to fit on screen
        cv2.imshow(window_name, frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
        time.sleep(0.001)
    print(f"Display thread joined for {window_name}")


def join_threads(thread_list):
    for thread in thread_list:
        thread.join()


def capture_frames(camera, queue_list, YYYY_MM_DD, stop_event):

    camera.BeginAcquisition()

    # Initialize variables to estimate fps
    start_time = time.time()
    frame_count = 0

    while not stop_event.is_set():
        try:
            image_result = camera.GetNextImage(250)

            if image_result.IsIncomplete():
                print("Image incomplete with image status %d ..." % image_result.GetImageStatus())
            else:
                # Get current time
                current_time = datetime.datetime.now()
                formatted_time = current_time.strftime("%H-%M-%S-") + str(current_time.microsecond).zfill(6)
                frame_time = f"{YYYY_MM_DD}_{formatted_time}"

                # Add image to queues
                image_copy = PySpin.Image.Create(image_result)
                for queue in queue_list:
                    queue.put((image_copy, frame_time, ""))

                # Ensure to release the image to avoid memory leak
                image_result.Release()

        except PySpin.SpinnakerException as ex:
            print("Error: %s" % ex)
            continue

        # Estimate fps
        frame_count += 1
        if frame_count % 15 == 0:
            end_time = time.time()
            fps = frame_count / (end_time - start_time)

            frame_count = 0
            start_time = time.time()

    camera.EndAcquisition()
    print("Capture thread joined")


def record_cam_sw(cam, queue_list, stop_event, fps, cam_name):

    YYYY_MM_DD = time.strftime("%Y-%m-%d")
    SAVE_DIR = Path("/mnt/Data4TB", YYYY_MM_DD, cam_name)
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    IMG_WIDTH = 1920
    IMG_HEIGHT = 1200

    try:
        cam.Init()

        # Configure camera settings
        cam.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)
        cam.AcquisitionFrameRateEnable.SetValue(True)
        cam.AcquisitionFrameRate.SetValue(fps)

    except PySpin.SpinnakerException as ex:
        print("Error: %s" % ex)
        exit()

    # Start thread that captures frames from camera, placing a copy in each queue.
    thread_capture = threading.Thread(target=capture_frames, args=(cam, queue_list, YYYY_MM_DD, stop_event))

    # Start thread that saves frames from queue 0 to disk
    thread_save = threading.Thread(
        target=save_frame_from_queue, args=(queue_list[0], SAVE_DIR, IMG_WIDTH, IMG_HEIGHT, fps)
    )

    thread_list = [thread_capture, thread_save]

    for th in thread_list:
        th.start()

    join_threads(
        thread_list,
    )


if __name__ == "__main__":

    CAM_SERIAL_A = "23398259"
    CAM_SERIAL_B = "23398260"

    system = PySpin.System.GetInstance()
    cam_list_all = system.GetCameras()
    camA = cam_list_all.GetBySerial(CAM_SERIAL_A)
    camB = cam_list_all.GetBySerial(CAM_SERIAL_B)

    cam_list_sub = [camA, camB]

    # Reset cameras
    for cam in cam_list_sub:
        cam.Init()
        cam.DeviceReset()
        del cam

    while True:
        time.sleep(5)  # Wait for camera to reconnect

        try:
            camA = cam_list_all.GetBySerial(CAM_SERIAL_A)
            camB = cam_list_all.GetBySerial(CAM_SERIAL_B)
            break
        except:
            continue

    stop_event = threading.Event()

    queueA_list = [Queue() for _ in range(3)]  # 0th queue is for saving, remainder are for display
    fps = 20.0
    record_threadA = threading.Thread(target=record_cam_sw, args=(camA, queueA_list, stop_event, fps, CAM_SERIAL_A))
    record_threadA.start()

    queueB_list = [Queue() for _ in range(3)]  # 0th queue is for saving, remainder are for display
    fps = 5.0
    record_threadB = threading.Thread(target=record_cam_sw, args=(camB, queueB_list, stop_event, fps, CAM_SERIAL_B))
    record_threadB.start()

    # Start display thread
    display1 = [queueA_list[1]]
    display2 = [queueB_list[1]]
    display3 = [queueA_list[2], queueB_list[2]]
    display_thread = threading.Thread(
        target=display_frame_from_queues,
        args=([display1, display2, display3], [CAM_SERIAL_A, CAM_SERIAL_B, "Combined"]),
    )
    display_thread.start()

    try:
        record_threadA.join()
        record_threadB.join()
    except KeyboardInterrupt:
        stop_event.set()
        for queue in queueA_list:
            queue.put((None, None))
        for queue in queueB_list:
            queue.put((None, None))
        cv2.destroyAllWindows()
    finally:
        record_threadA.join()
        record_threadB.join()

    # Release system instance
    camA.DeInit()
    camB.DeInit()
    del camA
    del camB
    del cam_list_sub
    cam_list_all.Clear()
    system.ReleaseInstance()
