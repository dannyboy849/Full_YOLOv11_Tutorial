# How to create a Docker container for YOLOv11

## Step 1. Run your Docker container:
- Recommended to make a folder for your Project (Bird_Project) in Documents, then refer below:
```python
sudo docker run --name yolov11_birds -v /home/daniel-airou/Documents/Bird_Project/ultralytics/ultralytics:/home/Documents/Bird_Project --gpus all --shm-size 16G -it yolov11_birds:latest
```
- gpus all: enables your Docker Container the ability to access all of your GPUS
- shm-size 16G: amount of shared memory (prevents memory-related errors)
- v: mounts your container in whichever directory you are in
- it: makes it interactive
- yolov11_birds:latest is your <image_name>:<image_tag>.

- Again, yolov11_birds is your container name, followed by the directory of your choice.
- Everything inside /home/daniel-airou/Documents/Bird_Project/ultralytics/ultralytics (on your host) will be available inside the container at /home/Documents/Bird_Project
- In other words, this is where the container will grab from and allow access (otherwise you will be restricted to the folder you mounted it in). Change to the files you want it to access.


## Step 2. Ensure your Docker Container

# To start your docker container in the future:

```python
sudo docker start -ai yolov11_birds
````
Simply change "yolov11_birds" to the name of your container, and you're ready to go!
# Good Luck! Next, we move into working with YOLO!
