# Initial Setup 

Some background: Ubuntu is one of the most used forms of Linux because of its easy-to-use nature, 
friendly to both beginning programmers and those with advanced experience with Linux 
(and its free!) Linux is another form of an operating system (OS), similar to MacOS, 
or WindowsOS, etc. Fun fact: every OS was built starting from Linux. Aside from this, 
Ubuntu is also one of the most secure forms of Linux because of its constant updates, 
so long you do not download unsecure items from online (although Ubuntu will immediately 
attempt to block these actions anyways)  
  

# How to dual boot a computer with Ubuntu (24.04) 

Review Steps 3 & 4 then Skip to step 7 if you already have the flashdrive ready! 

## Step 1. Backup Your Files
Before anything else, we strongly recommend backing up your files into an external SSD/flashdrive/in the cloud. 

## Step 2. Flashdrive Requirements
The first thing you will need is a flashdrive (at least 8GB) 

## Step 3. Computer Storage Requirements
Ensure you have at least 256 GB to allocate to the computer/laptop you wish to dual boot. 
(it's a lot, but the files you will be using will be heavy 
(we allocated 512GB and we’ve used 85% for 2 projects)) 
Look below **Step 4.** for an important note! 

## Step 4. Partitioning 

- Search “Disk Management” in your windows search bar
- Right-click on your “(C:) Drive
- Shrink your C: drive to the 64 GB below half of your total available storage
- There will be a section at the bottom in “Disk 0” labelled “Unallocated”
- Right click and select “New Simple Volume”
- Select “Assign letter” and select your favorite letter (ex M:) 

To ensure correct drive creation, it should appear in your files under your local disk (C:) 
- If you have more than 1 disk (SSD) you have the preferred method – You can allocate a full disk to Ubuntu! Ensure all your Windows's files are on Disk 0 (C:) then skip to 3b, but instead you’ll shrink Disk 1 to the total volume available (your other SSD that is NOT C: ) 

    Download balenaEtcher [3] for Windows x86|64 (Installer) 

    Download the official Ubuntu 24.04 [4] ISO onto your main SSD 

    Insert your flashdrive 

    Open balenaEtcher 

    Select your ISO (Ubuntu 24.04), then your flashdrive, and finally just click flash! 

    Insert your flashdrive if you haven’t already 

    Restart your computer – The Ubuntu installer should immediately show up 

    If it does not, restart and hold F12 throughout shows up up 

    Fill all of your preferences 

    When you reach the “What do you want to do” section, click install Ubuntu. 

    If you accidentally click “Try Ubuntu” you will need to delete all files associated with Ubuntu on your Windows and restart from step 8 

    Installation  

    On “Type of Installation” click “Interactive Install” 

    In “Applications” select Default selection 

    For “Optimize” enable both options (Install 3rd party and Download support...) 

    Select “Install Ubuntu alongside Windows Boot Manager” 

    Select the partition you made earlier (ex M:) 

    Allocate the full space 

    Install! 

    Create Password and Sign-in information (STRONGLY recommend writing it down) 

    Remove Flash drive after instructed and restart computer 

    You now will have the option of Ubuntu or Windows! 

You’ve successfully dual booted Windows and Ubuntu! Congratulations! 

  

Using Ubuntu 24.04 

Now that you’ve installed Ubuntu, you essentially have to relearn how to use a computer! Fortunately, Ubuntu automatically installs Firefox and pins it to your toolbar. “How to install *anything* on Linux” will become your catchphrase. Ubuntu also includes “Text Editor”, an “App Center” that is terribly optimized, and “Software Updater” which is known to crash computers! Instead of using these, you will now become a fully pledged programmer. The infamous “Terminal” will become your best friend. We will now go into the basics and some commands of how to use the terminal. 

Note that every time I say “type *something” I am referring to inside of your terminal. Also, it’s vital you understand everything in Linux is case-sensitive (ie, cd = good, Cd = will NOT work” 

    Either you can click on your terminal, or you can shortcut using “ctrl+alt+t” 

    You will see your username alongside the name you gave your computer and $ 

    Always update your computer! 

    Type “sudo apt update” to check available updates 

    Type “sudo apt upgrade” to download these updates 

    To check if your GPU was successfully, type “nvidia-smi” to confirm 

    You should now see your GPU listed 

    If you want to know your IP address, you can type “ifconfig” 

    To find which current directory you are in, type “ls” --> lower-case L 

    To change which current directory you are in, type “cd *directory_name* 

    To go back to the previous directory, type “cd ..” 

    To go back to your home directory, just type “cd” 

    To know which directory you are currently in, you’ll see this after your name: 

    ~/*directory_name* 

    If you want to create a new directory, type “mkdir *name*” 

    For your own sanity, always use *some_name* with a “_” instead of a space. 

    To make a simple file, such as for notes if you don’t want to open the Text Editor 

    Inside of your desired directory, type: 

    touch *name* or gedit *name* 

    nano *name* 

    You can now add your notes and things of the sort. Make sure you constantly save “ctrl+s”. To exit: “ctrl+x” 

    This also works to create specfic file types! 

    Type “touch *name*.py” for example, to create a python file 

    To move files to another folder: 

    mv *name* *directory_name* 

    To move folders into another folder: 

    sudo mv ~/current_directory ~/desired_directory 

    To delete a file, type “rm *name*” 

    To delete a folder: rm –r *name* 

To find more advanced guidance, I strongly recommend simply searching for them on Firefox, and following reliable sources such as StackExchange, official websites, or community forums. 

 

I STRONGLY recommend using VSCode for all your programming. Below is a guide: 

    Download Debian  

    sudo apt install ./<file>.deb 

    Run this and it should automatically do the rest of the work: 

    echo "code code/add-microsoft-repo boolean true" | sudo debconf-set-selections 

    If not, you will manually have to do it: 

    sudo apt-get install wget gpg 

    wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > packages.microsoft.gpg 

    sudo install -D -o root -g root -m 644 packages.microsoft.gpg /etc/apt/keyrings/packages.microsoft.gpg 

    echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" |sudo tee /etc/apt/sources.list.d/vscode.list > /dev/null 

    rm -f packages.microsoft.gpg 

    Update 

    sudo apt install apt-transport-https 

    sudo apt update 

    sudo apt install code # or code-insiders 

Done! This is FAR better than the code editors mentioned earlier. Below is what your workstation address will look like (after making docker container and downloading YOLO)  

Fun fact: you don’t have to activate your docker container unless you want to train! Just make sure to constantly save in VSCode so that it updates the file for everything. 
