import os
import PySpin
import threading
import queue
import time
from PIL import Image  # For faster saves

SAVE_DIR = "C:\\Users\\William\\Documents\\Data\\Test"  # The directory to save to
NUM_IMAGES = 100000  # The number of images to grab per camera
NUM_THREADS_PER_CAM = 4  # The number of saving threads per camera


def save_images(serial_number, image_queue, save_path, compress=False):
    """
    Loops infinitely saving images from the `image_queue`
    until it receives a "None", then returns. Images are saved
    with the filename `save_path`/`serial_number`-frame_id.ext
    where .ext is .jpeg if `compress` is True, and .tiff otherwise.
    """
    while True:
        image_to_save = image_queue.get(block=True)
        if image_to_save is None:  # No more images
            break

        frame_id = str(image_to_save.GetFrameID())
        filename = serial_number + '-' + frame_id
        filename += '.jpeg' if compress else '.tiff'
        filename = os.path.join(save_path, filename)
        # image_to_save.Save(filename)  # uncomment to use Spinnaker save
        Image.fromarray(image_to_save.GetNDArray()).save(filename)
        # image_to_save.GetNDArray().tofile(filename)  #  uncomment to save as raw
        print('[%s] image saved at path: %s' % (serial_number, filename))


def acquire_images(cam, image_queue):
    """
    Acquires `NUM_IMAGES` worth of images for the given `cam`.
    As each image is acquired it is put into the `image_queue`.
    """
    try:
        result = True
        cam.Init()
        device_serial_number = cam.GetUniqueID()

        # Set acquisition mode to continuous
        if cam.AcquisitionMode.GetAccessMode() != PySpin.RW:
            print('Unable to set acquisition mode to continuous. Aborting...')
            return False

        cam.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)
        print('[{}] Acquisition mode set to continuous...'.format(
            device_serial_number))

        cam.BeginAcquisition()
        print('[{}] Acquiring images...'.format(device_serial_number))

        for i in range(NUM_IMAGES):
            
            if cam.TransferQueueCurrentBlockCount() > 0:
                print(("# of images in {0}'s buffer: {1}").format(device_serial_number,cam.TransferQueueCurrentBlockCount()))
            
            try:
                image_result = cam.GetNextImage()

                if image_result.IsIncomplete():
                    print('[%s] Image incomplete with image status %d ...' % (
                        device_serial_number, image_result.GetImageStatus()))

                else:
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


def print_device_info(nodemap, cam_num):
    """
    Prints all the values from the DeviceInformation node
    of the given `nodemap`.
    """
    print('Printing device information for camera %d... \n' % cam_num)
    try:
        result = True
        node_device_information = PySpin.CCategoryPtr(
            nodemap.GetNode('DeviceInformation'))

        if PySpin.IsAvailable(node_device_information) and \
           PySpin.IsReadable(node_device_information):
            features = node_device_information.GetFeatures()
            for feature in features:
                node_feature = PySpin.CValuePtr(feature)
                print('%s: %s' % (node_feature.GetName(),
                                  node_feature.ToString() if PySpin.IsReadable(node_feature) else 'Node not readable'))
        else:
            print('Device control information not available.')
        print()

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        return False

    return result


def record_high_bandwidth_video(cam_list):
    """
    Creates and starts a recording a saving thread for each
    camera in `cam_list`. Then waits for the threads to run.

    Returns a boolean indicating whether the acquisition was successful or not.
    """
    try:
        result = True

        for i, cam in enumerate(cam_list):
            # Retrieve TL device nodemap
            nodemap_tldevice = cam.GetTLDeviceNodeMap()
            # Print device information
            result &= print_device_info(nodemap_tldevice, i)

        acquisition_threads = []
        saving_threads = []
        image_queues = []

        for i, cam in enumerate(cam_list):
            image_queues.append(queue.Queue())
            for j in range(NUM_THREADS_PER_CAM):
                saving_thread = threading.Thread(target=save_images,
                                                 args=(cam.GetUniqueID(), image_queues[-1], SAVE_DIR))
                saving_thread.start()
                saving_threads.append(saving_thread)

            acquisition_thread = threading.Thread(
                target=acquire_images, args=(cam, image_queues[-1]))
            acquisition_thread.start()
            acquisition_threads.append(acquisition_thread)

        for at in acquisition_threads:
            at.join()


        print('Finished Image Acquisition')

        # Signal processing to processing threads that acquisition is finished
        for q in image_queues:
            for j in range(NUM_THREADS_PER_CAM):
                q.put(None)
        for pt in saving_threads:
            pt.join()
        print('Finished Image Processing')

        # Release reference to camera
        # NOTE: Unlike the C++ examples, we cannot rely on pointer objects being automatically
        # cleaned up when going out of scope.
        # The usage of del is preferred to assigning the variable to None.
        del cam

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False

    return result


def write_test_file():
    """
    Creates a test.txt in the current directory then deletes it.
    Since this application saves images in the current folder
    we must ensure that we have permission to write to this folder.
    Return false if we do not have permission, else true.
    """
    try:
        test_file = open('test.txt', 'w+')
    except IOError:
        print('Unable to write to current directory. Please check permissions.')
        input('Press Enter to exit...')
        return False

    test_file.close()
    os.remove(test_file.name)
    return True


def main():
    if not write_test_file():
        return False

    result = True

    # Retrieve singleton reference to system object
    system = PySpin.System.GetInstance()

    # Get current library version
    version = system.GetLibraryVersion()
    print('Library version: %d.%d.%d.%d' %
          (version.major, version.minor, version.type, version.build))

    # Retrieve list of cameras from the system
    cam_list = system.GetCameras()
    num_cameras = cam_list.GetSize()
    print('Number of cameras detected: %d' % num_cameras)

    # Finish if there are no cameras
    if num_cameras == 0:
        # Clear camera list before releasing system
        cam_list.Clear()
        # Release system instance
        system.ReleaseInstance()
        print('Not enough cameras!')
        input('Done! Press Enter to exit...')
        return False

    # Run example on all cameras
    print('Running example for all cameras...')
    t1 = time.clock()
    result = record_high_bandwidth_video(cam_list)
    t2 = time.clock()
    print('Total runtime:', t2 - t1)
    print('Example complete... \n')

    # Clear camera list before releasing system
    cam_list.Clear()
    # Release system instance
    system.ReleaseInstance()
    input('Done! Press Enter to exit...')
    return result


if __name__ == '__main__':
    main()
