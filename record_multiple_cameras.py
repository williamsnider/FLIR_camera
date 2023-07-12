### Main script for recording from multiple FLIR cameras simultaneously. The cameras must be hardware triggered.

from utilities import find_cameras, set_camera_params, record_high_bandwidth_video

if __name__ == "__main__":
    # Identify connected cameras
    cam_list, system, num_cameras = find_cameras()

    if num_cameras != 0:
        # Initialize and set imaging parameters
        result = set_camera_params(cam_list)

        # Acquires and saves images using multiple threads; loops until ctrl+c
        if result == True:
            record_high_bandwidth_video(cam_list, system)

    else:
        print("No cameras found. Exiting.")
