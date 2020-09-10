import os, sys, glob
import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

"""
- USAGE -

Call script and input bin, subject, and tract to edit, a tckgen command will be run including the seed, all and, and all not rois in the folder.
The resultant tract will be given a name listing how many and and not rois were used

There are two modes for this script:
    
    1 - initialize the search for a tract, which creates a directory for me to save ROIs in
        "Mrtrix_manual_tractography.py AIS_L 01-1021 L_AF intiialize"
        Creates L_AF folder at .../Tractoflow_APSP_results/2_RecobundlesX/AIS_L/01-1021/2_manual_searches/L_AF/
        
    2 - produce a tract file (.tck) using all rois present in L_AF folder
        "Mrtrix_manual_tractography.py AIS_L 01-1021 L_AF"
        
      - note that this will ask you to manually input the # of streamlines you want to select (I found I wanted to change this often in practice)
     
- VERSIONS -

v1: Works as described above
    
"""

input = sys.argv[1:]
bin = input[0]
subject = input[1]
tract = input[2]

logging.info("...the inputs sent to script were bin: "+bin+' subject: '+subject+' tract: '+tract)

subject_data_dir = '/Volumes/Venus/Kirton_Diffusion_Processing/1_Tractoflow_APSP_results/'+bin+'/'+subject+'/Extract_DTI_Shell/'
subject_dwi = subject_data_dir+subject+'__dwi_dti.nii.gz'
subject_rgb = '/Volumes/Venus/Kirton_Diffusion_Processing/1_Tractoflow_APSP_results/'+bin+'/'+subject+'/DTI_Metrics/'+subject+'__rgb.nii.gz'
subject_bval = subject_data_dir+subject+'__bval_dti'
subject_bvec = subject_data_dir+subject+'__bvec_dti'

subject_atlas_dir = '/Volumes/Venus/RecobundlesX/1_Bryce_manual_tractography/'+bin+'/'+subject+'/'
tract_dir = subject_atlas_dir+'/'+tract+'/'

if len(input) > 3:
    stage = input[3]
    if stage == 'initialize':
        os.makedirs(tract_dir, exist_ok = True)
        command = 'mrview '+subject_dwi+' -overlay.load '+subject_rgb+' &'
        os.system(command)
    else:
        logging.error('looks like you added a stage but the input does not match initialize')
else:
    os.chdir(tract_dir)
    
    # find seed roi
    seed_roi = glob.glob('*seed*.mif')
    and_roi_list = glob.glob('*and*.mif')
    not_roi_list = glob.glob('*not*.mif')
    
    tract_output = tract_dir+subject+'_'+tract+'_'+str(len(and_roi_list))+'and_'+str(len(not_roi_list))+'not.tck'
    command = 'tckgen '+subject_dwi+' '+tract_output+' -algorithm Tensor_Prob -fslgrad '+subject_bvec+' '+subject_bval+' -select 20000 -seed_image '+seed_roi[0]+' -force'
    
    for roi in and_roi_list:
        command = command+' -include '+roi
        
    for roi in not_roi_list:
        command = command+' -exclude '+roi
        
    print(command)
    os.system(command)