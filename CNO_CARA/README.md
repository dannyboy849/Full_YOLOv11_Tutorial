# CARA
This will serve as a repo for the Comprehensive AI Risk Assessment (CARA) project. 

-Software:
The software is Ubuntu 24.04. 

-Hardware:
Tests were conducted on an Intel i7-14700KF x 28, NVIDIA GeForce RTX 4070 SUPER, and 32GB RAM. 

-Simulations: 
Simulations are ran on ROS2 Jazzy Jalisco with Gazebo Harmonic + PX4 Autopilot. 

**You will need to manually change the data header names**

# Installation
The following is formatted to be streamlined from start to finish for quick and easy data analysis. You can also [refer to the documentation within the project](https://github.com/dannyboy849/CARA/tree/main/docs) for details.


## 1. Update Your System
Before starting, ensure you have the most up-to-date releases.
```bash
sudo apt update && sudo apt upgrade
```


## 2. Clone the Repo
Clone this repo into your desired folder.

```bash
git clone https://github.com/dannyboy849/CARA.git
```


## 3. Create a venv (Optional)
Recommended for a new workspace. Create a virtual environment to install pip packages.
```bash
python3 -m venv venv  # change second venv to the desired name
```

Then, install the required packages.
```bash
pip install requirements.txt
```

### Install Conda (Optional)
You can also install Conda if you prefer. [Visit Conda for installation guidance](https://docs.conda.io/projects/conda/en/latest/user-guide/install/linux.html). Then you can run conda create to create your environment instead.
```bash
conda create --name <env> --file <this file>
```


## 4. Upload Your Data
You can test on the provided data or you can upload your data into the appropriate sections. [Check out here where and how to replace and format](https://github.com/dannyboy849/CARA/tree/main/data/processed).


## 5. Run script
After you have uploaded your data (if you chose to do so), run the following and the pipeline will be completed.
```bash
python3 DATUM.py
```
