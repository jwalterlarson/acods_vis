import sys

import numpy as np
import numpy.ma as ma

import awapIO as aio
import awapRegion as ar

myName = sys.argv[0]
maskFile = sys.argv[1]
srType = sys.argv[2]

ozDict = aio.readAWAP_hdr(maskFile)
print myName,':: Input continental-scale mask file = ',maskFile
print myName,':: Resulting header dictionary = ',ozDict

"""
Create Continent-scale Region instance.
"""
print myName,':: Generating continental-scale Region instance conAUS...'
conAUS = ar.Region(ozDict, RegionName='CONAUS', RegionType='CONTINENT',
                   SetSubRegionTable=True)
conAUS.printSummary()
print myName,':: conAUS.subRegionFlags = ',conAUS.subRegionFlags

"""
Pull SubRegion Flag Dictionary keys and use them to create all 
SubRegions.
"""
print myName,':: Creating SubRegion instances for ',conAUS.name,'...'
subRegNames = conAUS.subRegionFlags.keys()
subRegions = []
for sr in subRegNames:
    subRegions.append(ar.SubRegion(conAUS, conAUS.subRegionFlags[sr],
                                   RegionName=sr, RegionType=srType))

"""
Print out summary of SubRegions.
"""
print myName,':: ',50*'#'
print myName,':: Summaries of SubRegions automatically generated from CONAUS:'
print myName,':: ',50*'#'
for sr in subRegions:
    sr.printSummary()


