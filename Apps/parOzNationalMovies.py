"""
Application to build continental-scale movies from a timeseries 
collection of continental-scale 2D slices.  Runs in parallel 
using mpi4py.

Uses ffmpeg version >= 2 (so that input globbing is available).
"""
import sys
import subprocess
import time

from mpi4py import MPI

import awapIO as aio
import dirTools as dt

myName = sys.argv[0]

"""
start Total run time timer.
"""
totalStartTime = time.time()

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
Check readability of input image directory tree.
The directory name is defined in the .conf file
supplied to this script.
"""
imageRootDir = jobConfig['inputImageRoot']
if not dt.isReadableDir(imageRootDir):
    sys.exit()
"""
Get list of field tag requests from the job configuration.
"""
fieldReqs = jobConfig['fieldTags']

"""
Form file extensions for image input / movie output.
"""
imageFileExt = '.' + jobConfig['imageFormat']
movieFileExt = '.' + jobConfig['movieFormat']

"""
Create (safely) the directory tree for output videos.  Do this on the root
and sync afterwards.
"""
outputMovieRootDir = jobConfig['outputMovieRoot']
if myRank == rootID:

    """
    Create--if not yet created--the root of the output video
    directory tree.
    """
    dt.safeMakeDir(outputMovieRootDir)

myComm.Barrier()

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
Loop over requested fields list fieldReqs[:]
"""
for field in myFieldReqs:
    """
    Set data input directory and image output directories.
    """
    fieldName = jobConfig['fieldTagsToDirName'][field]
    inputDir = imageRootDir + '/' + fieldName + '/Full'
    """
    Is inputDir a valid directory?
    """
    if not dt.isReadableDir(inputDir):
        print myName,':: FATAL--Directory',inputDir,' is invalid.'
        sys.exit()

    """
    Form list of all image files.
    """
    allImages = aio.getFilesByExt(imageFileExt, Directory=inputDir)
    """
    Filter this list to extract/exclude percentile rank images,
    depending on whether the field is a percentile ranks or 
    physical units field.
    """
    if aio.isPercentileRankField(field):
        images = aio.extractPercentileRankFiles(allImages)
        fileNamePref = 'pcr_mth'
    else:
        images = aio.excludePercentileRankFiles(allImages)
        fileNamePref = 'mth'

    """
    Determine date span.
    """
    dateSpan = aio.getDateSpan(images)
    """

    Form output video file name.
    """
    movieFile = (outputMovieRootDir + '/' + fileNamePref + '_' + fieldName 
                 + '_' + dateSpan + movieFileExt)

    """
    Form movie-making command.  Inputs images at rate of 12/sec, outputs
    24 FPS.
    """
    inFilePrototype = inputDir + '/' + fileNamePref + '_' + fieldName + '_*' + imageFileExt
    mmCommand = ("ffmpeg -r 12 -pattern_type glob -i '" + inFilePrototype + "'"
                + " -r 24 " + movieFile)
    print myName,":: field tag: ",field," field name:  ",fieldName," movie generation command = ",mmCommand
    """
    Invoke the movie-making command using subprocess.Popen()
    """
    subprocess.Popen(mmCommand, shell=True)


