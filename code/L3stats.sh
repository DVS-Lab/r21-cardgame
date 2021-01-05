#!/bin/bash

# This script will perform Level 3 statistics in FSL.
# This script can also run randomise (permutation-based stats) on existing output.
# By default, randomise will not be be run if FEAT analyses do not exist. In addition,
# randomise will only be run on specific copes.

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"
logs=$maindir/logs

# study-specific inputs and general output folder
task=cardgame
copenum=$1
copename=$2
REPLACEME=$3 # this defines the parts of the path that differ across analyses
MAINOUTPUT=${maindir}/derivatives/fsl/L3_model-01_task-${task}_n31
mkdir -p $MAINOUTPUT

# set outputs and check for existing
cnum_pad=`zeropad ${copenum} 2`
OUTPUT=${MAINOUTPUT}/L3_task-${task}_${REPLACEME}_cnum-${cnum_pad}_cname-${copename}_onegroup
if [ -e ${OUTPUT}.gfeat/cope1.feat/cluster_mask_zstat1.nii.gz ]; then

	# run randomise if output doesn't exist and the contrasts (copes) are valid
	cd ${OUTPUT}.gfeat/cope1.feat
	if [ ! -e randomise_tfce_corrp_tstat2.nii.gz ] && [ $copenum -ge 5 ]; then
		randomise -i filtered_func_data.nii.gz -o randomise -d design.mat -t design.con -m mask.nii.gz -T -c 2.3 -n 10000
	fi

else # try to run feat and clean up previous effort with partial output

	echo "re-doing: ${OUTPUT}" >> $logs/re-runL3.log
	rm -rf ${OUTPUT}.gfeat

	# create template and run FEAT analyses
	ITEMPLATE=${maindir}/templates/L3_template_n31.fsf
	OTEMPLATE=${MAINOUTPUT}/L3_task-${task}_${REPLACEME}_copenum-${copenum}_onegroup.fsf
	sed -e 's@OUTPUT@'$OUTPUT'@g' \
	-e 's@COPENUM@'$copenum'@g' \
	-e 's@REPLACEME@'$REPLACEME'@g' \
	-e 's@BASEDIR@'$maindir'@g' \
	<$ITEMPLATE> $OTEMPLATE
	feat $OTEMPLATE

	# delete unused files
	rm -rf ${OUTPUT}.gfeat/cope${cope}.feat/stats/res4d.nii.gz
	rm -rf ${OUTPUT}.gfeat/cope${cope}.feat/stats/corrections.nii.gz
	rm -rf ${OUTPUT}.gfeat/cope${cope}.feat/stats/threshac1.nii.gz
	#rm -rf ${OUTPUT}.gfeat/cope${cope}.feat/filtered_func_data.nii.gz
	rm -rf ${OUTPUT}.gfeat/cope${cope}.feat/var_filtered_func_data.nii.gz

fi
