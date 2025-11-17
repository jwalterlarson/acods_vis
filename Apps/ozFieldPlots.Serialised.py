import sys
import math

import cProfile

import numpy as np
import numpy.ma as ma

import dirTools as dt

import awapIO as aio
import awapRegion as ar

import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
from matplotlib import colors as cols

"""
Major and minor axes of the WGS84 ellipsoid.
"""
rEquat = 6378137.00
rPolar = 6356752.3142

"""
Process command-line arguments. 
"""
myName = sys.argv[0]
"""
The .conf file supplied as the first command-line
argument.  It contains a number of hard-wired parameter
definitions that will all be pulled in as a dictionary.
"""
jobConfig = {}
execfile(sys.argv[1], jobConfig)

"""
Check readability of input data directory tree.
The directory name is defined in the .conf file
supplied to this script.
"""
if not dt.isReadableDir(jobConfig['inputDataRoot']):
    sys.exit()
"""
Create--if not yet created--the root of the output image 
directory tree.  The directory name itself is defined in
the .conf file supplied to this script.
"""
dt.safeMakeDir(jobConfig['outputImageRoot'])

"""
Get list of field tag requests from the job configuration.
"""
fieldReqs = jobConfig['fieldTags']

"""
Get time sampling intervals list from the job configuration.
"""
timeSamplingIntervals = jobConfig['timeSamplingIntervals']

"""
Get dictionary of renormalisation coefficients from the job
configuration.
"""
renormalisations = jobConfig['fieldTagsToRenormCoeffs']

"""
Read plot parameters file into nested dictionary plotPars.  
Used for all fields.
"""
plotPars = aio.readAWAP_PlotPars(jobConfig['plotParsFile'])

"""
Set up Continental Region for Australia.  Used for all fields.
"""
ozDict = aio.readAWAP_hdr(jobConfig['regionMask'])
conAUS = ar.Region(ozDict, RegionName='CONAUS', RegionType='Continent')

"""
Set map projection parameters for Lambert conformal conic.
"""
projType = 'lcc'
centerLat = 0.5 * (conAUS.maxLat + conAUS.minLat)
centerLon = 0.5 * (conAUS.maxLon + conAUS.minLon)
trueLat1 = -10.
trueLat2 = -40.
"""
If initialised straight from the BoM LCC parameters, the basemap is shifted 
to the ESE of where it should lie.  I don't know why!  Introduce fudge factors 
westDisp and northDisp to shift the domain to taste.
"""
westDisp = 7.
northDisp = 2.

