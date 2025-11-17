import sys
import time
import math

import numpy as np
import numpy.ma as ma

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

myName = sys.argv[0]
regionMask = sys.argv[1]
regionShape = sys.argv[2]
srType = sys.argv[3]

"""
Hard-wire some things for now; input data and plot label 
and colour scale settings.
"""
fieldDataDir = '../Data/Precip'
fieldDataFile = 'mth_Precip_20111231.hdr'
fieldName = 'Precip'
fieldTag = fieldName.lower()
plotParsFile = '../VisPars/AWAP/awapMonthlyColours+Titles.txt'
colourTablePath = '../VisPars/AWAP/ColourTables'

"""
Read plot parameters file into nested dictionary plotPars
"""
plotPars = aio.readAWAP_PlotPars(plotParsFile)

"""
Set up Continental Region for Australia.
"""
ozDict = aio.readAWAP_hdr(regionMask)
conAUS = ar.Region(ozDict, RegionName='CONAUS', RegionType='Continent', 
                   SetSubRegionTable=True)
"""
Generate SubRegions.
"""
subRegNames = conAUS.subRegionFlags.keys()
print myName,':: List of SubRegion names = ',subRegNames
subRegions = []
for sr in subRegNames:
    subRegions.append(ar.SubRegion(conAUS, conAUS.subRegionFlags[sr],
                                   RegionName=sr, RegionType=srType))
"""
Read in continental-scale orography-masked field.
"""
fieldDataPath = fieldDataDir + '/' + fieldDataFile
fieldDict = aio.readAWAP_hdr(fieldDataPath)
fieldData = aio.readAWAP_flt(fieldDict)
if fieldTag == 'precip':
    """
    Convert m/day to mm/day.
    """
    fieldData = 1000. * fieldData

"""
Begin plotting process.  First, set up colourMap, which is constant
for all SubRegions.
"""
cmapName = fieldName + 'Scale'
colourDict = aio.readAWAP_ColourTable(colourTablePath,fieldName.lower())
cMap = cols.LinearSegmentedColormap(cmapName, colourDict)

"""
Make each subregion plot.
"""
for sr in subRegions:
    """
    Extract SubRegion chunk from parent field and mask it using
    the SubRegion's mask.
    """
    subFieldData = fieldData[sr.parentLatStart:sr.parentLatStop,
                             sr.parentLonStart:sr.parentLonStop]
    maskedSubField = ma.masked_array(data=subFieldData, mask=sr.topoMask.mask)
    """
    Figure set-up:  Set up figure so that no viewport 
    frame nor axes are visible.
    """
    fig = plt.figure(frameon=True)
    ax = plt.axes()
    fig.patch.set_visible(False)
    ax.patch.set_visible(False)
    ax.axis('on')

    """
    Create cylindrical projection basemap.
    """
    bMap = Basemap(projection='cyl',llcrnrlat=sr.minLat-2.*sr.dLat, 
                   urcrnrlat=sr.maxLat+2.*sr.dLat, 
                   llcrnrlon=sr.minLon-2.*sr.dLon,
                   urcrnrlon=sr.maxLon+2.*sr.dLon,resolution='f')

    """
    Pseudocolour plot using supplied masked field data.  The data 
    are presented as *cell-centered*, but matplotlib's pcolor function
    works off of corners in the order presented (in this situation, the
    ULC of the cell).  Displace sr.lats/sr.lons accordingly for the 
    lat/lon to basemap coordinate transformation.
    """
    x, y = bMap(*np.meshgrid(sr.lons-0.5*sr.dLon, sr.lats+0.5*sr.dLat))
    im = bMap.pcolor(x, y, maskedSubField, cmap=cMap)

    """
    Read in the AWAP CONAUS shapefile information.
    """
    bMapShapes = bMap.readshapefile(regionShape, 'scalerank', drawbounds=True)

    """
    Limit colorbar range and pin out-of bounds values to nearest extremum.
    """

    minVal = plotPars[fieldTag]['minVal']
    maxVal = plotPars[fieldTag]['maxVal']
    if fieldTag == 'precip':
        """
        Renormalise to convert m/day -> mm/day
        """
        minVal = 1000. * minVal
        maxVal = 1000. * maxVal
    plt.clim(vmin=minVal, vmax=maxVal)
    """
    Add in color bar.
    """
    cbar = bMap.colorbar(im,"right", size="5%", pad="5%")
    cbar.ax.tick_params(axis='y', direction='out')
    """
    Renormalise precip colour bar tick labels to convert
    units from m/day to mm/day.
    """
    cbar.set_label(plotPars[fieldTag]['cbarCaption'])
    #plotDateRange = aio.getDateRange(fieldDataFile)
    plotDateRange = '20111201-20111231'
    """
    Put SubRegion name/type in supertitle.
    """
    plotSuperTitle = sr.regionType + ':  ' + sr.name
    plotTitle = plotPars[fieldTag]['plotTitle'] + ':  ' + plotDateRange
    titles = plotSuperTitle + ' \n ' + plotTitle
    t = plt.title(titles, size=10)
    t.set_y(1.01)
    imgFile = sr.name + '.' + fieldTag + '.' + plotDateRange + '.png' 
    plt.savefig(imgFile, dpi=300)
    plt.show()
    time.sleep(20)
    plt.close()
