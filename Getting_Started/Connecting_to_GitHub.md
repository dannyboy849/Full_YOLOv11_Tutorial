# This is strongly recommended to backup your data - you can actually upload the entirety of your Project to a repository! 

### Before continuing, it is important to note that you need a GitHub account already set up (personal or school).

## Step 1: Installing GitHub on Linux (Debian)
- Run this command to pull GitHub onto your repository
```bash
sudo apt update
sudo apt upgrade
sudo apt install git
```

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
dannyboy@dannys-labtop:~/NAME_Project$ git config --global user.email "user_email@gmail.com"
```


## Step 3: Create a Local Repository
- This step is just making a quick repository on your device you will connect to your GitHub account later
```bash
git init Mytest # Replace Mytest with the desired name of your future repository
```
- Example
```bash
dannyboy@dannys-labtop:~/NAME_Project$ git init Mytest
Initialized empty Git repository in /home/dannyboy/Bird_Project/Mytest/.git/

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
- Hopping over to GitHub on a browser, you can refer to the image below to find the add button:
<img src="https://github.com/dannyboy849/Full_YOLOv11_Tutorial/blob/main/Image_References/Creating_a_repository_add_button.png">

- Create a new repository. The image below is what it should look like:
<img src="https://github.com/dannyboy849/Full_YOLOv11_Tutorial/blob/main/Image_References/Creating_a_repository_example.png"> 
- It goes without saying, you can modify anything option you'd like. For projects, I strongly recommend making your repository private unless you want to make your work/data publicly available. **Ensure you remove any compromising information.**


## Step 9: Connect to the repository!
- Now that your repo is created, copy your repo address! This can be found as shown in the image below:
<img src="https://github.com/dannyboy849/Full_YOLOv11_Tutorial/blob/main/Image_References/Link_to_repository.png">

- Then, you'll run this command using your repo address:
```bash
git remote add origin https://github.com/username/repo_name.git
```

- **Important Note: Make sure you replace 'username' and 'repo_name' in the path with your Github username and folder!**

- Example
```bash
dannyboy@dannys-labtop:~/NAME_Project/Mytest$ git remote add origin https://github.com/dannyboy849/Mytest.git
```


## Step 10: Pushing files to your GitHub repo
- Using this command, this uploads your files/folders from local device to your GitHub online repo:
```bash
git push origin master
```

- Example
```bash
dannyboy@dannys-labtop:~/NAME_Project/Mytest$ git push origin master
Username for 'https://github.com': user_email@gmail.com
Password for 'https://user_email%99gmail.com@github.com': 
remote: Support for password authentication was removed on August 13, 2021.
remote: Please see https://docs.github.com/get-started/getting-started-with-git/about-remote-repositories#cloning-with-https-urls for information on currently recommended modes of authentication.
fatal: Authentication failed for 'https://github.com/dannyboy849/Mytest.git/'
```
- As shown above, you may be denied remote access. Don't worry yet! Simply follow Step 11. and you'll be ready to go!
**THIS IS CRITICALLY IMPORTANT: if you made an SSH key, you will sign in your your PERSONAL ACCESS TOKEN!!!**

  
## Step 11: How to find Personal Access Tokens
- Refer to *Developer Settings* Found at the bottom in settings
- As shown in the image below, you'll select *Generate new token*
<img src="https://github.com/dannyboy849/Full_YOLOv11_Tutorial/blob/main/Image_References/Generating_personal_token.png">
- You'll get a key. Make sure to save this somewhere secure for future use.
- You will then fill out the respective information
```bash
git clone https://github.com/USERNAME/REPO.git
Username: YOUR-USERNAME
Password: YOUR-PERSONAL-ACCESS-TOKEN
```
- If you successfully signed in and pushed, **skip to Step 13!**

## Step 12: Generate a SSH key
- This lets us create what's called an *SSH key* and it lets you access your repository remotely from your device. Make a note that it only works for **this particular device**. If you wish to access the same repository on another device, you have to repeat the *SSH key* process.
- Navigate to your GitHub settings as shown below:
<img src="https://github.com/dannyboy849/Full_YOLOv11_Tutorial/blob/main/Image_References/Making_SSH_keys.png">

- For obvious reasons I'm not showing my SSH key, but below is what you should see. Click on *New SSH key*:
<img src="https://github.com/dannyboy849/Full_YOLOv11_Tutorial/blob/main/Image_References/Create_ssh_key.png">

- Below is what you should see. You will fill in the information including the desired name of your device's SSH key, as well as the key generated from your local device:
<img src="https://github.com/dannyboy849/Full_YOLOv11_Tutorial/blob/main/Image_References/adding_ssh_key.png">

- Generate SSH key from your local device:
```bash
dannyboy@dannys-labtop:~/NAME_Project/ssh_key$ ssh-keygen -t ed25519 -C "user_email@gmail.com"
Generating public/private ed25519 key pair.
Enter file in which to save the key (/home/dannyboy/.ssh/id_ed25519): 
Enter passphrase (empty for no passphrase): [Type a passphrase]
Enter same passphrase again: [Type passphrase again]
```

- You will then type the following to confirm you successfully created your key:
```bash
eval "$(ssh-agent -s)"
```

- Example
```bash
dannyboy@dannys-labtop:~/NAME_Project/ssh_key$ eval "$(ssh-agent -s)"
Agent pid 12345 # This will be a pid unique to you
```

- Add your SSH private key to the ssh-agent:
```bash
ssh-add ~/.ssh/id_ed25519
```

- Example
```bash
dannyboy@dannys-labtop:~/NAME_Project/ssh_key$ ssh-add ~/.ssh/id_ed25519
Identity added: /home/dannyboy/.ssh/id_ed25519 (user_email@gmail.com)
```

- Finally, print your SSH public key:
```bash
cat ~/.ssh/id_ed25519.pub
```

- Example
```bash
dannyboy@dannys-labtop:~/NAME_Project$ cat ~/.ssh/id_ed25519.pub
# Copy the full string below
ssh-ed25519 *super long string of letters and numbers* user_email@gmail.com
```

- Copy the full string noted and paste it into where it asks for your SSH key.
- If the top of your screen says *You have successfully added the key 'user_email@gmail.com'* Congrats! You can now remotely access and push to your GitHub repository (and GitHub in general). **Now, refer back to Step 10**

## Step 13:
**Congratulations!** That's all there is to it! Now you can back all of your data safely. Here is a list of the most important and commonly used commands to push your files/folders to your repository:

```bash
git init # Initializes a new Git repository
```

```bash
git init # Initializes a new Git repositor
```

```bash
git clone [URL] # Clones a repository from a remote source-
```

```bash
git add [file] # Adds files to the staging area
```

```bash
git commit -m "commit message" # Commits your changes with a message
```

```bash
git push # Pushes your changes to the remote repository
```

```bash
git pull # Pulls updates from the remote repository
```


# Next, we move onto creating our docker container!



# References
- https://gist.github.com/derhuerst/1b15ff4652a867391f03#file-linux-md
