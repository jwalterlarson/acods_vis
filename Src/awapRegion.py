"""
Region/SubRegion objects for use in AWAP/ACODS geographically distributed data.
"""
import sys

import numpy as np
import numpy.ma as ma

import awapIO as aio

"""
Roundoff tolerance used for latitude and longitude and missing data
flag comparisons.
"""
epsilon = 1.e-6

class Region(object):
    """
    Region object for use in AWAP/ACODS geographically distributed data.
    """
    def __init__(self, HeaderDict, RegionName=None, RegionType=None,
                 SetSubRegionTable=False):
        """
        Constructor for a Region from the AWAP Header.
        
        Parameters
        ----------
        HeaderDict : dict
            Header dictionary.
        RegionName : string
            Name of region; default value of None specifies whole continent.
        RegionType : string
            Type of regionalisation scheme; default is 'NONE'
        SetSubRegionTable : bool
            Switch for setting subregionalisations.
        
        Returns
        -------
        Region
            Region class instance.
        """
        
        # Set Descriptors.
        if RegionName is not None:
            self.name = RegionName
        else:
            self.name = 'NONE'

        if RegionType is not None:
            self.regionType = RegionType
        else:
            self.regionType = 'NONE'
        
        # Set the level in the subregion hierarchy.  This
        # value is zero for this class.
        self.subRegionLevel = 0
        
        # Begin by setting quantities found in the header dictionary.
        self.numLats = HeaderDict['nrows']
        self.numLons = HeaderDict['ncols']
        self.dLat = HeaderDict['cellsize']
        self.dLon = HeaderDict['cellsize']
        self.minLat = HeaderDict['yllcorner']
        self.minLon = HeaderDict['xllcorner']
        self.missingFlag = HeaderDict['nodata_value']

        # Compute derived quantities.
        # 
        # Note self.minLat and self.minLon refer to the *LLHC*
        # of the grid cell located at the LLHC of the domain.
        # Likewise, self.maxLon and self.maxLat refer to the
        # *URHC* of the grid cell located at the URHC of the
        # domain.  The arrays self.lats[:] and self.lons[:] refer
        # to the locations of the *grid cell centers*.
        self.maxLat = self.numLats * self.dLat + self.minLat
        self.maxLon = self.numLons * self.dLon + self.minLon
        self.lats = aio.getLats(HeaderDict)
        self.lons = aio.getLons(HeaderDict)
        
        # Some geographic coordinate meshes reverse the indexing
        # of the latitudes.  Test for this and flag it if true.
        if self.lats[-1] < self.lats[0]:
            self.reversedLats = True
        
        # Set mask.  This mask should provide two things:  a definition
        # of what is not in the region (flagged by self.missingFlag) and
        # IDs of subregions (if present)
        self.topoMask = aio.readAWAP_flt(HeaderDict)
        self.numUnmaskedPoints = ma.count(self.topoMask)
        
        # Are there subregions?  If the header file to which HeaderDict
        # points has an accompanying .csv file, read it into a dictionary
        # of subregion definitions.  Set self.hasSubRegionDefs = False,
        # modify it if the subRegionTable is requested and set successfully.
        self.hasSubRegionDefs = False
        if SetSubRegionTable:
            self.subRegionFlags = aio.readAWAP_LUT(HeaderDict)
            self.hasSubRegionDefs = True
        
        #Finally, for hashing purposes, set the instance's object ID.
        self.objectID = id(self)
        
    def getSubRegionNames(self):
        """
        Returns list of SubRegion names.
        """
        if self.hasSubRegionDefs:
            return self.subRegionFlags.keys()
        else:
            print 'WARNING:  SubRegionFlags table not set!  No output returned.'
            sys.exit()
    
    def getSubRegionIDs(self):
        """
        Returns list of SubRegion ID numbers.
        """
        if self.hasSubRegionDefs:
            return self.subRegionFlags.values()
        else:
            print 'WARNING:  SubRegionFlags table not set!  No output returned.'
            sys.exit()
    
    def printSummary(self):
        if self.subRegionLevel == 0:
            self.printBanner()
        print self.name, ':: Region type:  ', self.regionType
        print self.name, ':: Object ID:  ', self.objectID
        print self.name, ':: Domain Bounding Box:  [', self.minLat, ',', self.minLon, ',', self.maxLat, ',', self.maxLon, '].'
        print self.name, ':: Domain dimensions (nLats,nLons):  (', self.numLats, ',', self.numLons, ').'
        print self.name, ':: Grid cell dimensions (degrees):  (', self.dLat, ',', self.dLon, ').'
        self.printCoordSummary('Latitude', self.lats)
        self.printCoordSummary('Longitude', self.lons)
        print self.name, ':: Number of unmasked grid points:  ', self.numUnmaskedPoints
    
    def printBanner(self):
        """
        Print headline banner for region diagnostic summary.
        """
        print 70 * '='
        print 10 * '*', ' Summary for Region ', self.name
        print 70 * '='
    
    def printCoordSummary(self, CoordName, Coords):
        print CoordName, ' grid values: [', Coords[0], ',', Coords[1], ',...,', Coords[-2], ',', Coords[-1], ']'

