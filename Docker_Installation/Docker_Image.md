# Download Docker

## 1. Remove any conflicting files
Run this command to remove and conflicting files for a smooth installation:
```bash
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do sudo apt-get remove $pkg; done
```


## 2. Set up Docker's apt Repository
Run this command to grab from Docker's repository and automatically downloads all of the necessary files:
```bash
# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
```


## 3. Install Latest Docker Packages
```bash
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```


## 4. Verify Docker was successfully installed
```bash
sudo docker run hello-world
```

You'll get a friendly response from our buddy Docker:
```bash
dannyboy@dannys-labtop:~$ sudo docker run hello-world
[sudo] password for dannyboy: enter_your_password_dummy

Hello from Docker!
This message shows that your installation appears to be working correctly.

To generate this message, Docker took the following steps:
 1. The Docker client contacted the Docker daemon.
 2. The Docker daemon pulled the "hello-world" image from the Docker Hub.
    (amd64)
 3. The Docker daemon created a new container from that image which runs the
    executable that produces the output you are currently reading.
 4. The Docker daemon streamed that output to the Docker client, which sent it
    to your terminal.
```
Our crusader lives! Now onwards.

# How to create a Docker image for YOLOv11

## Step 1. Pull The Latest Miniconda3 Image:
You can refer to /ultralytics/docker/docker for their built-in image. If not, refer to the folder containing this document and download the Docker file there. 

```bash
sudo docker pull continuumio/miniconda3:latest
```


## Step 2. Use Ultralytics Docker Image
Simply find the folder with the Docker Image (inside of ~/ultralytics folder)


## Step 3. Create A Name For Your To-Be Container:
```bash
sudo docker build -t NAME_Project .
```
- Change "NAME_Project" with your own image name.
- This may take a few minutes, so be patient!
- **To leave the container, type "exit" or "ctrl+d"**


## Step 4. Download NVIDIA-ToolKit
```bash
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

- You can test that Docker has GPU access by running:
```bash
sudo docker run --gpus all nvidia/cuda:12.0-base nvidia-smi
```
Continue to Step 5 if you encounter an error with finding the image!
### Note: this is my specific version of CUDA, the one your project requires may be different (ie, cuda:11.0). This site may be useful for you: https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/index.html

## Step 5. Error with cuda
You may get an error stating that it cannot find cuda. 
```bash
dannyboy@dannys-labtop:~/NAME_Project/Mytest/yolov5$ sudo docker run --gpus all nvidia/cuda:12.0-base nvidia-smi
> Unable to find image 'nvidia/cuda:12.0-base' locally
```

This is an issue as you might guess, but fear thou not! We have a solution! 
```bash
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
sudo apt install ./cuda-keyring_1.1-1_all.deb
sudo apt update
sudo apt install cuda-toolkit
```

This might take a while to download everything so be patient. After it downloads, check your cuda version to ensure it downloaded properly:
```bash
nvcc --version
```

You will get something like this: 
```bash
dannyboy@dannys-labtop:~$ nvcc --version
nvcc: NVIDIA (R) Cuda compiler driver
Copyright (c) 2005-2023 NVIDIA Corporation
Built on Fri_Jan__6_16:45:21_PST_2023
Cuda compilation tools, release 12.0, V12.0.140
Build cuda_12.0.r12.0/compiler.32267302_0
```

# Good work! Next, we move onto the Docker Container!

# References:
- Ultralytics, “YOLO11,” Ultralytics.com, 2024. Available: https://docs.ultralytics.com/models/yolo11/
