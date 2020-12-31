#!/bin/bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"
logs=$maindir/logs

# setting inputs and common variables; these define paths below
sm=6
task=cardgame
sub=$1
nruns=$2
analysis=$3
ncopes=$4

# subjects have a max of 4 runs
MAINOUTPUT=${maindir}/derivatives/fsl/sub-${sub}
INPUT1=${MAINOUTPUT}/L1_task-${task}_model-01_${analysis}_run-01_sm-${sm}.feat
INPUT2=${MAINOUTPUT}/L1_task-${task}_model-01_${analysis}_run-02_sm-${sm}.feat
INPUT3=${MAINOUTPUT}/L1_task-${task}_model-01_${analysis}_run-03_sm-${sm}.feat
INPUT4=${MAINOUTPUT}/L1_task-${task}_model-01_${analysis}_run-04_sm-${sm}.feat

# check for existing output and re-do if missing/incomplete
OUTPUT=${MAINOUTPUT}/L2_task-${task}_model-01_${analysis}_sm-${sm}
if [ -e ${OUTPUT}.gfeat/cope${ncopes}.feat/cluster_mask_zstat1.nii.gz ]; then
	echo "skipping existing output"
else
	echo "re-doing: ${OUTPUT}" >> $logs/re-runL2.log
	rm -rf ${OUTPUT}.gfeat

	# set output template and run template-specific analyses
	# note: sed will not complain if there is nothing to find/replace, so no need for if/elif statements for nruns
	ITEMPLATE=${maindir}/templates/L2_copes-${ncopes}_runs-${nruns}.fsf
	OTEMPLATE=${MAINOUTPUT}/L2_task-${task}_model-01_${analysis}.fsf
	sed -e 's@OUTPUT@'$OUTPUT'@g' \
	-e 's@INPUT1@'$INPUT1'@g' \
	-e 's@INPUT2@'$INPUT2'@g' \
	-e 's@INPUT3@'$INPUT3'@g' \
	-e 's@INPUT4@'$INPUT4'@g' \
	<$ITEMPLATE> $OTEMPLATE
	feat $OTEMPLATE

	# delete unused files
	for cope in `seq ${ncopes}`; do
		rm -rf ${OUTPUT}.gfeat/cope${cope}.feat/stats/res4d.nii.gz
		rm -rf ${OUTPUT}.gfeat/cope${cope}.feat/stats/corrections.nii.gz
		rm -rf ${OUTPUT}.gfeat/cope${cope}.feat/stats/threshac1.nii.gz
		rm -rf ${OUTPUT}.gfeat/cope${cope}.feat/filtered_func_data.nii.gz
		rm -rf ${OUTPUT}.gfeat/cope${cope}.feat/var_filtered_func_data.nii.gz
	done

fi
