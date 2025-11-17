"""
Test code to read in an AWAP continental/state mask, create a
Region instance for the continent, and SubRegion instances for
the states.
"""
import sys

import numpy as np
import numpy.ma as ma

import awapIO as aio
import awapRegion as ar
import awapRegionDefs as ard

"""
Set up a dictionary for the AWAP continental mask.
"""
ozDomainDict = aio.readAWAP_hdr('Masks/ozstates8ctr05_op_shk.hdr')

"""
Set up Region instance for Australia.
"""
conAUS = ar.Region(ozDomainDict, RegionName='AUS', RegionType='Continent')

"""
Create from conAUS a subdomain instance for each state.
"""
stateNames = ard.StateIDs.keys()
"""
State SubRegions using predefined BoundingBox.
"""
stateRegions = []
for state in stateNames:
    stateRegions.append(ar.SubRegion(conAUS, 
                                     ard.StateIDs[state], 
                                     ard.StateBBoxes[state], 
                                     RegionName=state, 
                                     RegionType='State'))
"""
State SubRegions using automatically generated 
BoundingBox.
"""
autoStateRegions = []
for state in stateNames:
    autoStateRegions.append(ar.SubRegion(conAUS, 
                                         ard.StateIDs[state], 
                                         RegionName=state, 
                                         RegionType='State'))
"""
Print some diagnostics.
"""
print 'National, or "Parent" domain information:  '
conAUS.printSummary()
print 25*'+',' topoMask: ',25*'+'
print 'conAUS.topoMask = ',conAUS.topoMask
print 25*'+',' topoMask: ',25*'+'
print 50*'#'
print 'Summary of the state domains (created from hard-wired BBoxes)...'
print 'States List = ',stateNames
print 50*'#'
stateUMPts = 0
flagSum = 0
for state in stateRegions:
    state.printSummary()
    print 25*'+',' topoMask: ',25*'+'
    print state.name + '.topoMask = ',state.topoMask
    print 25*'+',' topoMask: ',25*'+'
    print 50*'-'
    stateUMPts += state.numUnmaskedPoints
    matchingIDs = (conAUS.topoMask == float(state.regionID)).sum()
    print 'Number of grid points having this state regionID = ',matchingIDs
    flagSum += matchingIDs

autoStateUMPts = 0
print 50*'#'
print 'Summary of the state domains (created from automatic BBoxes)...'
print 'States List = ',stateNames
print 50*'#'
for state in autoStateRegions:
    state.printSummary()
    print 25*'+',' topoMask: ',25*'+'
    print state.name + '.topoMask = ',state.topoMask
    print 25*'+',' topoMask: ',25*'+'
    print 50*'-'
    autoStateUMPts += state.numUnmaskedPoints
    matchingIDs = (conAUS.topoMask == float(state.regionID)).sum()
    print 'Number of grid points in conAUS with this state regionID = ',matchingIDs

print 70*'%'
print 70*'%'
print 'Total number of unmasked grid points on the conAUS domain:',conAUS.numUnmaskedPoints
print 'State-by-state sum of unmasked grid points (hard-wired BBoxes):',stateUMPts
print 'State-by-state sum of unmasked grid points (automatic BBoxes):',autoStateUMPts
print 'State-by-state sum of unmasked grid points from scanning all of conAUS:',flagSum



