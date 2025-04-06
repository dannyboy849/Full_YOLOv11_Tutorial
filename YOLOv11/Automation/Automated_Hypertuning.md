# Automating your hyper parameters

This process is very simple, its merely a matter of ensuring your data is organized and well-structured.
I will list the step by instructions, but please note you will need to have at least one training results of your own 
tuned parameters in order for the automated system to find a beginning ground. 


## Step 1. Download the auto_run_experiments.py file
This file, of course, has everything you need to hypertune your model. You can manually adjust the testing values to your hearts desire. You can also rename the .py file to whatever you wish, just ensure you remember it!


## Step 2. Ensure Your Docker Container Was Created
In order to proceed any further, you need to have your container up and ready to run. Personally, I mounted my data on its own seperate folder that had been copied from the original folder and made its own new docker container (GPU-enabled) to ensure if there was any risk of corruption, it would only affect that folder/container.


## Step 3. Make a venv
In bash, I had many issues with "import pandas as pd" as it relied on python, yet I could only use python3 and no longer use pip3. This is likely due to my inexperience, as I'm a Mechanical Engineer with little experience in programming, so please forgive my novice formatting. So, I created a venv to bypass this issue. The following will guide you
through the simple set-up:
```bash
python3 -m venv .venv (build new venv)
source .venv/bin/activate (start venv)
```


## Step 4. Important Dependencies
Now that your venv is set up, lets ensure you have all of your required files downloaded too.
```bash
# Installing Dependencies

sudo apt-get install python3-pip
pip install pandas
pip install 
```


## Step 5. Start up the automation!
Now that you have 
```bash
1. Your data well structured
2. Your docker container(w/ GPU-enabled)
3. At least one custom-trained dataset with random parameters
4. Hyperparameter ranges set up to your desired range
5. Your venv set up
```

We can move onto starting up the automation sequence!

Run this command:
```bash
python3 auto_run_experiments.py
```

That's it! Now you wait for the automation process to complete. 
# **Important Note** The automation process is set automatically to 10 iterations - to adjust this, simply go into the python file and change "" to your desired amount of iterations.
