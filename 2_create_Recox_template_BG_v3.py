"""
PURPOSE:
 - after a set of tracts have been manually segmented in mrtrix from exemplar participants, 
 perform refinements and manual cluster pass/fail steps to produce atlas tract sets ready for use in RecobundlesX.
 
USAGE:

VERSIONS:
- August 19 - v3
 - refining my code to be a push-button solution from manually segmented trk (note not tck) files to recobundlesx atlas tracts
 - v3 complete August 25. All works smoothly. Next version will require an upgrade of how to copy and rename atlas tracts.
     IDEAS:
     - User inputs a list of tracts they want to copy, and names for them?
     - Read from a text file list with this data saved?
     - Make a list in main() and allow user to modify as they like? 
       Or better yet a dict so that the key-value pair is initial and final name elements?


"""

import os, sys, re, glob, logging
from dipy.io.streamline import load_tck, save_tractogram

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def getTractFolder():
    # Just set this directory for the purposes of testing out the full script, saves me some time dragging and dropping
    directory = input('Which folder of tracts to process into atlas tracts? ')
    directory = directory.strip() # remove leading or trailing whitespaces
    return directory

def getSubjectTags():
    # get a list of all unique subject tags in filenames in folder
    tag_list = set()
    for file in os.listdir('.'):
        tag_regex = re.compile('\d\d-\d\d\d\d')
        tag = tag_regex.findall(file)
        if not tag == []:
            if not tag[0] in tag_list:
                tag_list.add(tag[0])
    logging.info('Found data from the following subjects (TDC group assumed): '+str(tag_list))
    
    return tag_list

def t1Fixes(tract_directory):
    
    tag_list = getSubjectTags()
    
    for tag in tag_list:
        # find t1 file, pass through mrtrix, and save in tracts folder
        t1_reference = '/Volumes/Venus/Kirton_Diffusion_Processing/1_Tractoflow_Singleshell/TDC/'+tag+'/Register_T1/'+tag+'__t1_warped.nii.gz'
        t1_reference_fixed = tag+'__t1_warped_trk_reference.nii.gz'
    
        if not os.path.isfile(t1_reference_fixed):
            logging.info('Passing t1 image through mrtrix to get it to work with dipy commands, saved in '+tract_directory)
            command = 'mrconvert '+t1_reference+' '+t1_reference_fixed
            os.system(command)
        else:
            logging.info('T1 reference image already exists for '+tag+', moving on.')

def convertTrks(tract_directory):

    for file in os.listdir(tract_directory):
        if file.endswith(".tck"):
            
            filename = file.split('.')[0]        
            
            tag_regex = re.compile('\d\d-\d\d\d\d')
            tag = tag_regex.findall(filename)[0]
            t1_reference_fixed = tag+'__t1_warped_trk_reference.nii.gz'
            
            if os.path.isfile(filename+'.trk'):
                logging.info(filename+'.trk found, no need to convert tck file.')
            elif not os.path.isfile(filename+'.trk'):
                if os.path.isfile(t1_reference_fixed):
                    logging.info('T1 image found, converting '+file+' to trk.')
                    temp_tck = load_tck(file,reference=t1_reference_fixed,bbox_valid_check=False)
                    trk_save_name = filename+'.trk'
                    save_tractogram(temp_tck,trk_save_name,bbox_valid_check=False)
                else:
                    print(t1_reference_fixed)
                    logging.error('Fixed T1 image not found, conversion not executed.')
                    exit()

def clean_and_downsample():
    command = "for i in *.trk; do echo ${i}; base_name=$(basename ${i}); tag=$(echo $base_name | cut -d'_' -f 1);"+\
        "scil_remove_invalid_streamlines.py --reference ${tag}__t1_warped_trk_reference.nii.gz ${i} ${i/.trk/_valid.trk};"+\
        "scil_remove_similar_streamlines.py ${i/.trk/_valid.trk} 2 downsample/${base_name/.trk/_downsample.trk} -f -v;"+\
        "mv ${i/.trk/_valid.trk} validated/; done"
    os.system(command)


# --- 3 --- find, flip, and register t1 files for all subjects in the folder
def t1FlipRegister(tracts_dir):    
    
    tag_list = getSubjectTags()
    
    for tag in tag_list:
        #fixed t1 reference has already been created in converTrks() function above
        t1_reference_fixed = tag+'__t1_warped_trk_reference.nii.gz'
        t1_reference_flipped = 'flip/'+t1_reference_fixed[:-7]+'_flipped.nii.gz'
    
        if os.path.isfile(t1_reference_fixed) and not os.path.isfile(t1_reference_flipped):
            logging.info('Found t1 reference for: '+tag+', flipping and registering t1')
            command = 'scil_flip_volume.py '+t1_reference_fixed+' '+t1_reference_flipped+' x'
            os.system(command)
            command = 'antsRegistrationSyNQuick.sh -d 3 -f '+t1_reference_fixed+' -m '+t1_reference_flipped+' -t r -o '+tag+'_output_ -n 4'
            os.system(command)
            command = 'mv *output* flip/'
            os.system(command)
        elif os.path.isfile(t1_reference_flipped):
            logging.info('Flipped t1 reference found for: '+tag+', moving on.')

