#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul 16 10:02:10 2020

@author: Bryce

----- Usage ------

Perform RecoX tractography on a data folder, given a set of atlas subjects
(Sept 2020, probably 5 TDC atlas subjects I have built AF and UFs for).

python RecobundlesX_tractography_v#.py
 - change dir_data and dir_RecoX below as needed before running this script

----- Versions -----
1: the shell commands are included as rough comments that I used when first trying out recobundlex. More importantly, the loop below is a test for 5 AIS pxs, pointing to
atlas tracts from the Rheault Zenodo example (5 mystery subjects, all kinds of tracts)

2: RecobundlesX command and the relevant config file were modified to allow me to refine resultant tracts

3: script expanded to now process all subjects in data dir (Tractoflow_APSP_results)

4: modded parameters not doing well. Tested in 9 participants (3 per group) and returned to default parameters with minimal_vote 0.75,
   this script runs in all participants though, not just the 9.
       - Aug 20: changed minimal vote from 0.75 to 0.5, because TDC tracts had several 0 streamline results
       - Resultant tracts look very good!
       
5: Modified script to accept AIS_R and PVI_R participants, and to process new data from the
   RH_and_extra tractoflow run on ARC (see language work log for details on that sub-cohort)
--------------------
"""

"""
MODULE IMPORTS
"""
import os, re, logging, glob

"""
LOGGING INITIALIZATION
"""
# could change this to save to a file, but keeping output in terminal for now.
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


"""
FUNCTIONS SECTION BELOW
"""
# FUNCTION: for all folders in a directory, if the full path ends with
# a subject tag, add that full path to a list
def getSubjectList(data_dir):
    all_folders = [x[0] for x in os.walk(data_dir)]
    subject_folder_regex = re.compile(r'\d\d-\d\d\d\d\Z') #2 digits, dash, 4 digits at very end of string (\Z)
    subject_folder_list = list()
    for directory in all_folders:
        if subject_folder_regex.search(directory):
            subject_folder_list.append(directory)
    return subject_folder_list

# FUNCTION: input a full folder path, find the subject tag (format: XX-XXXX)
# and return that tag
def getSubjectTag(subject_directory):
    
    #make a regex below which will find one of 3 groups, and a subject tag
    identifier_regex = re.compile(r'(TDC|AIS_L|PVI_L|AIS_R|PVI_R).*(\d\d-\d\d\d\d)')
    info_list = identifier_regex.findall(subject_directory)
    
    #if working as intended, should return a list with group followed by tag
    group = info_list[0][0]
    tag = info_list[0][1]
    
    return group, tag

# FUNCTION: if registration of subject t1 to recox mni template has not been done,
# do it!
def antsRegistration(group, tag, t1, dir_atlas, dir_ants_registrations):
    recox_atlas_template = dir_atlas+'/mni_masked.nii.gz'
    ants_warps = dir_ants_registrations+tag+'_to_mni_'
    ants_affine_mat = ants_warps+'0GenericAffine.mat'
    ants_affine_txt = ants_warps+'0GenericAffine.txt'
    
    logging.info('ANTs registration beginning for: '+group+', '+tag)
    
    if not os.path.isfile(ants_affine_mat):
        command = 'antsRegistrationSyN.sh -d 3 -f '+recox_atlas_template+' -m '+t1+' -o '+ants_warps+' -t a -n 4'
        os.system(command)
        os.system(command)
        
    if not os.path.isfile(ants_affine_txt):
        command = 'ConvertTransformFile 3 '+ants_affine_mat+' '+ants_affine_txt+' --hm --ras'
        os.system(command)
        
    return ants_affine_txt

def executeRecoX(group, tag, tractogram, dir_atlas, affine, dir_recox_tracts):
    
    config = dir_atlas+'bg_recox_config_v4.json'
    dir_tract_templates = dir_atlas+'atlas/*'
    
    logging.info('RecobundlesX beginning for: '+group+', '+tag)
    
    command = 'scil_recognize_multi_bundles.py '+tractogram+' '+config+' '+dir_tract_templates+' '+affine+' --out_dir '+ \
        dir_recox_tracts+' --log_level DEBUG --minimal_vote 0.50 --multi_parameters 18 --tractogram_clustering 10 12 --processes 8 --seeds 0 -f'
    os.system(command)


"""
VARIABLES WHICH CONTROL THIS SCRIPT
"""
#dir_data = '/Volumes/Venus/Kirton_Diffusion_Processing/1_Tractoflow_APSP_results/'
dir_data = '/Volumes/Venus/Kirton_Diffusion_Processing/1_Tractoflow_RH_and_extras/'
dir_RecoX = '/Volumes/Venus/Kirton_Diffusion_Processing/2_RecobundlesX/'

"""
--------------
MAIN CODE BODY
--------------
"""
def main():
    subject_folders_list = getSubjectList(dir_data)
    
    for parent_directory in subject_folders_list:
        
        print(parent_directory)
        group, tag = getSubjectTag(parent_directory)
        logging.info('processing '+parent_directory)
        logging.info(' group found: '+group+', subject tag found: '+tag)
    
        os.chdir(parent_directory)
    
        # Do RecobundlesX below
        
        # Initialize file locations and save directories
        
        ## Subject's files from tractoflow
        subj_t1 = parent_directory+'/Register_T1/'+tag+'__t1_warped.nii.gz'
        subj_dwi_tracking = parent_directory+'/Tracking/'+tag+'__tracking.trk'
        
        # Where to save files: base = dir_RecoX initialized above
        if not os.path.isdir(dir_RecoX):
            os.makedirs(dir_RecoX)
        dir_ants_registrations = dir_RecoX+'4_RecoX_outputs/'+group+'/'+tag+'/0_ants_registrations/'
        if not os.path.isdir(dir_ants_registrations):
            os.makedirs(dir_ants_registrations)
        dir_recox_tracts = dir_RecoX+'4_RecoX_outputs/'+group+'/'+tag+'/1_recox_tracts/'
        if not os.path.isdir(dir_recox_tracts):
            os.makedirs(dir_recox_tracts)
            
        dir_atlas = dir_RecoX+'3_recox_atlas/'
    
        #perform registration, convert generic affine mat to txt
        ants_affine = antsRegistration(group, tag, subj_t1, dir_atlas, dir_ants_registrations)
    
        #try recobundlesX after registration is done
        if glob.glob(dir_recox_tracts+'/*.trk'):
            logging.info('Found trk files for '+group+' '+tag)
        else:
            executeRecoX(group, tag, subj_dwi_tracking, dir_atlas, ants_affine, dir_recox_tracts)

if __name__ == '__main__':
    main()
    
