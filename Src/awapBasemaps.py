import numpy as np
import awapRegion as ar

from mpl_toolkits.basemap import Basemap
"""
Major and minor axes of the WGS84 ellipsoid.
"""
rEquat = 6378137.00
rPolar = 6356752.3142

"""
LLC Reference Latitudes
"""
AusLLCLats = [-10., --40.]
"""
BBox shifts used for LCC projections.  Determined through
trial and error.  Layout is of shift parameters is
[LLC_lat, LLC_lon, URC_lat, URC_lon]
"""
AusBBoxShifts = [0., -7., 2., 0.]
TasBBoxShifts = []
VicBBoxShifts = []

def getAWAP_LLC_Basemap(Region):
    """
    Get Australian Continent Basemap.
    
    Uses Australian Bureau of Meteorology map projection parameters
    to set up an Labert Conformal Conic projection for the nominated 
    region.

    Parameters
    ----------
    Region : awapRegion.Region
        Region for which LCC basemap is desired.
    
    Returns
    ------
    BaseMap
        Matplotlib-Basemap Basemap object.
    """
    
    """
    BoM projection parameters.
    """
    projType = 'lcc'
    trueLat1 = AusLLCLats[0]
    trueLat2 = AusLLCLats[1]
    
    """
    Shift corner ponts using predefined offsets.
    """
    llcLat = Region.minLat + AusBBoxShifts[0]
    llcLon = Region.minLon + AusBBoxShifts[1]
    urcLat = Region.maxLat + AusBBoxShifts[2]
    urcLon = Region.maxLon + AusBBoxShifts[3]
    
    centerLat = 0.5 * (Region.minLat + Region.maxLat)
    centerLon = 0.5 * (Region.minLon + Region.maxLon)
    
    """
    Create the basemap.
    """
    bm = Basemap(llcrnrlon=llcLon, llcrnrlat=llcLat,
                 urcrnrlon=urcLon, urcrnrlat=urcLat,
                 rsphere=(rEquat, rPolar), anchor='C', resolution='f',
                 area_thresh=1000., projection='lcc',
                 lat_1=trueLat1, lat_2=trueLat2, lat_0=centerLat,
                 lon_0=centerLon)
    
    return bm