class SubRegion(Region):
    """
    Spatial subset of parent region.
    """
    def __init__(self, ParentRegion, RegFlag, BoundingBox=None,
                 RegionName=None, RegionType=None):
        """
        SubRegion constructor from ParentRegion.
        
        Parameters
        ----------
        ParentRegion : Region
            Parent Region instance.
        RegFlag : int
            Identifying flag.
        BoundingBox : list
            Lat/Lon bounding box for the subregion.  If default value 
            None specified, The parent Region instance's topo mask is 
            used in conjunction with RegFlag's value to generate the 
            SubRegion's bounding box automatically.
        RegionName : string
            Name of the subregion; default value of None results in name 
            set to 'NONE'.
        RegionType : string
            Type of regionalisation used to construct the subregion; 
            default value of None results in 'NONE' for this metadatum.
        
        Returns
        -------
        SubRegion
            A SubRegion instance.
        """
        
        # Set text descriptors (if provided).
        if RegionName is not None:
            self.name = RegionName
        else:
            self.name = 'NONE'
        
        if RegionType is not None:
            self.regionType = RegionType
        else:
            self.regionType = 'NONE'
        
        # Begin by setting quantities directly inherited.
        self.parentName = ParentRegion.name
        self.parentRegType = ParentRegion.regionType
        self.parentObjectID = id(ParentRegion)
        self.dLon = ParentRegion.dLon
        self.dLat = ParentRegion.dLat
        self.missingFlag = ParentRegion.missingFlag
        self.reversedLats = ParentRegion.reversedLats
        
        # Set the level in the subregion hierarchy.  This
        # value is one greater than that of ParentRegion.
        self.subRegionLevel = ParentRegion.subRegionLevel + 1

        # Set the Region ID flag used on the parent's topo mask.
        self.regionID = RegFlag
        
        # Use BoundingBox (if supplied) to determine the region's boundaries.
        # Pad out by one grid cell simply to ensure all points are captured.
        # If BoundingBox is not supplied, use the ParentRegion.topoMask and
        # RegFlag to determine the subregion's boundaries.
        if BoundingBox is not None:
            self.minLon = BoundingBox[0] - self.dLon - epsilon
            self.minLat = BoundingBox[1] - self.dLat - epsilon
            self.maxLon = BoundingBox[2] + self.dLon + epsilon
            self.maxLat = BoundingBox[3] + self.dLat + epsilon
        else:
            minLonIndex = np.where(
                ParentRegion.topoMask == float(RegFlag))[1].min()
            self.minLon = ParentRegion.lons[minLonIndex] - 0.5 * self.dLon
            maxLonIndex = np.where(
                ParentRegion.topoMask == float(RegFlag))[1].max()
            self.maxLon = ParentRegion.lons[maxLonIndex] + 0.5 * self.dLon
            if self.reversedLats:
                minLatIndex = np.where(
                    ParentRegion.topoMask == RegFlag)[0].max()
                maxLatIndex = np.where(
                    ParentRegion.topoMask == RegFlag)[0].min()
            else:
                minLatIndex = np.where(
                    ParentRegion.topoMask == RegFlag)[0].min()
                maxLatIndex = np.where(
                    ParentRegion.topoMask == RegFlag)[0].max()
            self.minLat = ParentRegion.lats[minLatIndex] - 0.5 * self.dLat
            self.maxLat = ParentRegion.lats[maxLatIndex] + 0.5 * self.dLat
        
        # Compare the region boundaries with the parent's latitude and
        # longitude grid arrays to determine indices in these arrays
        # lie in the subregion.  This is set up for reversed latitudes,
        # which are used in AWAP, and hard-wired in at the moment.
        if self.reversedLats:
            self.parentMinLatIndex = np.where(
                ParentRegion.lats >= self.minLat)[0][-1]
            self.parentMaxLatIndex = np.where(
                ParentRegion.lats <= self.maxLat)[0][0]
            self.parentLatStart = self.parentMaxLatIndex
            self.parentLatStop = self.parentMinLatIndex + 1
        else:
            self.parentMinLatIndex = np.where(
                ParentRegion.lats >= self.minLat)[0][0]
            self.parentMaxLatIndex = np.where(
                ParentRegion.lats <= self.maxLat)[0][-1]
            self.parentLatStart = self.parentMinLatIndex
            self.parentLatStop = self.parentMaxLatIndex + 1
        
        self.numLats = self.parentLatStop - self.parentLatStart
        self.lats = ParentRegion.lats[self.parentLatStart:self.parentLatStop]
        
        self.parentMinLonIndex = np.where(
            ParentRegion.lons >= self.minLon)[0][0]
        self.parentLonStart = self.parentMinLonIndex
        self.parentMaxLonIndex = np.where(
            ParentRegion.lons <= self.maxLon)[0][-1]
        self.parentLonStop = self.parentMaxLonIndex + 1
        self.numLons = self.parentLonStop - self.parentLonStart
        self.lons = ParentRegion.lons[self.parentLonStart:self.parentLonStop]
        
        # The subregion is probably not precisely a rectangle that fits the BoundingBox.
        # Construct the subregion mask from the parent region's mask and the supplied
        # RegFlag (self.regionID).
        regionIDs = ParentRegion.topoMask._get_data()[
            self.parentLatStart:self.parentLatStop,
            self.parentLonStart:self.parentLonStop]
        regionTopoMask = ParentRegion.topoMask._get_mask()[
            self.parentLatStart:self.parentLatStop,
            self.parentLonStart:self.parentLonStop]
        self.topoMask = ma.masked_array(
            regionIDs, regionIDs != float(
                self.regionID), fill_value=self.missingFlag)
        self.numUnmaskedPoints = ma.count(self.topoMask)
        
        # For now, only one level of sub-regionalisation is supported, so set the
        # flag hasSubRegionDefs to False.
        self.hasSubRegionDefs = False
        
        # Finally, for hashing purposes, set the instance's object ID.
        self.objectID = id(self)
    
    def printSummary(self):
        """
        Print a summary of SubRegion properties.
        """
        self.printBanner()
        Region.printSummary(self)
    
    def printBanner(self):
        """
        Print headline banner for SubRegion diagnostic summary.
        """
        print 70 * '='
        print 10 * '*', ' Summary for SubRegion ', self.name
        print 10 * '*', ' Parent Region: ', self.parentName,
        print 10 * '*', 'Parent Object ID=', self.parentObjectID
        print 10 * '*', ' Region ID Flag on Parent Topo Mask:  ', self.regionID
        print 70 * '='
