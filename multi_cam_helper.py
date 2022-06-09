import os
import PySpin
import threading
import queue
import time
from PIL import Image
from multi_cam_wrapper import camera_params, camera_names, save_location, save_prefix, GRAB_TIMEOUT, NUM_THREADS_PER_CAM, fps, save_format, save_format_extension, quality_level
import sys
import cv2
import natsort

# Two flags used globally
keep_acquiring = True
saving_done = False

def set_up_cameras():
    """
    Set up the system object and cameras.
    """

    # Retrieve singleton reference to system object
    system = PySpin.System.GetInstance()

    cam_list = system.GetCameras()

    num_cameras = cam_list.GetSize()

    print('Number of cameras detected: {0}'.format(num_cameras))

    if num_cameras == 0:
        print("Since no cameras were detected, cam_list is being cleared and the system is being released.")
        release_cameras(cam_list, system)

    return cam_list, system, num_cameras

def set_camera_params(cam_list):
    """
    Initialize the cameras and set experiment-specific parameters.
    """
    result = True

    for cam in cam_list:

        # Initialize
        cam.Init()

        # Set parameters from wrapper file
        for [param, value] in camera_params:

            # To handle nested attributes, split param strings by period. Basically, this will help the program handle updating parameters like "TLStream.StreamBufferCountMode"
            attr_list = param.split('.')

            # Updated the nested attribute pointer until we have reached the final attribute.
            nested_attr = cam
            for attr in attr_list:
                nested_attr = getattr(nested_attr, attr)
            
            # Set the value
            try:
                nested_attr.SetValue(value)
            except PySpin.SpinnakerException as ex:
                print('Error: %s' % ex)
                print('This was probably caused by not properly closing the cameras. The cameras need to be reset (or unplugged).')
                result = False

        # Assign DeviceUserID based on serial number
        for [serial, name] in camera_names:

            if serial == cam.DeviceID():
                cam.DeviceUserID.SetValue(name)

                
        
    return result

def acquire_images(cam, image_queue):
    """
    Acquires images until the keep_acquiring flag is set to False.
    As each image is acquired it is put into the `image_queue`.
    """
    try:
        result = True
        device_user_ID = cam.DeviceUserID()

        cam.BeginAcquisition()
        print('[{}] Acquiring images...'.format(device_user_ID))

        global keep_acquiring
        while keep_acquiring is True:

            try:
                
                # Print if camera buffer gets full, indicating saving is not happening fast enough
                if cam.TransferQueueCurrentBlockCount() > 0:
                    print(("# of images in {0}'s buffer: {1}").format(device_user_ID,cam.TransferQueueCurrentBlockCount()))

                # Grab image if one has been grabbed; if no image found within GRAB_TIMEOUT, restart the loop to check if the keep_acquiring flag has been set to false. In that case, end acquisition.
                try:
                    image_result = cam.GetNextImage(GRAB_TIMEOUT)
                except PySpin.SpinnakerException:
                    #print('Did not grab image because no trigger was given')
                    continue

                if image_result.IsIncomplete():
                    print('[%s] Image incomplete with image status %d ...' % (
                        device_user_ID, image_result.GetImageStatus()))

                else:
                    # Add grabbed image to queue
                    image_copy = PySpin.Image.Create(image_result)
                    image_queue.put(image_copy)
                    image_result.Release()
            except PySpin.SpinnakerException as ex:
                print('Error: %s' % ex)
                return False
        cam.EndAcquisition()
        cam.DeInit()

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        return False

    return result   

