import os
from multi_cam_helper import set_up_cameras, set_camera_params, record_high_bandwidth_video, convert_to_video, release_cameras
from multi_cam_wrapper import save_location
def main():
    
    """
    Main function for acquiring images from multiple cameras with hardware trigger.
    """
    # Change cwd to save location
    if os.path.isdir(save_location) is False:
        os.makedirs(save_location)
    os.chdir(save_location)

    # Find cameras
    cam_list, system, num_cameras = set_up_cameras()

    # Fail immediately if no cameras connected
    if num_cameras == 0: return False

    # Initialize and set imaging parameters
    result = set_camera_params(cam_list)

    # Acquire images, deinitialize
    result = record_high_bandwidth_video(cam_list)

    # Release cameras and system
    release_cameras(cam_list, system)

    # Convert images to mp4 video
    convert_to_video(save_location) # save_location is where the images are stored

if __name__ == '__main__':
    main()