# Automating your hyper parameters

This process is very simple, its merely a matter of ensuring your data is organized and well-structured.
I will list the step by instructions, but please note you will need to have at least one training results of your own 
tuned parameters in order for the automated system to find a beginning ground. 

## Download the auto_run_experiments.py file

This file, of course, has everything you need to hypertune your model. You can manually adjust the testing values to 
you desire (please check through and adjust as you need)

## Ensure you already have your docker container created

In order to proceed any further, you need to have your container up and ready to run. Personally, I mounted my data
on its own seperate folder that had been copied from the original folder and made its own new docker container 
(GPU-enabled) to ensure if there was any risk of corruption, it would only affect that folder/container.

## Make a venv
For me, I had many issues with "import pandas as pd" as it relied on python, yet I could only use python3 and no longer
use pip3. This is likely due to my inexperience, as I'm a Mechanical Engineer with little experience in programming,
so please forgive my novice formatting. So, I created a venv to bypass this issue. The following will guide you
through the simple set-up.

```python

python3 -m venv .venv (build new venv)
source .venv/bin/activate (start venv)

```
