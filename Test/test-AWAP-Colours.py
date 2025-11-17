"""
Script to work with CMAR-supplied AWAP variable definitions 
of ranges and colour tables to crank out a simple test pattern.

The test pattern is a 120x120 grid, which will be plotted as a
pseudocolour plot in a test pattern.  The test pattern is a 
series of horizontal bands of cells, whose values vary from 
[cmin - 0.1 * crange, cmax + 0.1 * crange], where 

crange = cmax - cmin.

That is, the data span a range that begins at a value 10% below 
the stated minimum for the colour map and ends 10% below the 
stated maximum for the colour map.  Thus, there should be fat
bands at the left and right whose colours correspond to the 
minimum and maximum values, respectively.

"""

import sys
import os.path

import numpy as np

import awapIO as aio

import matplotlib
from matplotlib import pyplot as plt
from matplotlib import colors as cols
from pylab import *

ImageFormat = 'gif'
DisplayPlots = True

myName = sys.argv[0]

"""
Get the name of the parameter file--Briggs' grd2gif parameters.
"""
PlotParsFile = sys.argv[1]
"""
Does the file exist?
"""
if not os.path.isfile(PlotParsFile):
    print myName,':: ERROR--file ',PlotParsFile,' is not a file.'
    sys.exit()
"""
Get colour table directory name.  This is for piecewise linear
colour scales.
"""
ColTabPath = sys.argv[2]
if not os.path.isdir(ColTabPath):
    print myName,':: ERROR--invalid directory ',ColTabPath,' .'
    sys.exit()

"""
Get optional arguments--field names--will plot only this field 
if supplied.
"""
if len(sys.argv) >= 4:
    numReqs = len(sys.argv) - 3
    FieldReqs = list(sys.argv[3:numReqs+3])
    plot = True
else:
    plot = False

"""
Build lists of fields, max/min values, plot titles, and colour 
bar captions from the plot parameters file.  These lists will 
will be indexed by field name, and will be used to define how
that field's plot is made.
"""
fieldNames = []
minVals = []
maxVals = []
plotTitles = []
cbarCaptions = []
parsLines = tuple( open(PlotParsFile,'r'))
for line in parsLines:
    words = line.rsplit(",")
    fieldNames.append(words[0].strip("\""))
    minVals.append(float(words[1].strip()))
    maxVals.append(float(words[2].strip()))
    plotTitles.append((words[5].strip()).strip("\""))
    cbarCaptions.append((words[6].strip()).strip("\""))

print myName,':: ',len(fieldNames),' available FieldNames = ',fieldNames

"""
Two paths:  create one or more plots for selected fields 
if the variable plot == True.  Otherwise, simply echo back
the data.
"""
if not plot:
    print myName,':: fieldNames[:] = ',fieldNames
    print myName,':: minVals[:] = ',minVals
    print myName,':: maxVals[:] = ',maxVals
    print myName,':: plotTitles[:] = ',plotTitles
    print myName,':: cbarCaptions[:] = ',cbarCaptions

if plot:
    """
    Determine whether all fields or a subset will be plotted.
    """
    print myName,':: Plotting the following fields:  ',FieldReqs
    if len(FieldReqs) == 1:
        if FieldReqs[0] in ['ALL', 'All', 'all']:
            FieldReqs = fieldNames

    numPlots = len(FieldReqs)
    for i in range(0,numPlots):
        """
        Index this field to the master field list.  The
        addition of .lower() is a hack to accommodate the
        inconsistencies between AWAP's .hdr/.flt and .clr 
        file-naming conventions.
        """
        fieldInd = fieldNames.index(FieldReqs[i].lower())
        """
        Create empty 2D array of floats.
        """
        dat = np.empty((120,120), dtype='float')
        """
        Set test pattern.
        """
        dynamicRange = maxVals[fieldInd] - minVals[fieldInd]
        testRange = 1.2 * dynamicRange
        testMin = minVals[fieldInd] - 0.1 * dynamicRange
        testInc = testRange / float(120.)
        for j in range(0,120):
            dat[j,:] = testMin + j * testInc
        """
        Create matplotlib color map
        """
        colorDict = aio.readAWAP_ColourTable(ColTabPath,fieldNames[fieldInd])
        cmapName = fieldNames[fieldInd] + 'Scale'
        cMap = cols.LinearSegmentedColormap(cmapName, colorDict)
        """
        Create matplotlib pseudocolor plot.
        """
        img = plt.pcolor(dat,cmap=cMap)
        plotTitle = 'Colour Test: ' + plotTitles[fieldInd]
        plt.title(plotTitle)
        """
        Limit colorbar range and pin out-of bounds values to nearest extremum.
        """
        plt.clim(vmin=minVals[fieldInd], vmax=maxVals[fieldInd])
        """
        Add in color bar.
        """
        cbar = plt.colorbar()
        cbar.ax.tick_params(axis='y', direction='out')
        cbar.set_label(cbarCaptions[fieldInd])
        """
        Save output file
        """
        outFile ='./TestPatterns/awapColourScaleTest-' + (fieldNames[fieldInd] +
                                                          '.' + ImageFormat)
        (plt.gcf()).savefig(outFile)
        """
        Display.
        """
        if DisplayPlots:
            plt.show()
        """
        Clean up--clear plot and remove colour scale dictionary.
        """
        plt.close()
        del colorDict
