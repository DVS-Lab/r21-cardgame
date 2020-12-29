# example code for FMRIPREP
# runs FMRIPREP on input subject
# usage: bash fmriprep.sh sub
# example: bash fmriprep.sh 102

sub=$1

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"

# bids directory (from Bart: https://github.com/klabhub/ds.tacsCardGame)
datadir=/data/projects/ds.tacsCardGame
inputdir=${datadir}/bids

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
singularity run --cleanenv -B $inputdir:/in -B $outputdir:/out -B /data/tools/licenses:/opts -B $scratchdir:/scratch \
/data/tools/fmriprep-20.1.0.simg \
/in /out \
participant --participant_label $sub \
--use-aroma --fs-no-reconall --fs-license-file /opts/fs_license.txt -w /scratch
