# Download Docker

## 1. Remove any conflicting files
Run this command to remove and conflicting files for a smooth installation:

```python
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do sudo apt-get remove $pkg; done
```

## 2. Set up Docker's apt Repository
Run this command to grab from Docker's repository and automatically downloads all of the necessary files:

```python
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

```python
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

## 4. Verify Docker was successfully installed

```python
sudo docker run hello-world
```

# How to create a Docker image for YOLOv11

## 1. Pull the latest miniconda3 image:

You can refer to /ultralytics/docker/docker for their built-in image

```python
sudo docker pull continuumio/miniconda3:latest
```

## 2. Use Ultralytics Docker Image

Simply find the folder with the Docker Image (inside of ultralytics folder) and skip to Step 4.

## 3. (Optional) Create your image:
```python
sudo docker build -t yolov11_birds:latest .
```
It follows <image_name>:<image_tag>, so the name for the image, then tag you want.

## 4. Create a name for your to-be container:

```python
sudo docker build -t yolov11_birds .
```
Change "yolov11_birds" with your own image name


# How to create a Docker container for YOLOv11

## 1. Build your Docker container:

```python
sudo docker run --name yolov11_birds -v /home/daniel-airou/Documents/Bird_Project/ultralytics/ultralytics:/home/Documents/Bird_Project --gpus all --shm-size 16G -it yolov11_birds:latest
```
Again, yolov11_birds is your container name, followed by the directory of your choice. The ":/home/..." is where the container will grab from. Change to the files you want it to access.
This is based on GPU, so it'll be on your GPU, then shm-size is how many memory you want to use. Mine is 16GB memory out of 32GB possible. Finally, yolov11_birds:latest is your <image_name>:<image_tag>.

## 2. Ensure your Docker Container

# To start your docker container in the future:

```python
sudo docker start -ai yolov11_birds
````
Simply change "yolov11_birds" to the name of your container, and you're ready to go!
# Good Luck!
