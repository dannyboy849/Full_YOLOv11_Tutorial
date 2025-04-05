# This will serves as a start-from-finish guide for YOLO training
For the most part, all of the work mentioned below will be in your bash terminal, but modifying any of the files inside YOLO will be in Python. I, Daniel Vargas, am the sole creator of this repository, so if there is anything missing or needs clarification, please feel free to reach out to me at dvargas88@ou.edu. Please note that I am a Mechanical Engineer by training, and I had to learn about Programming, Docker, and CNNs, in 3 months, so have mercy if there are any mistakes. Please notify me if there are or if I misguide any section, I always appreciate feedback and critism. Anyways, hope this helps and happy data training!!
<br>

### If you use this repository for guidance, please cite this repo. Good Luck!

### First, I would like to give credit to my co-researcher, Mathis Morales, for their repository that helped tremendously with the set up of the Docker Container, as well as the guidance throughout the project!
```bash
https://github.com/airou-lab/Docker-GPU-Tutorial.git
```
## Below is the recommend order of completion

## Step 1. Getting_Started
- Installing_Ubuntu24.04
- Using_Ubuntu24.04

## Step 2. Docker_Installation
- Docker_Image
- Docker_Container

## Step 3. Image_Conversion (Optional)
Do this if your images are in video format.

## Step 4. YOLOv11
- Data_Annotation
- YOLOv11_Build

## Step 5. Automation (Optional)
Do this if you want to find the optimal hyperparameters for your model.

# Done! Congratulations, and good luck!


# Bird_Project_Daniel Summary
This is also my repository I originally made for a research project called *link inserted if paper is accepted*. I have uploaded some of my experimental results. I will mainly use this as a backup for my files, but also as a free dataset for anyone who wants to work with it. Again, if there is anything missing or needs clarification, please feel free to reach out to me at dvargas88@ou.edu.


# Summary Results
For YOLOv5, our results of Camera 1 was 54% precison and 23.4% accurate in IoU (mAP-95)

For the results of Camera 3, our accuracy was 64% and 27.3% accurate in IoU (mAP-95)

I will be testing on YOLOv11 soon - working on complicated installation. 

- Complicated installation completed! We now have an accuracy using simultaneous tracking-and-classification of 71.4% for both camera angles! BUT, our tracking-THEN-classification acheived 87.5% accuracy! Hooray for StackExchange!
