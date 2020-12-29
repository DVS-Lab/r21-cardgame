# example code for FMRIPREP
# runs FMRIPREP on input subject
# usage: bash fmriprep.sh sub
# example: bash fmriprep.sh 102

sub=$1

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"

# bids directory (from Bart: https://github.com/klabhub/ds.tacsCardGame)
bidsdir=/data/projects/ds.tacsCardGame

# make derivatives and scratch folders if they do not exist.
if [ ! -d $maindir/derivatives ]; then
	mkdir -p $maindir/derivatives
fi
scratchdir=/data/scratch/`whoami`
if [ ! -d $scratchdir ]; then
	mkdir -p $scratchdir
fi

singularity run --cleanenv -B $bidsdir:/base -B /data/tools/licenses:/opts -B $scratchdir:/scratch \
/data/tools/fmriprep-20.1.0.simg \
/base/bids /base/derivatives \
participant --participant_label $sub \
--use-aroma --fs-no-reconall --fs-license-file /opts/fs_license.txt -w /scratch
