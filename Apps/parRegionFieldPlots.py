"""
Parallel regional-scale field plotting app.

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
Create--if not yet created--the root of the output image 
directory tree.  The directory name itself is defined in
the .conf file supplied to this script.  Do the directory
creation *only* on the root process, and then sync.
"""
if myRank == rootID:
    dt.safeMakeDir(jobConfig['outputImageRoot'])

myComm.Barrier()

"""
Get list of field tag requests from the job configuration.
"""
fieldReqs = jobConfig['fieldTags']

"""
Get time sampling intervals list from the job configuration.
"""
timeSamplingIntervals = jobConfig['timeSamplingIntervals']

"""
Determine whether or not to restrict the date range.
If the date range is to be restricted, minDate and 
maxDate (in YYYYMMDD integer format) will determin
the range of the closed date interval.
"""
restrictDateRange = jobConfig['restrictDateRange']
minDate = None
maxDate = None
if restrictDateRange:
    minDate = jobConfig['minDate']
    maxDate = jobConfig['maxDate']

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
conAUS = ar.Region(ozDict, RegionName=regName, RegionType=regType, 
                   SetSubRegionTable=True)
"""
Create subregions.
"""
if not jobConfig['createSubRegions']:
    print myName,':: FATAL--This is a SubRegion app; must have createSubRegions=True'
    sys.exit()
"""
Set SubRegion type (i.e., regionalisation scheme).
"""
srType = jobConfig['subRegionType']
"""
Determine which SubRegions to create.
"""
if jobConfig['createAllSubRegions']:
    """
    Create all possible SubSegions present in SubRegion mask.
    """
    subRegionIDs = conAUS.getSubRegionIDs()

else:
    """
    Work from a list of SubRegion (number) IDs.  Why numbers 
    rather than names?  Because many SubRegion names are long, 
    contain spaces, and the likelihood of typos derailing 
    execution would be greater.
    """
    subRegionIDs = jobConfig['selectedSubRegionIDs']

"""
Working from a list of SubRegion IDs, create a  List of 
SubRegion class instances.
"""
subRegions = []
for srID in subRegionIDs:
    """
    Reverse look-up from what is *meant* to be a nondegenerate
    dictionary (i.e., unique values, one for each key).
    """
    srInd = (conAUS.subRegionFlags.values()).index(srID)
    srName = (conAUS.subRegionFlags.keys())[srInd]
    subRegions.append(ar.SubRegion(conAUS, srID, RegionName=srName,
                                   RegionType=srType))

"""
Safe mkdir for region type directory layer.
"""
outputDir = jobConfig['outputImageRoot'] + '/' + srType
if dt.isWriteableDirectory(jobConfig['outputImageRoot']):
    if myRank == rootID:
        dt.safeMakeDir(outputDir)
else:
    print myName,':: Directory ',jobCofig['outputImageRoot'],' not writeable.'
    sys.exit()

myComm.Barrier()

"""
The variable outputDir now holds the path from which each SubRegion sits in its
own directory.  Create these SubRegion-related directories and their descendent 
layers.  Build a dictionary relating SubRegions to their respective output root 
directories.
"""    
srDirs = {}
for sReg in subRegions:
    srDir = outputDir + '/' + str(int(sReg.regionID))
    if myRank == rootID:
        dt.safeMakeDir(srDir)
    myComm.Barrier()
    srDirs.update({sReg:srDir})
    for field in fieldReqs:
        """
        Safe mkdir for field-specific directory layer.
        """
        fieldName = jobConfig['fieldTagsToDirName'][field]
        srFieldDir = srDir + '/' + fieldName
        if dt.isWriteableDirectory(srDir):
            if myRank == rootID:
                dt.safeMakeDir(srFieldDir)
        else:
            print myName,':: Directory ',srDir,' not writeable.'
            sys.exit()
        myComm.Barrier()
        """
        Safe mkdir for Thumbnail and Full-resolution plot file
        directories.
        """
        thumbnailImDir = srFieldDir + '/Thumbnail' 
        fullImDir = srFieldDir + '/Full' 
        if myRank == rootID:
            dt.safeMakeDir(thumbnailImDir)
            dt.safeMakeDir(fullImDir)
        myComm.Barrier()
