#!/usr/bin/env bash

# make everything relative to root of the GitHub repository
cd ..
maindir=`pwd`

sub=$1
nruns=$2
ppi=$3
TASK=cardgame
ncopes=28

# delete incomplete output
MAINOUTPUT=${maindir}/derivatives/fsl/sub-${sub}
OUTPUT=${MAINOUTPUT}/L2_task-${TASK}_model-01_type-nppi-${ppi}
if [ -e ${OUTPUT}.gfeat/cope${ncopes}.feat/cluster_mask_zstat1.nii.gz ]; then
	exit
else
	rm -rf ${OUTPUT}.gfeat
	echo ${OUTPUT} >> check_L2.log
fi

INPUT1=${MAINOUTPUT}/L1_task-${TASK}_model-01_type-nppi-${ppi}_run-01.feat
INPUT2=${MAINOUTPUT}/L1_task-${TASK}_model-01_type-nppi-${ppi}_run-02.feat
INPUT3=${MAINOUTPUT}/L1_task-${TASK}_model-01_type-nppi-${ppi}_run-03.feat
INPUT4=${MAINOUTPUT}/L1_task-${TASK}_model-01_type-nppi-${ppi}_run-04.feat

ITEMPLATE=${maindir}/code/templates/L2_copes-${ncopes}_runs-${nruns}.fsf
OTEMPLATE=${MAINOUTPUT}/L2_task-${TASK}_model-01_type-ppi-${ppi}_copes-${ncopes}_runs-${nruns}.fsf
sed -e 's@OUTPUT@'$OUTPUT'@g' \
-e 's@INPUT1@'$INPUT1'@g' \
-e 's@INPUT2@'$INPUT2'@g' \
-e 's@INPUT3@'$INPUT3'@g' \
-e 's@INPUT4@'$INPUT4'@g' \
<$ITEMPLATE> $OTEMPLATE

# runs feat on output template
feat $OTEMPLATE


# delete unused files
for c in `seq $ncopes`; do
	rm -rf ${OUTPUT}.gfeat/cope${c}.feat/filtered_func_data.nii.gz
	rm -rf ${OUTPUT}.gfeat/cope${c}.feat/var_filtered_func_data.nii.gz
	rm -rf ${OUTPUT}.gfeat/cope${c}.feat/stats/res4d.nii.gz
	rm -rf ${OUTPUT}.gfeat/cope${c}.feat/stats/corrections.nii.gz
	rm -rf ${OUTPUT}.gfeat/cope${c}.feat/stats/threshac1.nii.gz
done
