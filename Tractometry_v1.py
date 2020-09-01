#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug 26 12:25:28 2020

@author: Bryce
"""

# options to extract stats from RecoX tracts - notes Aug 26

"""
Note that before we do this, we'll need to convert RecoX trk files back to tck files, I guess..
"""

"""
Extract tract means
"""
tcksample tract.tck FA.nii.gz FA.csv -stat_tck mean #stat_tck opts: mean,median,min,max
# FA.nii.gz = measure map from which to pull stats
# FA.csv = file to save the values, not sure how they're organized

"""
Along tract profiling - Helen has definitely done, can ask her.
"""
# 1: re-sample the streamlines at equivalent locations along the tract of interest,
# by 'cutting' them up according to a set of uniformly-spaced planes.
tckresample tract.tck -line 20 1,2,3 4,5,10 CST_resampled.tck
# So to do this, we need to draw a 2D shape upon which to 'slice' the tract.
# In this example the resample is a line from (x,y,z) to (x,y,z) in 'scanner coordinates'
# We can also use an art with (start) (midpoint) (end) coords to resample a curved tract.
# I will need to test or google how these coordinates actually work. Like just pull the
# coordinates from mrview?

# Other example FROM HELEN here: https://community.mrtrix.org/t/tckresample-and-tcksample-for-along-the-tract-statistics/1368
# sampling the genu: tckresample genu.tck -arc 20 -18,54,2 0,28,2 18,54,2 genu_samples.tck -nthreads 0
##### 'SCANNER COORDINATES' are reported in MRVIEW as 'POSITION [x y z]mm'

# 2: sample whatever scalar map of interest using the resampled streamlines
tcksample CST_resampled.tck FA.mif FA_values.txt
# This will produce a text with all sampled FA values for a given streamline in a row,
# each streamline has its own row.

"""
Can visualize along-tract streamline points in mrview to validate that I'm doing what I want!
"""

def main():
    """
    put the script workflow here
    """

if __name__ == '__main__':
    main()
