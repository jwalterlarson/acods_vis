''' buildDataCube.py -- Builds a 3-D (lat/lon/time) univariate data cube.

    For now merely test on a fixed field of BIOS2 output stored on the Bowen
    cloud but mounted on pearcey.

'''
import sys
import math
import time

import numpy as np
import numpy.ma as ma

import awapIO as aio

timeSamplingInterval = 'mth'
start_date = 19000131
end_date = 20141231

data_root = '/OSM/CBR/OA_GLOBALCABLE/work/BIOS-2.1-160521/Oz/output/Run22b_RisingCO2/OutputTS/flthdr'
field_name = 'Tabar'
field_dir = data_root + '/' + field_name

tstart_find = time.time()
fieldDataFiles = aio.getFileList(field_dir)
monthly_files = aio.filterBySamplingInterval(fieldDataFiles, 'mth')
print 'number of monthly_files = ',len(monthly_files)
print 'earliest date = ',aio.getEarliestDate(monthly_files)
print 'latest date = ',aio.getLatestDate(monthly_files)
sorted_files = aio.sortByDate(monthly_files)
working_files = aio.filterByDateRange(monthly_files, start_date, end_date)
time_find = time.time() - tstart_find

print 'start_date = ',start_date
print 'end_date = ',end_date
print 'number of files between start and end dates = ',len(working_files)
print 'earliest date = ',aio.getEarliestDate(working_files)
print 'latest date = ',aio.getLatestDate(working_files)
print 'Total time spent building working files list = ',time_find,' sec.'

"""
Open first header file to get description of contents of first float
file.  Operate on the assumption that all other float files will be
laid out identically with this first one.
"""
tstart_ingest = time.time()

header = field_dir + '/' + working_files[0] + '.hdr'

file_layout = aio.readAWAP_hdr(header)
print 'file layout dictionary = ',file_layout

nlats = file_layout['nrows']
nlons = file_layout['ncols']
ntimes = len(working_files)
missing_data_flag = file_layout['nodata_value']

print 'nlats = ',nlats,' nlons = ',nlons,' ntimes = ',ntimes

"""
Create data_cube array.  Since we are reading time slices, set
the time index as the slowest-varying index.  This optimizes
read/load speeds.  Getting the data_cube into a different 
storage order will require a numpy transpose() call.
"""
data_cube = np.ndarray((ntimes, nlats, nlons), dtype='float32')

"""
Read in individual files--which have been chronologically ordered--and
load into the data_cube.
"""
curr_step = 0

time_read = 0.0
time_copy = 0.0
for fn in working_files:

    tstart_read = time.time()
    curr_hdr_file = field_dir + '/' + fn +'.hdr'
    curr_header = aio.readAWAP_hdr(curr_hdr_file)
    data_cube[curr_step, :, :] = aio.readAWAP_flt(curr_header)
    time_read += time.time() - tstart_read
    curr_step += 1
    
time_ingest = time.time() - tstart_ingest

print 'Data cube dimensions before transpose:  ',data_cube.shape
tstart_transpose = time.time()
perm_data_cube = np.transpose(data_cube, (1, 2, 0))
time_transpose = time.time() - tstart_transpose
print 'Data cube dimensions after transpose:  ',perm_data_cube.shape

print 'Total time spent reading + loading working files = ',time_ingest,' sec.'
print 'Total time spent solely on file input = ',time_read,' sec.'
print 'Total time spent solely on data_cube transpose = ',time_transpose,' sec.'

num_samps = 10000
samp_times = np.random.randint(0, ntimes, num_samps, dtype='int') 
samp_lats = np.random.randint(0, nlats, num_samps, dtype='int') 
samp_lons = np.random.randint(0, nlons, num_samps, dtype='int') 
identical = np.ndarray((num_samps), dtype='bool')
diffs = np.ndarray((num_samps), dtype='float32')

identical[:] = (data_cube[samp_times[:], samp_lats[:], samp_lons[:]] == 
                          perm_data_cube[samp_lats[:], samp_lons[:], samp_times[:]])
diffs[:] = data_cube[samp_times[:], samp_lats[:], samp_lons[:]] - perm_data_cube[samp_lats[:], samp_lons[:], samp_times[:]]

print 'Results for ',num_samps,'-sample random check for matches in arrays:  ',identical
print 'Results for ',num_samps,'-sample array element differences:  ',diffs


    

    





  




