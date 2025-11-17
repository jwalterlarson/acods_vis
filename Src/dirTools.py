"""
Directory manipulation tools.
"""
import os

def isReadableDir(Directory):
    """
    Check to see if Directory exists and is a directory.

    Parameters
    ----------
    Directory : string
        Pathname of directory.
    
    Returns
    -------
    bool
        True (False) if directory exists at the supplied pathname.
    """
    if os.path.exists(Directory):
        if os.path.isdir(Directory):
            if os.access(Directory, os.R_OK):
                return True
            else:
                print ':: FATAL--directory ', Directory, ' exists but is not readable.'
                return False
        else:
            print ':: FATAL--file ', Directory, ' exists but is not a directory.'
            return False
    else:
        print ':: FATAL--directory ', Directory, ' does not exist.'
        return False

def isWriteableDirectory(Directory):
    """
    Is the supplied directory user-writable?
    
    Parameters
    ----------
    Directory : string
        Name of nominated directory.
    
    Returns
    -------
    bool
        True if directory exists and is user-writable; False otherwise.
    """
    if os.path.exists(Directory):
        if os.path.isdir(Directory):
            if os.access(Directory, os.W_OK):
                return True
            else:
                print ':: FATAL--directory ', Directory, ' exists but is not writeable.'
                return False
        else:
            print ':: FATAL--file ', Directory, ' exists but is not a directory.'
            return False
    else:
        print ':: FATAL--directory ', Directory, ' does not exist.'
        return False

def safeMakeDir(Directory):
    """
    Safe directory creation mechanism.  Returns True for success.
    
    Parameters
    ----------
    Directory : string
        Name of nominated directory.
    
    Returns
    -------
    bool
        True (False) for success (failure).
    """
    if os.path.exists(Directory):
        if os.path.isdir(Directory):
            return True
        else:
            print ':: FATAL--file ', Directory, ' exists but is not a directory.'
            return False
    else:
        os.makedirs(Directory)
        return True
