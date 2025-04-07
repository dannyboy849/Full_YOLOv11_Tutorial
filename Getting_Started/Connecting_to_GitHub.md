# This is strongly recommended to backup your data - you can actually upload the entirety of your Project to a repository! 

### Before continuing, it is important to note that you need a GitHub account already set up (personal or school).

## Step 1: Installing GitHub on Linux (Debian)
- Run this command to pull GitHub onto your repository
```bash
sudo apt update
sudo apt upgrade
sudo apt install git
```
Image_References/Creating_a_repository_add_button.png
<img src="Image_References/Creating_a_repository_add_button.png"> 

- You can refer to the link below if needed:
<li class="masthead__menu-item">
    <a href="https://gist.github.com/derhuerst/1b15ff4652a867391f03#file-linux-md">GitHub</a>
</li>


## Step 2: Configuring GitHub
- Referring to your GitHub account, sign in with your username (ie, dannyboy849)
```bash
git config --global user.name "user_name"
```
- Example
```bash
dannyboy@dannys-labtop:~/NAME_Project$ git config --global user.name "dannyboy849"
```

- Then, sign-in with your respective email account (ie, some_name@gmail.com)
```bash
git config --global user.email "email_id"
```
- Example
```bash
dannyboy@dannys-labtop:~/NAME_Project$ git config --global user.email "some_name@gmail.com"
```


## Step 3: Create a Local Repository
- This step is just making a quick repository on your device you will connect to your GitHub account later
```bash
git init Mytest # Replace Mytest with the desired name of your future repository
```
- Example
```bash
dannyboy@dannys-labtop:~/NAME_Project$ git init Mytest
Initialized empty Git repository in /home/ghabibi/Bird_Project/Mytest/.git/

```

- Mytest is your folder that is created and "init" makes the folder a GitHub repository. Go into this new folder:
```bash
cd Mytestf
```
- Example
```bash
dannyboy@dannys-labtop:~/NAME_Project$ cd Mytest/
dannyboy@dannys-labtop:~/NAME_Project/Mytest$
```


## Step 5: Create a README file
- A README file is always the first file you want to make for your repository. Here, you can give an overview of what your repository contains and how to navigate it. Essentially, it helps keep everything organized. Open this file
```bash
gedit README # This is the text editor mentioned in the previous file "Using_Ubuntu24.04"
# Alternatively, you could also use nano README
# Remember, all you have to do is text_editor README and it creates and opens the file
```
- Once inside of the README file, insert some filler words until you want to write a full description:
```bash
This is a git repo
```

## Step 6: Adding repository files to an index
- Let's make a simple C program.
- **Remember, you just have to type name.c to create a file in that programming language:**
```bash
#include<stdio.h>
int main()
{
printf("hello world");
return 0;
}
```

- You should now have two files - README and c.c
```bash
git add README
git add sample.c
```

## Step 7: Committing Changes Made
Once all the desired files are added, we can commit it. You should do this every time you make a new file/folder to avoid long upload times. You should also name it a habibt to do this frequently while working to ensure you have a backup. Use the command :
```bash
git commit -m "A message that described what's inside of the update"
```
- Example
```bash
dannyboy@dannys-labtop:~/NAME_Project/Mytest$ git commit -m "A message that described what's inside of the update"
[master (root-commit) 12345d] A message that described what's inside of the update
 2 files changed, 7 insertions(+)
 create mode 100644 README
 create mode 100644 sample.c
```


## Step 8: Creating a repository on GitHub
- Hopping over to GitHub on a browser, 

## Step : Generate a SSH key
- In the command line, navigate to the directory where you would like to create a local clone of your new project (I recommend inside of your project folder)
```bash
ghabibi@dannys-labtop:~/Bird_Project$ cd Mytest/
ghabibi@dannys-labtop:~/Bird_Project/Mytest$ ls
```
- To create a repository for your project, use the gh repo create subcommand. When prompted, select Create a new repository on GitHub from scratch and enter the name of your new project. If you want your project to belong to an organization instead of to your personal account, specify the organization name and project name with organization-name/project-name.
- Follow the interactive prompts. To clone the repository locally, confirm yes when asked if you would like to clone the remote project directory.


## Step : Creating a repository


## Step : Adding a key
- This lets create what's called an *access key* and it lets you access your repository from your device. Make a note that it only works for **this particular device**. If you wish to access the same repository on another device, you have to repeat the *access key* process.


## Step :


## Step :


## Step 7:

```bash

```
<li class="masthead__menu-item">
    <a href=""></a>
</li>
- Then, sign-in with your password (Don't worry, its safe and the only person who can see your information are adminstrative accounts (you or your school))



# Done! Now you can back all of your data safely. Next, we move onto creating our docker container. 



# References
- https://gist.github.com/derhuerst/1b15ff4652a867391f03#file-linux-md
