import PySpin

if __name__ == "__main__":
    
    # Find cameras
    system = PySpin.System.GetInstance()
    cam_list = system.GetCameras()

    # Acquire images
    cam = cam_list[0]
    cam.Init()
    cam.BeginAcquisition()
    image_result = cam.GetNextImage(1000)

    print(image_result.GetNDArray().max())