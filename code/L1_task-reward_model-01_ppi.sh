#!/usr/bin/env bash

# make everything relative to root of the GitHub repository
cd ..
maindir=`pwd`

sub=$1
run=$2
ppi=$3
TASK=cardgame


# delete incomplete output
MAINOUTPUT=${maindir}/derivatives/fsl/sub-${sub}
mkdir -p $MAINOUTPUT
OUTPUT=${MAINOUTPUT}/L1_task-${TASK}_model-01_type-ppi-${ppi}_run-0${run}_sm-6
if [ -e ${OUTPUT}.feat/cluster_mask_zstat1.nii.gz ]; then
	exit
else
	rm -rf ${OUTPUT}.feat
	echo ${OUTPUT} >> check_L1.log
fi

DATA=${MAINOUTPUT}/L1_task-${TASK}_model-01_type-act_run-0${run}_sm-6.feat/filtered_func_data.nii.gz
EVDIR=${maindir}/derivatives/fsl/EVfiles/sub-${sub}/run-0${run}
NVOLUMES=`fslnvols ${DATA}`

PHYS=${MAINOUTPUT}/ts_task-cardgame_mask-${ppi}_run-0${run}.txt
MASK=${maindir}/masks/${ppi}.nii.gz
fslmeants -i $DATA -o $PHYS -m $MASK

ITEMPLATE=${maindir}/code/templates/L1_template-m01_ppi.fsf
OTEMPLATE=${MAINOUTPUT}/L1_task-${TASK}_model-01_type-ppi-${ppi}_run-0${run}.fsf
sed -e 's@OUTPUT@'$OUTPUT'@g' \
-e 's@DATA@'$DATA'@g' \
-e 's@EVDIR@'$EVDIR'@g' \
-e 's@NVOLUMES@'$NVOLUMES'@g' \
-e 's@PHYS@'$PHYS'@g' \
<$ITEMPLATE> $OTEMPLATE

# runs feat on output template
feat $OTEMPLATE

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