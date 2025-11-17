#################################################
AWAP Tools -- J.W. Larson (2013).
Created in collaboration with CSIRO/CMAR for the
analysis and visualisation of Australian Water 
Availability Project (AWAP) and Australian Carbon
Observatory Data Service (ACODS) data products.
#################################################

-----------
CONTENTS:
-----------

In this directory there are several subdirectories:

Src         The AWAP_Tools source code

Test        Unit tester scripts

Data        Data used by the unit testers

VisPars     Visualisation parameters used by the test
            and production scripts

Masks       Raster masks for Australia and various 
	    regionalisation schemes

Shapefiles  Australian and boundary shapefiles for 
	    various regionalisation schemes

-----------
QUICKSTART:
-----------
The source code for AWAP tools resides in the Src
subdirectory.  Add this directory to the PYTHONPATH
environment variable on your system.  On Unix, Linux,
and OS X systems under bash, do this:

> export PYTHONPATH=<path to AWAP_Tools/Src>:$PYTHONPATH

That should allow one to run any of the Test suite 
scripts in the Test subdirectory.