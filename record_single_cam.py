import cv2
import threading
from pathlib import Path
import time
import datetime
from queue import Queue
import PySpin


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

            # None is signal to stop thread
            if item is None:
                break

            # Save frame to mp4
            frame, frame_time = item
            frame_as_cv2 = cv2.cvtColor(frame.GetNDArray(), cv2.COLOR_BayerRG2BGR)
            mp4_out.write(frame_as_cv2)

            # Save frame_time to txt_file
            with open(txt_filename, "a") as file:
                file.write(frame_time + "\n")

            # # Save frame to file as grayscale
            # frame, frame_time = item
            # filename = Path(SAVE_DIR, str(group_number), f"{frame_time}.bmp")
            # filename.parent.mkdir(parents=True, exist_ok=True)
            # cv2.imwrite(str(filename), frame)

            # Estimate fps
            frame_count += 1
            if frame_count % 30 == 0:
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

    # Print number of frames in mp4_out
    cap = cv2.VideoCapture(str(mp4_filename))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Number of frames in {mp4_filename}: {frame_count}")

    # Print number of frames in txt file
    with open(txt_filename, "r") as file:
        lines = file.readlines()
        print(f"Number of frames in {txt_filename}: {len(lines)}")

    print("Save thread joined")


def display_frame_from_queue(queue_B, IMG_WIDTH, IMG_HEIGHT):

    while True:
        frame = queue_B.get()
        if frame is None:
            break

        frame = cv2.cvtColor(frame.GetNDArray(), cv2.COLOR_BayerRG2BGR)
        frame = cv2.resize(frame, (IMG_WIDTH // 2, IMG_HEIGHT // 2))  # Resize to fit on screen
        cv2.imshow("Webcam Stream", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
        time.sleep(0.001)
    print("Display thread joined")


def join_threads(thread_list):
    for thread in thread_list:
        thread.join()


def capture_frames(camera, queue_A, queue_B, YYYY_MM_DD, stop_event):

    camera.BeginAcquisition()

    # Initialize variables to estimate fps
    start_time = time.time()
    frame_count = 0
    total_frame_count = 0

    while not stop_event.is_set():

        try:
            image_result = camera.GetNextImage(100)

            if image_result.IsIncomplete():
                print("Image incomplete with image status %d ..." % image_result.GetImageStatus())
            else:
                # Get current time
                current_time = datetime.datetime.now()
                formatted_time = current_time.strftime("%H-%M-%S-") + str(current_time.microsecond).zfill(6)
                frame_time = f"{YYYY_MM_DD}_{formatted_time}"

                # Add image to queues
                image_copy = PySpin.Image.Create(image_result)
                queue_A.put((image_copy, frame_time))
                queue_B.put(image_copy)

                # Ensure to release the image to avoid memory leak
                image_result.Release()

        except PySpin.SpinnakerException as ex:
            print("Error: %s" % ex)
            continue

        # Estimate fps
        frame_count += 1
        if frame_count % 30 == 0:
            end_time = time.time()
            fps = frame_count / (end_time - start_time)
            # print(f"Estimated FPS of capture: {fps}")

            # Reset variables
            frame_count = 0
            start_time = time.time()

    camera.EndAcquisition()
    print("Capture thread joined")


def record_overhead(cam, queue_A, queue_B, stop_event):

    YYYY_MM_DD = time.strftime("%Y-%m-%d")
    SAVE_DIR = Path("/mnt/Data4TB", YYYY_MM_DD, "overhead")
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    IMG_WIDTH = 1920
    IMG_HEIGHT = 1200
    FPS = 30.0

    try:
        # Initialize camera
        cam.Init()

        # Configure camera settings
        cam.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)
        cam.AcquisitionFrameRateEnable.SetValue(True)
        cam.AcquisitionFrameRate.SetValue(30.0)

    except PySpin.SpinnakerException as ex:
        print("Error: %s" % ex)
        exit()

    thread_capture = threading.Thread(target=capture_frames, args=(cam, queue_A, queue_B, YYYY_MM_DD, stop_event))
    thread_save = threading.Thread(target=save_frame_from_queue, args=(queue_A, SAVE_DIR, IMG_WIDTH, IMG_HEIGHT, FPS))
    thread_display = threading.Thread(target=display_frame_from_queue, args=(queue_B, IMG_WIDTH, IMG_HEIGHT))

    thread_list = [thread_capture, thread_save, thread_display]

    for th in thread_list:
        th.start()

    join_threads(thread_list)
    # try:
    #     join_threads(thread_list)
    # except KeyboardInterrupt:
    #     print("Detected keyboard interrupt")
    #     queue_A.put(None)
    #     queue_B.put(None)
    #     cv2.destroyAllWindows()
    # finally:
    #     join_threads(thread_list)


if __name__ == "__main__":

    CAM_SERIAL = "23398261"

    # Get system
    system = PySpin.System.GetInstance()

    # Get camera by serial number
    cam_list = system.GetCameras()
    cam = cam_list.GetBySerial(CAM_SERIAL)

    # Factory reset cameras to ensure nodes are rewritable (necessary if they were not properly closed)
    print(f"Resetting overhead camera {CAM_SERIAL}...")
    for cam in [cam]:
        cam.Init()
        cam.DeviceReset()
        del cam

    # Wait until cameras are reconnected
    while True:
        print(f"Waiting for camera {CAM_SERIAL} to reconnect...")
        time.sleep(5)  # Wait for camera to reconnect

        try:
            cam = cam_list.GetBySerial(CAM_SERIAL)
            break
        except:
            continue

    queue_A = Queue()
    queue_B = Queue()
    stop_event = threading.Event()
    record_thread = threading.Thread(target=record_overhead, args=(cam, queue_A, queue_B, stop_event))
    record_thread.start()

    try:
        record_thread.join()
    except KeyboardInterrupt:
        print("Detected keyboard interrupt")
        stop_event.set()
        queue_A.put(None)
        queue_B.put(None)
        cv2.destroyAllWindows()
    finally:
        record_thread.join()

    # Release system instance
    cam.DeInit()
    del cam
    cam_list.Clear()
    system.ReleaseInstance()


# def acquire_images(camera, num_images):
#     camera.BeginAcquisition()

#     start_time = time.time()
#     for i in range(num_images):
#         try:
#             image_result = camera.GetNextImage(1000)

#             if image_result.IsIncomplete():
#                 print("Image incomplete with image status %d ..." % image_result.GetImageStatus())
#             else:
#                 # You can process the image here

#                 print("Acquired image %d" % i)

#                 # Ensure to release the image to avoid memory leak
#                 image_result.Release()

#         except PySpin.SpinnakerException as ex:
#             print("Error: %s" % ex)
#             return False

#     end_time = time.time()
#     print("Estimated FPS: %.2f" % (num_images / (end_time - start_time)))
#     camera.EndAcquisition()
#     return True
