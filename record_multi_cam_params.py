import PySpin

SAVE_LOCATION = "/mnt/Data4TB"
# SAVE_LOCATION = "/home/oconnorlab/Data"
SAVE_PREFIX = ""  # String appended to beginning of each image filename. Can be left blank.
GRAB_TIMEOUT = 100  # (ms) length of time before cam.GrabNextImage() will timeout and stop hanging
NUM_THREADS_PER_CAM = 10  # The number of saving threads per camera; each system has different best value
VIDEO_FPS = 10  # What fps to save the video file as
# PIXEL_FORMAT = (
#     PySpin.PixelFormat_BayerRG8
# )  # What color format to convert from bayer; must match above
FILETYPE = ".bmp"  #
QUALITY_LEVEL = (
    75  # 0 is worst; 95 is best; 100 disbles jpeg compression. Only matters if save_format_extension is jpg.
)
MIN_BATCH_INTERVAL = 1  # (s) If time between this and previous image is more than this, a new directory is created (this separates images into directories for each new trial)


# Assign custom names to cameras based on their serial numbers. Comment out to ignore that camera.

CAMERA_NAMES_DICT_COLOR = {
    "19472072": "camTR-orig",
    # "19472089": "camBo-orig",
}  # Indicate which cameras need to be debayered


CAMERA_NAMES_DICT_MONO = {
    "23398259": "camTL-orig",
    "23398260": "camBL-orig",
    "23398261": "camBR-orig",
    "23428985": "camTo-orig",
    "24048476": "camBo-orig",
}

# According to the API, trigger mode needs to be turned off for other parameters (like TriggerSource) to be changed. For this reason, the order of the items in this list matters. After setting the parameters, TriggerMode is turned back to True.
CAMERA_PARAMS_COLOR = [
    ["AcquisitionMode", PySpin.AcquisitionMode_Continuous],
    ["DecimationHorizontal", 1],  # 1 is off, 2 is on
    ["DecimationVertical", 1],
    ["ExposureAuto", False],
    ["ExposureTime", 500],  # us
    ["GainAuto", False],
    ["PixelFormat", PySpin.PixelFormat_BayerRG8],  # Which Bayer filter the camera uses
    ["BalanceWhiteAuto", False],
    ["IspEnable", False],  # Necessary to reach max framerate at full resolution
    ["TriggerMode", False],
    ["TriggerSource", PySpin.TriggerSource_Line3],
    ["TriggerActivation", PySpin.TriggerActivation_RisingEdge],
    ["TriggerOverlap", True],
    ["TriggerDelay", 32],
]

CAMERA_PARAMS_MONO = [
    ["AcquisitionMode", PySpin.AcquisitionMode_Continuous],
    ["DecimationHorizontal", 1],  # 1 is off, 2 is on
    ["DecimationVertical", 1],
    ["ExposureAuto", False],
    ["ExposureTime", 500],  # us
    ["GainAuto", False],
    ["PixelFormat", PySpin.PixelFormat_Mono8],  # Which Bayer filter the camera uses
    ["IspEnable", False],  # Necessary to reach max framerate at full resolution
    ["TriggerMode", False],
    ["TriggerSource", PySpin.TriggerSource_Line3],
    ["TriggerActivation", PySpin.TriggerActivation_RisingEdge],
    ["TriggerOverlap", True],
    ["TriggerDelay", 32],
]


CAMERA_SPECIFIC_DICT = {
    "23428985": [
        ["Width", 960],
        ["Height", 960],
        ["OffsetX", 248],
        ["OffsetY", 100],
        ["Gain", 25],
    ],
    "19472089": [
        ["Width", 960],
        ["Height", 960],
        ["OffsetX", 472],
        ["OffsetY", 100],
        ["Gain", 25],
    ],
    "19472072": [
        ["Width", 960],
        ["Height", 960],
        ["OffsetX", 400],
        ["OffsetY", 50],
        ["Gain", 25],
    ],
    "23398259": [
        ["Width", 960],
        ["Height", 960],
        ["OffsetX", 300],
        ["OffsetY", 150],
        ["Gain", 25],
    ],
    "23398260": [
        ["Width", 960],
        ["Height", 960],
        ["OffsetX", 400],
        ["OffsetY", 200],
        ["Gain", 25],
    ],
    "23398261": [
        ["Width", 960],
        ["Height", 960],
        ["OffsetX", 548],
        ["OffsetY", 150],
        ["Gain", 25],
    ],
    "24048476": [
        ["Width", 960],
        ["Height", 960],
        ["OffsetX", 680],
        ["OffsetY", 150],
        ["Gain", 25],
    ],
}
