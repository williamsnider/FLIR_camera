# FLIR_multi_cam

Code to save images from multiple hardware-triggered FLIR Blackfly S cameras.

Recording grasps at 100Hz from 6 hardware-triggered cameras.

https://github.com/williamsnider/FLIR_multi_cam/assets/38354953/4e635d91-89a6-4f74-adad-b43fa7ced762


## Description

The `record_multi_cam.py` script interfaces with connected FLIR Blackfly cameras. First, it detects and connects to all FLIR cameras, initializing each to the parameters set in `record_mutli_cam_params.py`. Second, for each camera, an acquisition thread is created, which grabs frames from the camera buffer and stores them in an image queue (RAM). Third, the script uses multiple saving threads per camera, which pull images from the image queues and writes them to disk. Using this multithreaded approach, high speed video from multiple cameras can be acquired.

## How to use

- First, update `record_multi_cam_params.py` to indicate the correct serial numbers of your cameras.
- Next, change the camera parameters (exposure, gain, etc) according to the setup.
- Finally, running `record_multi_cam` will connect to the cameras and begin acquiring frames after hardware triggering.
- To stop, use `ctrl+c` which will gracefully release the cameras.

## Installation Instructions (Ubuntu 20.04)

Set up conda environment with python 3.8

```
conda create --name flir_venv python=3.8
conda install -c conda-forge opencv
```

#### Install Spinnaker SDK

https://www.flir.com/support-center/iis/machine-vision/downloads/spinnaker-sdk-download/spinnaker-sdk--download-files/

Download spinnaker-3.1.0.79-amd64-pkg.tar.gz

Extract and follow readme instructions:

```
sudo apt install libusb-1.0-0 libavcodec58 libavformat58 libswscale5 libswresample3 libavutil56 qt5-default
cd ~/Downloads/spinnaker-3.1.0.79-amd64/  # where the tar file was extracted
sudo sh install_spinnaker.sh
```

Follow the prompts. Be sure to allow 1000MB of buffer.

Reboot the system.

#### Install spinnaker_python

(same link as above)

Download spinnaker_python-3.1.0.79-cp38-cp38-linux_x86_64.tar.gz

Extract and follow readme instructions:

```
conda activate flir_venv
conda install numpy matplotlib
pip install spinnaker_python-3.1.0.79-cp38-cp38-linux_x86_64.whl
```

#### Misc Notes

Needed to downgrade one package due to conda issue (https://github.com/conda/conda/issues/12287)

```
conda install libffi==3.3
```

## Useful ffmpeg snippets

#### Convert files to png

`for i in *.tiff; do ffmpeg -i "$i" "${i%.*}.png"; done`

#### Convert to mkv

`ffmpeg -framerate 10 -pattern_type glob -i "*.png" -c:v copy output.mkv`

#### Convert to mp4 (compressed)

`ffmpeg -framerate 100 -pattern_type glob -i "*.tiff" -vf format=yuv420p compressed_100fps.mp4`

#### Convert to mp4 (lossless)

`ffmpeg -framerate 10 -pattern_type glob -i "*.tiff" -vf format=yuv420p -crf 0 output.mp4`
