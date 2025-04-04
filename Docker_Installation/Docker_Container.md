# How to create a Docker container for YOLOv11

## Run your Docker container:
- Recommended to make a folder for your Project (Bird_Project) in Documents, then refer below:
```bash
sudo docker run --name yolov11_birds -v /home/daniel-airou/Documents/Bird_Project/ultralytics/ultralytics:/home/Documents/Bird_Project --gpus all --shm-size 16G -it yolov11_birds:latest
```
- gpus all: enables your Docker Container the ability to access all of your GPUS
- shm-size 16G: amount of shared memory (prevents memory-related errors)
- v: mounts your container in whichever directory you are in
- it: makes it interactive
- yolov11_birds:latest is your <image_name>:<image_tag>.

- Everything inside /home/daniel-airou/Documents/Bird_Project/ultralytics/ultralytics (on your host) will be available inside the container at /home/Documents/Bird_Project
- In other words, this is where the container will grab from and allow access (otherwise you will be restricted to the folder you mounted it in). Change to the files you want it to access.


## To start your docker container in the future:

```bash
sudo docker start -ai yolov11_birds
````
- Simply change "yolov11_birds" to the name of your container, and you're ready to go!



# Great Job! Next, we move into working into Data_Annotation!
