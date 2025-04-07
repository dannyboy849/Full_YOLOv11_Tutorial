# Using Ubuntu 24.04 

Now that you’ve installed Ubuntu, you essentially have to relearn how to use a computer! Fortunately, Ubuntu automatically installs Firefox and pins it to your toolbar. “How to install *anything* on Linux” will become your catchphrase. Ubuntu also includes “Text Editor”, an “App Center” that is terribly optimized, and “Software Updater” which is known to crash computers! Instead of using these, you will now become a fully pledged programmer. The infamous “Terminal” and heavenly "VSCode" will become your new best friends. We will now go into the basics and some commands of how to use the terminal. 

Note from now on: every time I say “type *something*” I am referring to inside of your terminal. Also, it’s vital you understand **everything in Linux is case-sensitive** 
(ie, 
- cd = good
- Cd = will NOT work

## Open a terminal
- Either you can click on your terminal on the taskbar, or you can shortcut using “ctrl+alt+t” on your keyboard

## Knowing your current directory
- You will see your username alongside the name you gave your computer and *your_name*:~$ Note that ~ means you're in your "home" directory. It will look something like this:
```bash
danny_boy@dannys-labtop:~$ 
```

## Always update your computer! 
- Check available updates:
```bash
sudo apt-get update
```

- Download upgrades:
```bash
sudo apt-get upgrade
```

## Check if your GPU is successfully identified
- Confirm Ubuntu is able to identify your GPU:
```bash
nvidia-smi
```
- You should see your GPU listed 

## Your IP address
- If you want to know your IP address, you can type “ifconfig” 

## Listing Folders/Files Inside of Current Folder
- To find out which folders/files are under the directory you are in, type “ls” --> lower-case L:
```bash
ls
```
Example:
```bash
danny_boy@dannys-labtop:~$ ls
NAME_Project  Documents
```

## Changing Directory's
- To change which current directory you are in:
```bash
cd *directory_name*
```
Example:
```bash
danny_boy@dannys-labtop:~$ ls
NAME_Project  Documents  Work-Tin
danny_boy@dannys-labtop:~$ cd Worn-Tin/
danny_boy@dannys-labtop:~/Worn-Tin$ ls
Rosemary
```
 
- To go back to the previous directory:
```bash
cd ..
```
Example:
```bash
danny_boy@dannys-labtop:~/Bird_Project$ cd ..
danny_boy@dannys-labtop:~$ 
```

- To go back to your home directory, just type:
```bash
cd
```
Example:
```bash
danny_boy@dannys-labtop:~/NAME_Project/yolov5$ cd
danny_boy@dannys-labtop:~$
```

## To Find A Specfic Directory
To find a specfic directory, type: 
```bash
~/*directory_name*
``` 
Example:
```bash
danny_boy@dannys-labtop:~$ ~/NAME_Project/
bash: /home/danny_boy/NAME_Project/: Is a directory
```

## If you want to create a new directory, type “mkdir *name*” 
- For your own sanity, always use *some_name* with a “_” instead of a space with every folder/file.
Example:
```bash
danny_boy@dannys-labtop:~$ ls
NAME_Project  Desktop
danny_boy@dannys-labtop:~$ mkdir Deftones
danny_boy@dannys-labtop:~$ ls
NAME_Project  Desktop    Deftones
```

## To make a simple file, such as for notes (if you don’t want to open the Text Editor) 
- Note that you will need to download these packages.
- Inside of your desired directory, type:
```bash
touch *name*
```
Example:
```bash
danny_boy@dannys-labtop:~/Deftones$ ls
_
danny_boy@dannys-labtop:~/Deftones$ touch Rosemary
danny_boy@dannys-labtop:~/Deftones$ ls
Rosemary
```

- To open and modify these files:
```bash
gedit *name*
```

or

```bash
nano *name* 
```

- You can now create notes and things of the sort, or even write your code if you enjoy pain. Make sure you constantly save “ctrl+s”. To exit: “ctrl+x” 

## This also works to create specfic file types! 
- For example, to create a python file:
```bash
touch *file_name*.py
```
Example:
```bash
danny_boy@dannys-labtop:~/Deftones$ ls
Rosemary
danny_boy@dannys-labtop:~/Deftones$ touch Entombed.py
danny_boy@dannys-labtop:~/Deftones$ ls
Entombed.py  Rosemary
```

## To move a file to another folder: 
```bash
mv ~/path/to/*file_name* ~/path/to/*new_directory* 
```
Example:
```bash
danny_boy@dannys-labtop:~/Deftones$ ls
Entombed.py  Rosemary
danny_boy@dannys-labtop:~$ sudo mv ~/Deftones/Entombed.py ~/Worn-Tin/
danny_boy@dannys-labtop:~/Deftones$ ls
Rosemary
danny_boy@dannys-labtop:~/Worn-Tin$ ls
Entombed.py
```

## To move a folder into another folder: 
```bash
sudo mv ~/current_directory ~/desired_directory 
```
Example:
```bash
danny_boy@dannys-labtop:~$ ls
NAME_Project   Desktop   Deftones   Worn-Tin
danny_boy@dannys-labtop:~$ sudo mv ~/Deftones/ ~/Worn-Tin/
danny_boy@dannys-labtop:~$ ls
NAME_Project   Desktop   Worn-Tin
danny_boy@dannys-labtop:~/Worn-Tin$ ls
Deftones  Entombed.py
```
 
## To delete a file:
```bash
rm *file_name*
```
Example:
```bash
danny_boy@dannys-labtop:~/Worn-Tin$ ls
Deftones  Entombed.py
danny_boy@dannys-labtop:~/Worn-Tin$ rm Entombed.py 
danny_boy@dannys-labtop:~/Worn-Tin$ ls
Deftones
```

## To delete a folder:
```bash
rm –r *folder_name* 
```
Example:
```bash
danny_boy@dannys-labtop:~/Worn-Tin$ ls
Deftones
danny_boy@dannys-labtop:~/Worn-Tin$ rm -r Deftones/
danny_boy@dannys-labtop:~/Worn-Tin$ ls
_
```

To find more advanced guidance, I strongly recommend simply searching for them on Firefox, and following reliable sources such as StackExchange, Official Websites, or Community Forums. 

 

**I STRONGLY recommend using VSCode for all your programming.** Below is a short guide: 
# Downloading VSCode
## Step 1. Download Debian  
```bash
sudo apt install ./<file>.deb 
```

  
# Step 2: Run this and it should automatically do the rest of the work: 
```bash
echo "code code/add-microsoft-repo boolean true" | sudo debconf-set-selections 
```

- If this doesn't work, you will manually have to do it: 
```bash
sudo apt-get install wget gpg

wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > packages.microsoft.gpg

sudo install -D -o root -g root -m 644 packages.microsoft.gpg /etc/apt/keyrings/packages.microsoft.gpg

echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" |sudo tee /etc/apt/sources.list.d/vscode.list > /dev/null 

rm -f packages.microsoft.gpg 
```


## Step 3: Updates
```bash
sudo apt install apt-transport-https 

sudo apt update 

sudo apt install code # or code-insiders
```


## Step 4: Sign in!
**Done! This is FAR better than the small code editors mentioned earlier.**
Make a note that your workstation will be where your YOLO is located in your files.

Fun fact: you don’t have to activate your docker container unless you want to train! Just make sure to constantly save in VSCode so that it updates the file for everything. 



# That's it! Now, onto building our Docker Container (or the recommended connection to GitHub to upload your data to a repository)! 


# References:
- B. Marijan, “Bash Commands: The Ultimate Cheat Sheet + Downloadable PDF,” Knowledge Base by phoenixNAP, Aug. 24, 2023. Available: https://phoenixnap.com/kb/bash-commands
