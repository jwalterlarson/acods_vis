import os
import subprocess

from mpi4py import MPI

getPath = 'echo $PATH'
subprocess.Popen(getPath, shell=True)

myCommand = "time ffmpeg -r 12 -pattern_type glob -i '/data/noflush/lar104/awap_tools/Apps/ACODS_National/Sbar_g/Full/mth_Sbar_g_*.jpeg' -r 25 ./mth_Sbar_w_19110101-20111231.mp4"

subprocess.Popen(myCommand, shell=True)
