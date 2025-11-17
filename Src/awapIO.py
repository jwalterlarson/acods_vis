"""
awapIO.py:  AWAP and BIOS2 File I/O

This module supports the following operations:

1) Reads/Writes AWAP/BIOS2 header (.hdr), float (.flt), and
Excel-format (.csv) files.

2) Wrangling of large numbers of AWAP/BIOS2 files.  This function
relies on the conventions for naming AWAP/BIOS2 data files.
"""

"""
System and standard library modules.
"""
import sys
import os
import re
import glob
import csv

"""
NumPy.
"""
import numpy as np
import numpy.ma as ma

"""
Julian date module
"""
import jdcal

"""
Acceptable filename extensions
"""
floatFilenameExt = '.flt'
headerFilenameExt = '.hdr'
lutFilenameExt = '.csv'
csvFilenameExt = '.csv'
jpegFilenameExt = '.jpeg'

"""
Set of acceptable data sampling intervals.
"""
SamplingIntervals = ['mth', 'ann']

def is_a_SamplingInterval(IntervalName):
    """
    Checks to see if the argument is a supported sampling interval.
    
    At present, supported values are ['mth', 'ann'].
    
    Parameters
    ----------
    IntervalName : string
        Name of candidate sampling interval.
    
    Returns
    -------
    bool
        True (False) if the candidate sampling interval is valid
        (invalid).
    """
    if IntervalName in SamplingInterval:
        return True
    else:
        print 'WARNING--Unrecognised sampling interval name ', IntervalName
        return False

"""
Set of month abbreviations, all lower-case.  A comparitor
function does the case conversion to check correct for
any user name capitalisation scheme.
"""

MonthAbbrs = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
              'jul', 'aug', 'sep', 'oct', 'nov', 'dec']

MonthAbbrToNum = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
                  'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
                  'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}

MonthNumToAbbr = {1: 'jan', 2: 'feb', 3: 'mar', 4: 'apr',
                  5: 'may', 6: 'jun', 7: 'jul', 8: 'aug',
                  9: 'sep', 10: 'oct', 11: 'nov', 12: 'dec'}

def is_a_Month(MonthStr):
    """
    Checks to see if the supplied string is a month name.
    
    Case-insensitive comparison with set of month name
    abbreviations.
    
    Parameters
    ----------
    MonthStr : string
        Candidate month abbreviation
    
    Returns
    -------
    bool
        True (False) if a valid (an invalid) month abbreviation.
    """
    
    """
    Convert to lower-case to compare with MonthAbbrs[:].
    """
    if MonthStr.lower() in MonthAbbrs:
        return True
    else:
        return False

def is_a_MonthNum(Num):
    """
    Checks to see if 0 < Num < 13 and Num is an integer.
    
    Parameters
    ----------
    
    Num : int
        Candidate month number.
    
    Returns
    -------
    bool
        True (False) if the argument is (not) a valid month number.
    """
    if ((0 < Num) and (Num < 13)) and isinstance(Num, (int, long)):
        return True
    else:
        return False
"""
Set of season abbreviations, all lower case.  A comparitor
function does the case conversion to check correct for
any user name capitalisation scheme.
"""
SeasonAbbrs = ['djf', 'mam', 'jja', 'son']
SeasonDict = {'mam': ['mar', 'apr', 'may'],
              'jja': ['jun', 'jul', 'aug'],
              'son': ['sep', 'oct', 'nov'],
              'djf': ['dec', 'jan', 'feb']}

def is_a_Season(SeasonStr):
    """
    Checks to see if the supplied string is a season name.
    
    Case-insensitive comparison of string with season abbreviations
    set {'djf', 'mam', 'jja', 'son'}.
    
    Parameters
    ----------
    SeasonStr : string
        Candidate season abbreviation.
    
    Returns
    -------
    bool
        True (False) if SeasonStr identifies a valid (invalid) season.
    """
    
    """
    Convert to lower-case to compare with MonthAbbrs[:].
    """
    if SeasonStr.lower() in SeasonAbbrs:
        return True
    else:
        return False

def seasonToMonths(SeasonStr):
    """
    Converts a season string into list of month names.
    
    For example 'DJF' is converted into ['dec' 'jan', 'feb'].
    
    Parameters
    ----------
    SeasonStr : string
        Season abbreviation.
    
    Returns
    -------
    List
        List of month abbreviations comprising the supplied season.
    """
    if is_a_Season(SeasonStr):
        return SeasonDict[SeasonStr.lower()]
    else:
        print 'awapIO.seasonToMonths:  FATAL--Argument ', SeasonStr, ' not a season!'
        sys.exit()

