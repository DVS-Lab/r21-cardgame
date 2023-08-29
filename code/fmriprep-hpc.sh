#!/bin/bash
#PBS -l walltime=24:00:00
#PBS -N fmriprep-all
#PBS -q normal
#PBS -m ae
#PBS -M david.v.smith@temple.edu
#PBS -l nodes=12:ppn=4

# load modules and go to workdir
module load fsl/6.0.2
source $FSLDIR/etc/fslconf/fsl.sh
module load singularity/3.8.5
cd $PBS_O_WORKDIR

# ensure paths are correct
maindir=~/work/r21-cardgame #this should be the only line that has to change if the rest of the script is set up correctly
scriptdir=$maindir/code
bidsdir=$maindir/bids
logdir=$maindir/logs
mkdir -p $logdir


rm -f $logdir/cmd_fmriprep_${PBS_JOBID}.txt
touch $logdir/cmd_fmriprep_${PBS_JOBID}.txt

# make derivatives folder if it doesn't exist.
# let's keep this out of bids for now
if [ ! -d $maindir/derivatives ]; then
	mkdir -p $maindir/derivatives
fi

scratchdir=~/scratch/fmriprep
if [ ! -d $scratchdir ]; then
	mkdir -p $scratchdir
fi

TEMPLATEFLOW_DIR=~/work/tools/templateflow
MPLCONFIGDIR_DIR=~/work/mplconfigdir
export SINGULARITYENV_TEMPLATEFLOW_HOME=/opt/templateflow
export SINGULARITYENV_MPLCONFIGDIR=/opt/mplconfigdir

# need to change this to a more targetted list of subjects
for sub in `ls -1d $bidsdir/sub-*`; do
	sub=${sub:(-3)}
	echo singularity run --cleanenv \
	-B ${TEMPLATEFLOW_DIR}:/opt/templateflow \
	-B ${MPLCONFIGDIR_DIR}:/opt/mplconfigdir \
	-B $maindir:/base \
	-B ~/work/tools/licenses:/opts \
	-B $scratchdir:/scratch \
	~/work/tools/fmriprep-23.1.3.simg \
	/base/bids /base/derivatives/fmriprep \
	participant --participant_label $sub \
	--stop-on-first-crash \
	--nthreads 12 \
	--cifti-output 91k \
	--output-spaces fsLR fsaverage MNI152NLin6Asym MNI152NLin2009cAsym \
	--skip-bids-validation \
	--fs-license-file /opts/fs_license.txt -w /scratch >> $logdir/cmd_fmriprep_${PBS_JOBID}.txt
done

torque-launch -p $logdir/chk_fmriprep_${PBS_JOBID}.txt $logdir/cmd_fmriprep_${PBS_JOBID}.txt
