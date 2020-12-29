# example code for FMRIPREP
# runs FMRIPREP on input subject
# usage: bash fmriprep.sh sub
# example: bash fmriprep.sh 102

sub=$1

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"

# base bids directory (from Bart: https://github.com/klabhub/ds.tacsCardGame)
inputdir=/data/projects/ds.tacsCardGame

# make derivatives and scratch folders if they do not exist.
outputdir=${maindir}/derivatives
if [ ! -d ${outputdir} ]; then
	mkdir -p ${outputdir}
fi
scratchdir=/data/scratch/`whoami`
if [ ! -d $scratchdir ]; then
	mkdir -p $scratchdir
fi

# run fmriprep through singularity
# note: singularity doesn't seem to read the bids directory correctly unless it has a parent directory in the container
singularity run --cleanenv -B ${inputdir}:/input -B $outputdir:/output -B /data/tools/licenses:/opts -B $scratchdir:/scratch \
/data/tools/fmriprep-20.1.0.simg \
/input/bids /output \
participant --participant_label $sub \
--use-aroma --fs-no-reconall --fs-license-file /opts/fs_license.txt -w /scratch