def flipFuseTracts():
    
    command = 'for i in flip/*output*.mat; do echo ${i}; base_name=$(basename ${i}); ConvertTransformFile 3 ${i} flip/${base_name/.mat/.txt} --hm --ras; done'
    os.system(command)
    # smart steps are here onwards, will need to re-evaluate the 4 lines up above to get the antsRegistraion command to output a file of format: "03-3095_output_0GenericAffine.mat"
    command = 'for i in downsample/*.trk; do echo ${i}; base_name=$(basename ${i}); scil_flip_streamlines.py ${i} flip/flip.trk x; tag=$(basename ${base_name} | cut -c1-7); scil_apply_transform_to_tractogram.py flip/flip.trk ${tag}__t1_warped_trk_reference.nii.gz flip/${tag}_output_0GenericAffine.mat flip/${base_name/.trk/_flip.trk} --inverse --remove_invalid; rm flip/flip.trk; done'
    os.system(command)
    
    # 3.5: Fuse tracts
   
    # Currently configured to fuse L with R tracts separately from R with L
    # L tracts
    command = 'for i in downsample/*L*.trk; do echo ${i}; base_name=$(basename ${i}); R_flip=${base_name/L/R}; R_flip=${R_flip/.trk/_flip.trk}; scil_streamlines_math.py concatenate ${i} flip/${R_flip} fuse/fuse.trk; scil_remove_similar_streamlines.py fuse/fuse.trk 1 fuse/${base_name/.trk/_fuse.trk} --avg --processes 1 --min_cluster_size 2 -v; rm fuse/fuse.trk; done'
    os.system(command)
    # R tracts
    command = 'for i in downsample/*R*.trk; do echo ${i}; base_name=$(basename ${i}); L_flip=${base_name/R/L}; L_flip=${L_flip/.trk/_flip.trk}; scil_streamlines_math.py concatenate ${i} flip/${L_flip} fuse/fuse.trk; scil_remove_similar_streamlines.py fuse/fuse.trk 1 fuse/${base_name/.trk/_fuse.trk} --avg --processes 1 --min_cluster_size 2 -v; rm fuse/fuse.trk; done'
    os.system(command)

def tractClusters():
    
    # mkdir manually_clean;
    command = 'for i in fuse/*.trk; do echo ${i}; base_name=$(basename ${i} .trk); scil_compute_qbx.py ${i} 4 manually_clean/${base_name}/; done'
    os.system(command)

def manualClusterChecks():
    
    ready_bool = input('Are you ready to begin manual cluster checks? (y/n) ')
    
    if ready_bool == 'y':
        command = "for i in fuse/*.trk; do echo ${i}; base_name=$(basename ${i} .trk); echo ${base_name}; "+\
        "scil_clean_qbx_clusters.py manually_clean/${base_name}/*.trk manually_clean/${base_name}.trk manually_clean/${base_name}_.trk --min_cluster_size 5; done;"
        os.system(command)
        command = 'rm manually_clean/*_.trk'
        os.system(command)
    elif ready_bool == 'n':
        logging.error('Not ready for manual cluster checks, run this script again when you are ready.')
        exit()

def smoothClean():
    command = 'for i in manually_clean/*.trk; do echo ${i}; base_name=$(basename ${i}); scil_smooth_streamlines.py ${i} smooth_clean/smooth.trk --gaussian 10 -e 0.05; scil_outlier_rejection.py smooth_clean/smooth.trk smooth_clean/${base_name/.trk/_smooth_clean.trk} --alpha 0.5; rm smooth_clean/smooth.trk; done;'
    os.system(command)

def coregisterSmoothedTracts(tract_directory):
    
    tag_list = getSubjectTags()
    mni_template = tract_directory+'/mni_masked.nii.gz'
    
    for tag in tag_list:
        
        t1_reference = tag+'__t1_warped_trk_reference.nii.gz'
        
        if not os.path.isfile('coregistered/'+tag+'_mni_output_0GenericAffine.mat'):
            command = 'antsRegistrationSyNQuick.sh -d 3 -f '+mni_template+' -m '+t1_reference+' -t r -o coregistered/'+tag+'_mni_output_ -n 4'
            os.system(command)
        
    command = 'for i in smooth_clean/*.trk; do echo ${i}; base_name=$(basename ${i}); tag=$(basename ${base_name} | cut -c1-7); scil_apply_transform_to_tractogram.py ${i} '+mni_template+' coregistered/${tag}_mni_output_0GenericAffine.mat coregistered/${base_name/.trk/_coregistered.trk} --remove_invalid --inverse -f; done'
    os.system(command)
        