"""
Loop over requested fields list fieldReqs[:]
"""
for field in fieldReqs:
    """
    Set data input directory and image output directories.
    """
    fieldName = jobConfig['fieldTagsToDirName'][field]
    inputDir = jobConfig['inputDataRoot'] + '/' + fieldName
    """
    Is inputDir a valid directory?
    """
    if not dt.isReadableDir(inputDir):
        print myName,':: FATAL--Directory',inputDir,' is invalid.'
        sys.exit()
    """
    Safe mkdir for destinations of full- and thumbnail-sized images.
    """
    if dt.isWriteableDirectory(jobConfig['outputImageRoot']):
        outputDir = jobConfig['outputImageRoot'] + '/' + fieldName
        dt.safeMakeDir(outputDir)
    else:
        print myName,':: Directory ',jobCofig['outputImageRoot'],' not writeable.'
        sys.exit()
    thumbnailImDir = outputDir + '/Thumbnail' 
    dt.safeMakeDir(thumbnailImDir)
    fullImDir = outputDir + '/Full' 
    dt.safeMakeDir(fullImDir)

    """
    Retrieve list of all of the filename stems (i.e., minus filetype extension) 
    in fieldDataDir.
    """
    fieldDataFiles = aio.getFileList(inputDir)

    """
    Iterate over sampling intervals:
    """
    for ts in timeSamplingIntervals:
        """
        Filter list of filename stems to retrieve files for this time
        sampling strategy only.
        """
        allFiles = aio.filterBySamplingInterval(fieldDataFiles, ts)
        if aio.isPercentileRankField(field):
            sampFiles = [x for x in allFiles if aio.isPercentileRankFile(x)]
        else:
            sampFiles = [x for x in allFiles if not aio.isPercentileRankFile(x)]

        """
        Create colourMap for monthly files.
        """
        cmapName = field + 'Scale'
        colourDict = aio.readAWAP_ColourTable(jobConfig['colourTablePath'],
                                              field)
        cMap = cols.LinearSegmentedColormap(cmapName, colourDict)
        """
        Colourbar range settings.
        """
        minVal = plotPars[field]['minVal']
        maxVal = plotPars[field]['maxVal']

        if field in renormalisations.keys():
            """
            Apply multiplicative renormalisation.
            """
            minVal *= renormalisations[field]
            maxVal *= renormalisations[field]
         
        """
        Loop over monthly aggregate files.
        """
        for fn in sampFiles:
            """
            Read in masked field.
            """
            fieldDataFile = inputDir + '/' + fn + aio.headerFilenameExt
            fieldDict = aio.readAWAP_hdr(fieldDataFile)
            fieldData = aio.readAWAP_flt(fieldDict)
            
            """
            Renormalise field if neccesary.
            """
            if field in renormalisations.keys():
                """
                Apply multiplicative renormalisation.
                """
                fieldData *= renormalisations[field]
                    
            """
            Figure set-up:  Set up figure so that no viewport 
            frame nor axes are visible.
            """
            fig = plt.figure(frameon=False, tight_layout=True)
            ax = plt.axes()
            fig.patch.set_visible(False)
            ax.patch.set_visible(False)
            ax.axis('off')

            """
            Create Basemap with shapefile info on board.
            """
            mOz = Basemap(llcrnrlon=conAUS.minLon-westDisp, 
                          llcrnrlat=conAUS.minLat,
                          urcrnrlon=conAUS.maxLon, 
                          urcrnrlat=conAUS.maxLat+northDisp,
                          rsphere=(rEquat,rPolar), anchor='C', resolution='f',
                          area_thresh=1000.,projection='lcc',
                          lat_1=trueLat1,lat_2=trueLat2,lat_0=centerLat,
                          lon_0=centerLon)
            
            """
            Read in the AWAP CONAUS shapefile information.
            """
            mOzShapes = mOz.readshapefile(jobConfig['shapeFile'], 
                                          'scalerank', drawbounds=True)            
            """ 
            Compute x,y coordinates in map projection; shift cell-center lat/lon 
            values to ULC values for use with matplotlib's pcolor() function.
            """
            x, y = mOz(*np.meshgrid(conAUS.lons-0.5*conAUS.dLon, 
                                    conAUS.lats+0.5*conAUS.dLat))
            
            im = mOz.pcolor(x, y, fieldData, cmap=cMap)
            plt.clim(vmin=minVal, vmax=maxVal)
            """
            Save thumbnail as a .jpeg file.
            """
            tnFile = thumbnailImDir + '/' + fn + '.jpeg'
            tnFig = plt.gcf()
            tnFig.set_size_inches(1.0,0.825)
            plt.savefig(tnFile, bbox_inches='tight', pad_inches=0.02, dpi=100)
            """
            Create Full-Resolution Image with labels, title, and 
            colour bar.
            """
            tnFig.set_size_inches(6.0,4.5)
            """
            Add in color bar.
            """
            cbar = mOz.colorbar(im,"right", size="5%", pad="2%")
            cbar.ax.tick_params(axis='y', direction='out')
            """
            Renormalise precip colour bar tick labels to convert
            units from m/day to mm/day.
            """
            cbar.set_label(plotPars[field]['cbarCaption'])
            plotDateRange = aio.getDateRange(fn)
            
            plotTitle = plotPars[field]['plotTitle'] + (':  ' + 
                                                        plotDateRange)
            plt.title(plotTitle)
            """
            Save full plot as a .jpeg file.
            """
            frFile = fullImDir + '/' + fn + '.jpeg'
            plt.savefig(frFile, bbox_inches='tight', pad_inches=0.1, dpi=300)
            plt.close()
