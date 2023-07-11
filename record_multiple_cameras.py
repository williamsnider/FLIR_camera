"""
This script records images from multiple cameras simultaneously. Acquisition is hardware triggered (5V pulse from DAQ)."""
from utilities import set_up_cameras, set_camera_params, record_high_bandwidth_video, convert_to_video, release_cameras
from parameters import SAVE_LOCATION, CAMERA_NAMES_DICT
    
if __name__ == '__main__':

    # Find cameras
    cam_list, system, num_cameras = set_up_cameras(CAMERA_NAMES_DICT)

    # Fail immediately if no cameras connected
    if num_cameras == 0: 
        print("No cameras found. Exiting.")
    else:

        set_camera_params(cam_list) # Initialize and set imaging parameters

        record_high_bandwidth_video(cam_list) # Acquire images, loops until ctrl+c

        release_cameras(cam_list, system)  # Release cameras and system

        # Convert images to video
        user_response = input("\nWrite YES to convert images to video: ")
        if user_response == "YES":
            convert_to_video() # save_location is where the images are stored


    #TODO: Decide how to handle new trials