def renameAtlasTracts():
    #note that this should be adjusted once I need to copy and rename new tracts. Right now it works for my hard-coded L/R AF/UF needs!
    tag_list = getSubjectTags()
    
    i = 0
    for tag in tag_list:
        i += 1
        tag_tracts = glob.glob('coregistered/*'+str(tag)+'*.trk')

        for tract_file in tag_tracts:

            tract_name = tract_file.split('_downsample')[0]
            tract_name = tract_name.split(tag+'_')[1]
            logging.info(tract_file)
            logging.info('Renaming '+tag+' '+tract_name)

            command = 'cp '+tract_file+' final_renamed/subj_'+str(i)+'/'+tract_name+'.trk'
            os.system(command)


def main():
    
    tract_directory = getTractFolder()
    
    os.chdir(tract_directory)
    
    tag_list = getSubjectTags()
    
    # --- 1 --- Pass t1 images through mrtrix to get into the right format to serve as a reference
    if len(glob.glob('*t1*reference.nii.gz')) == len(tag_list):
        logging.info('Found a t1 reference file for each subject tag in '+tract_directory+'. moving on.')
    else:
        logging.info('Passing t1 images through mrtrix for '+str(tag_list))
        t1Fixes(tract_directory)
    
    # --- 2 --- Convert tck to trk files
    if len(glob.glob('*.tck')) == len(glob.glob('*.trk')):
        logging.info('Looks like all .tck files have a matching .trk file, skipping tract conversion.')
    else:
        logging.info('Stepping into tract conversion function!')
        convertTrks(tract_directory)
    
    # --- 3 --- Downsample trk files
    os.makedirs('validated/', exist_ok = True)
    os.makedirs('downsample/', exist_ok = True)
    if len(glob.glob('downsample/*.trk')) == len(glob.glob('*.trk')):
        logging.info('Looks like all .trk files have been downsampled, moving on.')
    else:
        logging.info('Downsampling tracts!')
        clean_and_downsample()
     
    # --- 4 --- Flip t1 images, register flipped to original,
    os.makedirs('flip/', exist_ok = True)
    if len(glob.glob('flip/*.mat')) == len(glob.glob('*t1*.nii.gz')):
        logging.info('Looks like t1 images have been flipped and affine registrations have been calculated, moving on.')
    else:
        logging.info('Flipping and registering t1 images.')
        t1FlipRegister(tract_directory)
        
    # --- 5 --- Flip downsampled trk files, fuse with ipsi-hemisphere tract
    os.makedirs('fuse/', exist_ok = True)
    if len(glob.glob('fuse/*.trk')) == len(glob.glob('downsample/*.trk')):
        logging.info('Looks like downsample/trks have all been flipped and fused, moving on.')
    else:
        logging.info('Flipping and fusing downsample/trk files!')
        flipFuseTracts()
    
    # --- 6 --- Compute clusters for fused tracts, then manually check
    os.makedirs('manually_clean/', exist_ok = True)
    if len(glob.glob('manually_clean/*downsample_fuse/')) == len(glob.glob('fuse/*.trk')):
        logging.info('Looks like clusters have been computed for all fused tracts, moving on.')
    else:
        logging.info('Computing clusters for fuse/*.trk files.')
        tractClusters()
        logging.info('Clusters have been computed, now you''ll need to manually check them.')
        
    if len(glob.glob('manually_clean/*.trk')) == len(glob.glob('manually_clean/*downsample_fuse/')):
        logging.info('All folders have had manual cluster checks performed, moving on.')
    else:
        logging.info('Manual cluster checks to be performed on all tracts in manually_clean/ folder.')
        manualClusterChecks()
    
    # --- 7 --- Smooth and clean the manually checked tracts
    os.makedirs('smooth_clean/', exist_ok = True)
    if len(glob.glob('smooth_clean/*.trk')) == len(glob.glob('manually_clean/*.trk')):
        logging.info('Tracts have been smoothed and cleaned, moving on.')
    else:
        logging.info('Smoothing and cleaning manually checked tracts.')
        smoothClean()
    
    # --- 8 --- Coregister smoothed atlas tracts
    os.makedirs('coregistered/', exist_ok = True)
    if len(glob.glob('coregistered/*.trk')) == len(glob.glob('smooth_clean/*.trk')):
        logging.info('Final atlas tracts have been coregistered to mni!')
    else:
        logging.info('Coregistering smoothed/cleaned atlast tracts to mni template')
        coregisterSmoothedTracts(tract_directory)

    # --- 9 --- Coregister smoothed atlas tracts
    #note that this should be adjusted once I need to copy and rename new tracts. Right now it works for my hard-coded L/R AF/UF needs!
    os.makedirs('final_renamed/', exist_ok = True)
    logging.info('Making coregistered/subj_X folders if they don''t exist.')
    for i in range(1,6):
        os.makedirs('final_renamed/subj_'+str(i), exist_ok = True)
        
    logging.info('Going ahead with the final renaming process (copying L/R AF & UF tracts from coregistered).')
    renameAtlasTracts()
    
if __name__ == '__main__':
    main()
