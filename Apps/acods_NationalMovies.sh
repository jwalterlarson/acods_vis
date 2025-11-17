#!/bin/bash
#PBS -l walltime=1:00:00
#PBS -l vmem=128GB
#PBS -l nodes=3:ppn=12

##cd ${PBS_O_WORKDIR:-.}
cd /data/noflush/lar104/awap_tools/Apps

module load python/2.7.3 
module load openmpi
module load ffmpeg/2.2.1
export PYTHONPATH=/home/cmar/lar104/lib/python2.7/site-packages:/data/noflush/lar104/awap_tools/Src:$PYTHONPATH

mpiexec --mca mpi_warn_on_fork 0 -n 26 python parOzNationalMovies.py acodsOzNationalMovies.conf

