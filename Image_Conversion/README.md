# Use frame_maker.py to convert your video into the proper .PNG format to feed into YOLO.
Go to the frame_maker.py file and modify these two lines of code below. Replace the video_file variable with the path to the first camera angle.
Next, copy the path to your frames directory in the processed_data folder and add /Camera1 to the path.

Repeat this step for the second camera angle and make sure to add /Camera2 to the path. (Below is an example)

Running the script should create the frames in the respective folder.

```bash
# Define the path to your video file
video_file = '/path/to/file/your_video.MP4'

# Create a directory to save the frames
output_directory = '/path/to/file/desired_folder'
```

# References:
- airou-lab, “GitHub - airou-lab/3D_Multi_Bird_Tracking,” GitHub, 2024. Available: https://github.com/airou-lab/3D_Multi_Bird_Tracking.git
