# How to create a Docker container for YOLOv11

## Run your Docker container:
- Recommended to make a folder for your Project (NAME_Project) in Documents, then refer below:
```bash
sudo docker run --name NAME_Project -v /home/dannyboy/Documents/NAME_Project/ultralytics/ultralytics:/home/Documents/NAME_Project --gpus all --shm-size 16G -it NAME_Project:latest
```
- gpus all: enables your Docker Container the ability to access all of your GPUS
- shm-size 16G: amount of shared memory (prevents memory-related errors)
- v: mounts your container in whichever directory you are in
- it: makes it interactive
- NAME_Project:latest is your <image_name>:<image_tag>.

- Everything inside /home/dannyboy/Documents/NAME_Project/ultralytics/ultralytics (on your host) will be available inside the container at /home/Documents/NAME_Project
- In other words, this is where the container will grab from and allow access (otherwise you will be restricted to the folder you mounted it in). Change to the files you want it to access.


## To start your docker container in the future:

```bash
sudo docker start -ai NAME_Project
````
- Simply change "NAME_Project" to the name of your container, and you're ready to go!



# Great Job! Next, we move into working into Data_Annotation!


# References:

- airou-lab, “GitHub - airou-lab/Docker-GPU-Tutorial: Docker Tutorial,” GitHub, 2024. Available: https://github.com/airou-lab/Docker-GPU-Tutorial.git (Mathis!)

- “Enable GPU support,” Docker Documentation, 2025. Available: https://docs.docker.com/compose/how-tos/gpu-support/ 

- S. Agarwal, “How to Use Your GPU in a Docker Container,” Roboflow Blog, Oct. 22, 2024. Available: https://blog.roboflow.com/use-the-gpu-in-docker/ 
