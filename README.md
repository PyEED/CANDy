# Domain-Analysis-of-CAZymes
This Jupyter Notebook allows the domain detection and annotation of protein sequences from any CAZy family.

Make sure to have following tools installed in the same directory as the Jupyter Notebook:

1. CD-HIT

For MacOS:

  Download the source code for CD-HIT from the GitHub repository at https://github.com/weizhongli/cdhit/releases.

  Open a terminal window and navigate to the directory where you downloaded the source code.

  Type the following commands in the terminal to compile the CD-HIT package:
  
    tar xvf cd-hit-v4.8.1-2019-0228.tar.gz
    cd cd-hit-v4.8.1-2019-0228
    make

  After the compilation process completes, you will find the CD-HIT executable file in the "cd-hit-v4.8.1-2019-0228" directory.
  
For Linux:

  Download the source code for CD-HIT from the GitHub repository at https://github.com/weizhongli/cdhit/releases.

  Open a terminal window and navigate to the directory where you downloaded the source code.

  Type the following commands in the terminal to compile the CD-HIT package:
  
    tar xvf cd-hit-v4.8.1-2019-0228.tar.gz
    cd cd-hit-v4.8.1-2019-0228
    make
   
  After the compilation process completes, you will find the CD-HIT executable file in the "cd-hit-v4.8.1-2019-0228" directory.

For Windows:

  Download and install Cygwin from https://www.cygwin.com/.

  During the installation process, make sure to select the "make" package.

  Download the source code for CD-HIT from the GitHub repository at https://github.com/weizhongli/cdhit/releases.

  Open a Cygwin terminal window and navigate to the directory where you downloaded the source code.

  Type the following commands in the terminal to compile the CD-HIT package:
  
    tar xvf cd-hit-v4.8.1-2019-0228.tar.gz
    cd cd-hit-v4.8.1-2019-0228
    make
  
  After the compilation process completes, you will find the CD-HIT executable file in the "cd-hit-v4.8.1-2019-0228" directory.
  
2. Clustal Omega. 

Precompiled binary can be downloaded here: http://www.clustal.org/omega/

3. FastTree. 

For MacOS:

   Follow installation instructions for your system on http://www.microbesonline.org/fasttree/#Install
   
   or
   
   Open a terminal window and install the Xcode Command Line Tools by typing the following command:
   
     xcode-select --install
    
   Install Homebrew by typing the following command:
     
     /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

   Install FastTree by typing the following command:
    
     brew install fasttree

For Linux:

  Download the FastTree source code from the FastTree website at http://www.microbesonline.org/fasttree/.

  Open a terminal window and navigate to the directory where you downloaded the source code.

  Type the following commands to compile the FastTree package:
  
    tar xvzf FastTree-2.1.13.c
    cd FastTree-2.1.13
    make
    
  After the compilation process completes, you will find the FastTree executable file in the "FastTree-2.1.13" directory.
  
For Windows:

   Download the FastTree Windows binary from the FastTree website at http://www.microbesonline.org/fasttree/#Download.

   Extract the FastTree executable from the downloaded ZIP file.



