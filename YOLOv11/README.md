# How to install YOLOv11 on Ubuntu 24.04 (the easy way)

# 1. Pull yolov11 from github:

```python
pip install ultralytics
```

Note: this may not work on your terminal. You can
```
a) make a python venv and use pip from there. Then, move it to whatever folder you are going to work in. 
b) in another existing docker container, run it there. Then, move it to whatever folder you are going to work in.
```

# 2. Make a Docker Image - See Docker Image Instructions (Strongly Recommend GPU-enabled)

# 3. Make a Docker Container - See Docker Container Instructions

# 4. Start your docker container

```python
sudo docker start -ai yolov11_birds
````
Simply change "yolov11_birds" to the name of your container.

# How to train your custom dataset

# 1. Create a clear structure where you will be working in:
```
In my experience, 60% of images to train, 20% val, and 20% test split is the most optimal. To understand why, you need to understand what its doing:
Train - trains your data using your labelled data, then adjust the weights to minimize its difference between its prediction vs ground truth (your labels.)
Val - After each epoch, YOLO evaluates its performance on the validation set. It then uses this to measure its accuracy, precision, recall, and loss. You can adjust the hyperparameters to fine-tune
Test - Once your training is complete, the best.pt is applied to your test set. The test set contains unseen data to evaluate how well the model generalizes to new images. This phase provides final accuracy metrics but does not influence the training process.
You can also run detect.py using your weights on any image directory and YOLO will estimate and provide how accurate it is with your custom-trained weights.
```
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
|   |   ├── img5.txt
|   |   ├── img6.txt
```

IMPORTANT:

!!! Inside of Data, you may have to create an "Images" and "Labels" Folder
Inside of Images AND labels, make 3 folders: train, val, test. Ensure you match appropriately!!!

# 2. Inside of ~/data/annotator.py, change it to these values:

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

- det_model will use yolo11s (or which ever .pt you want) so long as the file is inside of the data folder as well. if not, it will assume yolo11n.
- device="0" ensures you use your GPU (if you have more add "0,1,2,...")
- conf=0.70 is confidence threshold, depending on your images, I recommend .7 for 70%
- iou=0.5 should be standard, unless you plan on using it for multi-object tracking.
- imgsz=640 is how many images you train, 640 is standard.
- max_det=100 is the maximum number of detected objects per epoch. We changed it to 100 to not over-annotate.
```

# 3. Inside of ~/data/dataset.py, change it to these values:
```python
def __init__(self, root, args, augment=True,prefix=""): #Changed from False

augment=True allows the augmentation to actually augment itself and ensure you have a fine-tuned model.
```

Resources: 
Massive help from: https://medium.com/@estebanuri/training-yolov11-object-detector-on-a-custom-dataset-39bba09530ff
Documentation: https://docs.ultralytics.com/models/yolo11/#performance-metrics

# 4. Ensure you have your custom .yaml file inside of ~/data/
You should create your file and put it inside of the data. 
Example is ~/data/bird_project.yaml

These will be the structure of your file:

```python
# Dataset configuration for YOLOv5 with manual train/val/test splits

path: /home/Documents/Bird_Project/data # Base dataset path 

train: /home/Documents/Bird_Project/data/images/train # Path to the train images
val: /home/Documents/Bird_Project/data/images/val # Path to the validation images
test: /home/Documents/Bird_Project/data/images/test # Path to the test images

nc: 2  # Number of classes
names: ['male', 'female']  # List of class names
```

# 5. Train!
Finally, ensure you have the yolos.pt INSIDE of the ~/data/ folder. If not, it will assume yolon.pt as mentioned earlier. Now, run:

```python
yolo detect train data= /path/to/your/bird_project.yaml # Replace bird_project with whatever you named your .yaml
```

Depending on your GPU, it should only take 5-20 minutes to train on 1800 images with 100 epochs. I recommend upgrading it to 1000 epochs, and adding:

```python
...yaml --patience 100
```

To ensure you have as accurate data as you can get without having to train for hours.

# 6. Validate your data:
Now that you're done training, validate your data by running:

```python
yolo val model=/path/to/weights/best.pt data=/path/to/data.yaml split=test
```

This will go back and test on your /test image folder. You can also apply the trained best.pt weight to other images for classification, although for birds, this will not be very accurate without heavy fine-tuning/re-annotating.