"""
Files containing percentile rank data will be tagged as such in their
names.  PercentileRankTag contains acceptable tags.
"""
PercentileRankTag = ['pcr']

def isPercentileRankFile(FileName):
    """
    Determines whether the file contains percentile rank data.
    
    Function does this based on its name and the AWAP/BIOS2 file naming
    convention, searching for the percentil rank tag string 'pcr' in the
    filename.
    
    Parameters
    ----------
    FileName : string
        Name of file.
    
    Returns
    -------
    bool
        True (False) if the file is (not) a percentile rank file.
    """
    nameChunks = re.split('\W+|_', FileName)
    for ptag in PercentileRankTag:
        for chunk in nameChunks:
            if ptag == chunk:
                return True
    return False

def readAWAP_hdr(FileName):
    """
    Reads an AWAP header file.
    
    Processes the header file and stores spatial domain, byte-ordering,
    and missing value information in dictionary format.
    
    Parameters
    ----------
    FileName : string
        Name (full path or name in cwd) of header file.
    
    Returns
    -------
    dict
        Dictionary of domain/data layout and data source parameters.
    """

    """
    Do not alter the following line unless the AWAP .hdr format
    changes!  These keys are the string tokens used immediately
    preceding data values in an AWAP header file.  The only extra
    key is the namestem of the .hdr file from which the dictionary
    was compiled.
    """
    keys = ['ncols', 'nrows', 'xllcorner', 'yllcorner',
            'cellsize', 'nodata_value', 'byteorder']
    
    header = open(FileName, 'r')
    hdrDict = {}
    """
    Add first entry--the name of the header file, minus the
    .hdr extension.
    """
    hdrDict.update({'fileNameStem': chop(FileName, '.hdr')})
    
    """
    Scan file for each key, read value immediately following it,
    and add a dictionary entry.
    """
    for line in header:
        # jwl--changed to split on *any* whitespace
        # words = (line.strip()).rsplit(' ')
        words = (line.strip()).split()
        for key in keys:
            if key in words:
                """
                Read in the correct type of numerical or
                string data.
                """
                valInd = words.index(key) + 1
                if key in ['ncols', 'nrows']:
                    value = int(words[valInd])
                elif key in ['cellsize', 'xllcorner', 'yllcorner', 'nodata_value']:
                    value = float(words[valInd])
                elif key in ['byteorder']:
                    value = words[valInd]
                else:
                    print 'ERROR--Pattern "', key, '" not recognized.'
                    sys.exit()
                """
                Add this value to the dictionary.
                """
                hdrDict.update({key: value})
                break
    
    return hdrDict

def writeAWAP_hdr(HeaderDict, FileName=None):
    """
    Output a header dictionary in .hdr file format.
    
    Parameters
    ----------
    HeaderDict : dict
        Dictionary containing field header information.
    
    FileName : string
        Name of file to which the .hdr file is written; default
        value None leads automatically-generated filename using
        header dictionary information.
    """
    
    if FileName != None:
        outFile = open(FileName, 'w')
    else:
        outFileName = HeaderDict['fileNameStem'] + '.hdr'
        outFile = open(outFileName)

    outFile.write(' ncols ' + str(HeaderDict['ncols']) + '\n')
    outFile.write(' nrows ' + str(HeaderDict['nrows']) + '\n')
    outFile.write(' xllcorner ' + str(HeaderDict['xllcorner']) + '\n')
    outFile.write(' yllcorner ' + str(HeaderDict['yllcorner']) + '\n')
    outFile.write(' cellsize ' + str(HeaderDict['cellsize']) + '\n')
    outFile.write(' nodata_value ' +
                  str(int(HeaderDict['nodata_value'])) + '\n')
    outFile.write(' byteorder ' + str(HeaderDict['byteorder']) + '\n')
    outFile.close

def readAWAP_flt(HeaderDict, FileName=None):
    """
    Returns a 2D NumPy masked array from a .flt file.

    Parameters
    ----------
    HeaderDict : dict
        Domain and data layout information

    FileName : string
        Name of file from which the field data is read;
        value None leads to use of automatically-generated
        filename based on header dictionary information.
    
    Returns
    -------
    numpy masked array (2D)

    """
    if FileName == None:
        fileName = HeaderDict['fileNameStem'] + floatFilenameExt
    else:
        fileName = FileName
    
    """
    Read in field data from .flt file, reshape into 2D array.
    """
    fieldData = np.fromfile(fileName, dtype='float32', count=-1)
    numLats = HeaderDict['nrows']
    numLons = HeaderDict['ncols']
    fieldData.shape = (numLats, numLons)
    
    """
    Retrieve missing data flag, apply to array to create masked array.
    """
    missingFlag = HeaderDict['nodata_value']
    maskedField = ma.masked_values(fieldData, missingFlag)
    
    return maskedField

