#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug 26 12:25:28 2020

@author: Bryce

----- Usage ------

python 4_tractometry_v1.py

Point the script to a folder containing RecobundlesX resultant tracts, .trk format. This script
converts .trk files to .tck and binary .nii files, then calculates metric means, std dev., and
streamline counts for each tract. Results are saved in a csv file in the parent directory
(dir_parent variable), for visual evaluation and merging into APSP tractometry script.

----- Versions -----

- v1: initial script, set up to work for L/R AF and UF.

What will I need to change when I add NODDI measures?
change measure_means_list to include ndi and odi
change measure_map variable declaration (currently line 98) in appendMeansToLists() to correctly point to subject NDI and ODI maps


"""

"""
MODULE & LOGGING INITIALIZATION
"""
import os, re, logging
import pandas as pd
import subprocess
from datetime import date
from dipy.io.streamline import load_trk, load_tck, save_tractogram

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

"""
1 -- Find subject folders to process (use handy python functions)
"""
# -- Specify which folder to calculate metric means for (should contain subfolders
# for each group, containing all subjects as sub-subfolders). Currently hard-coded
# to save time but can change to input() line to ask user to drag and drop.
def getParentFolder():
    directory = '/Volumes/Venus/Kirton_Diffusion_Processing/2_RecobundlesX/4_RecoX_outputs'
    #directory = input('Which folder has the RecoX tracts to process?')
    directory = directory.strip() # remove leading or trailing whitespaces
    return directory

# -- Find all paths that end in a subject tag (so find all subject subfolders in group folder)
def getSubjectList(data_dir):
    all_folders = [x[0] for x in os.walk(data_dir)]
    subject_folder_regex = re.compile(r'\d\d-\d\d\d\d\Z') #2 digits, dash, 4 digits at very end of string (\Z)
    subject_folder_list = list()
    for directory in all_folders:
        if subject_folder_regex.search(directory):
            subject_folder_list.append(directory)
    return subject_folder_list

# -- For a given path, pull out the group and tag information using regex
def getSubjectTag(subject_directory):
    
    #make a regex below which will find one of 3 groups, and a subject tag
    identifier_regex = re.compile(r'(TDC|AIS_L|AIS_R|PVI_L|PVI_R).*(\d\d-\d\d\d\d)')
    info_list = identifier_regex.findall(subject_directory)
    
    #if working as intended, should return a list with group followed by tag
    group = info_list[0][0]
    tag = info_list[0][1]
    
    return group, tag

"""
2 -- Convert RecoX trk files back to tck files
"""

# -- For .trk files in the <subject>/1_recox_tracts/ directory, convert to .tck
# and create a binary .nii mask file
def convertAndMaskTrks(subject_tracts_folder, group, tag):
    #for every file in the folder, if it has the .trk suffix:
        if file.endswith(".trk"):
            #get filename of .trk file
            filename = file.split('.')[0]
            if not os.path.isfile(filename+'.tck'):
                #load trk and save as tck (no reference image needed)
                temp_trk = load_trk(file,'same',bbox_valid_check=False)
                save_tractogram(temp_trk,filename+'.tck',bbox_valid_check=False)
                logging.info('saved: '+filename+'.tck and produced '+filename+'.nii mask')
            elif os.path.isfile(filename+'.tck'):
                logging.info(filename+'.tck already exists')
                
            #produce binary .nii mask
            if os.path.isfile(filename+'.tck') and not os.path.isfile(filename+'.nii'):
                logging.info('Producing binary .nii mask')
                #reference image is required for tckmap, so let's specify where we expect to find the dwi image
                dwi_template = '/Volumes/Venus/Kirton_Diffusion_Processing/1_Tractoflow_APSP_results/'\
                    +group+'/'+tag+'/Extract_DTI_Shell/'+tag+'__dwi_dti.nii.gz'
                command = 'tckmap '+filename+'.tck '+filename+'.nii -template '+dwi_template
                os.system(command)
    
"""
3 -- Extract mean, sd, streamline count, save to individual list vars
"""

# -- For each tract in tract_order_list, calculate mean/sd/count for each metric
# and add to lists. If either tract mask or measure map does not exist, add 'no tract'
# or 'no map' instead to mark the cause of the missing value.
def calculateMetrics(subject_folder, group, tag):
    
    for tract in tract_order_list:
        
        list_subj.append(tag)
        list_group.append(group)
        list_tract.append(tract)
        
        tract_mask = tract+'.nii'
        
        if os.path.isfile(tract_mask):
            logging.info('Found '+tract_mask+', calculating metrics!')
            for measure in measure_means_list:
                if not measure == 'ndi' and not measure == 'odi':
                    measure_map = '/Volumes/Venus/Kirton_Diffusion_Processing/1_Tractoflow_APSP_results/'\
                        +group+'/'+tag+'/DTI_Metrics/'+tag+'__'+measure+'.nii.gz'
                    if os.path.isfile(measure_map):
                        logging.info('Found '+measure+' map for '+tag+', calculating mean and SD')
                        
                        measure_output = subprocess.run(['mrstats',measure_map,'-mask',tract_mask,'-output','mean','-output','std','-output','count','-ignorezero'], stdout=subprocess.PIPE)
                        
                        measure_output_re = re.compile(r'\d\S*')
                        measure_output_values = measure_output_re.findall(measure_output.stdout.decode('utf-8'))
                        appendMeasures(measure, measure_output_values)
                        del(measure_output_values)
                    else:
                        logging.error('Could not find '+measure+' map for '+tag+', adding na values')
                        measure_output_values = ['no map','no map','no map']
                        appendMeasures(measure, measure_output_values)
                        del(measure_output_values)
        else:
            logging.error('Could not find tract mask: '+tract_mask+' for '+tag+', adding na values')
            for measure in measure_means_list:
                measure_output_values = ['no tract','no tract','no tract']
                appendMeasures(measure, measure_output_values)
                del(measure_output_values)

# -- Add measures calculated above to relevant lists (essentially a switch case
# function replacement)
def appendMeasures(measure, values):
    
    if measure in measure_means_list:
        if measure == 'fa':
            list_FA_mean.append(values[0])
            list_FA_std.append(values[1])
            list_FA_count.append(values[2])
        elif measure == 'md':
            list_MD_mean.append(values[0])
            list_MD_std.append(values[1])
            list_MD_count.append(values[2])
        elif measure == 'ad':
            list_AD_mean.append(values[0])
            list_AD_std.append(values[1])
            list_AD_count.append(values[2])
        elif measure == 'rd':
            list_RD_mean.append(values[0])
            list_RD_std.append(values[1])
            list_RD_count.append(values[2])
    else:
        logging.error('Measure string not in measure_means_list')

"""
VARIABLES THAT CONTROL THIS SCRIPT
"""
# which order to process groups in?
group_order_list = ['TDC','AIS_L','AIS_R','PVI_L','PVI_R']
# which tract file names to find means for?
tract_order_list = ['AF_L_m','AF_R_m','UF_L_m','UF_R_m']
# which measure maps to find and record means for (per tract)?
measure_means_list = ['fa','md','ad','rd']
# order of metrics output by mrstats (used in calculateMetrics)
metrics_order = ['mean','std','count']

"""
Further development ideas:
    
