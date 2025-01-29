# How to install YOLOv11 (the easy way)

# 1. Make a Docker Image - See Docker Image Instructions (Strongly Recommend GPU enabled)
# 2. Make a Docker Container - See Docker Container Instructions
# 3. Create a clear structure where you will be working in:

```
home/path/your/folder/to/data
├── images/
│   ├── train/
│   │   ├── img1.png
│   │   ├── img2.png
│   └── val/
│   |   ├── img3.png
│   |   ├── img4.png
|   └── test/  
|   |   ├── img5.png
|   |   ├── img6.png
├── labels/
│   ├── train/
│   │   ├── img1.txt
│   │   ├── img2.txt
│   └── val/
│   |   ├── img3.txt
│   |   ├── img4.txt
|   └── test/  
|   |   ├── img5.png
|   |   ├── img6.png
```

IMPORTANT:

!!! Inside of Data, you may have to create an "Images" and "Labels" Folder
Inside of Images AND labels, make 3 folders: train, val, test. Ensure you match appropriately!!!

# 4. Inside of ~/data/annotator.py, change it to these values:

```python
def auto_annotate(
    data,
    det_model="yolo11s.pt",
    sam_model="sam_b.pt",
    device="0",
    conf=0.70,
    iou=0.5,
    imgsz=640,
    max_det=100,
    classes=None,
    output_dir=None,
):
```
```
- det_model will use yolo11s (or which ever .pt you want) so long as the file is inside of the data folder as well. if not, it will assume yolo11n.
- device="0" ensures you use your GPU (if you have more add "0,1,2,...")
- conf is confidence threshold, depending on your images, I recommend .7 for 70%
- iou should be standard at .5, unless you plan on using it for multi-object tracking.
- imgz is how many images you train, 640 is standard.
- max_det is the maximum number of detected objects per epoch. We changed it to 100 to not over-annotate.
```

Resources: 
Massive help from: https://medium.com/@estebanuri/training-yolov11-object-detector-on-a-custom-dataset-39bba09530ff
Documentation: https://docs.ultralytics.com/models/yolo11/#performance-metrics