def readAWAP_LUT(HeaderDict):
    """
    Reads a two-column .csv file and returns a dictionary.
    
    Parameters
    ----------
    HeaderDict : dict
        Dictionary containing header information.
    
    Returns
    -------
    dict
        Lookup table in dictionary format.
    """
    lookupTableFile = HeaderDict['fileNameStem'] + lutFilenameExt
    with open(lookupTableFile, mode='r') as infile:
        reader = csv.reader(filter(lambda row: row[0] != '!', infile))
        lut = {rows[1]: int(rows[0]) for rows in reader}
    return lut

def readAWAP_ColourTable(CTPath, Field):
    """
    Creates a matplotlib-compatible colour map in dictionary format.
    
        Uses a supplied path and the file-naming convention to find the
        file containing the piecewise-linear colour function definition
        table.
    
    Parameters
    ----------
    CTPath : string
        Directory path location of colour table files.
    Field : string
        Name of variable for which a colour table is to be constructed.
    
    Returns
    -------
    dict
        Color table dictionary for use in matplotlib.
    """
    import sys
    import os.path
    import numpy as np
    
    """
    Form colour table file name, using current convention.
    """
    colourTableFile = CTPath + '/' + Field.lower() + '.clr'
    if not os.path.isfile(colourTableFile):
        print 'setColourTable() error--colour table ', colourTableFile, ' not found.'
        sys.exit()
    """
    Read in whole file, skip first line, and
    input vals[:], reds[:], greens[:], blues[:]
    for each subsequent line.
    """
    data = np.loadtxt(colourTableFile, skiprows=1)
    """
    Extract the domain for the color scale, and
    RGB function values. These will be used to
    make a matplotlib LinearSegmentedColormap
    object.
    """
    vals = data[:, 0]
    reds = data[:, 1].astype(float)
    greens = data[:, 2].astype(float)
    blues = data[:, 3].astype(float)
    """
    Renormalize RGB values to interval [0.,1.].
    Required by matplotlib.
    """
    reds = reds / 255.
    greens = greens / 255.
    blues = blues / 255.
    """
    Renormalize vals[:] to interval [0.,1.].
    Again, required by matplotlib.  Note that
    this applies to the fraction of the data's
    dynamic range.
    """
    vals = vals / 100.
    """
    Create a matplotlib-compatible color map dictionary.
    """
    numVals = vals.size
    cdict = {'red': tuple([(vals[i], reds[i], reds[i])
                          for i in range(0, numVals)])}
    colorDict = dict(red=tuple([(vals[i], reds[i], reds[i]) for i in range(0, numVals)]),
                     blue=tuple([(vals[i], blues[i], blues[i])
                                for i in range(0, numVals)]),
                     green=tuple([(vals[i], greens[i], greens[i]) for i in range(0, numVals)]))
    return colorDict

def readAWAP_PlotPars(PlotParsFile):
    """
    Returns a nested dictionary of plot parameters from a plot parameters file.
    
    These plotting parameters include minimum/maximum field vaulues,
    title, colour bar caption, et cetera.  The function does this for
    all fields listed in the plot parameters file.
    
    Parameters
    ----------
    PlotParsFile : string
        File containing plot parameters.
    
    Returns
    -------
    dict
        Nested dictionary--outer dictionary keyed by variable name tag--of
        plotting parameters.
    """
    fieldTags = []
    minVals = []
    maxVals = []
    plotTitles = []
    cbarCaptions = []
    parsLines = tuple(open(PlotParsFile, 'r'))
    for line in parsLines:
        words = line.rsplit(",")
        fieldTags.append(words[0].strip("\""))
        minVals.append(float(words[1].strip()))
        maxVals.append(float(words[2].strip()))
        plotTitles.append((words[5].strip()).strip("\""))
        cbarCaptions.append((words[6].strip()).strip("\""))
    """
    Organise these data in a nested dictionary.  The outer
    dictionary is keyed by field tag.
    """
    figProps = {}
    for tag in fieldTags:
        tagInd = fieldTags.index(tag)
        figProps.update({tag: {'minVal': minVals[tagInd],
                              'maxVal': maxVals[tagInd],
                              'plotTitle': plotTitles[tagInd],
                              'cbarCaption': cbarCaptions[tagInd]}})
    return figProps

