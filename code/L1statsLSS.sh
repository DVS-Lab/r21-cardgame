#!/usr/bin/env bash

# This script will perform Level 1 statistics in FSL.
# Rather than having multiple scripts, we are merging three analyses
# into this one script:
#		1) activation
#		2) seed-based ppi
#		3) network-based ppi
# Note that activation analysis must be performed first.
# Seed-based PPI and Network PPI should follow activation analyses.

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"
logs=$maindir/logs

# study-specific inputs
TASK=cardgame
sm=6 # this is already hard coded into all fsf files
sub=$1
run=$2
ppi=$3 # 0 for activation, otherwise seed region or network
trial=`zeropad $4 2` # pad zeros
logfile=$5

# set inputs and general outputs (should not need to chage across studies in Smith Lab)
MAINOUTPUT=${maindir}/derivatives/fsl/sub-${sub}
mkdir -p $MAINOUTPUT
DATA=${maindir}/derivatives/fmriprep/sub-${sub}/func/sub-${sub}_task-${TASK}_run-${run}_space-MNI152NLin2009cAsym_desc-preproc_bold.nii.gz
NVOLUMES=`fslnvols ${DATA}`
CONFOUNDEVS=${maindir}/derivatives/fsl/confounds/sub-${sub}/sub-${sub}_task-${TASK}_run-${run}_desc-fslConfounds.tsv
if [ ! -e $CONFOUNDEVS ]; then
	echo "missing: $CONFOUNDEVS " >> $logfile
	exit # exiting to ensure nothing gets run without confounds
fi

# EV files
EVDIR=${maindir}/derivatives/fsl/EVfiles/sub-${sub}/singletrial/run-0${run}
SINGLETRIAL=${EVDIR}/run-0${run}_SingleTrial${trial}.txt
OTHERTRIAL=${EVDIR}/run-0${run}_OtherTrials${trial}.txt

# create common directory for zstat outputs
zoutdir=${MAINOUTPUT}/LSS-images_task-${TASK}_model-02_conn-${ppi}_run-0${run}_sm-${sm}
if [ ! -d $zoutdir ]; then
	mkdir -p $zoutdir
fi

# if network (ecn or dmn), do nppi; otherwise, do activation or seed-based ppi
if [ "$ppi" == "ecn" -o "$ppi" == "dmn" ]; then

	# check for output and skip existing
	OUTPUT=${MAINOUTPUT}/L1_task-${TASK}_model-02_type-nppi-${ppi}_run-0${run}_sm-${sm}_trial-${trial}
	if [ -e ${zoutdir}/zstat_trial-${trial}.nii.gz ]; then
		exit
	else
		echo "running: $OUTPUT " >> $logfile
		rm -rf ${OUTPUT}.feat
	fi

	# network extraction. need to ensure you have run Level 1 activation
	MASK=${MAINOUTPUT}/L1_task-${TASK}_model-01_type-act_run-0${run}_sm-${sm}.feat/mask
	if [ ! -e ${MASK}.nii.gz ]; then
		echo "cannot run nPPI because you're missing $MASK"
		exit
	fi
	for net in `seq 0 9`; do
		NET=${maindir}/masks/nets/rPNAS_2mm_net000${net}.nii
		TSFILE=${MAINOUTPUT}/ts_task-${TASK}_net000${net}_nppi-${ppi}_run-0${run}.txt
		fsl_glm -i $DATA -d $NET -o $TSFILE --demean -m $MASK
		eval INPUT${net}=$TSFILE
	done

	# set names for network ppi (we generally only care about ECN and DMN)
	DMN=$INPUT3
	ECN=$INPUT7
	if [ "$ppi" == "dmn" ]; then
		MAINNET=$DMN
		OTHERNET=$ECN
	else
		MAINNET=$ECN
		OTHERNET=$DMN
	fi

	# create template and run analyses
	ITEMPLATE=${maindir}/templates/L1_template-m02_netppi.fsf
	OTEMPLATE=${MAINOUTPUT}/L1_task-${TASK}_model-02_seed-${ppi}_run-0${run}_trial-${trial}.fsf
	sed -e 's@OUTPUT@'$OUTPUT'@g' \
	-e 's@NVOLUMES@'$NVOLUMES'@g' \
	-e 's@DATA@'$DATA'@g' \
	-e 's@SINGLETRIAL@'$SINGLETRIAL'@g' \
	-e 's@OTHERTRIAL@'$OTHERTRIAL'@g' \
	-e 's@CONFOUNDEVS@'$CONFOUNDEVS'@g' \
	-e 's@MAINNET@'$MAINNET'@g' \
	-e 's@OTHERNET@'$OTHERNET'@g' \
	-e 's@INPUT0@'$INPUT0'@g' \
	-e 's@INPUT1@'$INPUT1'@g' \
	-e 's@INPUT2@'$INPUT2'@g' \
	-e 's@INPUT4@'$INPUT4'@g' \
	-e 's@INPUT5@'$INPUT5'@g' \
	-e 's@INPUT6@'$INPUT6'@g' \
	-e 's@INPUT8@'$INPUT8'@g' \
	-e 's@INPUT9@'$INPUT9'@g' \
	<$ITEMPLATE> $OTEMPLATE
	feat $OTEMPLATE

