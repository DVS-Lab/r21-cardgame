#!/usr/bin/env bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"

# base paths
TASK=cardgame
MAINOUTPUT=${maindir}/derivatives/fsl/L3_model-01_task-${TASK}_n28_wStimEffects
outputdir=${maindir}/derivatives/imaging_plots
mkdir -p $outputdir

# activation: ROI name and other path information
for ROI in act_lVLPFC act_SMA act_rVLPFC act_IFG act_thalamus; do
	MASK=${maindir}/masks/singletrial-masks/${ROI}.nii.gz
	TYPE=act
	for COPENUM in 1 2 3 4; do # act
		cnum_padded=`zeropad ${COPENUM} 2`
		DATA=`ls -1 ${MAINOUTPUT}/L3_task-${TASK}_type-${TYPE}_cnum-${cnum_padded}_*.gfeat/cope1.feat/filtered_func_data.nii.gz`
		fslmeants -i $DATA -o ${outputdir}/${ROI}_type-${TYPE}_cope-${cnum_padded}.txt -m ${MASK}
	done
done
# clust_img=$basedir/L3_task-${task}_${other}_cnum-${copenum}_cname-${copename}_${model}.gfeat/cope1.feat/cluster_mask_zstat${cov}.nii.gz
# MAX=`fslstats $i -R | awk '{ print $2 }'`
# Nclusters=`fslstats $clust_img -R | awk '{ print $2 }'`
# for c in `seq ${Nclusters}`; do
# 	fslmaths $clust_img -thr $c -uthr $c -bin ${NVdir}/cluster_${task}_${other}_${model}_${copename}_cov-${cov}_cluster${c}.nii.gz
# done



# tangential to paper, but could still add to neurovault
# conn_rFPN_precun.nii.gz
# conn_rFPN_VLPFC.nii.gz

# connectivity: ROI name and other path information
for seedROI in "leftVS dACC" "leftVS LPFC" "leftVS visual" "rightVS dACC" "rightVS dPrecun" "rightVS vPrecun"; do
	set -- $seedROI
	seed=$1
	ROI=$2
	TYPE=ppi_seed-${seed}
	MASK=${maindir}/masks/singletrial-masks/conn_${seed}_${ROI}.nii.gz
	for COPENUM in 11 12 13 14; do
		cnum_padded=`zeropad ${COPENUM} 2`
		DATA=`ls -1 ${MAINOUTPUT}/L3_task-${TASK}_type-${TYPE}_cnum-${cnum_padded}_*.gfeat/cope1.feat/filtered_func_data.nii.gz`
		fslmeants -i $DATA -o ${outputdir}/${ROI}_type-${TYPE}_cope-${cnum_padded}.txt -m ${MASK}
	done
done


# # connectivity: ROI name and other path information (flipped to check laterality)
# for seedROI in "leftVS dACC" "leftVS LPFC" "leftVS visual" "rightVS dACC" "rightVS dPrecun" "rightVS vPrecun" "rightVS VMPFC_cov" "rightVS DLPFC_cov"; do
# 	set -- $seedROI
# 	seed=$1
# 	ROI=$2
# 	if [ "$seed" == "leftVS" ]; then
# 		seed_flipped=rightVS
# 	elif [ "$seed" == "rightVS" ]; then
# 		seed_flipped=leftVS
# 	else
# 		echo "no match for $seed, so exiting..."
# 	fi
# 	TYPE=ppi_seed-${seed_flipped}
# 	MASK=${maindir}/masks/singletrial-masks/conn_${seed}_${ROI}.nii.gz
# 	for COPENUM in 11 12 13 14; do
# 		cnum_padded=`zeropad ${COPENUM} 2`
# 		DATA=`ls -1 ${MAINOUTPUT}/L3_task-${TASK}_type-${TYPE}_cnum-${cnum_padded}_*.gfeat/cope1.feat/filtered_func_data.nii.gz`
# 		fslmeants -i $DATA -o ${outputdir}/${ROI}_type-${TYPE}_cope-${cnum_padded}_flipped.txt -m ${MASK}
# 	done
# done
