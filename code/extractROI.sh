#!/usr/bin/env bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"

# activation: ROI name and other path information
for ROI in bilateralVLPFC leftVLPFC rightVLPFC bilateralVS leftVS rightVS; do
	MASK=${maindir}/masks/${ROI}.nii.gz
	TASK=cardgame
	TYPE=ppi_seed-rightVS
	outputdir=${maindir}/derivatives/imaging_plots
	mkdir -p $outputdir

	for COPENUM in 1 2 3 4; do # act

		cnum_padded=`zeropad ${COPENUM} 2`
		MAINOUTPUT=${maindir}/derivatives/fsl/L3_model-01_task-cardgame_n28_FLAME1+2
		DATA=`ls -1 ${MAINOUTPUT}/L3_task-${TASK}_type-${TYPE}_cnum-${cnum_padded}_*.gfeat/cope1.feat/filtered_func_data.nii.gz`
		fslmeants -i $DATA -o ${outputdir}/${ROI}_type-${TYPE}_cope-${cnum_padded}.txt -m ${MASK}

	done
done

# network conn: ROI name and other path information
for ROI in DMNstriatal_conn; do
	MASK=${maindir}/masks/${ROI}.nii.gz
	TASK=cardgame
	TYPE=nppi-dmn
	outputdir=${maindir}/derivatives/imaging_plots
	mkdir -p $outputdir

	for COPENUM in 11 12 13 14; do

		cnum_padded=`zeropad ${COPENUM} 2`
		MAINOUTPUT=${maindir}/derivatives/fsl/L3_model-01_task-cardgame_n28_FLAME1+2 # seed-based controls end with _ppi
		# L3_task-cardgame_type-nppi-dmn_cnum-17_cname-ppi_R_vlpfc-tpj_onegroup.gfeat
		DATA=`ls -1 ${MAINOUTPUT}/L3_task-${TASK}_type-${TYPE}_cnum-${cnum_padded}_*.gfeat/cope1.feat/filtered_func_data.nii.gz`
		fslmeants -i $DATA -o ${outputdir}/${ROI}_type-${TYPE}_cope-${cnum_padded}.txt -m ${MASK}

	done
done


# seed-based conn: ROI name and other path information
for ROI in rightVSconn-DLPFC; do
	MASK=${maindir}/masks/singletrial-masks/${ROI}.nii.gz
	TASK=cardgame
	TYPE=ppi_seed-rightVS
	outputdir=${maindir}/derivatives/imaging_plots
	mkdir -p $outputdir

	for COPENUM in 11 12 13 14; do

		cnum_padded=`zeropad ${COPENUM} 2`
		MAINOUTPUT=${maindir}/derivatives/fsl/L3_model-01_task-cardgame_n28_FLAME1+2_ppi # seed-based controls end with _ppi
		# L3_task-cardgame_type-ppi_seed-rightVS_cnum-19_cname-ppi_interaction_onegroup.gfeat
		DATA=`ls -1 ${MAINOUTPUT}/L3_task-${TASK}_type-${TYPE}_cnum-${cnum_padded}_*.gfeat/cope1.feat/filtered_func_data.nii.gz`
		fslmeants -i $DATA -o ${outputdir}/${ROI}_type-${TYPE}_cope-${cnum_padded}.txt -m ${MASK}

	done
done
