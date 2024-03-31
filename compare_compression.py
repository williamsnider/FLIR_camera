# Compare compression using different cq values
from pathlib import Path
import subprocess

IMG_DIR = Path("/home/oconnorlab/Desktop/2024-03-06_15-28-53_662725")
preset_list = ["slow", "hp", "hq", "ll", "default"]
cq_range = [x for x in range(16, 50, 2)]

# FFMPEG command
filesize_dict = {}
for preset in preset_list[::-1]:
    filesize_dict[preset] = []
    for cq in cq_range:

        cam = "camTo-orig"

        input_name = Path(IMG_DIR, cam + ".mp4")
        output_name = Path(IMG_DIR, cam[:5] + "_" + preset + "_output_" + str(cq) + ".mp4")
        output_name.parent.mkdir(parents=True, exist_ok=True)

        # cmd_string = f"ffmpeg -y -hwaccel cuda -framerate 100.0 -pattern_type glob -i '{IMG_DIR}/*.bmp' -c:v h264_nvenc -cq {cq} {output_name}"
        cmd_string = f"nice -n -19 ffmpeg -y -hwaccel cuda -i {input_name} -c:v h264_nvenc -cq {cq} -preset {preset} {output_name}"
        subprocess.run(
            cmd_string,
            shell=True,
            cwd=IMG_DIR,
        )

        filesize_dict[preset].append([cq, output_name.stat().st_size / 1e6])


# Plot results
import matplotlib.pyplot as plt
import numpy as np

for preset in preset_list:
    if preset == "lossless":
        continue
    data = np.array(filesize_dict[preset])
    plt.plot(data[:, 0], data[:, 1], label=preset)
plt.xlabel("Constant Quality (cq)")
plt.ylabel("Filesize (MB)")
plt.title("Filesize vs. CQ for GPU Accelerated H.264 Encoding")
plt.legend()
plt.show()
