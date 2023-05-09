# Carbohydrate Active eNzyme Domain analYsis tool (CANDy)
This Jupyter Notebook allows the domain detection and annotation of protein sequences from any [CAZy](http://www.cazy.org/) family.

## Requirements

Make sure to have following tools installed in the same directory as the Jupyter Notebook:

### 1. CD-HIT

#### MacOS
  Download the source code for CD-HIT from the GitHub repository at https://github.com/weizhongli/cdhit/releases.

  Open a terminal window and navigate to the directory where you downloaded the source code.

  Type the following commands in the terminal to compile the CD-HIT package:
  
    tar xvf cd-hit-v4.8.1-2019-0228.tar.gz
    cd cd-hit-v4.8.1-2019-0228
    make

  After the compilation process completes, you will find the CD-HIT executable file in the "cd-hit-v4.8.1-2019-0228" directory.
  
#### Linux
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
  
### 2. MAFFT

Precompiled binary can be downloaded here: https://mafft.cbrc.jp/alignment/software/

### 3. FastTree 

#### MacOS

   Follow installation instructions for your system on http://www.microbesonline.org/fasttree/#Install
   
   Or
   
   Open a terminal window and install the Xcode Command Line Tools by typing the following command:
   
     xcode-select --install
    
   Install Homebrew by typing the following command:
     
     /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

   Install FastTree by typing the following command:
    
     brew install fasttree

#### Linux

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

<img width="385" alt="image" src="https://github.com/PyEED/CANDy/assets/72694200/26370212-d8a8-42df-a0a8-917e2eae6d56">



Also, for large families, avoid your computer entering sleep or stand-by mode since this will interupt the run. Change the settings in your computer or [caffeinate](https://pypi.org/project/caffeinate/) your system.

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

### (Annotated) Phylogenetic tree 

To view the phylogenetic tree, several free services are available. The Notebook makes use of the ete3 package to visualize the annotated tree in there. For a more interactive experience we recommend [iTOL](https://itol.embl.de/). The script outputs iTOL annotation files for the visualization of the protein domains and the activity of the included characterized sequences.

![image](https://github.com/PyEED/CANDy/assets/72694200/bc8969ab-0181-4417-9678-c26e624a3d5e)

## Acknowledgements

CANDy communicates with and/or references the following separate libraries, packages and tools:

- [Biopython](https://biopython.org/)
- [pandas](https://pandas.pydata.org/)
- [tqdm](https://github.com/tqdm/tqdm) 
- [sqlitebrowser](https://sqlitebrowser.org/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [sdRDM](https://github.com/JR-1991/software-driven-rdm)
- [requests](https://requests.readthedocs.io/en/latest/)
- [ete3](http://etetoolkit.org/)
- [CD-HIT](https://academic.oup.com/bioinformatics/article/22/13/1658/194225?login=true)
- [MAFFT](https://academic.oup.com/nar/article/30/14/3059/2904316?login=true)
- [FastTree](http://www.microbesonline.org/fasttree/)

## Legal terms

### License and Disclaimer

This Jupyter Notebook is licensed under [MIT](https://github.com/PyEED/CANDy/blob/main/SECURITY.md#mit-license).

This Notebook and other information provided is for theoretical utilisation only, caution should be exercised in its use. It is provided ‘as-is’ without any warranty of any kind, whether expressed or implied. Information is not intended to be a substitute for professional medical advice, diagnosis, or treatment, and does not constitute medical or other professional advice.

### Third-party software

Use of the third-party software, libraries or code referred to in the [Acknowledgements section](https://github.com/PyEED/CANDy#acknowledgements) in the CANDy README may be governed by separate terms and conditions or license provisions. Your use of the third-party software, libraries or code is subject to any such terms and you should check that you can comply with any applicable restrictions or terms and conditions before use.

### Databases

The following databases are used by CANDy, and are available with reference to the following:
- UniProt: (unmodified), by The UniProt Consortium, available under a [Creative Commons Attribution-NoDerivatives 4.0 International License](http://creativecommons.org/licenses/by-nd/4.0/).
- NCBI: (unmodified), by the National Library of Medicine, available under a [Creative Commons Attribution-NoDerivatives 4.0 International License](http://creativecommons.org/licenses/by-nd/4.0/). 
- CAZy: (unmodified), by http://www.cazy.org/ and Elodie Drula, Marie-Line Garron, Suzan Dogan, Vincent Lombard, Bernard Henrissat, Nicolas Terrapon, The carbohydrate-active enzyme database: functions and literature, Nucleic Acids Research, Volume 50, Issue D1, 7 January 2022, Pages D571–D577, https://doi.org/10.1093/nar/gkab1045, available under a [Creative Commons Attribution-NoDerivatives 4.0 International License](http://creativecommons.org/licenses/by-nd/4.0/). 
- InterPro: (unmodified), by EMBL-EBI, available under a [Creative Commons Attribution-NoDerivatives 4.0 International License](http://creativecommons.org/licenses/by-nd/4.0/). 
