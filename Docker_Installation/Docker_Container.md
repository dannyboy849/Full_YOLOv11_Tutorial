# How to create a Docker container for YOLOv11

## Step 1. Build your Docker container:

```python
sudo docker run --name yolov11_birds -v /home/daniel-airou/Documents/Bird_Project/ultralytics/ultralytics:/home/Documents/Bird_Project --gpus all --shm-size 16G -it yolov11_birds:latest
```
Again, yolov11_birds is your container name, followed by the directory of your choice. The ":/home/..." is where the container will grab from. Change to the files you want it to access.
This is based on GPU, so it'll be on your GPU, then shm-size is how many memory you want to use. Mine is 16GB memory out of 32GB possible. Finally, yolov11_birds:latest is your <image_name>:<image_tag>.

## Step 2. Ensure your Docker Container

# To start your docker container in the future:

```python
sudo docker start -ai yolov11_birds
````
Simply change "yolov11_birds" to the name of your container, and you're ready to go!
# Good Luck! Next, we move into working with YOLO!
