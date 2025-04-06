# Setting up CVAT 
CVAT is very simple and intuitive to use. However, you will need to install and use Google Chrome for this as it is not supported by Firefox. 

-I do want to make a note that you can also use roboflow as a data annotation software, but I did not use it, thereby I am not familiar with its setup. I do know its better for automating some parts of the annotation, but again, I did not use it. Feel free to check it out though!

<li class="masthead__menu-item">
    <a href="https://roboflow.com/">Research</a>
</li>

- https://roboflow.com/

## Step 1. Create a CVAT acount
- Create an account in CVAT. I recommend personal accounts, but I'm unsure if this affects organizations and potential for inviting other users. 


## Step 2. Create a Project
- Select “Create Project” 


## Step 3. Create Task
- Make a Task


## Step 4. Assign Task
- Assign the task to someone (yourself) 


## Step 5. Upload Raw Images
- Upload your dataset (raw images) and create your labels (We used .PNG images)


## Step 6. Manually Annotate
- Now, you’ll simply go through your entire dataset and manually annotate (you only have to do this once, but the more annotated data you have, the more accurate your model will be)
- This is by far the most time-consuming step. Be patient and remember to save consistently!


## Step 7. Export your annotations!
Finally, to export your data will depend on which software you wish you use: (in our case, YOLO uses .txt, so we used the YOLO 1.1 option at the very bottom) 


# Data annotation is done! Onto working in YOLOv11!


# References:
- Google, “Google Chrome - The Fast, Simple and Secure Browser from Google,” Google.com. Available: https://www.google.com/chrome/

- “Computer Vision Annotation Tool,” Cvat.ai, 2025. Available: https://app.cvat.ai/auth/login
