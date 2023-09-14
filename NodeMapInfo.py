import PySpin

# Defines max number of characters that will be used
MAX_CHARS = 35

class ReadType:
    VALUE = 0,
    INDIVIDUAL = 1

CHOSEN_READ = ReadType.INDIVIDUAL

def retrieve_values(node, level, camera_dict):
    try:
        result = True

        if node.GetPrincipalInterfaceType() == PySpin.intfIString:
            node_string = PySpin.CStringPtr(node)
            display_name = node_string.GetDisplayName()
            value = node_string.GetValue()
            camera_dict[display_name] = value[:MAX_CHARS] if len(value) > MAX_CHARS else value
        elif node.GetPrincipalInterfaceType() == PySpin.intfIInteger:
            node_integer = PySpin.CIntegerPtr(node)
            display_name = node_integer.GetDisplayName()
            value = node_integer.GetValue()
            camera_dict[display_name] = value
        elif node.GetPrincipalInterfaceType() == PySpin.intfIFloat:
            node_float = PySpin.CFloatPtr(node)
            display_name = node_float.GetDisplayName()
            value = node_float.GetValue()
            camera_dict[display_name] = value
        elif node.GetPrincipalInterfaceType() == PySpin.intfIBoolean:
            node_boolean = PySpin.CBooleanPtr(node)
            display_name = node_boolean.GetDisplayName()
            value = node_boolean.GetValue()
            camera_dict[display_name] = value
        elif node.GetPrincipalInterfaceType() == PySpin.intfICommand:
            node_command = PySpin.CCommandPtr(node)
            display_name = node_command.GetDisplayName()
            tooltip = node_command.GetToolTip()
            camera_dict[display_name] = tooltip[:MAX_CHARS] if len(tooltip) > MAX_CHARS else tooltip
        elif node.GetPrincipalInterfaceType() == PySpin.intfIEnumeration:
            node_enumeration = PySpin.CEnumerationPtr(node)
            node_enum_entry = PySpin.CEnumEntryPtr(node_enumeration.GetCurrentEntry())
            display_name = node_enumeration.GetDisplayName()
            entry_symbolic = node_enum_entry.GetSymbolic()
            camera_dict[display_name] = entry_symbolic

    except PySpin.SpinnakerException as ex:
        print("Error: {}".format(ex))
        return False

    return result

def retrieve_category_node_and_all_features(node, level, camera_dict):
    try:
        result = True
        node_category = PySpin.CCategoryPtr(node)

        for node_feature in node_category.GetFeatures():
            if not PySpin.IsAvailable(node_feature) or not PySpin.IsReadable(node_feature):
                continue
            if node_feature.GetPrincipalInterfaceType() == PySpin.intfICategory:
                result &= retrieve_category_node_and_all_features(node_feature, level + 1, camera_dict)
            elif CHOSEN_READ == ReadType.VALUE:
                result &= retrieve_values(node_feature, level + 1, camera_dict)
            elif CHOSEN_READ == ReadType.INDIVIDUAL:
                result &= retrieve_values(node_feature, level + 1, camera_dict)

    except PySpin.SpinnakerException as ex:
        print("Error: {}".format(ex))
        return False

    return result

def run_single_camera(cam, camera_dict):
    try:
        result = True
        level = 0
        nodemap_gentl = cam.GetTLDeviceNodeMap()
        result &= retrieve_category_node_and_all_features(nodemap_gentl.GetNode('Root'), level, camera_dict)

        nodemap_tlstream = cam.GetTLStreamNodeMap()
        result &= retrieve_category_node_and_all_features(nodemap_tlstream.GetNode('Root'), level, camera_dict)

        cam.Init()
        nodemap_applayer = cam.GetNodeMap()
        result &= retrieve_category_node_and_all_features(nodemap_applayer.GetNode('Root'), level, camera_dict)
        cam.DeInit()

    except PySpin.SpinnakerException as ex:
        print("Error {}".format(ex))
        return False

    return True

def main():
    system = PySpin.System.GetInstance()
    cam_list = system.GetCameras()
    num_cameras = cam_list.GetSize()
    print("Number of cameras detected: %d" % num_cameras)
    if num_cameras == 0:
        cam_list.Clear()
        system.ReleaseInstance()
        print("Not enough cameras!")
        input("Done! Press Enter to exit...")
        return False

    # Dictionary to store camera data
    all_cameras_dict = {}

    for i in range(num_cameras):
        cam = cam_list.GetByIndex(i)
        camera_dict = {}
        print("Running example for camera %d..." % i)
        result = run_single_camera(cam, camera_dict)
        all_cameras_dict[f'Camera {i}'] = camera_dict
        print("Camera %d example complete..." % i)
        del cam

    cam_list.Clear()
    system.ReleaseInstance()

    # Print the collected data if they differ between cameras
    cam_names = list(all_cameras_dict.keys())
    attributes = all_cameras_dict[cam_names[0]].keys()
    for attribute in attributes:

        # Get the first camera's value for this attribute
        first_camera_value = all_cameras_dict["Camera 0"][attribute]

        # Check if the other cameras have the same value
        same_value = True
        for cam_name in cam_names[1:]:
            camera_dict = all_cameras_dict[cam_name]
            if camera_dict[attribute] != first_camera_value:
                same_value = False
                break

        # If the values differ, print the attribute and the values for each camera
        if not same_value:
            print(f"\n{attribute}:")
            for camera_name, camera_dict in all_cameras_dict.items():
                print(f"  {camera_name}: {camera_dict[attribute]}")

    for k,v in all_cameras_dict[cam_names[0]].items():
        print(k, v)
    # for camera_name, attributes in all_cameras_dict.items():

    #     print(f"\n{camera_name} Attributes:")
    #     for key, value in attributes.items():
    #         print(f"  {key}: {value}")

    input("Done! Press Enter to exit...")
    return result

if __name__ == "__main__":
    main()
