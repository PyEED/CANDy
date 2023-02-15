# Domain Analysis of CAZymes
This Jupyter Notebook allows the domain detection and annotation of protein sequences from any CAZy family.

## Requirements

Make sure to have following tools installed in the same directory as the Jupyter Notebook:

### 1. CD-HIT

#### MacOS
  Download the source code from this GitHub repository and navigate to the source directory. 
  
  Write following command in your Terminal to compile the code:
  
     make
     
  Or
  
  Download the source code for CD-HIT from the GitHub repository at https://github.com/weizhongli/cdhit/releases.

  Open a terminal window and navigate to the directory where you downloaded the source code.

  Type the following commands in the terminal to compile the CD-HIT package:
  
    tar xvf cd-hit-v4.8.1-2019-0228.tar.gz
    cd cd-hit-v4.8.1-2019-0228
    make

  After the compilation process completes, you will find the CD-HIT executable file in the "cd-hit-v4.8.1-2019-0228" directory.
  
#### Linux
 Download the source code from this GitHub repository and navigate to the source directory. 
  
  Write following command in your Terminal to compile the code:
  
     make
     
  Or
  
  Download the source code for CD-HIT from the GitHub repository at https://github.com/weizhongli/cdhit/releases.

  Open a terminal window and navigate to the directory where you downloaded the source code.

  Type the following commands in the terminal to compile the CD-HIT package:
  
    tar xvf cd-hit-v4.8.1-2019-0228.tar.gz
    cd cd-hit-v4.8.1-2019-0228
    make
   
  After the compilation process completes, you will find the CD-HIT executable file in the "cd-hit-v4.8.1-2019-0228" directory.

#### Windows

  Download and install Cygwin from https://www.cygwin.com/.

  During the installation process, make sure to select the "make" package.

  Download the source code for CD-HIT from the GitHub repository at https://github.com/weizhongli/cdhit/releases.

  Open a Cygwin terminal window and navigate to the directory where you downloaded the source code.

  Type the following commands in the terminal to compile the CD-HIT package:
  
    tar xvf cd-hit-v4.8.1-2019-0228.tar.gz
    cd cd-hit-v4.8.1-2019-0228
    make
  
  After the compilation process completes, you will find the CD-HIT executable file in the "cd-hit-v4.8.1-2019-0228" directory.
  
### 2. Clustal Omega 

Precompiled binary can be downloaded here: http://www.clustal.org/omega/

### 3. FastTree 

#### MacOS

  Download the source code from this GitHub repository and navigate to the source directory. 
  
  Write following command in your Terminal to compile the code:
  
     make -f Makefile.GCC
   
   Or

   Follow installation instructions for your system on http://www.microbesonline.org/fasttree/#Install
   
   Or
   
   Open a terminal window and install the Xcode Command Line Tools by typing the following command:
   
     xcode-select --install
    
   Install Homebrew by typing the following command:
     
     /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

   Install FastTree by typing the following command:
    
     brew install fasttree

#### Linux

  Download the source code from this GitHub repository and navigate to the source directory. 
  
  Write following command in your Terminal to compile the code:
  
     make -f Makefile.GCC
   
  Or
   
  Follow installation instructions for your system on http://www.microbesonline.org/fasttree/#Install
  
  Or

  Download the FastTree source code from the FastTree website at http://www.microbesonline.org/fasttree/.

  Open a terminal window and navigate to the directory where you downloaded the source code.

  Type the following commands to compile the FastTree package:
  
    tar xvzf FastTree-2.1.13.c
    cd FastTree-2.1.13
    make
    
  After the compilation process completes, you will find the FastTree executable file in the "FastTree-2.1.13" directory.
  
#### Windows

   Download the FastTree Windows binary from the FastTree website at http://www.microbesonline.org/fasttree/#Download.

   Extract the FastTree executable from the downloaded ZIP file.



## Before you start
Your directory shoud look like this:

<img width="439" alt="image" src="https://user-images.githubusercontent.com/72694200/218505704-bc0f40ef-61bd-4e03-96d6-7a085032b841.png">

Also, for large families, avoid your computer entering sleep or stand-by mode since this will interupt the run. Change the settings in your computer or caffeinate your system.

#### MacOS

Install caffeinate package by running in your Terminal:

    brew install caffeinate
    
Start the package by running:

    caffeinate -d
    
Stop by running: 

    ctrl + C

#### Linux

Install caffeinate package by running in your Terminal:

    sudo apt-get install caffeinate
    
Start the package by running:

    caffeinate -d
    
Stop by running: 

    ctrl + C
#### Windows

Note: The caffeinate package is not available for Windows. However, you can use a similar feature called "powercfg" to prevent the system from going to sleep.

Open the Command Prompt application.

Type following line to see the current power requests:
   
    powercfg /requests

Type following line, followed by the type of request you want to override (e.g., "system" or "display"):
 
    powercfg /requestsoverride

To stop the power request override, type in "powercfg /requestsoverride" followed by the type of request and the "/remove" argument

## Output

### Database

To open the results in the database, download SQLite from: https://sqlitebrowser.org/

