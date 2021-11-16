#!/usr/bin/env bash

# Example code for running group-level MRIQC


# ensure paths are correct irrespective from where user runs the script
codedir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
dsroot="$(dirname "$codedir")"

# base bids directory (from Bart: https://github.com/klabhub/ds.tacsCardGame)
#inputdir=/data/projects/ds.tacsCardGame
# copied to dsroot on 2021-11-07


# make derivatives/mriqc folder if it doesn't exist
if [ ! -d $dsroot/derivatives/mriqc ]; then
	mkdir -p $dsroot/derivatives/mriqc
fi



# make scratch
scratch=/data/scratch/`whoami`
if [ ! -d $scratch ]; then
	mkdir -p $scratch
fi

# no space left on device error for v0.15.2 and higher
# https://neurostars.org/t/mriqc-no-space-left-on-device-error/16187/1
# https://github.com/poldracklab/mriqc/issues/850
TEMPLATEFLOW_DIR=/data/tools/templateflow
export SINGULARITYENV_TEMPLATEFLOW_HOME=/opt/templateflow
singularity run --cleanenv \
-B ${TEMPLATEFLOW_DIR}:/opt/templateflow \
-B $dsroot/bids:/data \
-B $dsroot/derivatives/mriqc:/out \
-B $scratch:/scratch \
/data/tools/mriqc-0.16.1.simg \
/data /out \
participant -w /scratch
