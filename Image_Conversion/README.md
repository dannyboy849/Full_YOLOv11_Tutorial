# Convert your video into the proper .PNG format
- Refer to my "frame_maker.py" file and modify these two lines of code below.
- Copy the path to your frames directory (your /video_frames folder) and add your camera videos (/camera_angle_1.mp4) to the path.
- Running the script should create the frames in the respective folder.
```bash
# Define the path to your video file
video_file = '~/NAME_Project/yolov11/data/videos/camera_angle_1.mp4'

# Create a directory to save the frames
output_directory = '~/NAME_Project/yolov11/data/video_frames/camera_angle_1'
```

- Repeat this step for every other camera angle and make replace the video (ie, /camera_angle_2) with the new path. Example:
```bash
# Define the path to your video file
video_file = '~/NAME_Project/yolov11/data/videos/camera_angle_2.mp4'

# Create a directory to save the frames
output_directory = '~/NAME_Project/yolov11/data/video_frames/camera_angle_1'
```

# References:
- airou-lab, “GitHub - airou-lab/3D_Multi_Bird_Tracking,” GitHub, 2024. Available: https://github.com/airou-lab/3D_Multi_Bird_Tracking.git
