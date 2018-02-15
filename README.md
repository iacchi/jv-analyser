# J-V analyser
Processes output files from solar simulators and creates an image of the J-V curve, calculates main cell parameters and gives a list of tab separated J-V points ready to be plotted. All output files are written in a subfolder named 'processed' inside the input folder.

## Dependencies
This script is written in python3 and relies on python modules that are not part of the standard python installation — namely numpy, pandas, yaml and matplotlib. These modules can be installed in a debian-based system with:
```
apt-get install python3-numpy python3-pandas python3-yaml python3-matplotlib
```
Or otherwise everywhere using the python package installer:
```
pip3 install numpy pandas yaml matplotlib
```

## Usage
Before using this script, you will need to create a configuration file containing parameters required for the script to run correctly which need to be adapted to suit your need. To start, rename config.yaml.example into config.yaml and edit the file according to your input files. After creating the configuration file, launch the script in this way:
```
jvanalysis.py path/to/folder/containing/jv/files/
```
The path to the folder can be relative.

## Examples
The example folder contains three folders, namely 'uu', 'monash' and 'monash2' — which contain J-V files in different formats — and their related configuration files. To test the script, move the configuration file related to the folder you want to analyse in the same folder of jvanalysis.py and rename it to config.yaml, then run the script on the folder.
