# Bird_Project_Daniel
This will be my repository where I upload all of my files mainly as a backup, but also to be easily accessible for anyone who wants to work on it/borrow my data. If there is anything missing(although only the Airlab team has access as of now) or needs clarification, please feel free to reach out to me here, or preferably at dvargas88@ou.edu. Hope this helps!

As of now, our best results for Camera 1 are 54% precison and 23.4% accurate in IoU. This, of course, is without the aid of semantic segmentation which is likely to boost the accuracy to ~70% or higher.
Our best results for Camera 2 are 64% precison and 27.3% accurate in IoU (mAP-50-95)

Instructions: 
Download Yolov5
Set up your system with Ubuntu (version doesn't matter) - I used dual boot
Install Docker with access to GPU (CPU will also be demonstrated)
Upload your images/lables to your data - will look like this:

yolov5
  - classify (Don't touch)
  - data
      - hyps (Don't touch)
      - scripts (Don't touch)
      - birds_dataset_1.yaml (you have to make this - view documents)
      - train
          - images (60%)
          - labels (60%)
      - val
          - images (20%)
          - labels (20%)
      - test
          - images (20%)
          - lables (20%)
  - datasets (Don't touch)
  - models (Don't touch)
  - _pycache_ (Don't touch)
  - runs
      - Detect (Train with previous weights and provides those results)
      - Train (Contains results AND weights after training)
  - segment (Don't touch)
  - utils (Import Albumentations for augmentation for more accurate data) (these are the main important ones)
      - augmentations.py (Update sizing of augmentation pending your results (ours is dependent on color, so we only change sizing)
      - dataloaders.py (Change: self.albumentations = Albumentations(size=img_size) if augment else None ; to: self.albumentations = Albumentations() if augment else None )
