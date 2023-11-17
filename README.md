# FLIR_camera

Code to save images from multiple hardware-triggered FLIR Blackfly S cameras.

## Description

The `record_multiple_cameras.py` script interfaces with connected FLIR Blackfly cameras. It creates an aquisition thread for each camera, which grabs images from the cameras buffer. It creates several saving threads for each camera, which saves the images at a rate faster than they are acquired. In our experimental setup, this script is able to save images generated from multiple cameras at maximum resolution and framerate (~360MB/s per camera).

## How to use

First, update parameters.py to indicate the correct serial numbers of your cameras. Additionally, change the camera parameters (exposure, gain, etc) according to the setup.

#### Installation Instructions for Ubuntu 20.04

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

#### Misc

Needed to downgrade one package due to conda issue (https://github.com/conda/conda/issues/12287)

```
conda install libffi==3.3
```

#### Running the script

```
conda activate flir_venv
python record_multiple_cameras.py
```

The script should save any images that are acquired. Images are grouped into timestamped directories based on MIN_BATCH_INTERVAL.

### Useful snippets

#### Convert files to png

`for i in *.tiff; do ffmpeg -i "$i" "${i%.*}.png"; done`

#### Convert to mkv

`ffmpeg -framerate 10 -pattern_type glob -i "*.png" -c:v copy output.mkv`

#### Convert to mp4 (compressed)

`ffmpeg -framerate 20 -pattern_type glob -i "*.bmp" -vf format=yuv420p compressed_20fps.mp4`

#### Convert to mp4 (lossless)

`ffmpeg -framerate 10 -pattern_type glob -i "*.bmp" -vf format=yuv420p -crf 0 output.mp4`
