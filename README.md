# This repository serves as a start-from-finish guide for YOLO training
For the most part, all of the work mentioned below will be in your bash terminal, but modifying any of the files inside YOLO will be in Python. 
<br>
<br>
I, Daniel Vargas, am the sole creator of this repository, so if there is anything missing or needs clarification, please feel free to reach out to me at dvargas88@ou.edu. **Please note that I am a Mechanical Engineer by training, and I had to learn about Programming, Docker, and CNNs in 3 months.** So, have mercy if there are any mistakes. Please notify me if there are issues or if I misguide a section as I always appreciate feedback and criticism. Anyways, hope this helps - good luck and happy data training!!
<br>

## If you use this repository for guidance, please cite this repo

### First, I would like to give credit to my co-researcher, Mathis Morales, for their repository that helped tremendously with the set up of the Docker Container, as well as their advice throughout the project!
```bash
https://github.com/airou-lab/Docker-GPU-Tutorial.git
```
# Recommend Order Of Completion

## Step 1. Getting_Started
- Installing_Ubuntu24.04
- Using_Ubuntu24.04
[Installing_Ubuntu24.04](#Installing_Ubuntu).
## Step 2. Docker_Installation
- Docker_Image
- Docker_Container

## Step 3. Image_Conversion (Optional)
Do this to convert your video (.mp4) to images (.PNG) to feed into CVAT for data_annotation

## Step 4. YOLOv11
- Data_Annotation
- YOLOv11_Build

## Step 5. Automation (Optional)
Do this if you want to find the optimal hyperparameters for your model.

# Done! Congratulations For Your Hard Work!


# Daniel's Project Summary
This is my repository I originally made for a research project called * *link inserted if paper is accepted* *. If the link is not inserted, this means its still under review. I am not allowed to discuss the project details as it is an anonymous submission. I have uploaded some of my experimental results, and I'm treating this repositroy as a backup for my files, but also as a free dataset for anyone who wants to work with it. If the experiment folder is also lacking data, this is due to the reason mentioned earlier. But again, if there is anything missing or needs clarification, please feel free to reach out at dvargas88@ou.edu.


# Summary Results
## For YOLOv5
- Our results of Camera 1 was 54% precison for tracking and classification and 23.4% accurate in IoU (mAP-95)
  
- Our results of Camera 3, our accuracy was 64% for tracking and classification and 27.3% accurate in IoU (mAP-95)
  
- As you may notice, these results are low. On top of this fact, these arent even our camera feed combined together yet. As of now, we believe this is due to our parameters, as well as the data input. We will feed it our full 9600 images instead of the half we have been doing up until now. We will also resort to using YOLOv11 instead as YOLOv5 is now 5 years old. 

- I will be testing on YOLOv11 soon - working on a very complicated installation. 

## Update!

- Complicated installation completed! We now have an accuracy using simultaneous tracking-and-classification of 71.4% for both camera angles! BUT, our tracking-THEN-classification acheived 87.5% accuracy! Hooray for StackExchange!
