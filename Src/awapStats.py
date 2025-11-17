"""
Computes spatiotemporal statistics for AWAP spatially masked data.
Time-dependent data are from collections of AWAP .flt format files
and thus thes operations involve both file input and computation.
"""

import sys
import os

import numpy as np
import numpy.ma as ma

import awapIO as aio

def computeContinentalAverageTimeseries(FileList, Directory=None):
    """
    Compute a timeseries of continental averages from a time-ordered FileList.
    
    N.B.:  The entries in FileList are filename stems; that is, they are stripped
    of the AWAP .flt or .hdr extensions.

    Parameters
    ----------
    FileList : list
        List of chronologically-ordered input data files.
    Directory : string
        Location of data files; if None specified uses current working directory.
    """
    
    """
    Change working directory (if supplied), otherwise input files from current
    working directory.
    """
    if Directory is not None:
        os.chdir(Directory)

    numTimes = len(FileList)
    if numTimes == 0:
        print '::  Empty list, FileList = ', FileList, '.  Exiting.'
        sys.exit()
    
    """
    Creat numpy arrays to hold timeseries.  For now, return time coordinate as
    an integer in YYYYMMDD format because it is trivial to take off of the file
    name.  Both arrays are native floating-point.
    """
    times = np.ndarray((numTimes))
    averages = np.ndarray((numTimes))
    
    """
    Input header from first file.  Big--but legitimate--assumption:  this header
    is valid for all subsequent files; that is, the supplied FileList are self-
    consistent in domain size and layout.
    """
    hdrFile = FileList[0] + aio.headerFilenameExt
    headerDict = aio.readAWAP_hdr(hdrFile)
    
    """
    Compute (unmasked) area weights from the information supplied in headerDict.
    This weight field will be used in conjunction with masked physical variable
    fields to compute masked area-weighted averages.
    """
    areaWeights = aio.getAreaWeights(headerDict)
    
    """
    Process the files, computing a timeseries masked area-weighted averages.
    """
    timeInd = 0
    for file in FileList:
        fltFile = file + aio.floatFilenameExt
        times[timeInd] = aio.getJulianDate(file)
        fieldSlice = aio.readAWAP_flt(headerDict, fltFile)
        averages[timeInd] = ma.average(fieldSlice, weights=areaWeights)
        timeInd += 1
    
    return times, averages
