# How to install YOLOv11 on Ubuntu 24.04 using a GPU-enabled Docker container (the easy way)
### Notes:

- We used our GeForce RTX 4070 SUPER (12 GB VRAM) and an Intel® Core™ i7-14700KF (28 threads) to train YOLO. On the CPU, training for 1000 epochs took 20 hours 36 minutes, while on the GPU it took 4 hours 4 minutes.

- Why is GPU better? Simple — it's designed to process images in parallel (it’s a graphics processing unit).

- Why 1000 epochs? We wanted to ensure full convergence of our model. Later, we added early stopping with a patience of 300 epochs to avoid overfitting.


## Step 1. Pull yolov11 from GitHub:
```bash
pip install ultralytics
```

Note: This may not work on your terminal. If this is the case, try either of these methods:

The easiest way:
- option a) make a python3 venv and use pip from there. Then, move it to whatever folder you are going to work in. You can do this either in a terminal or in VSCOde (see Docker_Installation)

- Make sure you have python3 installed, check if its already installed:
```bash
python3 --version
```
 
- If not, run (3.x being current version - its 3.12 as of now):
```bash
sudo apt-get install python3.x
```

- To make a venv, run:
```bash
python3 -m venv venv
```

- **For future activation**:
```bash
source venv/bin/activate
```

The more difficult route:
- option b) In another existing docker container you have, run it there. Then, move it to whatever folder you are going to work in.
Or you can run this command to create a temporary container:
```bash
docker run --rm -it ubuntu bash
```


## Step 2. Before proceeding, ensure you have created your Docker Container (Refer to Docker Installation)

### Make a Docker Image (Image already provided by /Ultralytics- inside of ~/Docker folder)

### Make A Docker Container (Strongly Recommend GPU-enabled)


## Step 3. Start Your Docker Container
```bash
sudo docker start -ai yolov11_birds
```
Change "yolov11_birds" to the desired name of your container.


# How to train your custom dataset

## Step 1. Organize Your Dataset
In my novice experience, 60% of images to train, 20% val, and 20% test split is the most optimal method. To understand why, you need to understand what its doing:
- Train - trains your data using your labeled data, then adjusts the weights to minimize its difference between its prediction vs ground truth (your labeled data). See Step #5 for more details.
- Val - After each epoch, YOLO evaluates its performance on the validation set. It then uses this to measure its current accuracy, precision, recall, and loss. You can adjust the hyperparameters to fine-tune these values (See Automated Hyperparameterization). See Step #6 for more details.
- Test - Once your training is complete, the best.pt can be applied to your test set. The test set contains previously-unseen data and uses it to evaluate how well the model generalizes to new images. This phase provides final accuracy metrics but does not influence the training process. See Step #7 for more details.
You can also run detect.py using your weights on any image directory and YOLO will estimate and provide how accurate it is with your custom-trained weights.

```bash
/path/to/your/folder/data
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

!!! Inside of Data, you may have to create an "images" and "labels" folder if not already existing
Inside of images AND labels, make 3 folders: train, val, test. Ensure you match frames appropriately!!!


## Step 2. (Optional) Inside of ~/data/annotator.py, you can modify these parameters:
```bash
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
)
```

- det_model will use yolo11s (or which ever .pt you want) so long as the file is inside of the data folder as well. Ultralytics provides **n**ano, **s**mall, **m**edium, **l**arge, **x**-large model weights
- device="0" ensures you use your GPU (if you have more add "0,1,2,...")
- conf=0.70 is confidence threshold, depending on your images, I recommend .7 for 70%
- iou=0.5 should be standard, unless you plan on using it for multi-object tracking.
- imgsz=640 resolution of your images, 640 is standard, but can be adjusted to the appropriate resolution (computationally expensive)
- max_det=100 is the maximum number of detected objects per epoch. We changed it to 100 to not over-annotate.


## Step 3. (Optional) Inside of ~/data/dataset.py, change it to these values:
```bash
def __init__(self, root, args, augment=True,prefix=""): # Changed from False

augment=True allows the augmentation to actually augment itself and ensure you have a fine-tuned model.
```

Resources: 
<li class="masthead__menu-item">
    <a href="https://medium.com/@estebanuri/training-yolov11-object-detector-on-a-custom-dataset-39bba09530ff">Massive help from Medium!</a>
</li>

<li class="masthead__menu-item">
    <a href="https://docs.ultralytics.com/models/yolo11/#performance-metrics">YOLOv11 Documentation</a>
</li>

## Step 4. Manually Annotate Data
Refer to instructions inside the /Data_Annotation folder. Return here for Step 5.


## Step 5. Create Your Custom .yaml
Ensure your custom .yaml file is inside of your ~/data/ follder.
Example: ~/ultralytics/ultralytics/data/bird_project.yaml

- This should be what the your structure of *words*.yaml file look like:
```bash
# Dataset configuration for YOLO with manual train/val/test splits

