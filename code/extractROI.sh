#!/usr/bin/env bash

# make everything relative to root of the GitHub repository
cd ..
maindir=`pwd`

ROI=$1

MASK=${maindir}/masks/${ROI}.nii.gz #NAcc_resliced or PreCun_func
TASK=cardgame
TYPE=ppi

for COPENUM in 11 12 13 14; do
#for COPENUM in 1 2 3 4; do

	cnum_padded=`zeropad ${COPENUM} 2`

	MAINOUTPUT=${maindir}/derivatives/fsl/L3_n27_model-01_FLAME1+2_exclusions
	OUTPUT=${MAINOUTPUT}/L3_task-${TASK}_model-01_type-${TYPE}_cope-${cnum_padded}
	DATA=${OUTPUT}.gfeat/cope1.feat/filtered_func_data.nii.gz
	fslmeants -i $DATA -o ${ROI}_type-${TYPE}_cope-${cnum_padded}.txt -m ${MASK}


done
