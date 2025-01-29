# How to create a docker image for YOLOv11

# 1. Pull the latest miniconda3 image:

You can refer to /ultralytics/docker/docker for the image

```python
sudo docker pull continuumio/miniconda3:latest
```

# 2. Create your image:
```python
sudo docker build -t yolov11_birds:latest .
```
It follows <image_name>:<image_tag>, so the name for the image, then tag you want.

# 3. Create a name for your to-be container:

```python
sudo docker build -t yolov11_birds .
```
Change "yolov11_birds" with your own image name


# How to create a docker container for YOLOv11

# 1. Build your docker container:

```python
sudo docker run --name yolov11_birds -v /home/daniel-airou/Documents/Bird_Project/ultralytics/ultralytics:/home/Documents/Bird_Project --gpus all --shm-size 16G -it yolov11_birds:latest
```
Again, yolov11_birds is your container name, followed by the directory of your choice. The ":/home/..." is where the container will grab from. Change to the files you want it to access.
This is based on GPU, so it'll be on your GPU, then shm-size is how many memory you want to use. Mine is 16GB memory out of 32GB possible. Finally, yolov11_birds:latest is your <image_name>:<image_tag>.