def chop(InputString, Ending):
    """
    Chops off the trailing substring Ending from InputString.
    
    Used for cropping filename extensions off of data files;
    e.g., chop('foo.bar', '.bar') yields 'foo'.
    
    Parameters
    ----------
    InputString : string
        Input string
    Ending : string
        Ending to be truncated from string
    
    Returns
    -------
    string
        Truncated string.
    """
    if InputString.endswith(Ending):
        return InputString[:-len(Ending)]

def getYMD(Item):
    """
    Returns the 8 character YYYYMMDD sub-string of argument.
    
    Parameters
    ----------
    Item : string
        String from which YYYYMMDD date is to be extracted
    
    Returns
    -------
    string
        Eight-character YYYYMMDD date.
    """
    ymd_dates = re.findall(r'\d{8}', Item)
    
    if len(ymd_dates) > 1:
        print 'getYMD()::Error--more than one YYYYMMDD date present!'
        print ymd_dates
        sys.exit()
    
    if len(ymd_dates) == 0:
        print 'getYMD()::Error--no YYYYMMDD date detected in Item!'
        print 'Item = ', Item
        sys.exit()
    
    return ymd_dates[0]

def getFileList(Directory=None):
    """
    Builds a list of header/float files without the .hdr / .flt file
    extensions.
    
    Parameters
    ----------
    Directory : string
        Path to directory containing files of interest; if None is
        supplied, function uses current working directory.
    
    Returns
    -------
    List
        List of hdr/float files minus the filename extension.
    """
    fileList = []
    """
    If no value for the argument Directory was supplied, work in the
    current directory, otherwise, change to this directory.
    """
    if Directory != None:
        startDir = os.getcwd()
        os.chdir(Directory)
    
    for file in glob.glob("*.hdr"):
        fileList.append(chop(file, '.hdr'))
    
    os.chdir(startDir)
    
    return fileList

def getFilesByExt(FileTypeExt, Directory=None):
    """
    Retrieves names of all of the files of a particular file extension type.
    
    Parameters
    ----------
    
    FileExtType : string
        File extension type (e.g., '.flt', '.jpeg',...)
    Directory : string
        Directory to be searched; if value None is specified,
        function uses current working directory.
    
    Returns
    -------
    List
        List of filenames of a given type, minus the supplied filename
        extension.
    """
    
    fileList = []
    if Directory != None:
        startDir = os.getcwd()
        os.chdir(Directory)
    
    filePrototype = '*' + FileTypeExt
    for file in glob.glob(filePrototype):
        fileList.append(chop(file, FileTypeExt))
    
    if Directory != None:
        """
        Jump back to startDir.
        """
        os.chdir(startDir)
    
    return fileList

def excludePercentileRankFiles(FileList):
    """
    Exclude percentile rank files from a list of filenames
    
    Searches through supplied list of filenames, excising elements
    whose names contain the percentile rank tag 'pcr'.
    
    Parameters
    ----------
    FileList : List
        Input list of filenames.
    
    Returns
    -------
    List
        List of filenames not labeled as percentile rank files.
    """
    filteredList = []
    for file in FileList:
        if not isPercentileRankFile(file):
            """
            Append it to filteredList.
            """
            filteredList.append(file)
    
    return filteredList

def extractPercentileRankFiles(FileList):
    """
    Extract percentile rank files from a list fo filenames.

    Filters list of filenames, identifying those containing
    the percentile rank in their filenames.
    
    Parameters
    ----------
    FileList : list
        A list of filenames.
    
    Returns
    -------
    list
        List of percentile-rank filenames.
    """
    filteredList = []
    for file in FileList:
        if isPercentileRankFile(file):
            """
            Append it to filteredList.
            """
            filteredList.append(file)
    
    return filteredList

def getSortedFileList(Directory=None):
    """
    Builds a sorted list of header/float filenames
    
    Searches directory for header and float files by filename extension
    and builds a list of distinct filename stems; i.e., minus the
    .hdr / .flt filename extensions.
    
    Parameters
    ----------
    Directory : string
        Path to search directory; if default value None, the function
        searches the current working directory.
    
    Returns
    -------
    list
        List of header/float filename stems, lexicographically sorted \
        by YYYYMMDD date.
    """
    fileList = getFileList(Directory)
    
    """
    Transform this list into one sorted by date.  This will enable
    input of data in chronological order.
    """
    sortedFileList = sortByDate(fileList)
    return sortedFileList

