# Setting up CVAT 
CVAT - created by Intel - is very simple and intuitive to use. However, you will need to install and use Google Chrome for this as it is not supported by any other browser as of now. . According to CVAT, this is because it was only tested and designed for use on Chrome.
<br>

- I want to make a note that you can also use Roboflow as a data annotation software, but I did not use it, thereby I am not familiar with its setup. I do know its better for automating some parts of the annotation, but again, I did not use it. Feel free to check it out though!

<li class="masthead__menu-item">
    <a href="https://roboflow.com/">Roboflow</a>
</li>

## Step 1. Load into Google Chrome
- As mentioned in the beginning, Google Chrome is the only browser that CVAT works on as of now. Hope your CPU is ready!

<li class="masthead__menu-item">
    <a href="https://roboflow.com/">Google Chrome</a>
</li>

## Step 2. Create a CVAT acount
You'll have to copy and paste the link into Chrome - Or use this guide on Chrome!
<li class="masthead__menu-item">
    <a href="https://app.cvat.ai/auth/login">Quickjump to CVAT!</a>
</li>

<br>
- Below is the login screen you should now see:
<img src="https://github.com/dannyboy849/Full_YOLOv11_Tutorial/blob/main/Image_References/CVAT_Login.png">

- Create an account in CVAT. I recommend personal accounts, but I'm unsure if this affects organizations and potential for inviting other users. 


## Step 3. Create a Project - Starting from Homepage
- You're now in the homepage! 
- Select “Create Project” 
<img src="https://github.com/dannyboy849/Full_YOLOv11_Tutorial/blob/main/Image_References/creating_a_project_homepage.png">


## Step 4. Project Details
- Fill in your desired project details - you can put whatever you want here, from vague to highly-detailed.
- Select "Submit and Continue". Otherwise, you'll be taken back to the homepage
<img src="https://github.com/dannyboy849/Full_YOLOv11_Tutorial/blob/main/Image_References/create_new_project.png">


## Step 5. Create Task
- Now, select "Create a new task"
<img src="https://github.com/dannyboy849/Full_YOLOv11_Tutorial/blob/main/Image_References/prior_to_task.png">

- Here, you'll upload your raw images - that is, all of the images you want to annotate.

- By default, CVAT reduces your image quality to save space. However, pending on your project detail, you can adjust this back to 100%. You can also select starting frame, and if you wish to stop on some specific frame.

- Frame step is how many frames it will "grab". Depending on your camera FPS (ours is 60FPS) you can adjust this to something like "$`60/15 = 4FPS`$" The higher the FPS does not necessariliy mean the higher the accuracy, unless high speeds are involved. 
<img src="https://github.com/dannyboy849/Full_YOLOv11_Tutorial/blob/main/Image_References/creating_a_task.png">


## Step 6. My projects
<img src="https://github.com/dannyboy849/Full_YOLOv11_Tutorial/blob/main/Image_References/prior_to_task.png">

## Step 7. Assign Task
- Assign the task to someone (yourself)
<img src="https://github.com/dannyboy849/Full_YOLOv11_Tutorial/blob/main/Image_References/Assigning%20_and_opening_annotation.png">


## Step 8. Select your label
Choose the label you want and 2 point box - the dropdown selection allows you to jump.
<img src="https://github.com/dannyboy849/Full_YOLOv11_Tutorial/blob/main/Image_References/Selecting_Labels.png">
**You can press "N" to reuse a label, but you will have to refer to the dropdown selection to switch labels each time**


## Step 9. Manually Annotate
- Now, you’ll go through your entire dataset and manually annotate (you only have to annotate once, but the more annotated data you have, the more accurate your model will be)
<img src="https://github.com/dannyboy849/Full_YOLOv11_Tutorial/blob/main/Image_References/Annotation_Process.png">

- This is by far the most time-consuming step. Be patient and remember to save consistently!
**WARNING: Do NOT use the automation tool provided by CVAT, as it frequently freezes and crashes. This makes is vitally important you save very often.**


## Step 10. Export your annotations!
Finally, export your data!
<img src="https://github.com/dannyboy849/Full_YOLOv11_Tutorial/blob/main/Image_References/export_selection.png">

- Now, export your data as YOLO1.1 (or as you need pending your CNN) - you can find it at the very bottom of the options. Note that there is an option to save images, but this saves the original images, not the annotated ones. 
<img src="https://github.com/dannyboy849/Full_YOLOv11_Tutorial/blob/main/Image_References/export_as_yolo1.1.png">

- Refer to "Requests" tab at the top:
<img src="https://github.com/dannyboy849/Full_YOLOv11_Tutorial/blob/main/Image_References/requests_exports.png">

## Step 11.
- CVAT will export your annotations as a .zip file. Unzip it, and you should be provided .txt files
- The directory should be something like "Documents/job_JOB#_annotations_DATE_yolo 1.1/obj_train_data/ALL_YOUR_.txt" as shown below:
<img src="https://github.com/dannyboy849/Full_YOLOv11_Tutorial/blob/main/Image_References/files_unzipped.png">
- Feed this annotations into your YOLOv11 /data/labels folder:
<img src="https://github.com/dannyboy849/Full_YOLOv11_Tutorial/blob/main/Image_References/upload_.txt.png">

# Data annotation is done! Now, onto working in YOLOv11! How exciting.

# References:
- Google, “Google Chrome - The Fast, Simple and Secure Browser from Google,” Google.com. Available: https://www.google.com/chrome/

- “Computer Vision Annotation Tool,” Cvat.ai, 2025. Available: https://app.cvat.ai/auth/login
