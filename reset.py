import PySpin

def reset_camera(cam):
    cam.Init()
    cam.UserSetSelector.SetValue(PySpin.UserSetSelector_Default)
    cam.UserSetLoad.Execute()
    cam.DeInit()

def main():
    # Initialize the system
    system = PySpin.System.GetInstance()
    cam_list = system.GetCameras()
    
    for i in range(cam_list.GetSize()):
        try:
            cam = cam_list.GetByIndex(i)
            reset_camera(cam)
            print(f"Camera at index {i} has been reset.")
        except PySpin.SpinnakerException as e:
            print(f"Failed to reset camera at index {i}. Error: {e}")
    
    cam_list.Clear()
    system.ReleaseInstance()

if __name__ == "__main__":
    main()