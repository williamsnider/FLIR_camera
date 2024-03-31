# Compare saving images singly or as a video
import cv2
import numpy as np
import time
from pathlib import Path
import queue
import threading
import datetime

# params
WIDTH = 960
HEIGHT = 960
FPS = 100.0
SAVE_DIR = Path("/home/oconnorlab/Desktop/single_vs_multi")
NUM_SAVE_THREADS = 1
frame_stop = 1000
# Flags
keep_acquiring_flag = True
mp4_lock = threading.Lock()
# Update batch_dir_name to reflect the current timestamp

batch_dir_name = datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d_%H-%M-%S_%f")


def acquire_frames(queue_list):
    global batch_dir_name
    frame_count = 0
    while keep_acquiring_flag == True:

        # Read sample data
        SAMPLE_DIR = Path("/home/oconnorlab/Desktop/single_vs_multi/sample_data/camTo")
        file_list = list(SAMPLE_DIR.glob("*.bmp"))
        file_list.sort()

        for f in file_list:
            frame = cv2.imread(str(f), cv2.IMREAD_GRAYSCALE)
            for q in queue_list:
                q.put((frame, frame_count, batch_dir_name))
            frame_count += 1
            time.sleep(1 / FPS)

            if frame_count > frame_stop:
                break
        for q in queue_list:
            q.put(("end_of_batch", frame_count, batch_dir_name))

        # Second batch
        batch_dir_name = datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d_%H-%M-%S_%f")
        frame_count = 0
        for f in file_list[::-1]:

            frame = cv2.imread(str(f), cv2.IMREAD_GRAYSCALE)
            for q in queue_list:
                q.put((frame, frame_count, batch_dir_name))
            frame_count += 1
            time.sleep(1 / FPS)

            if frame_count > frame_stop:
                break

        for q in queue_list:
            q.put(("end_of_batch", frame_count, batch_dir_name))

        break
        # frame = np.ones((WIDTH, HEIGHT, 1), dtype=np.uint8) * int(frame_count / frame_stop * 255)

        # # Save frame to queues
        # for q in queue_list:

        #     q.put((frame, frame_count))

        # # Iterate frame count
        # frame_count += 1

        # # Sleep
        # time.sleep(1 / FPS)

        # if frame_count > frame_stop:
        #     keep_acquiring_flag = False
        #     break

    print("Acquire thread done")


# def save_single(queue_s):

#     while keep_acquiring_flag == True:

#         # Get frame from queue
#         try:
#             frame, frame_count = queue_s.get(block=False)
#         except:
#             time.sleep(0.001)
#             continue

#         # Save frame
#         t_start = time.time()
#         filename = Path(SAVE_DIR, "single", f"single_{frame_count}.bmp")
#         filename.parent.mkdir(parents=True, exist_ok=True)

#         # 8 bit
#         cv2.imwrite(str(filename), frame)
#         # print("Single: ", time.time() - t_start, " s")


def save_mp4(cam_name, image_queue, save_location):
    """Saves images that are in the image_queue to a mp4 file."""

    while (keep_acquiring_flag == True) or (image_queue.qsize() > 0):

        frame_count = -1
        while True:

            # Get frame from image_queue
            try:
                frame, frame_idx, batch_dir = image_queue.get(block=False)
                frame_count += 1
            except:
                time.sleep(0.001)  # Allow other threads to run
                continue

            # If first frame, create video writer
            if frame_count == 0:
                time_start = time.time()
                codec = "mp4v"
                fourcc = cv2.VideoWriter_fourcc(*codec)
                savename = Path(save_location, batch_dir, f"{cam_name}.mp4")
                savename.parent.mkdir(parents=True, exist_ok=True)
                out = cv2.VideoWriter(str(savename), fourcc, FPS, (WIDTH, HEIGHT), isColor=False)

            # Add frame to video
            if type(frame) == np.ndarray:
                out.write(frame)

            # If last frame, release video writer
            if type(frame) == type("end_of_batch"):

                if frame == "end_of_batch":
                    out.release()
                    print(f"Saved {frame_count} frames in {time.time() - time_start} s")
                else:
                    raise ValueError("Frame is not 'end_of_batch' or np.ndarray")

                # Exit loop at end of batch
                break


# def save_multi(queue_m, id):
#     global batch_dir_name

#     t_start = None
#     while keep_acquiring_flag == True:

#         # Wait for a frame
#         if queue_m.qsize() == 0:
#             time.sleep(0.001)
#             continue

#         # Set up new video for each batch
#         print("New batch)")
#         codec = "mp4v"
#         fourcc = cv2.VideoWriter_fourcc(*codec)
#         savename = Path(SAVE_DIR, batch_dir_name, f"multi_{codec}_{id}.mp4")
#         savename.parent.mkdir(parents=True, exist_ok=True)
#         out = cv2.VideoWriter(str(savename), fourcc, FPS, (WIDTH, HEIGHT), isColor=False)

#         while (keep_acquiring_flag == True) or (queue_m.qsize() > 0):

#             # Get frame from queue
#             try:
#                 frame, frame_count = queue_m.get(block=False)

#                 if t_start is None:
#                     t_start = time.time()
#             except:
#                 time.sleep(0.0001)
#                 continue

#             # Handle batch changes
#             if type(frame) == type("end_of_batch"):
#                 out.release()
#                 print("Exit out")
#                 break

#             out.write(frame)
#         print("Finished loop")

#         # Release video writer

#     # Create mp4

#     # t_start = time.time()
#     # for f in frame_list:
#     #     out.write(f)
#     print("Multi: ", time.time() - t_start, " s")


if __name__ == "__main__":

    NUM_MULTI = 1

    # Create queues
    queue_list = []
    for i in range(NUM_MULTI):
        queue_list.append(queue.Queue())

    # Start threads
    thread_list = []
    for i in range(NUM_MULTI):
        save_multi_thread = threading.Thread(target=save_mp4, args=(i, queue_list[i], SAVE_DIR))
        save_multi_thread.start()
        thread_list.append(save_multi_thread)

    # Start acquisition
    acquire_thread = threading.Thread(target=acquire_frames, args=(queue_list,))
    acquire_thread.start()

    acquire_thread.join()
    print("Flag switched to false")
    keep_acquiring_flag = False
    # Join threads
    for i in range(NUM_MULTI):
        thread_list[i].join()

    # for i in range(NUM_SAVE_THREADS):
    #     save_single_threads[i].join()
