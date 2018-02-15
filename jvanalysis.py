#!/usr/bin/env python3

import yaml, argparse, os, numpy, pandas
import matplotlib.pyplot as plt
from pathlib import Path

# Defining functions first. Main program starts at line 98.

# Function to move the JV curve to the first quadrant.
def fix_quadrant(jv,quadrant):
    if quadrant == 2:
        jv['V'] *= -1
    elif quadrant == 3:
        jv['V'] *= -1
        jv['C'] *= -1
    elif quadrant == 4:
        jv['C'] *= -1
    else:
        print('The quadrant you provided in the configuration file does not exist.')
        exit()
    return jv

# Function to calculate main cell parameters: Voc, Jsc, FF and PCE.
def get_parameters(jv):
    # Check if Jsc has been measured, otherwise calculate it from interpolation.
    # The interpolation function also returns the actual value for a point if
    # this is present in the provided array, so this check might be skipped in
    # theory. In practice, I feel like calling the interpolation function is more
    # expensive, so I try to avoid it if possible.
    if 0 in jv['V'].values:
        Jsc = jv[jv['V'] == 0].index.tolist()
        Jsc = float(jv.iloc[Jsc]['C'].values)
    else:
        # numpy.interp requires x values to be increasing in order to work properly.
        # Depending of the measurement was a forward or reverse scan this may or may
        # not be true. Checking here to behave accordingly.
        if jv.iloc[0]['V'] < jv.iloc[1]['V']: # Forward scan, no modification needed.
            Jsc = numpy.interp(0,jv['V'],jv['C'])
        else: # Reverse scan, need to reverse the arrays.
            Jsc = numpy.interp(0,jv['V'][::-1],jv['C'][::-1])
    # Calculate Voc from interpolation. The chances that there is a measured value
    # where the current is exactly 0 are almost nonexistant and in that case the
    # actual value will be returned anyway.
    if jv.iloc[0]['V'] > jv.iloc[1]['V']: # Reverse scan, no modification needed.
        Voc = numpy.interp(0,jv['C'],jv['V'])
    else: # Forward scan, need to reverse the arrays.
        Voc = numpy.interp(0,jv['C'][::-1],jv['V'][::-1])
    # Calculate maximum power point, needed for FF and PCE.
    Wmax = numpy.amax(jv['V']*jv['C'])
    # Calculate fill factor.
    FF = (Wmax/(Jsc*Voc))*100
    # Calculate efficiency. For the moment it assumes full sun irradiation
    # (1000 W m-2). Reading irradiation from source file needs to be implemented.
    PCE = Wmax/1000
    # Convert main parameters to strings and round them up with meaningful decimals.
    Voc = format(Voc, '.0f')
    Jsc = format(Jsc, '.2f')
    FF = format(FF, '.0f')
    PCE = format(PCE, '.2f')
    return Voc,Jsc,FF,PCE

# Function to plot the JV curve with a table of main parameters underneath.
def jv_plot(jv,filename,Voc,Jsc,FF,PCE,output_dir):
    # Don't plot cell parameters if it's a dark scan.
    if PCE != '0.00':
        table_values = [[Voc,Jsc,FF,PCE]]
    else:
        table_values = [['----','----','----','----']]
    fig = plt.figure(figsize=(8,4))
    ax = fig.add_subplot(111)
    ax.set_title(filename)
    ax.set_xlabel('Voltage (mV)')
    ax.set_ylabel('Current density (mA cm$^{-2}$)')
    ax.plot(jv['V'],jv['C'])
    ax.axhline(0,color='k',lw=1)
    ax.axvline(0,color='k',lw=1)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    #ax.set_ylim(ymin=-2) I don't know if I want this or not yet
    table = plt.table(cellText=table_values,colLabels=('V$_{OC}$\n(mV)','J$_{SC}$\n(mA cm$^{-2}$)','FF\n(%)','PCE\n(%)'),cellLoc='center',bbox=(0.15,-0.43,0.7,0.25))
    plt.savefig(output_dir+filename+'.png',dpi=150,format='png',additional_artists=[table],bbox_inches='tight')
    plt.close(fig)

# Function to write an output text file containing the main cell parameters and
# tab separated JV raw values in the correct quadrant and units of measure.
def jv_datafile(jv,filename,Voc,Jsc,FF,PCE,output_dir):
    with open(output_dir+filename+'.txt','w') as output:
        output.write('Main cell parameters:\n')
        output.write('Voc (mV): '+Voc+'\n')
        output.write('Jsc (mA cm-2): '+Jsc+'\n')
        output.write('FF (%): '+FF+'\n')
        output.write('PCE (%): '+PCE+'\n\n')
        output.write('List of JV data points:\n')
        output.write('V (mV)\tJ (mA cm-2)\n')
        for index,row in jv.iterrows():
            output.write(str(row['V'])+'\t'+str(row['C'])+'\n')

