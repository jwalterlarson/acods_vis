"""
PDF builder for BIOS2 output.  Uses DataCube class.
"""
import sys
import math
import time

import numpy as np
import numpy.ma as ma

import matplotlib.pyplot as plt

import awapIO as aio
import dataCube as dc

my_name = 'pdfs-From-DataCubes.py'

usage = 'python %s ' % my_name
if len(sys.argv) < 3:
    print usage
    sys.exit()

data_root = sys.argv[1]
field_name = sys.argv[2]

"""
Hard-wire the rest for now until we get kwargs implemented
at the command line.
"""

sample_type = 'mth'
seasons = aio.SeasonAbbrs

"""
Build seasonal DataCubes from input data.
"""
season_cubes = {}
print '%s:: Building DataCubes for variable %s...' % (my_name, field_name)
tstart = time.time()
for season in seasons:
    print 'Ingest for season %s...' % season
    ts = time.time()
    season_cubes[season] = dc.DataCube(data_root, field_name, sample_type,
                                       CycleFilter=season)
    print 'Ingest of %d files for season %s completed in %s sec.' % (season_cubes[season].ntimes,
                                                                     season, 
                                                                     time.time() - ts)

print 'Ingest for all seasons of field %s completed in %s sec.' % (field_name, 
                                                                   time.time() - tstart)
for season in seasons:
    print 'source directory for season ',season,' = ',season_cubes[season].source_dir
    print 'source files for season ',season,' = ',season_cubes[season].source_files

"""
Processing of masked data to obtain pdfs.  
First, the overall, whole-sample pdfs'
"""
full_pdfs = {}
for season in seasons:
    sample = season_cubes[season].data[~season_cubes[season].data.mask]
    print 'Dimensions of unmasked data for season %s = ' % season, sample.shape

    """
    Rescale water fields from MKS to cgs units.
    """
    if field_name in ['FWDis', 'FWE', 'FWPrec', 'FWPt', 'FWRun', 
                      'FWSoil', 'FWTra', 'FWwc']:
        sample = sample * 1000.

    full_pdfs[season] = np.histogram(sample, bins='scott', density=True)
    
    num_years = season_cubes[season].ntimes / 3
    start_year = int(str(season_cubes[season].start_date)[0:4])
    end_year = int(str(season_cubes[season].end_date)[0:4])

    print 'Full sample for %s covers years %d-%d.' % (season, start_year, end_year)
    print 'Minimum value in sample = ',sample.min()
    print 'Maximum value in sample = ',sample.max()
    print 'Plotting %s seasonal density for %s...' %(season, field_name)
    bins = full_pdfs[season][1]
    vals = full_pdfs[season][0]
    print 'Number of bins for %s grand pdf = %d' % (season, vals.size)

    """
    Plot the Grand PDF.
    """
    plt.figure(facecolor="white")
    n, bins, patches = plt.hist(sample, bins, normed=1, histtype='stepfilled', color='c')
    title = 'Spatiotemporally Sampled ' + field_name + ' PDF'
    subtitle = season.upper() + ' years ' + str(start_year) + '-' + str(end_year) + ' Scott\'s Rule (' + str(vals.size) + ' bins)'
    title = title + '\n' + subtitle
    plt.title(title)
    plt.ylabel('Probability Density')
    plt.xlabel(field_name)
    output_file = 'grand_pdf_' + field_name + '_' + str(start_year) + '-' + str(end_year) + '_' + season+ '_scott' + '.png'
    plt.savefig(output_file)
    #plt.show()
    




