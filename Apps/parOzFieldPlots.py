"""
Parallel continental-scale field plotting app.

Uses mpi4py.
"""

import sys
import time
import math

import numpy as np
import numpy.ma as ma

import dirTools as dt

import awapIO as aio
import awapRegion as ar

from mpi4py import MPI
# added these two lines below because burnet was using
# tkagg as the default back-end on its compute nodes (!?!?!?)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
from matplotlib import colors as cols
from matplotlib import rc

"""
Set mathtext to match regular label text by default.
This banishes annoying italicised Roman font exponents.
"""
rc('mathtext', default='regular')

"""
Major and minor axes of the WGS84 ellipsoid.
"""
rEquat = 6378137.00
rPolar = 6356752.3142

"""
start Total run time timer.
"""
totalStartTime = time.time()
"""
Process command-line arguments. 
"""
myName = sys.argv[0]
"""
MPI setup.  Number of PEs and myPE
"""
myComm = MPI.COMM_WORLD
numPEs = myComm.Get_size()
myRank = myComm.Get_rank()
rootID = 0

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
regName = jobConfig['parentRegionName']
regType = jobConfig['parentRegionType']
conAUS = ar.Region(ozDict, RegionName=regName, RegionType=regType)

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
Create (safely) the directory tree for output images.  Do this on the root
and sync afterwards.
"""
if myRank == rootID:

    """
    Create--if not yet created--the root of the output image 
    directory tree.  The directory name itself is defined in
    the .conf file supplied to this script.
    """
    dt.safeMakeDir(jobConfig['outputImageRoot'])
    """
    Create Image output directories
    """
    for field in fieldReqs:
        """
        Safe mkdir for destinations of full- and thumbnail-sized images.
        """
        fieldName = jobConfig['fieldTagsToDirName'][field]
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

myComm.Barrier()

"""
Domain decomposition over field requests.  Card-deal
them so that the maximum load imbalance is one field.
"""
numFields = len(fieldReqs)
quotient = numFields / numPEs
remainder = numFields % numPEs
if remainder == 0:
    myStart = myRank * quotient
    myStop = myStart + quotient
    myFieldReqs = fieldReqs[myStart:myStop]
else:
    print myName,':: Number of requested fields must be an integral number of numPEs.'
    sys.exit()

"""
Loop over requested fields list fieldReqs[:]
"""
readFileTimes = []
baseMapTimes = []
meshGridTimes = []
shapeFileTimes = []
pColorTimes = []
saveFullResFileTimes = []
saveThumbnailFileTimes = []
noBackground = True

for field in myFieldReqs:
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
    Set thumbnail- and full-res image directories for this field.
    """
    outputDir = jobConfig['outputImageRoot'] + '/' + fieldName
    thumbnailImDir = outputDir + '/Thumbnail' 
    fullImDir = outputDir + '/Full' 

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
            startTime = time.time()
            fieldData = aio.readAWAP_flt(fieldDict)
            readFileTimes.append(time.time() - startTime)
            
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

            startTime = time.time()
            if noBackground:
                mOz = Basemap(llcrnrlon=conAUS.minLon-westDisp, 
                              llcrnrlat=conAUS.minLat,
                              urcrnrlon=conAUS.maxLon, 
                              urcrnrlat=conAUS.maxLat+northDisp,
                              rsphere=(rEquat,rPolar), anchor='C', resolution='f',
                              area_thresh=1000.,projection='lcc',
                              lat_1=trueLat1,lat_2=trueLat2,lat_0=centerLat,
                              lon_0=centerLon)

                noBackground = False
                
            baseMapTimes.append(time.time() - startTime)
            
            """
            Read in the AWAP CONAUS shapefile information.
            """
            startTime = time.time()
            mOzShapes = mOz.readshapefile(jobConfig['shapeFile'], 
                                          'scalerank', drawbounds=True)
            shapeFileTimes.append(time.time() - startTime)
            """
            Compute x,y coordinates in map projection; shift cell-center lat/lon 
            values to ULC values for use with matplotlib's pcolor() function.
            """
            startTime = time.time()
            x, y = mOz(*np.meshgrid(conAUS.lons-0.5*conAUS.dLon, 
                                    conAUS.lats+0.5*conAUS.dLat))            
            meshGridTimes.append(time.time() - startTime)

            startTime = time.time()
            im = mOz.pcolormesh(x, y, fieldData, cmap=cMap)
            pColorTimes.append(time.time() - startTime)
            plt.clim(vmin=minVal, vmax=maxVal)
            """
            Save thumbnail as a .jpeg file.
            """
            tnFile = thumbnailImDir + '/' + fn + '.jpeg'
            tnFig = plt.gcf()
            tnFig.set_size_inches(1.38,1.14)
            startTime = time.time()
            plt.savefig(tnFile, bbox_inches='tight', pad_inches=0.02, dpi=150)
            saveThumbnailFileTimes.append(time.time() - startTime)
            tnFig.set_size_inches(5.25,4.5)

            """
            Add in color bar (if desired).
            """
            if jobConfig['DisplayColorBarOnFR']:
                cbar = mOz.colorbar(im,"right", size="3%", pad="2%")
                cbar.ax.tick_params(axis='y', direction='out', labelsize=8)
                cbar.set_label(plotPars[field]['cbarCaption'], size=8)

            """
            Add Labels for field/units, time period, region name.
            """
            xRange = x.max() - x.min()
            yRange = y.max() - y.min()
            """
            Date label.
            """
            plotDateRange = aio.getDateRange(fn)
            xDate = x.max()
            yDate = y.min()
            plt.text(xDate, yDate, plotDateRange, ha='right', va='top', 
                     family='monospace', fontsize=8)
            """
            Title string
            """
            plotTitle = plotPars[field]['plotTitle']
            """
            If no colour bar, append units to title.
            """
            if not jobConfig['DisplayColorBarOnFR']:
                plotTitle += ' ' + plotPars[field]['cbarCaption']

            xTitle = x.min()
            yTitle = y.max()
            plt.text(xTitle, yTitle, plotTitle, ha='left', va='bottom', fontsize=8)
            
            """
            Region Name
            """
            if jobConfig['DisplayRegionNameOnFR']:
                xRegLabel = x.min()
                yRegLabel = y.min()
                if jobConfig['DisplayRegionTypeOnFR']:
                    regLabel = conAUS.regionType + ':  ' + conAUS.name 
                else:
                    regLabel = conAUS.name

                plt.text(xRegLabel, yRegLabel, regLabel, ha='left', va='top', fontsize=8)

            """
            Save full plot as a .jpeg file.
            """
            frFile = fullImDir + '/' + fn + '.jpeg'
            startTime = time.time()
            plt.savefig(frFile, bbox_inches='tight', pad_inches=0.1, dpi=300)
            saveFullResFileTimes.append(time.time() - startTime)
            plt.close()


