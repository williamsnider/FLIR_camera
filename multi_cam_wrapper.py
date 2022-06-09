import PySpin

# According to the API, trigger mode needs to be turned off for other parameters (like TriggerSource) to be changed. For this reason, the order of the items in this list matters, and some parameters like TriggerMode appear twice. Obviously, the last value is the one we want.
camera_params = [
    ['AcquisitionMode', PySpin.AcquisitionMode_Continuous],    
    ['DecimationHorizontal', 2], #1 is off, 2 is on
    ['DecimationVertical', 2],
    ['ExposureAuto', False],
    ['ExposureTime', 5000], #us
    ['GainAuto', False],
    ['Gain', 25],
    ['PixelFormat', PySpin.PixelFormat_BayerRG8], # Which Bayer filter the camera uses
    ['BalanceWhiteAuto', False],
    ['IspEnable', False],
    ['Width', 960],
    ['Height', 600],
    ['OffsetX', 0],
    ['OffsetY', 0],
    ['TriggerMode', False],
    ['TriggerSource', PySpin.TriggerSource_Line3],
    ['TriggerActivation', PySpin.TriggerActivation_RisingEdge],
    ['TriggerOverlap', True],
    ['TriggerDelay', 32],
    ['TriggerMode', True]
]

# Assign custom names to cameras based on their serial numbers.
camera_names = [
    ['19472072', 'cam-A'],
    ['19472089', 'cam-B']
]
 
save_location = "C:\\Users\\William\\Documents\\Data\\dan_test_3"
save_prefix = "dan"
GRAB_TIMEOUT = 100 # (ms) length of time before cam.GrabNextImage() will timeout and stop hanging
NUM_THREADS_PER_CAM = 6 # The number of saving threads per camera; each system has different best value
fps = 100 # What fps to save the video file as
save_format = PySpin.PixelFormat_RGB8 # What color format to convert from bayer; must match above
save_format_extension = ".jpg" # 
quality_level = 75 # 0 is worst; 95 is best; 100 disbles jpeg compression. Only matters if save_format_extension is jpg.
