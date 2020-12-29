#!/usr/bin/env bash

# make everything relative to root of the GitHub repository
cd ..
maindir=`pwd`
MAINOUTPUT=${maindir}/derivatives/fsl/L3_n27_model-01_FLAME1+2_exclusions
TASK=cardgame

#
#TYPE=nppi-ecn
#for COPENUM in 5 6 7 8 9 10 15 16 17 18 19; do
#	
#	cnum_padded=`zeropad ${COPENUM} 2`
#	OUTPUT=${MAINOUTPUT}/L3_task-${TASK}_model-01_type-${TYPE}_cope-${cnum_padded}
#	cd ${OUTPUT}.gfeat/cope1.feat
#	randomise -i filtered_func_data.nii.gz -o randomise -d design.mat -t design.con -m mask.nii.gz -T -c 2.3 -n 10000 &
#	sleep 1
#done
#
#
#TYPE=nppi-dmn
#for COPENUM in 5 6 7 8 9 10 15 16 17 18 19; do
#	
#	cnum_padded=`zeropad ${COPENUM} 2`
#	OUTPUT=${MAINOUTPUT}/L3_task-${TASK}_model-01_type-${TYPE}_cope-${cnum_padded}
#	cd ${OUTPUT}.gfeat/cope1.feat
#	randomise -i filtered_func_data.nii.gz -o randomise -d design.mat -t design.con -m mask.nii.gz -T -c 2.3 -n 10000 &
#	sleep 1
#done
#
#
#
#TYPE=act
#for COPENUM in 5 6 7 8 9`; do
#	
#	cnum_padded=`zeropad ${COPENUM} 2`
#	OUTPUT=${MAINOUTPUT}/L3_task-${TASK}_model-01_type-${TYPE}_cope-${cnum_padded}
#	cd ${OUTPUT}.gfeat/cope1.feat
#	randomise -i filtered_func_data.nii.gz -o randomise -d design.mat -t design.con -m mask.nii.gz -T -c 2.3 -n 10000 &
#	sleep 1
#done


TYPE=ppi-TPJ
for COPENUM in 5 6 7 8 9 10 15 16 17 18 19; do
	
	cnum_padded=`zeropad ${COPENUM} 2`
	OUTPUT=${MAINOUTPUT}/L3_task-${TASK}_model-01_type-${TYPE}_cope-${cnum_padded}
	cd ${OUTPUT}.gfeat/cope1.feat
	randomise -i filtered_func_data.nii.gz -o randomise -d design.mat -t design.con -m mask.nii.gz -T -c 2.3 -n 10000 &
	sleep 1
done

TYPE=ppi-VLPFC
for COPENUM in 5 6 7 8 9 10 15 16 17 18 19; do
	
	cnum_padded=`zeropad ${COPENUM} 2`
	OUTPUT=${MAINOUTPUT}/L3_task-${TASK}_model-01_type-${TYPE}_cope-${cnum_padded}
	cd ${OUTPUT}.gfeat/cope1.feat
	randomise -i filtered_func_data.nii.gz -o randomise -d design.mat -t design.con -m mask.nii.gz -T -c 2.3 -n 10000 &
	sleep 1
done