"""
Print out the profile:
"""
print myName,':: myRank = ',myRank,':: Total Run TIme = ',time.time() - totalStartTime,' s.'
avgRFTime = sum(readFileTimes) / float(len(readFileTimes))
print myName,':: myRank = ',myRank,':: Total Read File Time = ',sum(readFileTimes),' s.'
print myName,':: myRank = ',myRank,':: Number of Read File Operations = ',len(readFileTimes),' with time/op of ',avgRFTime,' s.'
print myName,':: myRank = ',myRank,':: Total BaseMap TIme = ',sum(baseMapTimes),' s.'
avgBMTime = sum(baseMapTimes) / float(len(baseMapTimes))
print myName,':: myRank = ',myRank,':: Number of BaseMap Operations = ',len(baseMapTimes),' with time/op of ',avgBMTime,' s.'
print myName,':: myRank = ',myRank,':: Total shapeFile read onto basemap Time = ',sum(shapeFileTimes),' s.'
avgShFTime = sum(shapeFileTimes) / float(len(shapeFileTimes))
print myName,':: myRank = ',myRank,':: Number of shapeFile Operations = ',len(shapeFileTimes),' with time/op of ',avgShFTime,' s.'
print myName,':: myRank = ',myRank,':: Total np.meshgrid TIme = ',sum(meshGridTimes),' s.'
avgMGTime = sum(meshGridTimes) / float(len(meshGridTimes))
print myName,':: myRank = ',myRank,':: Number of meshgrid Operations = ',len(meshGridTimes),' with time/op of ',avgMGTime,' s.'
print myName,':: myRank = ',myRank,':: Total bmap.pcolormesh() Times = ',sum(pColorTimes),' s.'
avgPCTime = sum(pColorTimes) / float(len(pColorTimes))
print myName,':: myRank = ',myRank,':: Number of bmap.pcolormesh() Operations = ',len(pColorTimes),' with time/op of ',avgPCTime,' s.'
print myName,':: myRank = ',myRank,':: Total save thumbnail image file time = ',sum(saveThumbnailFileTimes),' s.'
avgSTnFTime = sum(saveThumbnailFileTimes) / float(len(saveThumbnailFileTimes))
print myName,':: myRank = ',myRank,':: Number of saveFile Operations = ',len(saveThumbnailFileTimes),' with time/op of ',avgSTnFTime,' s.'
print myName,':: myRank = ',myRank,':: Total save full-res image file time = ',sum(saveFullResFileTimes),' s.'
avgSFRFTime = sum(saveFullResFileTimes) / float(len(saveFullResFileTimes))
print myName,':: myRank = ',myRank,':: Number of saveFile Operations = ',len(saveFullResFileTimes),' with time/op of ',avgSFRFTime,' s.'
sys.stdout.flush()