def save_images(cam_name, image_queue, save_location):
    """
    Loops infinitely saving images from the `image_queue`
    until it receives a "None", then returns. Images are saved
    with the filename `save_path`/`serial_number`-frame_id.ext
    where .ext is .jpeg if `compress` is True, and .tiff otherwise.
    """
    while True:
        image = image_queue.get(block=True)
        if image is None:  # No more images
            break

        frame_id = str(image.GetFrameID())
        filename = save_prefix + '-' + cam_name + '-' + frame_id
        filename += save_format_extension
        filename = os.path.join(save_location, filename)
        
        # Spinnaker save - slow
        # image.Save(filename)  # uncomment to use Spinnaker save

        # Convert to RGB and save - moderately slow
        image_converted = image.Convert(save_format)

        if save_format_extension == ".jpg":
            Image.fromarray(image_converted.GetNDArray()).save(filename, quality=quality_level)
        else:
            Image.fromarray(image_converted.GetNDArray()).save(filename)

        # Leave as Bayer and save
        #Image.fromarray(image.GetNDArray()).save(filename)

        # Save as raw
        #image.GetNDArray().tofile(filename)  #  uncomment to save as raw
        #print(threading.currentThread().getName()+" saved image:"+filename, end="\r")
        #print('[%s] image saved at path: %s' % (serial_number, filename))

def queue_counter(image_queues):
    """
    Create a new thread that displays the size of the image queue. Thread is preferred to having it in the main code so that it is easy to have both during acqusition and saving. This is solely for printing output, not used functionally.
    """
    while saving_done is False:
        time.sleep(0.1)
        queue_lengths = [" Queue #"+ str(idx) + ": " + str(q.qsize()).zfill(5) for idx, q in enumerate(image_queues)]
        print(" Image queue lengths:"+"".join(queue_lengths), end="\r")


def record_high_bandwidth_video(cam_list):
    """
    Creates and starts a recording a saving thread for each
    camera in `cam_list`. Then waits for the threads to run.

    Returns a boolean indicating whether the acquisition was successful or not.
    """
    try:
        result = True

        acquisition_threads = []
        saving_threads = []
        image_queues = []

        for i, cam in enumerate(cam_list):
            image_queues.append(queue.Queue())
            for j in range(NUM_THREADS_PER_CAM):
                
                saving_thread = threading.Thread(target=save_images, args=(cam.DeviceUserID(), image_queues[-1], save_location))
                saving_thread.start()
                saving_threads.append(saving_thread)

            acquisition_thread = threading.Thread( target=acquire_images, args=(cam, image_queues[-1]))
            acquisition_thread.start()
            acquisition_threads.append(acquisition_thread)
        
        # Setup the queue counter
        time.sleep(0.5)
        queue_counter_thread = threading.Thread(target=queue_counter, args=([image_queues]))
        queue_counter_thread.start()

        # Trigger an end to acquisition with keyboard interrupt. 
        global keep_acquiring
        while keep_acquiring is True:
            try:
                time.sleep(0.1)

                # Print the size of the image queues to see if the threads are working fast enough.
                #queue_lengths = [" Queue #"+ str(idx) + ": " + str(q.qsize()).zfill(5) for idx, q in enumerate(image_queues)]
                #print(queue_lengths, end="\r")
            except KeyboardInterrupt:
                keep_acquiring = False
                continue

        # Cause the main thread to wait until the other threads are done; with the keep_acquiring method above, this may be redundant, but good form to wait for the .join() method in my opinion.
        for at in acquisition_threads:
            at.join()
        print(' '*80)
        print('Finished acquiring images...')

        # Signal to processing threads that acquisition is finished. None in image queue signals end of saving.
        for q in image_queues:
            for j in range(NUM_THREADS_PER_CAM):
                q.put(None)
        
        # This block prevents ctrl+c from closing program before images have finished saving.
        global saving_done
        while saving_done is False:
            try:
                for pt in saving_threads:
                    pt.join()
                # Mark saving as done, end the queue_counter
                saving_done = True
                queue_counter_thread.join()
            except KeyboardInterrupt:
                print('KeyboardInterrupt rejected. Be patient, images are still being saved...')
                continue
        
        print(' '*80)
        print('Finished saving images...')
        print(' '*80)

        # Release reference to camera
        # NOTE: Unlike the C++ examples, we cannot rely on pointer objects being automatically
        # cleaned up when going out of scope.
        # The usage of del is preferred to assigning the variable to None.
        del cam

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False

    return result

