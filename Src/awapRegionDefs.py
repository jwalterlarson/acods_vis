"""
Region definitions for AWAP and ACODS data mapping.
"""

import sys
import numpy as np
import numpy.ma as ma

import awapIO as aio

"""
Numerical ID Dictionary for Australian States.
"""
StateIDs = {'NSW': 1, 'ACT': 2, 'VIC': 3, 'TAS': 4,
            'SA': 5, 'WA': 6, 'NT': 7, 'QLD': 8}

"""
Hard-wired state bounding boxes.  Cobbled together from online
resourcees, primarily GA, but also BoM, and state departments.
"""

StateBBoxes = {'NSW': [140.95, -37.5, 153.575, -28.0],
               'ACT': [148.76, -35.92, 149.4, -35.12],
               'VIC': [141.0, -39.15, 149.98, -33.95],
               'TAS': [143.5, -43.575, 149.0, -39.20],
               'SA': [129.0, -38.10, 141.0, -26.0],
               'WA': [112.93, -35.08, 129.0, -13.75],
               'NT': [129.0, -26.0, 138.0, -11.0],
               'QLD': [137.8, -29.175, 153.575, -10.075]}

"""
Set state masks.
"""

def setStateMask(StateName, StatesMasksFile):
    """
    Loads states ID array/mask from file.
    """
    statesHeader = aio.read_hdr(StatesMaskFile)
    """
    Load field of regionIDs
    """
    statesIDs = aio.read_flt(statesHeader)
    return statesIDs