def getEarliestDate(FileList):
    """
    Return in YYYYMMDD integer format the earliest date in a FileList.
    
    This function parses the elements of the supplied list argument,
    identifies the earliest date by YYYYMMDD date stamps on filenames,
    and returns a YYYYMMDD date corresponding to the first day of the
    month of the earliest data file.
    
    Parameters
    ----------
    FileList : list

        List of data file names.
    
    Returns
    -------
    int
        YYYYYMMDD date of beginning of data set defined by the list of
        files.
    """
    dateList = [int(getYMD(f)) for f in FileList]
    firstDate = min(dateList)
    monthLength = firstDate % 100
    earliestDate = firstDate - monthLength + 1
    
    return earliestDate

def getDateSpan(FileList):
    """
    Determine dates spanned by supplied list of data files.

    This function parses the supplied list of data file names and
    finds the first and last dates covered by the data set.
    
    Parameters
    ----------
    FileList : list
    
    Returns
    -------
    string
        Date spanned by supplied file list in the format YYYYMMDD-YYYYMMDD.
    """
    startDate = str(getEarliestDate(FileList))
    endDate = str(getLatestDate(FileList))
    dateSpan = startDate + '-' + endDate
    
    return dateSpan

def getLatestDate(FileList):
    """
    Return in YYYYMMDD integer format the latest date in a FileList.
    
    This function parses the elements of the supplied list argument,
    identifies the latest date by YYYYMMDD date stamps on filenames,
    and returns a YYYYMMDD date corresponding to the last day of the
    final chronologically-ordered file in the data set.
    
    Parameters
    ----------
    FileList : list
        List of data file names.
    
    Returns
    -------
    int
        YYYYYMMDD date of end of data set defined by the list of
        files.
    """
    dateList = [int(getYMD(f)) for f in FileList]
    latestDate = max(dateList)
    
    return latestDate

def sortByDate(FileList):
    """
    Sort a list of filenames by their date stamps.
    
    This function parses the supplied list of filenames and
    sorts the list elements into lexicographic order by YYYYMMDD
    date, returning a separate, ordered list.
    
    Parameters
    ----------
    FileList : list
        List of filenames to be sorted.
    
    Returns
    -------
    list
        List of YYYYMMDD-lexicographically ordered filenames.
    """
    return sorted(FileList, key=getYMD)

def isPercentileRankField(Field):
    """
    Determines whether the Field is a percenile rank quantity.
    
    Parameters
    ----------
    Field : string
        Name of supplied field.
    
    Returns
    -------
    bool
        True (False) if the supplied field is (not) a percentile
        rank field.
    """
    if Field[0:3] == 'pcr':
        return True
    else:
        return False

def getJulianDate(FileName):
    """
    Converts YYYYMMDD date in filename to Julian Date.
    
    Parameters
    ----------
    FileName : string
        Name of data file.
    
    Returns
    -------
    float
        Julian date.
    """
    iYear = getYear(FileName)
    iMonth = getMonth(FileName)
    iDay = getDay(FileName)
    
    jDate = sum(jdcal.gcal2jd(iYear, iMonth, iDay))
    
    return jDate

def getDate(FileName):
    """
    Returns integer YYYYMMDD date from filename.
    
    Parameters
    ----------
    FileName
        Filename containing YYYYMMDD date stamp.
    
    Returns
    -------
    int
        YYYYMMDD date in integer format.
    """
    return int(getYMD(FileName))

def getYear(FileName):
    """
    Returns year field from fileName as an integer.
    
    Parameters
    ----------
    FileName : string
        Filename containing a YYYYMMDD date.
    
    Returns
    -------
    int
        YYYY year.
    """
    dateString = getYMD(FileName)
    return int(dateString[-8:-4])

def getMonth(FileName):
    """
    Returns month field from fileName as an integer.
    
    Parameters
    ----------
    FileName : string
        Filename that contains a YYYYMMDD date.
    
    Returns
    -------
    int
        MM month in integer format.
    """
    dateString = getYMD(FileName)
    return int(dateString[-4:-2])

def getMonthAbbr(FileName):
    """
    Returns month abbreviation from FileName YYYYMMDD date.
    
    Parameters
    ----------
    FileName : string
        Filename containing YYYYMMDD date.
    
    Returns
    -------
    string
        Abbreviation of filename month.
    """
    return MonthNumToAbbr[getMonth(FileName)]