def release_cameras(cam_list, system):
    """
    Clear the camera list and release the system. This is important to do when the program closes or else you might need to reset (unplug) the cameras.
    """
    cam_list.Clear()
    system.ReleaseInstance()
    print("Cameras and system released.\n")

def convert_to_video(image_folder):
    """ 
    Converts a folder of images into a video avi file. Use the wrapper file to adjust the fps.
    """
    should_convert = input("\nWrite YES to convert images to video now: ")
    if should_convert != "YES":
        pass

    else:
            
        for [_, cam_ID]  in camera_names:
            video_name = save_prefix+'-'+cam_ID+'.avi'

            # Sort images using natsort; otherwise image-1 grouped with image-10
            sorted_image_names = natsort.natsorted(os.listdir(image_folder))
            images = [img for img in sorted_image_names if img.endswith(save_format_extension) & img.startswith(save_prefix+'-'+cam_ID)]
            
            if images == []:
                print("No images found for "+cam_ID+" of type "+save_format_extension+" so no video was created.\n")
                continue
            else:
                print("Converting images to video format for camera " + cam_ID + ".\n")

            frame = cv2.imread(os.path.join(image_folder, images[0]))
            height, width, layers = frame.shape
            fourcc = cv2.VideoWriter_fourcc('M','J','P','G') # TODO: suboptimal because it introduces second round of compression.
            video = cv2.VideoWriter(video_name, fourcc, fps, (width,height), True)

            for image in images:
                print(image)
                video.write(cv2.imread(os.path.join(image_folder, image)))

            cv2.destroyAllWindows()
            video.release()

            print("Video saved as "+video_name+" at "+str(fps)+"fps.\n")
    
    #TODO: Put in a check on whether the input FPS is plausible given the timestamps of the images.
    
    #TODO: Ensure that skipped frames are handled properly (black screen)

def rename_images(image_folder, initial_prefix_list, target_prefix_list, save_format_extension=".tiff"):
    """
    Rename the images in the folder given a list of the initial names and target_names. Changes the prefix, so "1947202-01.tiff" becomes "cam-A-01.tiff".
    """
    for [idx, initial_prefix] in enumerate(initial_prefix_list):
        
        # Make list containing images of correct initial prefix and ending
        image_list = [i for i in os.listdir(image_folder) if i.startswith(initial_prefix) & i.endswith(save_format_extension)]

        if image_list == []:
            print("No images found with prefix {0} and extension {1}.".format(initial_prefix, save_format_extension))
        else:
            pass

        # Iterate through images, assigning new names
        for image_name in image_list:
            image_number = image_name.split(initial_prefix)[1].split(save_format_extension)[0]
            new_prefix = target_prefix_list[idx]
            new_name = new_prefix + image_number + save_format_extension
            os.rename(os.path.join(image_folder,image_name), os.path.join(image_folder,new_name))


#################################################
### Not used but potentially useful functions ###
#################################################

# def print_device_info(nodemap, cam_num):
#     """
#     This function prints the device information of the camera from the transport
#     layer; please see NodeMapInfo example for more in-depth comments on printing
#     device information from the nodemap.

#     :param nodemap: Transport layer device nodemap.
#     :param cam_num: Camera number.
#     :type nodemap: INodeMap
#     :type cam_num: int
#     :returns: True if successful, False otherwise.
#     :rtype: bool
#     """

#     print('Printing device information for camera %d... \n' % cam_num)

#     try:
#         result = True
#         node_device_information = PySpin.CCategoryPtr(nodemap.GetNode('DeviceInformation'))

#         if PySpin.IsAvailable(node_device_information) and PySpin.IsReadable(node_device_information):
#             features = node_device_information.GetFeatures()
#             for feature in features:
#                 node_feature = PySpin.CValuePtr(feature)
#                 print('%s: %s' % (node_feature.GetName(),
#                                   node_feature.ToString() if PySpin.IsReadable(node_feature) else 'Node not readable'))

#         else:
#             print('Device control information not available.')
#         print()

#     except PySpin.SpinnakerException as ex:
#         print('Error: %s' % ex)
#         return False