Along tract profiling is possible, see Tractometry_draft_commands.py or ask Helen eventually

Can visualize along-tract streamline points in mrview to validate that I'm doing what I want!
"""
 
def main():

    #Determine which folder of data RecoX outputs to process
    dir_parent = getParentFolder() #current hard-coded for testing

    for group in group_order_list:
        
        dir_group = dir_parent+'/'+group
        # make a list of all subject folders in the group directory
        subject_list = getSubjectList(dir_group)
        
        for subject_folder in subject_list:
            
            group, tag = getSubjectTag(subject_folder)
            logging.info('Processing '+tag)
            
            # --- 1 --- Convert trk files to tck files and produce binary .nii mask
            logging.info('Step 1: Trk conversion')
            #change working directory to tracts folder, so masks are saved in the right place
            os.chdir(subject_folder+'/1_recox_tracts/')
            convertAndMaskTrks(subject_folder+'/1_recox_tracts/', group, tag)

            # --- 2 --- Build lists up with measure means
            logging.info('Step 2: Extracting measure means')
            ### functions below: still to be finished.
            calculateMetrics(subject_folder, group, tag)

    # --- 3 --- Create dataframe
    logging.info('Step 3: Creating a dataframe with all measure means')
    dataframe_dict = {'Group':list_group,'Subject':list_subj,'Tract':list_tract,'FA':list_FA_mean,\
                      'MD':list_MD_mean,'AD':list_AD_mean,'RD':list_RD_mean}
    dataframe = pd.DataFrame(dataframe_dict)
            
    # --- 4 --- Save dataframe
    csv_save = dir_parent+'/tractometry_'+str(date.today())+'.csv'
    if os.path.isfile(csv_save):
        os.remove(csv_save)
    dataframe.to_csv(csv_save)
    logging.info('Script completed! Results saved at: '+csv_save)

if __name__ == '__main__':
    #Initialize empty lists
    list_subj = list()
    list_group = list()
    list_tract = list()
    list_FA_mean = list()
    list_MD_mean = list()
    list_RD_mean = list()
    list_AD_mean = list()
    list_FA_std = list()
    list_MD_std = list()
    list_RD_std = list()
    list_AD_std = list()
    list_FA_count = list()
    list_MD_count = list()
    list_RD_count = list()
    list_AD_count = list()
    main()
