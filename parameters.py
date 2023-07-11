import PySpin

 
SAVE_LOCATION = "/home/oconnorlab/Data/cameras/test_acquisitions"
SAVE_PREFIX = ""
GRAB_TIMEOUT = 100 # (ms) length of time before cam.GrabNextImage() will timeout and stop hanging
NUM_THREADS_PER_CAM = 6 # The number of saving threads per camera; each system has different best value
VIDEO_FPS = 10 # What fps to save the video file as
PIXEL_FORMAT = PySpin.PixelFormat_Mono8 # What color format to convert from bayer; must match above
FILETYPE = ".tiff" # 
QUALITY_LEVEL = 75 # 0 is worst; 95 is best; 100 disbles jpeg compression. Only matters if save_format_extension is jpg.
MIN_BATCH_INTERVAL = 3  # (s) If time between this and previous image is more than this, a new directory is created (this separates images into directories for each new trial)


# Assign custom names to cameras based on their serial numbers. Comment out to ignore that camera.
CAMERA_NAMES_DICT = {
    '19472072': 'cam-A',
    '19472089': 'cam-B'
}

# According to the API, trigger mode needs to be turned off for other parameters (like TriggerSource) to be changed. For this reason, the order of the items in this list matters, and some parameters like TriggerMode appear twice. Obviously, the last value is the one we want.
CAMERA_PARAMS = [
    ['AcquisitionMode', PySpin.AcquisitionMode_Continuous],    
    ['DecimationHorizontal', 1], #1 is off, 2 is on
    ['DecimationVertical', 1],
    ['ExposureAuto', False],
    ['ExposureTime', 250], #us
    ['GainAuto', False],
    ['Gain', 1],
    ['PixelFormat', PIXEL_FORMAT], # Which Bayer filter the camera uses
    ['Width', 1920],
    ['Height', 1200],
    ['OffsetX', 0],
    ['OffsetY', 0],
    ['TriggerMode', False],
    ['TriggerSource', PySpin.TriggerSource_Line3],
    ['TriggerActivation', PySpin.TriggerActivation_RisingEdge],
    ['TriggerOverlap', True],
    ['TriggerDelay', 32],
    ['TriggerMode', True]
]



