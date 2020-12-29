#!/usr/bin/env bash

# make everything relative to root of the GitHub repository
cd ..
maindir=`pwd`

MAINOUTPUT=${maindir}/derivatives/fsl/L3_n27_model-01_FLAME1+2_exclusions

TASK=cardgame
ncopes=19
TYPE=nppi-ecn

#5 6 7 8 9 10 15 16 17 18 19

for COPENUM in 5 6 7 8 9 10 15 16 17 18 19; do
	
	cnum_padded=`zeropad ${COPENUM} 2`
	
	# delete incomplete output
	if [ ! -d ${MAINOUTPUT} ]; then
		mkdir $MAINOUTPUT
	fi
	OUTPUT=${MAINOUTPUT}/L3_task-${TASK}_model-01_type-${TYPE}_cope-${cnum_padded}
	if [ -e ${OUTPUT}.gfeat/cope1.feat/cluster_mask_zstat1.nii.gz ]; then
		continue
	else
		rm -rf ${OUTPUT}.gfeat
	fi
	
	ITEMPLATE=${maindir}/code/templates/L3_template_n27.fsf
	OTEMPLATE=${MAINOUTPUT}/L3_task-${TASK}_model-01_type-${TYPE}_cope-${cnum_padded}.fsf
	sed -e 's@OUTPUT@'$OUTPUT'@g' \
	-e 's@TYPE@'$TYPE'@g' \
	-e 's@COPENUM@'$COPENUM'@g' \
	<$ITEMPLATE> $OTEMPLATE
	
	# runs feat on output template
	feat $OTEMPLATE &
	sleep 1
done


ncopes=9
TYPE=act

for COPENUM in `seq $ncopes`; do
	
	cnum_padded=`zeropad ${COPENUM} 2`
	
	# delete incomplete output
	if [ ! -d ${MAINOUTPUT} ]; then
		mkdir $MAINOUTPUT
	fi
	OUTPUT=${MAINOUTPUT}/L3_task-${TASK}_model-01_type-${TYPE}_cope-${cnum_padded}
	if [ -e ${OUTPUT}.gfeat/cope1.feat/cluster_mask_zstat1.nii.gz ]; then
		continue
	else
		rm -rf ${OUTPUT}.gfeat
	fi
	
	ITEMPLATE=${maindir}/code/templates/L3_template_n27.fsf
	OTEMPLATE=${MAINOUTPUT}/L3_task-${TASK}_model-01_type-${TYPE}_cope-${cnum_padded}.fsf
	sed -e 's@OUTPUT@'$OUTPUT'@g' \
	-e 's@TYPE@'$TYPE'@g' \
	-e 's@COPENUM@'$COPENUM'@g' \
	<$ITEMPLATE> $OTEMPLATE
	
	# runs feat on output template
	feat $OTEMPLATE &
	#cd ${OUTPUT}.gfeat/cope1.feat
	#randomise -i filtered_func_data.nii.gz -o randomise -d design.mat -t design.con -m mask.nii.gz -T -c 2.3 -n 10000

done


ncopes=19
TYPE=ppi-TPJ

for COPENUM in `seq $ncopes`; do
	
	cnum_padded=`zeropad ${COPENUM} 2`
	
	# delete incomplete output
	if [ ! -d ${MAINOUTPUT} ]; then
		mkdir $MAINOUTPUT
	fi
	OUTPUT=${MAINOUTPUT}/L3_task-${TASK}_model-01_type-${TYPE}_cope-${cnum_padded}
	if [ -e ${OUTPUT}.gfeat/cope1.feat/cluster_mask_zstat1.nii.gz ]; then
		continue
	else
		rm -rf ${OUTPUT}.gfeat
	fi
	
	ITEMPLATE=${maindir}/code/templates/L3_template_n27.fsf
	OTEMPLATE=${MAINOUTPUT}/L3_task-${TASK}_model-01_type-${TYPE}_cope-${cnum_padded}.fsf
	sed -e 's@OUTPUT@'$OUTPUT'@g' \
	-e 's@TYPE@'$TYPE'@g' \
	-e 's@COPENUM@'$COPENUM'@g' \
	<$ITEMPLATE> $OTEMPLATE
	
	# runs feat on output template
	feat $OTEMPLATE &
	#cd ${OUTPUT}.gfeat/cope1.feat
	#randomise -i filtered_func_data.nii.gz -o randomise -d design.mat -t design.con -m mask.nii.gz -T -c 2.3 -n 10000

done

ncopes=19
TYPE=ppi-VLPFC

for COPENUM in `seq $ncopes`; do
	
	cnum_padded=`zeropad ${COPENUM} 2`
	
	# delete incomplete output
	if [ ! -d ${MAINOUTPUT} ]; then
		mkdir $MAINOUTPUT
	fi
	OUTPUT=${MAINOUTPUT}/L3_task-${TASK}_model-01_type-${TYPE}_cope-${cnum_padded}
	if [ -e ${OUTPUT}.gfeat/cope1.feat/cluster_mask_zstat1.nii.gz ]; then
		continue
	else
		rm -rf ${OUTPUT}.gfeat
	fi
	
	ITEMPLATE=${maindir}/code/templates/L3_template_n27.fsf
	OTEMPLATE=${MAINOUTPUT}/L3_task-${TASK}_model-01_type-${TYPE}_cope-${cnum_padded}.fsf
	sed -e 's@OUTPUT@'$OUTPUT'@g' \
	-e 's@TYPE@'$TYPE'@g' \
	-e 's@COPENUM@'$COPENUM'@g' \
	<$ITEMPLATE> $OTEMPLATE
	
	# runs feat on output template
	feat $OTEMPLATE &
	#cd ${OUTPUT}.gfeat/cope1.feat
	#randomise -i filtered_func_data.nii.gz -o randomise -d design.mat -t design.con -m mask.nii.gz -T -c 2.3 -n 10000

done

#randomise -i filtered_func_data.nii.gz -o randomise -d design.mat -t design.con -m mask.nii.gz -T -c 3.1 -n 10000
#randomise_parallel -i filtered_func_data.nii.gz -o randomise -d design.mat -t design.con -m mask.nii.gz -T -c 3.1 -n 10000
