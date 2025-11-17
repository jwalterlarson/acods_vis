"""
Unit tester for DataCube class.
"""
import sys
import math
import time

import numpy as np
import numpy.ma as ma

import awapIO as aio
import dataCube as dc

my_name = 'test-DataCube.py'
usage = 'python %s ' % my_name
if len(sys.argv) < 3:
    print usage
    sys.exit()

data_root = sys.argv[1]
field_name = sys.argv[2]

"""
Hard-wire the rest for now until we get kwargs implemented
at the command line.
"""

sample_type = 'mth'
seasons = aio.SeasonAbbrs

"""
Build seasonal DataCubes from input data.
"""
season_cubes = {}
print '%s:: Building DataCubes for variable %s...' % (my_name, field_name)
tstart = time.time()
for season in seasons:
    print 'Ingest for season %s...' % season
    season_cubes[season] = dc.DataCube(data_root, field_name, sample_type,
                                       CycleFilter=season)
print 'Ingest for field %s completed in %s sec.' % (field_name, time.time() - tstart)

for season in seasons:
    print 80*'%'
    print 'Printing attributes of data cube for season ',season
    season_cubes[season].printAttributes()
    print 80*'%'