# Main program

# Check if configuration file for the script exists and load it.
script_path = os.path.dirname(os.path.realpath(__file__)) # This is done so I can call the script from everywhere.
if Path(script_path+'/config.yaml').is_file():
    cfg = yaml.load(open(script_path+'/config.yaml', 'r'))
else:
    print('The configuration file is missing! Make sure you\nhave one in the same directory of your script!')
    exit()

# Allow input of a directory from command line and provide the directory to be
# analysed as a string. This structure auto-generates help for the script.
parser = argparse.ArgumentParser(description='J-V analyser: processes output files from solar simulators and creates an image of the J-V curve, calculates main cell parameters and gives a list of tab separated J-V points ready to be plotted. All output files are written in a subfolder named \'processed\' inside the input folder.',
                                 epilog='Remember to properly configure this script by editing config.yaml to suit your needs!')
parser.add_argument('path',
                    metavar='[DIR]',
                    help='directory containing the JV files to be analysed')
parser.add_argument('-v','--version',
                    action='version',
                    version='1.0')
analyse_dir = parser.parse_args()
analyse_dir = os.getcwd()+'/'+format(analyse_dir.path) # This way I provide an absolute path.

# Check that the input directory is actually a directory and fix trailing slash.
if not Path(analyse_dir).is_dir():
    print('You have not provided a valid directory. Make sure that you\nhave not provided a file name and that the directory exists.')
    exit()
if analyse_dir[-1] != '/':
    analyse_dir = analyse_dir+'/'

# Create an array with all relevant files in the directory based on the extension
# provided in the config file. If no extension is given (because the solar simulator
# doesn't provide one) all files will be taken into account. This may create
# problems later on, though, if the directory doesn't contain JV files only.
# One basic check has been implemented to verify that the current file is not
# a directory.
files = os.listdir(analyse_dir)
if cfg['format']:
    good_files = []
    for filename in files:
        if  Path(analyse_dir+filename).is_dir():
            continue
        if filename[-len(cfg['format']):] == cfg['format']:
            good_files.append(filename)
else:
    good_files = []
    for filename in files:
        if  Path(analyse_dir+filename).is_dir():
            continue
        good_files.append(filename)

# Create the output directory, if it doesn't exist.
output_dir = analyse_dir+'processed/'
if not Path(output_dir).is_dir():
    os.makedirs(output_dir)

# Main loop to process files in directory.
for filename in good_files:
    print('Processing file: '+filename)
    # Determine order of current and voltage column.
    if cfg['vcol'] < cfg['ccol']:
        cnames = ['V','C']
    else:
        cnames = ['C','V']
    # Read file and create pandas table.
    jvdata = pandas.read_table(analyse_dir+filename,
                               sep=cfg['spacer'],
                               header=None,
                               names=cnames,
                               usecols=[cfg['vcol']-1,cfg['ccol']-1],
                               dtype='float64',
                               engine='python',
                               skipinitialspace=True,
                               skiprows=cfg['hlines'],
                               skipfooter=cfg['flines'],
                               skip_blank_lines=False,
                               compression=None,
                               decimal=cfg['dseparator'])
    # Fix the quadrant if needed.
    if cfg['quadrant'] != 1:
        jvdata = fix_quadrant(jvdata,cfg['quadrant'])
    # Convert current to current density if needed.
    if cfg['current'].upper() != 'J':
        jvdata['C'] = jvdata['C']/cfg['carea']
    # Convert current density units of measure if needed.
    if cfg['ucurrent'] != 0 or cfg['uarea'] != 0:
        jvdata['C'] = jvdata['C']*(10**cfg['ucurrent'])*(10**-cfg['uarea'])
    # Convert voltage units of measure if needed.
    if cfg['uvoltage'] != 0:
        jvdata['V'] *= 10**cfg['uvoltage']
    # Calculate main cell parameters
    Voc,Jsc,FF,PCE = get_parameters(jvdata)
    # Remove file extension from file name if present, useful to save data afterwards.
    if cfg['format']:
        filename = filename[:-len(cfg['format'])]
    # Plot JV curve
    jv_plot(jvdata,filename,Voc,Jsc,FF,PCE,output_dir)
    # Write output file with JV data
    jv_datafile(jvdata,filename,Voc,Jsc,FF,PCE,output_dir)