else # otherwise, do activation and seed-based ppi

	# set output based in whether it is activation or ppi
	if [ "$ppi" == "0" ]; then
		TYPE=act
		OUTPUT=${MAINOUTPUT}/L1_task-${TASK}_model-02_type-${TYPE}_run-0${run}_sm-${sm}_trial-${trial}
	else
		TYPE=ppi
		OUTPUT=${MAINOUTPUT}/L1_task-${TASK}_model-02_type-${TYPE}_seed-${ppi}_run-0${run}_sm-${sm}_trial-${trial}
	fi

	# check for output and skip existing
	if [ -e ${zoutdir}/zstat_trial-${trial}.nii.gz ]; then
		exit
	else
		echo "running: $OUTPUT " >> $logfile
		rm -rf ${OUTPUT}.feat
	fi

	# create template and run analyses
	ITEMPLATE=${maindir}/templates/L1_template-m02_${TYPE}.fsf
	OTEMPLATE=${MAINOUTPUT}/L1_sub-${sub}_task-${TASK}_model-02_seed-${ppi}_run-0${run}_trial-${trial}.fsf
	if [ "$ppi" == "0" ]; then
		sed -e 's@OUTPUT@'$OUTPUT'@g' \
		-e 's@DATA@'$DATA'@g' \
		-e 's@SINGLETRIAL@'$SINGLETRIAL'@g' \
		-e 's@OTHERTRIAL@'$OTHERTRIAL'@g' \
		-e 's@CONFOUNDEVS@'$CONFOUNDEVS'@g' \
		-e 's@NVOLUMES@'$NVOLUMES'@g' \
		<$ITEMPLATE> $OTEMPLATE
	else
		PHYS=${MAINOUTPUT}/ts_task-${TASK}_mask-${ppi}_run-0${run}.txt
		MASK=${maindir}/masks/${ppi}.nii.gz
		fslmeants -i $DATA -o $PHYS -m $MASK
		sed -e 's@OUTPUT@'$OUTPUT'@g' \
		-e 's@DATA@'$DATA'@g' \
		-e 's@SINGLETRIAL@'$SINGLETRIAL'@g' \
		-e 's@OTHERTRIAL@'$OTHERTRIAL'@g' \
		-e 's@PHYS@'$PHYS'@g' \
		-e 's@CONFOUNDEVS@'$CONFOUNDEVS'@g' \
		-e 's@NVOLUMES@'$NVOLUMES'@g' \
		<$ITEMPLATE> $OTEMPLATE
	fi
	feat $OTEMPLATE
fi


# copy zstat image to common output folder and delete feat output
cp ${OUTPUT}.feat/stats/zstat1.nii.gz ${zoutdir}/zstat_trial-${trial}.nii.gz
rm -rf ${OUTPUT}.feat