def getDay(FileName):
    """
    Returns day field from filename ame YYYYMMDD date.
    
    Parameters
    ----------
    FileName : string
        Filename containing YYYYMMDD date.
    
    Returns
    -------
    int
        Day of month based on YYYYMMDD date.
    """
    dateString = getYMD(FileName)
    return int(dateString[-2:])

def getDateRange(FileName):
    """
    Return the date range (as a string) from FileName.
    
    Takes filename YYYYMMDD date as ending date and returns
    date range string (in YYYYMMDD-YYYYMMDD format) based
    on presumed start date of file.  Works for both monthly
    and annual sampling.
    
    Parameters
    ----------
    FileName : string
        Filename containing YYYYMMDD date.
    
    Returns
    -------
    string
        Date range in YYYYMMDD-YYYYMMDD format.
    """
    fileYear = str(getYear(FileName))
    fileMonth = getMonth(FileName)
    if fileMonth < 10:
        fileMonth = '0' + str(fileMonth)
    else:
        fileMonth = str(fileMonth)
    fileEndDay = str(getDay(FileName))
    if getDataSamplingInterval(FileName) == 'mth':
        fileStartDay = '01'
        fileStartDate = fileYear + '/' + fileMonth + '/' + fileStartDay
        fileEndDate = fileYear + '/' + fileMonth + '/' + fileEndDay
    elif getDataSamplingInterval(FileName) == 'ann':
        fileStartDate = fileYear + '/01/01'
        fileEndDate = fileYear + '/12/31'
    else:
        print 'Unable to determine sampling interval for file ', FileName
        sys.exit()
    
    fileDateRange = fileStartDate + '-' + fileEndDate
    return fileDateRange

def getFieldName(FileName):
    """
    Determine field name from FileName.

    Employs AWAP/BIOS2 file naming conventions to determine
    field  from supplied file name.
    
    Parameters
    ----------
    FileName : string
        Filename conforming to AWAP/BIOS2 naming convention.
    
    Returns
    -------
    string
        Name of field stored in file.
    """
    
    nameChunks = re.split('\W+|_', FileName)
    """
    Work through nameChunks, excising chunks corresponding to
    known sampling interval , date, and percentile rank tags.
    The chunk(s) that remain defines the field name.  If more
    than one chunk remains, these chunks are joined with an
    underscore to reconstruct the fieldname.
    """
    for chunk in nameChunks:
        if chunk in SamplingIntervals:
            nameChunks.remove(chunk)
            continue
        if chunk in PercentileRankTag:
            nameChunks.remove(chunk)
            continue
        if len(chunk) == 8 and chunk.isdigit():
            nameChunks.remove(chunk)
            continue
    
    if len(nameChunks) == 0:
        print 'awapIO.getFieldname():: Error--No fieldname detected for file ', FileName
        sys.exit()
    
    if len(nameChunks) == 1:
        return nameChunks[0]
    
    return '_'.join(nameChunks)

def getDataSamplingInterval(FileName):
    """
    Determines the time sampling interval from filename conforming to
    AWAP/BIOS2 naming conventions.
    
    Parameters
    ----------
    FileName : string
        Name of file.
    
    Returns
    -------
    string
        Sampling interval tag.
    """
    
    nameChunks = re.split('\W+|_', FileName)
    
    for sampInt in SamplingIntervals:
        if sampInt in nameChunks:
            return sampInt
    """
    If no sampling interval is detected, flag error and exit
    """
    print 'awapIO.getDataSamplingInterval():: No interval tag for file ', FileName
    print 'Legitimate sampling interval tags = ', SamplingIntervals
    sys.exit()

def filterByMonthName(FileList, Month):
    """
    Filter a filename list, returning those containing nominated
    month abbreviation.
    
    Parameters
    ----------
    FileList : list
        List of filenames to be filtered.
    Month : string
        Abbreviation of desired month name.
    
    Returns
    -------
    list
        List of filenames only corresponding to the desired month.
    """
    if not is_a_Month(Month.lower()):
        print 'ERROR:  month name ', Month, ' not recognised.'
        sys.exit()
    
    """
    Get month number from abbreviation.
    """
    monthAbbr = Month.lower()
    monthNum = MonthAbbrToNum[monthAbbr]
    
    """
    Take FileList, build a new list filtered by month.
    """
    filteredList = filterByMonthNum(FileList, monthNum)
    return filteredList