"""
Lists to hold profile timing data; one element per operation.
"""
readFileTimes = []
baseMapTimes = []
meshGridTimes = []
shapeFileTimes = []
pColorTimes = []
saveFullResFileTimes = []
saveThumbnailFileTimes = []
"""
Basemap dictionary.  To be filled in on first pass over all
the subregions.
"""
baseMaps = {}
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
Loop over requested fields list myFieldReqs[:]
"""
loopStartTime = time.time()
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
    Create colourMap for this field.
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
    Retrieve list of all of the filename stems (i.e., minus filetype extension) 
    in fieldDataDir.
    """
    fieldDataFiles = aio.getFileList(inputDir)
    if restrictDateRange:
        fieldDataFiles = aio.filterByDateRange(fieldDataFiles, minDate, maxDate)

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
        Loop over sample files.
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
            Loop over subregions to be plotted.
            """
            for sReg in subRegions:
                """
                Set output directory names for this subregion.
                """
                srFieldDir = srDirs[sReg] + '/' + fieldName
                thumbnailImDir = srFieldDir + '/Thumbnail'
                fullImDir = srFieldDir + '/Full'
                """
                Extract SubRegion field data from parent region.
                Mask it using the SubRegion's mask.
                """
                subFieldData = fieldData[sReg.parentLatStart:sReg.parentLatStop,
                                         sReg.parentLonStart:sReg.parentLonStop]
                maskedSubField = ma.masked_array(data=subFieldData, 
                                                 mask=sReg.topoMask.mask)

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
                Does this region have an existing Basemap?  If not,
                generate it.
                """
                startTime = time.time()
                if sReg.name not in baseMaps.keys():
                    baseMaps.update({sReg.name:Basemap(projection='cyl',
                                                        llcrnrlat=sReg.minLat-2.*sReg.dLat, 
                                                        urcrnrlat=sReg.maxLat+2.*sReg.dLat, 
                                                        llcrnrlon=sReg.minLon-2.*sReg.dLon,
                                                        urcrnrlon=sReg.maxLon+2.*sReg.dLon,
                                                        resolution='f')})

                baseMapTimes.append(time.time() - startTime)
                """
                Moving forward, use myBaseMap as a reference to the dictionary
                entry
                """
                myBaseMap = baseMaps[sReg.name]
            
                """
                Read in the AWAP CONAUS shapefile information.
                """
                startTime = time.time()
                myShapes = myBaseMap.readshapefile(jobConfig['shapeFile'], 
                                                   'scalerank', drawbounds=True)
                shapeFileTimes.append(time.time() - startTime)
                """
                Compute x,y coordinates in map projection; shift cell-center lat/lon 
                values to ULC values for use with matplotlib's pcolor() function.
                """
                startTime = time.time()
                x, y = myBaseMap(*np.meshgrid(sReg.lons-0.5*sReg.dLon, 
                                              sReg.lats+0.5*sReg.dLat))            
                meshGridTimes.append(time.time() - startTime)

                startTime = time.time()
                im = myBaseMap.pcolormesh(x, y, maskedSubField, cmap=cMap)
                pColorTimes.append(time.time() - startTime)
                plt.clim(vmin=minVal, vmax=maxVal)
                """
                Save thumbnail as a .jpeg file.
                """
                tnFile = thumbnailImDir + '/' + fn + '.jpeg'
                tnFig = plt.gcf()
                tnFig.set_size_inches(1.38,1.14)
                startTime = time.time()
                plt.savefig(tnFile, bbox_inches='tight', pad_inches=0.02, 
                            dpi=100)
                saveThumbnailFileTimes.append(time.time() - startTime)
                """
                Set up full-resolution figure and save it.
                """
                tnFig.set_size_inches(5.25,4.5)
                ax.axis('on')
                """
                Add in color bar (if desired).
                """
                if jobConfig['DisplayColorBarOnFR']:
                    cbar = myBaseMap.colorbar(im,"right", size='5%', pad='2%')
                    cbar.ax.tick_params(axis='y', direction='out')
                    cbar.set_label(plotPars[field]['cbarCaption'])
                
                """
                Add Labels for field/units, time period, region name.
                """
                xRange = x.max() - x.min()
                yRange = y.max() - y.min()
                """
                Date label.
                """
                plotDateRange = aio.getDateRange(fn)
                xDate = 0.5
                yDate = 0.01
                plt.figtext(xDate, yDate, plotDateRange, ha='center', va='bottom', 
                            family='monospace', fontsize=8)
                """
                Title string.  Put SubRegion name/type in supertitle.
                """
                plotTitle = plotPars[field]['plotTitle']
                """
                If no colour bar, append units to title.
                """
                if not jobConfig['DisplayColorBarOnFR']:
                    plotTitle += ' ' + plotPars[field]['cbarCaption']
                """
                Include region information (if desired).
                """
                if jobConfig['DisplayRegionNameOnFR']:
                    if jobConfig['DisplayRegionTypeOnFR']:
                        plotSubTitle = sReg.regionType + ':  ' + sReg.name
                    else:
                        plotSubTitle = sReg.name
                    """
                    Display the title with region information desired
                    """
                    titles = plotTitle + ' \n ' + plotSubTitle
                    t = plt.title(titles, size=8, ha='center')
                    t.set_y(1.01)
                else:
                    """
                    Merely display the field information in the title.
                    """
                    t = plt.title(plotTitle, size=8, ha='center')
                    t.set_y(1.01)

                """
                Save full plot as a .jpeg file.
                """
                frFile = fullImDir + '/' + fn + '.jpeg'
                startTime = time.time()
                plt.savefig(frFile, bbox_inches='tight', pad_inches=0.1, 
                            dpi=300)
                saveFullResFileTimes.append(time.time() - startTime)
                plt.close()
