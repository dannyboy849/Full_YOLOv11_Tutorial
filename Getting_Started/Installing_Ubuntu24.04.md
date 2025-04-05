# Initial Setup 

Some background: Ubuntu is one of the most used forms of Linux because of its easy-to-use nature, 
friendly to both beginning programmers and those with advanced experience with Linux 
(and its free!) Linux is another form of an operating system (OS), similar to MacOS, 
or WindowsOS, etc. Fun fact: every OS was built starting from Linux. Aside from this, 
Ubuntu is also one of the most secure forms of Linux because of its constant updates, 
so long you do not download unsecure items from online (although Ubuntu will immediately 
attempt to block these actions anyways)  
  


# How To Dual-Boot A Computer With Ubuntu (24.04) 

If you already have the flashdrive ready, review Steps 3 & 4 then Skip to step 7! 


## Step 1. Backup Your Files
Before anything else, I strongly recommend backing up your files into an external SSD/flashdrive/in the cloud. 


## Step 2. Flashdrive Requirements
The first thing you will need is a flashdrive (at least 8GB) 


## Step 3. Computer Storage Requirements
Ensure you have at least 256 GB to allocate to the computer/laptop you wish to dual boot. 
(it's a lot, but the files you will be using will be heavy 
(we allocated 512GB and we’ve alredy used 85% for 2 projects!)) 
Refer below **Step 4** for an important note! 


## Step 4. Partitioning 

- Search “Disk Management” in your windows search bar
- Right-click on your “(C:) Drive
- Shrink your C: drive to the 64 GB below half of your total available storage
- There will be a section at the bottom in “Disk 0” labelled “Unallocated”
- Right click and select “New Simple Volume”
- Select “Assign letter” and select your favorite letter (ex M:)
- To ensure correct drive creation, it should appear in your files under your local disk (C:)

- **If you have more than 1 disk (SSD) you have the preferred method – You can allocate a full SSD to Ubuntu! Ensure all your Windows's files are on Disk 0 (C:) then skip to step 7, but instead you’ll shrink Disk 1 to the total volume available (your other SSD that is NOT C:)**


## Step 5. Download balenaEtcher For Windows x86|64 (Installer) 


## Step 6. Download Ubuntu
- Ensure you're at the official Ubuntu 24.04 ISO, then download it onto your main SSD 
- Insert your flashdrive
- Open balenaEtcher
- Select your ISO (Ubuntu 24.04), then your flashdrive, and finally just click flash! 


## Step 7. Insert Your Flashdrive If You Haven’t Already 


## Step 8. Restart Your Computer
- The Ubuntu installer should immediately show up
- If it does not, restart and hold F12 throughout the reboot until it appears


## Step 9. Fill All Preferences


## Step 10. "What do you want to do” Section, 
- Click "Install Ubuntu"
- **If you accidentally click “Try Ubuntu” you will need to delete all files associated with Ubuntu on your Windows and restart from Step 8**


## Step 11. Installation  
- On “Type of Installation” click “Interactive Install”
- In “Applications” select Default selection
- For “Optimize” enable both options (Install 3rd party and Download support...)
- Select “Install Ubuntu alongside Windows Boot Manager”
- Select the partition you made earlier (ex M:)
- Allocate the full space
- Install!
- Create Password and Sign-in information (**STRONGLY recommend writing it down**)
- Remove Flash drive after instructed and restart computer
- You now will have the option of Ubuntu or Windows! 

**You’ve successfully dual booted Windows and Ubuntu! Congratulations!**

  

# Thats it! Next, I recommend checking out "Using_Ubuntu24.04"!


# References:
- Ubuntu.com, 2024. Available: https://ubuntu.com/blog/ubuntu-desktop-24-04-noble-numbat-deep-dive
  
- “Install Ubuntu desktop,” Ubuntu. Available: https://ubuntu.com/tutorials/install-ubuntu-desktop#2-download-an-ubuntu-image
  
- “balenaEtcher - Flash OS images to SD cards & USB drives,” etcher.balena.io. Available: https://etcher.balena.io/
  
- Ubuntu, “Download Ubuntu Desktop | Download | Ubuntu,” Ubuntu, 2019. Available: https://ubuntu.com/download/desktop