def filterByMonthNum(FileList, MonthNum):
    """
    Filter a filename list, returning those containing the nominated
    month number.
    
    Parameters
    ----------
    FileList : list
        List of filenames.
    MonthNum : int
        Two-digit month specifier; 0 < MonthNum <= 12.
    
    Returns
    -------
    list
        List of filenames with YYYYMMDD date having the desired
        month number.
    """
    if not is_a_MonthNum(MonthNum):
        print 'ERROR:  month number ', MonthNum, ' not recognised.'
        sys.exit()
    
    FilteredList = []
    for file in FileList:
        if getMonth(file) == MonthNum:
            FilteredList.append(file)
    
    return FilteredList

def filterBySeason(FileList, SeasonName):
    """
    Filter filename list by season.
    
    Parameters
    ----------
    FileList : list
        List of filenames.
    SeasonName : string
        Abbreviation for season; i.e., 'djf', 'mam', 'jja', 'son'.
    
    Returns
    -------
    list
        Filename list whose elements fall within the desired season.
    """
    
    month_list = seasonToMonths(SeasonName)
    month_files = []
    for month in month_list:
        month_files += filterByMonthName(FileList, month)
    
    month_files = sortByDate(month_files)

    """
    At this point we have a time-ordered, subsetted list of files
    corresponding     to the months comprising a particular season.
    We do not yet, however, have valid seasons--i.e., runs of
    consecutive months making up the season.
    """
    
    for offset in range(0, len(month_files) - 3):
        month_run = [getMonthAbbr(file) for file in
                     month_files[offset:offset + 3]]
        if month_run == month_list:
            first_ind = offset
            break
    
    for backset in range(3, len(month_files)):
        month_run = [getMonthAbbr(file) for file in
                     month_files[-backset:len(month_files) - backset + 3]]
        if month_run == month_list:
            last_ind = len(month_files) - backset + 3
            break
    
    return month_files[first_ind:last_ind]

def filterByFieldName(FileList, FieldName):
    """
    Filter a list of filenames, returning those with nominated FieldName.
    
    Parameters
    ----------
    FileList : list
        List of filenames.
    FieldName : string
        Name of desired field.
    
    Returns
    -------
    list
        List of filenames that contain the desired field.
    """
    FilteredList = []
    for file in FileList:
        if getFieldName[file] == FieldName:
            FilteredList.append(file)

def filterBySamplingInterval(FileList, IntervalName):
    """
    Include files only having the supplied time sampling IntervalName.
    
    Parameters
    ----------
    FileList : list
        List of filenames to be filtered
    IntervalName : string
        Abbreviation of sampling interval; i.e., 'mon', and 'ann'.
    
    Returns
    -------
    list
        List of filenames whose sampling interval tags match the
        desired sampling interval.
    """
    filteredList = []
    for file in FileList:
        if getDataSamplingInterval(file) == IntervalName:
            filteredList.append(file)
    
    return filteredList

def filterByDateRange(FileList, StartDate, EndDate):
    """
    Filter FileList, keeping only files with StartDate <=  YYYYMMDD <= EndDate.
    
    Parameters
    ----------
    FileList : list
        List of filenames to be filtered.
    StartDate : int
        Eight-digit start date in YYYYMMDD format.
    EndDate : int
        Eight-digit end date in YYYYMMDD format.
    
    Returns
    -------
    list
        List of files falling within the desired date range.
    """
    filteredList = []
    for file in FileList:
        fileDate = getDate(file)
        if (fileDate >= StartDate) and (fileDate <= EndDate):
            filteredList.append(file)
    filteredList = sorted(filteredList, key=getYMD)
    return filteredList

def getLats(HeaderDict, Reverse=True):
    """
    Computes a NumPy array of latitudes given a header dictionary.
    
    Parameters
    ----------
    HeaderDict : dict
        AWAP/BIOS2 header dictionary.
    Reverse : bool
        True (False) value yields latitudes in decreasing
        (increasing) order.
    
    Returns
    -------
    numpy.ndarray
        Vector of floating-point latitude values.
    """
    numLats = HeaderDict['nrows']
    minLat = HeaderDict['yllcorner']
    dLat = HeaderDict['cellsize']
    """
    Note minLat refers to the *bottom edge* of the grid cell located
    at the LLHC of the domain.  The array lats[:], however, refers
    to the locations of the *grid cell centers*.  The quantity
    maxLat--defined below--refers to the top edge of the grid
    cell located at the UHRC of the domain.
    """
    maxLat = numLats * dLat + minLat
    """
    The quantity firstLat is the latitude of the center of the grid
    cell at the the LLHC of the domain.  Likewise, lastLat is the
    latitude of the center of the grid cell at the the URHC of the
    domain.
    """
    firstLat = minLat + 0.5 * dLat
    lastLat = firstLat + (numLats - 1) * dLat
    lats = np.linspace(firstLat, lastLat, num=numLats)
    
    if Reverse:
        lats = lats[::-1]
    
    return lats


