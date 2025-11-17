''' dataCube.py -- a 3-D (lat/lon/time) univariate data cube.

'''
import sys
import math

import numpy as np
import numpy.ma as ma

import awapIO as aio

class DataCube(object):
    """
    DataCube:  a 3D collection--2D Space-like/1D Time-like--of field data.
    
    The DataCube stores spatiotemporal gridded field data.  The default 
    storage order is (x, y, t) but numpy provides fast transpose mechanisms
    that allow the user to reorder data to any desired storage order.
    """
    
    def __init__(self, DataPath, FieldName, SampleType='mth',
                 StartDate=None, EndDate=None, CycleFilter=None):
        """
        Create a new DataCube instance.
        
        Parameters
        ----------
        
        DataPath : string
            The root directory for a multivariate data collection.
        
        FieldName : string
            Name of field, univariate subdirectory within data collection.
        
        SampleType : string
            Classification filter for types of data files (default 'mth').
        
        StartDate : string or int
            YYYYMMDD-format start date for Cube (default None).
        
        EndDate : string or int
            YYYYMMDD-format end date for Cube (default None).
        
        CycleFilter : string or List
            Seasonal (e.g., 'DJF') or Monthly (e.g., 'Jan') filter.
        
        Returns
        -------
        DataCube
            A DataCube instance.
        """
        
        self.field_name = FieldName
        self.source_dir = DataPath + '/' + FieldName
        

        # Grab all files in source directory.
        all_files = aio.getFileList(self.source_dir)

        
        # Eliminate from all_files files not of the prescribed SampleType.
        sample_files = aio.filterBySamplingInterval(all_files, SampleType)
        
        # Set collection start and end dates based on argument values (or lack thereof).
        first_date = aio.getEarliestDate(sample_files)
        last_date = aio.getLatestDate(sample_files)
        if StartDate is None:
            my_start = first_date
        else:
            my_start = StartDate
        if EndDate is None:
            my_end = last_date
        else:
            my_end = EndDate


        # Filter accordingly by these time bounds.
        sample_files = aio.filterByDateRange(sample_files, my_start,
                                             my_end)
        
        # Sort files chronologically by YYYYMMDD date.
        sample_files = aio.sortByDate(sample_files)
        

        # Filter by portion of seasonal cycle if applicable.
        if CycleFilter is None:
            self.cycle_filter = None
        else:
            if aio.is_a_Month(CycleFilter) or aio.is_a_Season(CycleFilter):
                self.cycle_filter = CycleFilter
                if aio.is_a_Month(CycleFilter):
                    sample_files = aio.filterByMonthName(
                        sample_files, CycleFilter)
                else:
                    sample_files = aio.filterBySeason(
                        sample_files, CycleFilter)
        
        self.sample_files = sample_files
        
        # The seasonal filtering preserves chronological ordering in the List
        # sample_files.  Now, pick off the start and end dates from this list
        # and store them in the instance.
        self.start_date = int(aio.getYMD(sample_files[0]))
        self.end_date = int(aio.getYMD(sample_files[-1]))
        
        # Build a list of time stamps for the ordered file data.
        self.times = [int(aio.getYMD(fn)) for fn in sample_files]
        
        # At this point we have a chronologically-ordered, time-window-restricted,
        # and seasonal-cycle-restricted (if applicable), set of filenames for
        # univariate field data.
        # 
        # Open first header file to get description of contents of first float
        # file.  Operate on the assumption that all other float files will be
        # laid out identically with this first one.
        header = self.source_dir + '/' + sample_files[0] + '.hdr'
        file_layout = aio.readAWAP_hdr(header)
        
        self.nlats = file_layout['nrows']
        self.nlons = file_layout['ncols']
        self.xllcorner = file_layout['xllcorner']
        self.yllcorner = file_layout['yllcorner']
        self.cellsize = file_layout['cellsize']
        self.ntimes = len(sample_files)
        self.missing_data_flag = file_layout['nodata_value']
        self.source_files = sample_files
        
        # Now, correct the earlier stored start/end dates to reflect
        # actual files loaded.
        # 
        # Create data_cube array.  Since we are reading time slices, set
        # the time index as the slowest-varying index.  This optimizes
        # read/load speeds.  Getting the data_cube into a different
        # storage order will require a numpy transpose() call.
        self.data = np.ndarray((self.ntimes, self.nlats, self.nlons),
                               dtype='float32')
        
        # Read in individual files--which have been chronologically ordered--and
        # load into the data_cube.ma
        curr_step = 0
                
        for fn in sample_files:
            curr_hdr_file = self.source_dir + '/' + fn + '.hdr'
            curr_header = aio.readAWAP_hdr(curr_hdr_file)
            self.data[curr_step, :, :] = aio.readAWAP_flt(curr_header)
            curr_step += 1
        
        self.data = np.transpose(self.data, (1, 2, 0))
        self.data = ma.masked_values(self.data, self.missing_data_flag)
    
    def printAttributes(self, PrintTimes=False, PrintFileList=False):
        """
        Pretty print DataCube attributes to stdout.
        
        Parameters
        ----------
        PrintTimes : bool
            Toggle to print out all of the DataCube's time axis values.

        PrintFileList : bool
            Toggle to print out all of the DataCube's filename stems.
        """
        print 80 * '#'
        print 'DataCube instance attributes:'
        print 'Field name = ', self.field_name
        print 'Data Source Directory:  ', self.source_dir
        print 'Cycle filtering:  ', self.cycle_filter
        print 20 * '-', ' DataCube Spatiotemporal domain ', 20 * '-'
        print 'Number of Latitudes:  ', self.nlats
        print 'Number of Longitudes:  ', self.nlons
        print 'DataCube Start Date:  ', self.start_date
        print 'DataCube End Date:  ', self.end_date
        print 'Number of time samples:  ', self.ntimes
        print 'Lat/Lon grid point spacing (degrees):  ', self.cellsize
        print 'Lower-left domain starting point (Lat,Lon) = (', (self.xllcorner,
                                                                 self.yllcorner), ')'
        print 'Missing data flag value:  ', self.missing_data_flag
        if(PrintTimes):
            print 20 * '-', ' YYYYMMDD time stamps ', 20 * '-'
            print self.times
        
        if(PrintFileList):
            print 20 * '-', ' List of filename stems for source files ', 20 * '-'
            print self.source_files
        
        print 80 * '#'
