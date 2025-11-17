"""
Windowed PDF builder for BIOS2 output.  Uses DataCube class.
"""
import sys
import math
import time

import numpy as np
import numpy.ma as ma

import matplotlib.pyplot as plt

import awapIO as aio
import dataCube as dc

def compute_KLD(p, q, dx):
    """
    Compute classic Kullback-Leibler Divergence from two
    densities that use the same binning scheme.
    Elegant version doesn't work--don't know why.
    quo = np.divide(p, q, out=np.zeros_like(p), where=q!=0)
    log_quo = np.log2(quo, out=np.zeros_like(quo), where=quo!=0)
    kld = np.dot(p, log_quo) * dx
    """
    if p.size != q.size:
        print 'compute_KLD():: FATAL--p and q size mismatch:  '
        print 'compute_KLD():: p.size = ',p.size
        print 'compute_KLD():: q.size = ',q.size
        sys.exit()
    kld = 0.
    for i in range(0, p.size):
        if (p[i] <= 0.) or (q[i] <= 0.):
            continue
        else:
            kld += p[i] * np.log2(p[i] / q[i]) * dx
    return kld
        
my_name = 'pdfs-From-DataCubes.py'

usage = 'python %s ' % my_name
if len(sys.argv) < 3:
    print usage
    sys.exit()

data_root = sys.argv[1]
field_name = sys.argv[2]
window_years = 30

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

    num_times = season_cubes[season].ntimes
    num_years = num_times / 3
    start_year = int(str(season_cubes[season].start_date)[0:4])
    end_year = int(str(season_cubes[season].end_date)[0:4])

    print 'Full sample for %s covers years %d-%d.' % (season, start_year, end_year)
    sample_min = sample.min()
    sample_max = sample.max()
    print 'Sample shape = ',sample.shape
    print 'Minimum value in full sample = ',sample_min
    print 'Maximum value in full sample = ',sample_max

    """
    This is a lucid way of solving the strided sampling problem.
    It probably can be sped up...

    num_locs is the number of locations for which valid sample 
    timeseries exist.

    sample is collapsed into 1D with data lexicographically sorted 
    by location--collapsed lat/lon--and time.  

    Reshape sample as a 2D array with the time index as the fastest-
    varying index.  Then, just do some strided slicing in a loop to
    extract the temporal windows for the whole domain.

    Each temporal window is fed into np.histogram() with a fixed 
    set of bounding values and number of bins.  This will make it
    easy to create raster plots of the time-evolving density.
    """
    num_locs = sample.size / num_times
    samp2D = np.reshape(sample, (num_locs, num_times))
    print 'Shape of samp2D = ',samp2D.shape
    win_size = 90
    win_slide = 3 
    num_wins = 1 + (num_times - win_size) / 3

    num_bins = 200

    print 'Building histogram slices for field %s and season %s' % (field_name, season)
    histart = time.time()

    """
    Set up ordinate and abcissa slices for tdpdf.
    """
    tdpdf_y = np.ndarray((num_wins, num_bins), dtype='float64')
    tdpdf_x = np.ndarray((num_wins, num_bins+1), dtype='float64')

    for win in range(0, num_wins):
        offset = win_slide * win
        start = offset
        stop = offset + win_size
        win_sample = samp2D[:,start:stop]

        y,x = np.histogram(win_sample, bins=num_bins, range=(sample_min, sample_max), density=True)
        tdpdf_y[win,:] = y
        tdpdf_x[win,:] = x

    histime = time.time() - histart
    
    print 'Time to build tdpdf for field %s and season %s = %s sec' % (field_name, season, histime)
    print 'Shape of density values = ',tdpdf_y.shape
    print 'Shape of bin edge array = ',tdpdf_x.shape

    num_pdf_slices = tdpdf_x.shape[0]
    first_pdf_year = end_year - num_pdf_slices + 1
    last_pdf_year = end_year

    time_axis = np.linspace(first_pdf_year, last_pdf_year, num_pdf_slices)
    print 'season = ',season,' time_axis = ',time_axis
    bin_edges = tdpdf_x[0,:-1]
    print 'season = ',season,' bin_edges = ',bin_edges

    X,Y = np.meshgrid(time_axis, bin_edges)

    plt.figure(facecolor="white")
    plt.pcolormesh(X, Y, tdpdf_y.transpose())
    plt.autoscale(enable=True, axis='x', tight=True)
    plt.autoscale(enable=True, axis='y', tight=True)
    title = '30-Year Windowed PDFs (' + field_name + ')'
    subtitle = season.upper() + ' ' + str(start_year) + '-' + str(end_year) + ' (' + str(num_bins) + ' bins)'
    title = title + '\n' + subtitle
    plt.title(title)
    plt.xlabel('Final Year of 30-Year Sampling Window')
    plt.ylabel(field_name)
    cbar = plt.colorbar()
    cbar.set_label('Probability Density')
    """
    plt.show()
    """
    output_file = 'tdpdf_' + field_name + '_' + str(start_year) + '-' + str(end_year) + '_' + season + '_200_bins' + '.png'
    plt.savefig(output_file)

    """
    Code currently commented out due to persistent NaN problem.
    Given the density's history, we can now compute time-shifted
    Kullback-Leibler divergences.

    Given the uniform binning, compute the bin_width.  Also, 
    create the KLD array.
    """
    bin_width = bin_edges[1] - bin_edges[0]
    kld_values = np.zeros((num_wins, num_wins), dtype='float64')
    tstart_kld = time.time()
    print 'Season = ',season,' Minimum tdpdf value = ',tdpdf_y.min()
    print 'Season = ',season,' Maximum tdpdf value = ',tdpdf_y.max()
    for i in range(0, num_wins):
        p = tdpdf_y[i,:]
        p = (p + 1.e-8) / (1. + p.size * 1.e-8)
        for j in range(0, num_wins):
            q = tdpdf_y[j,:]
            kld_values[i, j] = compute_KLD(p, q, bin_width)

    print 'Total time to compute time-shifted KLD field = ',time.time()-tstart_kld,' sec.'
    print 'season = ',season,' min(kld) = ',kld_values.min(),' max(kld) = ',kld_values.max()

    X,Y = np.meshgrid(time_axis, time_axis)

    plt.figure(facecolor="white")
    plt.pcolormesh(X, Y, kld_values.transpose())
    plt.autoscale(enable=True, axis='x', tight=True)
    plt.autoscale(enable=True, axis='y', tight=True)
    title = 'Time-Shifted Kullback-Leibler Divergence (' + field_name + ')'
    subtitle = season.upper() + ' ' + str(start_year) + '-' + str(end_year) + ' (' + str(num_bins) + ' bins)'
    title = title + '\n' + subtitle
    plt.title(title)
    plt.xlabel('Final Year of 30-Year p-Sampling Window')
    plt.ylabel('Final Year of 30-Year q-Sampling Window')
    cbar = plt.colorbar()
    cbar.set_label('$D_{KL}(p||q)$ (bits)')
    output_file = 'ts_kld_' + field_name + '_' + str(start_year) + '-' + str(end_year) + '_' + season + '_200_bins' + '.png'
    plt.savefig(output_file)

    

    