#     return result

    
# def have_write_access():
#     """
#     Quickly test if we have permission to write by opening a test_file.
#     """

#     try:
#         test_file = open('test.txt', 'w+')
#         result = True
#         test_file.close()
#         os.remove(test_file.name)
#     except IOError:
#         result = False

#     return result

# def run_multiple_cameras(cam_list):
#     """
#     This function acts as the body of the example.
#     """
#     try:
#         result = True


#         # Acquire images on all cameras
#         result &= acquire_images(cam_list)

#         # Deinitialize each camera
#         #
#         # *** NOTES ***
#         # Again, each camera must be deinitialized separately by first
#         # selecting the camera and then deinitializing it.
#         for cam in cam_list:

#             # Deinitialize camera
#             cam.DeInit()

#         # Release reference to camera
#         # NOTE: Unlike the C++ examples, we cannot rely on pointer objects being automatically
#         # cleaned up when going out of scope.
#         # The usage of del is preferred to assigning the variable to None.
#         del cam

#     except PySpin.SpinnakerException as ex:
#         print('Error: %s' % ex)
#         result = False

#     return resultd

# def acquire_images(cam_list):
#     """
#     This function acquires and saves images from each device.
#     """

#     try:
#         result = True

#         # Begin acquisition
#         for i, cam in enumerate(cam_list):
#             cam.BeginAcquisition()

#             print('Camera %d started acquiring images...' % i)

        
#         # Keep track of device id's (don't look up each time)
#         device_id_vec = [cam.DeviceID() for cam in cam_list]

#         # Keep track of which # image each camera is taking
#         image_number_vec = [0 for cam in cam_list] # TODO: I do not know if this would handle a dropped frame well.
#         keep_acquiring = True

#         while keep_acquiring is True:

#             for i, cam in enumerate(cam_list):
#                 try:
#                     # Retrieve device serial number for filename
#                     device_serial_number = device_id_vec[i]

#                     # Print if buffer gets full
#                     if cam.TransferQueueCurrentBlockCount() > 0:
#                         print(("# of images in {0}'s buffer: {1}").format(device_serial_number,cam.TransferQueueCurrentBlockCount()))

#                     # Grab the next image. 
#                     # If an image is not made available before GRAB_TIMEOUT ms, restart the loop. This enables us to break out of the program and avoid getting hung when no more hardware triggers are occuring.
#                     try:
#                         #print('   Press ctrl + c to stop acquiring and safely deinitialize cameras.', end='\r')
#                         image_result = cam.GetNextImage(GRAB_TIMEOUT)

#                         # increment counter on first camera; otherwise gets out of count 

#                     except:
#                         #print('Camera {0} grabbed no image because no hardware trigger was given.'.format(i))
#                         continue

#                     if image_result.IsIncomplete():
#                         print('Image incomplete with image status %d ... \n' % image_result.GetImageStatus())
#                     else:
#                         # Print image information
#                         #print('Camera {0} grabbed image {1}'.format(i, image_number),' '*50)

#                         # Convert image to mono 8
#                         image_converted = image_result
#                         #image_result.Convert(PySpin.PixelFormat_Mono8, PySpin.HQ_LINEAR)

#                         # Create a unique filename
#                         filename = 'Test-{0}-{1}.raw'.format(device_serial_number, image_number_vec[i]) 

#                         # Save image
#                         image_converted.Save(filename)
#                         image_number_vec[i] += 1 
#                         #print('Image saved at %s' % filename)

#                     # Release image
#                     image_result.Release()
#                 except KeyboardInterrupt:
#                     #print('KeyboardInterrupt used to stop camera acquisition. Shutting down...')
#                     keep_acquiring = False
#                 except PySpin.SpinnakerException as ex:
#                     print('Error: %s' % ex)
#                     result = False
        
#         # End acquisition for each camera
#         for cam in cam_list:
#             cam.EndAcquisition()

#     except PySpin.SpinnakerException as ex:
#         print('Error: %s' % ex)
#         result = False

#     return result