path: /home/Documents/Bird_Project/data # Base dataset path 

train: /home/Documents/Bird_Project/data/images/train # Path to the train images
val: /home/Documents/Bird_Project/data/images/val # Path to the validation images
test: /home/Documents/Bird_Project/data/images/test # Path to the test images

nc: 2  # Number of classes
names: ['male', 'female']  # List of class names
```


## Step 6. Train You Model!
Finally, ensure you have the yolos.pt INSIDE of the ~/data/ folder. If not, it will assume yolon.pt as mentioned earlier. Also, note that you can modify the confidence threshold (%) - in other words, it ignores detections that are below the confidence level you set.  Now, run:
```bash
yolo train model=yolo11s.pt data=/home/Documents/Bird_Project/data/birds_dataset_1.yaml epochs=1000 batch=24 device=0
```

- model = yolo11s - your version of yolo you want to train on
- data = where your *words*.yaml is located.  
- epochs = 1000 - how many training iterations you want. The training iterations directly relates to your dataset and its difficulty to train on.
- imgsz = Image resolution of each image (can be adjusted at a higher computational expense) 
- batch = 24 - number of images per epoch 
- device = 0 - your GPU


**A note before continuing: All of these can be changed by performing Step #2**


### Monitor GPU Usage
- If your training sessions demands more computaional power than capable, your computer will crash! **Lowering the batch size** (since its consuming all of your dedicated VRAM) is the best solution I have found. Avoid going higher than **XGB-4GB** (X is your total available).

- Now, depending on your GPU, it should only take 5-20 minutes to train on 1800 (out of 3000) images with 100 epochs. I recommend training on 1000 epochs, and adding an early stop at the end. Early stop (patience) acts when there is no improvement in results over the number of assigned patience.
```bash
...*words*.yaml patience=100
```

- Our training session stopped at 154 epochs - this means our model saw no improvement after 54 epochs. But with the size of our dataset, this is highly unlikely. The training session's total duration was 18 minutes (7 seconds per epoch). 

- This also ensures you have as accurate your model you can get after converging and avoids having to train for hours - but stopping too early (like this example) most likely will not converge fully. We recommend adjusting early stop (patience) to at least 500.


## Step 7. Validate your data
```bash
yolo val model=path/to/your/custom_dataset/best.pt data=/path/to/*words*.yaml split=test imgsz=640 device=0
```

A note before continuing - All of these can be changed by performing Step #2

- yolo val - tests the accuracy of your data
- model = for val, this is your custom-trained dataset (best.pt)
- data = path to your .yaml file from previous
- split = which set of images it will grab images (assuming you divided files properly as - instructed previously)
- Imgsz = Image resolution of each image (can be adjusted at a higher computational expense)
- device = 0 - which GPU its training on


## Step 8. Test your data:
Now that you're done training, you can test the accuracy of your trained model by testing on your images/test data on the previously unseen images (that were not in your images folder from earlier). You can do this by running:
```bash
yolo predict model=runs/detect/train/weights/best.pt source=/path/to/new/images device=0 save=True 
```

- model = predict - for testing your model, this is your custom-trained dataset (best.pt)
- source = path to your images /test images folder
- split = which set of images it will grab images (assuming you divided files properly as instructed previously)**
- save = saves your results (mAP, mAP-50, etc) 


This will go back and test on your /test images folder. You can also apply the trained best.pt weight to other new images for classification, although for birds, this will not be very accurate without heavy fine-tuning/re-annotating (again, see Automatation).


# You now have a fully custom-trained CNN model you can apply to any of your data! Congratulations!

### Notes for myself (Ignore):
Yolov5: When applying images all together and inserting a divide to allow for yolo to randomly grab images, the model was too precise, with no overfitting. The results were too accurate because they essentially trained all on the same data and when we would test on them, the weights new exactly what gender and where the birds were. This, of course, does not produce valid results and should be rejected. However, when we trained with the appropriate split, the accuracy went from 98% to 48%. A vastly different result, and indicates we change modify some of the values, such as the training model (engine) and attempt to find a more accurate model. As of now, we are using Adam and AdamW, however the results have not been promising. The highest results acheived have been on independent cameras with Camera 3 being the highest at 78% precison. The next action is to continue to find a higher model, as with both cameras, we have only achieved a maximum of 63% accuracy (basically guessing.) We may continue to test, but due to deadlines, we may be restricted to limiting to one camera at a time and ensuring we fine-tune to the best of our ability and use the data we attain.
- Update: after using hyperparameter automation in YOLOv11, we achieved 72% accuracy!

# References:
- Ultralytics, “YOLO11,” Ultralytics.com, 2024. Available: https://docs.ultralytics.com/models/yolo11/