def getLons(HeaderDict):
    """
    Computes a NumPy array of longitudes given a header dictionary.
    
    Parameters
    ----------
    HeaderDict : dict
        AWAP/BIOS2 header dictionary.
    
    Returns
    -------
    numpy.ndarray
        Vector of floating-point longitude values.
    """
    numLons = HeaderDict['ncols']
    minLon = HeaderDict['xllcorner']
    dLon = HeaderDict['cellsize']
    
    """
    Note minLon refers to the *left edge* of the grid cell located 
    at the LLHC of the domain.  The array lons[:], however, refers
    to the longitudes of the *grid cell centers*.  The quantity 
    maxLon--defined below--refers to the right edge of the grid 
    cell located at the UHRC of the domain.
    """
    maxLon = numLons * dLon + minLon
    """
    The quantity firstLon is the longitude of the center of the grid 
    cell at the the LLHC of the domain.  Likewise, lastLon is the 
    longitude of the center of the grid cell at the the URHC of the 
    domain.
    """
    firstLon = minLon + 0.5 * dLon
    lastLon = firstLon + (numLons -1) * dLon
    lons = np.linspace(firstLon, lastLon, num=numLons)
    
    return lons
    
def getAreaWeights(HeaderDict, Radius=1.0):
    """
    Computes a NumPy array of area weights given a header dictionary.

    N.B.:  This array of weights is solely a function of the geometry 
    of the domain.  It is is *unmasked* and *unnormalised*. A .flt file 
    must be read to determine which cells have missing values in order 
    to create a masked array.  

    Parameters
    ----------
    HeaderDict : dict
        AWAP/BIOS2 header dictionary.
    Radius : float
        Radius of spherical approximation of the geoid; default value
        is unity.

    Returns
    -------
    numpy.ndarray
        Two-dimensional array of unnormalised/unmasked floating-point 
        weights.
    """
    
    import math
    
    lats = getLats(HeaderDict)
    lons = getLons(HeaderDict)
    dLat = math.radians(HeaderDict['cellsize'])
    dLon = dLat
    numLats = lats.size
    numLons = lons.size
    
    weights = np.ndarray((numLats,numLons))
    for i in range(0,numLats):
        for j in range(0,numLons):
            weights[i,j] = math.cos(math.radians(lats[i])) * dLat * dLon
            
    weights *= Radius * Radius
    
    return weights

def getMaskedAreaWeights(HeaderDict, Radius=1.0):
    """
    Computes a masked NumPy array of area weights given a header dictionary.

    N.B.:  This array of weights is solely a function of the geometry 
    and topography of the domain.  It is *unnormalised*. The .flt file 
    referenced in the header is read to determine which cells have 
    missing values in order to create the masked array.  

    Parameters
    ----------
    HeaderDict : dict
        AWAP/BIOS2 header dictionary.
    Radius : float
        Radius of spherical approximation of the geoid; default value
        is unity.

    Returns
    -------
    numpy.ndarray
        Two-dimensional masked array of unnormalised floating-point weights.
    """

    """
    Compute spatial weights from domain geometry.
    """
    bareWeights = getAreaWeights(HeaderDict, Radius)
    """
    Using missing data values, define the domain's topography mask.
    """
    topoMask = getMaskFromFltFile(HeaderDict)
    """
    Create a NumPy masked arrary with the masked weights.
    """
    missingFlag = HeaderDict['nodata_value']
    maskedWeights = ma.masked_array(bareWeights, mask=topoMask, 
                                    fill_value=missingFlag)

    return maskedWeights

def getMaskFromFltFile(HeaderDict, FloatFileName=None):
    """
    Create 2D spatial mask from missing values.

    Parameters
    ----------
    HeaderDict : dict
        AWAP/BIOS2 header dictionary.
    FLoatFileName : string
        Field data floating-point filename to be used to define mask;
        default value None reverts to filename nominated in the header
        dictionary.

    Returns
    -------
    numpy.ndarray
        Two-dimensional mask.
    """

    if FloatFileName == None:
        fltFileName = HeaderDict['fileNameStem'] + floatFilenameExt
    else:
        fltFileName = FloatFileName

    mask =  readAWAP_flt(HeaderDict)._get_mask()

    return mask

    







            
    
        

