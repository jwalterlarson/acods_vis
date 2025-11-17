import sys
import math
import cPickle as pickle

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

"""
Hard-wire some things for now...
"""

regionMask = '../Masks/States/ozstates8ctr05_op_shk.hdr'
shapeFile = '../Shapefiles/States/aus10fgd_r'
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
conAUS = ar.Region(ozDict, RegionName='CONAUS', RegionType='Continent')

"""
Read in masked field.
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
Set map projection parameters.
"""
projType = 'lcc'
centerLat = 0.5 * (conAUS.maxLat + conAUS.minLat)
centerLon = 0.5 * (conAUS.maxLon + conAUS.minLon)
trueLat1 = -10.
trueLat2 = -40.

"""
Begin plotting process....

First, set up colourMap.
"""
cmapName = fieldName + 'Scale'
colourDict = aio.readAWAP_ColourTable(colourTablePath,fieldName.lower())
cMap = cols.LinearSegmentedColormap(cmapName, colourDict)
"""
Print the CONAUS bounding box as a check...
"""
print myName,':: conAUS.minLat = ',conAUS.minLat
print myName,':: conAUS.maxLat = ',conAUS.maxLat
print myName,':: conAUS.minLon = ',conAUS.minLon
print myName,':: conAUS.maxLon = ',conAUS.maxLon

"""
Figure set-up:  Set up figure so that no viewport 
frame nor axes are visible.
"""
fig = plt.figure(frameon=False)
ax = plt.axes()
fig.patch.set_visible(False)
ax.patch.set_visible(False)
ax.axis('off')

"""
If initialised straight from the BoM LCC parameters, the basemap is shifted 
to the ESE of where it should lie.  I don't know why!  Introduce fudge factors 
westDisp and northDisp to shift the domain to taste.
"""
westDisp = 7.
northDisp = 2.

mOz = Basemap(llcrnrlon=conAUS.minLon-westDisp, llcrnrlat=conAUS.minLat,
              urcrnrlon=conAUS.maxLon, urcrnrlat= conAUS.maxLat+northDisp,
              rsphere=(rEquat,rPolar), anchor='C', resolution='f',
              area_thresh=1000.,projection='lcc',
              lat_1=trueLat1,lat_2=trueLat2,lat_0=centerLat,
              lon_0=centerLon)
"""
Test:  pickle the basemap.
"""
pickle.dump( mOz, open( 'mOz.Basemap.p', 'wb'))
mOz = pickle.load(open('mOz.Basemap.p', 'rb'))
"""
Read in the AWAP CONAUS shapefile information.
"""
mOzShapes = mOz.readshapefile(shapeFile, 'scalerank', drawbounds=True)

x, y = mOz(*np.meshgrid(conAUS.lons, conAUS.lats))
    
im = mOz.pcolor(x, y, fieldData, cmap=cMap)

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
cbar = mOz.colorbar(im,"right", size="5%", pad="2%")
cbar.ax.tick_params(axis='y', direction='out')
"""
Renormalise precip colour bar tick labels to convert
units from m/day to mm/day.
"""
cbar.set_label(plotPars[fieldTag]['cbarCaption'])
plotDateRange = aio.getDateRange(fieldDataFile)

plotTitle = plotPars[fieldTag]['plotTitle'] + ':  ' + plotDateRange
plt.title(plotTitle)

plt.show()