"""
Print out the profile:
"""
loopRunTime = time.time() - loopStartTime
print myName,':: myRank = ',myRank,' :: Total Run Time for outermost loop = ',loopRunTime,' s.'
print myName,':: myRank = ',myRank,' :: Total Run Time = ',time.time() - totalStartTime,' s.'
sys.stdout.flush()
avgRFTime = sum(readFileTimes) / float(len(readFileTimes))
print myName,':: myRank = ',myRank,' :: Total Read File Time = ',sum(readFileTimes),' s.'
sys.stdout.flush()
print myName,':: myRank = ',myRank,' :: Number of Read File Operations = ',len(readFileTimes),' with time/op of ',avgRFTime,' s.'
sys.stdout.flush()
print myName,':: myRank = ',myRank,' :: Total BaseMap TIme = ',sum(baseMapTimes),' s.'
sys.stdout.flush()
avgBMTime = sum(baseMapTimes) / float(len(baseMapTimes))
print myName,':: myRank = ',myRank,' :: Number of BaseMap Operations = ',len(baseMapTimes),' with time/op of ',avgBMTime,' s.'
sys.stdout.flush()
print myName,':: myRank = ',myRank,' :: Total shapeFile read onto basemap Time = ',sum(shapeFileTimes),' s.'
sys.stdout.flush()
avgShFTime = sum(shapeFileTimes) / float(len(shapeFileTimes))
print myName,':: myRank = ',myRank,' :: Number of shapeFile Operations = ',len(shapeFileTimes),' with time/op of ',avgShFTime,' s.'
sys.stdout.flush()
print myName,':: myRank = ',myRank,' :: Total np.meshgrid TIme = ',sum(meshGridTimes),' s.'
sys.stdout.flush()
avgMGTime = sum(meshGridTimes) / float(len(meshGridTimes))
print myName,':: myRank = ',myRank,' :: Number of meshgrid Operations = ',len(meshGridTimes),' with time/op of ',avgMGTime,' s.'
sys.stdout.flush()
print myName,':: myRank = ',myRank,' :: Total bmap.pcolormesh() Times = ',sum(pColorTimes),' s.'
avgPCTime = sum(pColorTimes) / float(len(pColorTimes))
print myName,':: myRank = ',myRank,' :: Number of bmap.pcolormesh() Operations = ',len(pColorTimes),' with time/op of ',avgPCTime,' s.'

print myName,':: myRank = ',myRank,' :: Total save thumbnail image file time = ',sum(saveThumbnailFileTimes),' s.'
sys.stdout.flush()
avgSTnFTime = sum(saveThumbnailFileTimes) / float(len(saveThumbnailFileTimes))
print myName,':: myRank = ',myRank,' :: Number of saveFile Operations = ',len(saveThumbnailFileTimes),' with time/op of ',avgSTnFTime,' s.'
print myName,':: myRank = ',myRank,' :: Total save full-res image file time = ',sum(saveFullResFileTimes),' s.'
sys.stdout.flush()
avgSFRFTime = sum(saveFullResFileTimes) / float(len(saveFullResFileTimes))
print myName,':: myRank = ',myRank,' :: Number of saveFile Operations = ',len(saveFullResFileTimes),' with time/op of ',avgSFRFTime,' s.'
sys.stdout.flush()

