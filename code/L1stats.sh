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

# study-specific inputs
TASK=cardgame
sm=6 # this is already hard coded into all fsf files
sub=$1
run=$2
ppi=$3 # 0 for activation, otherwise seed region or network
logfile=$4


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
EVDIR=${maindir}/derivatives/fsl/EVfiles/sub-${sub}/run-0${run}

# if network (ecn or dmn), do nppi; otherwise, do activation or seed-based ppi
if [ "$ppi" == "ecn" -o "$ppi" == "dmn" -o "$ppi" == "rfpn" -o "$ppi" == "lfpn" ]; then

	# check for output and skip existing
	OUTPUT=${MAINOUTPUT}/L1_task-${TASK}_model-01_type-nppi-${ppi}_run-0${run}_sm-${sm}
	if [ -e ${OUTPUT}.feat/cluster_mask_zstat1.nii.gz ]; then
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

	# set names for network ppi
	if [ "$ppi" == "dmn" ]; then
		DMN=$INPUT3
		ECN=$INPUT7
		MAINNET=$DMN
		OTHERNET=$ECN
		ITEMPLATE=${maindir}/templates/L1_template-m01_netppi.fsf
	elif [ "$ppi" == "ecn" ]; then
		DMN=$INPUT3
		ECN=$INPUT7
		MAINNET=$ECN
		OTHERNET=$DMN
		ITEMPLATE=${maindir}/templates/L1_template-m01_netppi.fsf
	elif [ "$ppi" == "rfpn" ]; then
		RFPN=$INPUT8
		LFPN=$INPUT9
		MAINNET=$RFPN
		OTHERNET=$LFPN
		ITEMPLATE=${maindir}/templates/L1_template-m01_netppi_FPN.fsf
	elif [ "$ppi" == "lfpn" ]; then
		RFPN=$INPUT8
		LFPN=$INPUT9
		MAINNET=$LFPN
		OTHERNET=$RFPN
		ITEMPLATE=${maindir}/templates/L1_template-m01_netppi_FPN.fsf
	fi


	# create template and run analyses
	OTEMPLATE=${MAINOUTPUT}/L1_task-${TASK}_model-01_seed-${ppi}_run-0${run}.fsf
	sed -e 's@OUTPUT@'$OUTPUT'@g' \
	-e 's@NVOLUMES@'$NVOLUMES'@g' \
	-e 's@DATA@'$DATA'@g' \
	-e 's@EVDIR@'$EVDIR'@g' \
	-e 's@CONFOUNDEVS@'$CONFOUNDEVS'@g' \
	-e 's@MAINNET@'$MAINNET'@g' \
	-e 's@OTHERNET@'$OTHERNET'@g' \
	-e 's@INPUT0@'$INPUT0'@g' \
	-e 's@INPUT1@'$INPUT1'@g' \
	-e 's@INPUT2@'$INPUT2'@g' \
	-e 's@INPUT3@'$INPUT3'@g' \
	-e 's@INPUT4@'$INPUT4'@g' \
	-e 's@INPUT5@'$INPUT5'@g' \
	-e 's@INPUT6@'$INPUT6'@g' \
	-e 's@INPUT7@'$INPUT7'@g' \
	-e 's@INPUT8@'$INPUT8'@g' \
	-e 's@INPUT9@'$INPUT9'@g' \
	<$ITEMPLATE> $OTEMPLATE
	feat $OTEMPLATE

else # otherwise, do activation and seed-based ppi

	# set output based in whether it is activation or ppi
	if [ "$ppi" == "0" ]; then
		TYPE=act
		OUTPUT=${MAINOUTPUT}/L1_task-${TASK}_model-01_type-${TYPE}_run-0${run}_sm-${sm}
	else
		TYPE=ppi
		OUTPUT=${MAINOUTPUT}/L1_task-${TASK}_model-01_type-${TYPE}_seed-${ppi}_run-0${run}_sm-${sm}
	fi

	# check for output and skip existing
	if [ -e ${OUTPUT}.feat/cluster_mask_zstat1.nii.gz ]; then
		exit
	else
		echo "running: $OUTPUT " >> $logfile
		rm -rf ${OUTPUT}.feat
	fi

	# create template and run analyses
	ITEMPLATE=${maindir}/templates/L1_template-m01_${TYPE}.fsf
	OTEMPLATE=${MAINOUTPUT}/L1_sub-${sub}_task-${TASK}_model-01_seed-${ppi}_run-0${run}.fsf
	if [ "$ppi" == "0" ]; then
		sed -e 's@OUTPUT@'$OUTPUT'@g' \
		-e 's@DATA@'$DATA'@g' \
		-e 's@EVDIR@'$EVDIR'@g' \
		-e 's@CONFOUNDEVS@'$CONFOUNDEVS'@g' \
		-e 's@NVOLUMES@'$NVOLUMES'@g' \
		<$ITEMPLATE> $OTEMPLATE
	else
		PHYS=${MAINOUTPUT}/ts_task-${TASK}_mask-${ppi}_run-0${run}.txt
		MASK=${maindir}/masks/seed-${ppi}.nii.gz
		fslmeants -i $DATA -o $PHYS -m $MASK --eig
		sed -e 's@OUTPUT@'$OUTPUT'@g' \
		-e 's@DATA@'$DATA'@g' \
		-e 's@EVDIR@'$EVDIR'@g' \
		-e 's@PHYS@'$PHYS'@g' \
		-e 's@CONFOUNDEVS@'$CONFOUNDEVS'@g' \
		-e 's@NVOLUMES@'$NVOLUMES'@g' \
		<$ITEMPLATE> $OTEMPLATE
	fi
	feat $OTEMPLATE
fi

# fix registration as per NeuroStars post:
# https://neurostars.org/t/performing-full-glm-analysis-with-fsl-on-the-bold-images-preprocessed-by-fmriprep-without-re-registering-the-data-to-the-mni-space/784/3
mkdir -p ${OUTPUT}.feat/reg
ln -s $FSLDIR/etc/flirtsch/ident.mat ${OUTPUT}.feat/reg/example_func2standard.mat
ln -s $FSLDIR/etc/flirtsch/ident.mat ${OUTPUT}.feat/reg/standard2example_func.mat
ln -s ${OUTPUT}.feat/mean_func.nii.gz ${OUTPUT}.feat/reg/standard.nii.gz

# delete unused files
rm -rf ${OUTPUT}.feat/stats/res4d.nii.gz
rm -rf ${OUTPUT}.feat/stats/corrections.nii.gz
rm -rf ${OUTPUT}.feat/stats/threshac1.nii.gz
rm -rf ${OUTPUT}.feat/filtered_func_data.nii.gz
