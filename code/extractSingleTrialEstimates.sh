#!/usr/bin/env bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"


TASK=cardgame
sm=6



# analyses we are doing; these define input/output paths in the L1stats.sh script
#for ppi in 0 lfpn rfpn ecn dmn rightVS leftVS; do # putting 0 first will indicate "activation"
for ppi in 0 rfpn rightVS leftVS; do # putting 0 first will indicate "activation"

	# loops through the subject/run list
	cat ${scriptdir}/runcount_excluded.tsv |
	while read subrun; do
		set -- ${subrun}
		sub=$1
		nruns=$2
		echo "running: sub-${sub} on conn-${ppi} at `date`..."


		for run in `seq ${nruns}`; do

			# skip the bad runs
			if [ $sub -eq 217 ] && [ $run -eq 2 ]; then
				continue
			elif [ $sub -eq 232 ] && [ $run -eq 3 ]; then
				continue
			fi


			# common directory for zstat outputs
			MAINOUTPUT=${maindir}/derivatives/fsl/sub-${sub}
			zoutdir=${MAINOUTPUT}/LSS-images_task-${TASK}_model-02_conn-${ppi}_run-0${run}_sm-${sm}
			cd $zoutdir
			rm -rf sub-${sub}*.nii.gz
			fslmerge -t sub-${sub}_run-0${run}_conn-${ppi}_merged_z zstat_trial-*.nii.gz

			# output for extractions
			out_meants=${maindir}/derivatives/singletrial/sub-${sub}
			mkdir -p ${out_meants}


			if [ "${ppi}" == "0" ]; then
				for mask in act_lVLPFC act_IFG act_rVLPFC act_SMA act_thalamus; do
					maskfile=${maindir}/masks/singletrial-masks/${mask}.nii.gz
					fslmeants -i ${zoutdir}/sub-${sub}_run-0${run}_conn-${ppi}_merged_z.nii.gz \
						-o ${out_meants}/sub-${sub}_run-0${run}_mask-${mask}.txt \
						-m ${maskfile}
				done
			elif [ "${ppi}" == "rfpn" ]; then
				for mask in conn_rFPN_VLPFC conn_rFPN_precun; do
					maskfile=${maindir}/masks/singletrial-masks/${mask}.nii.gz
					fslmeants -i ${zoutdir}/sub-${sub}_run-0${run}_conn-${ppi}_merged_z.nii.gz \
						-o ${out_meants}/sub-${sub}_run-0${run}_mask-${mask}.txt \
						-m ${maskfile}
				done
			elif [ "${ppi}" == "leftVS" ]; then
				for mask in conn_leftVS_LPFC conn_leftVS_dACC conn_leftVS_visual; do
					maskfile=${maindir}/masks/singletrial-masks/${mask}.nii.gz
					fslmeants -i ${zoutdir}/sub-${sub}_run-0${run}_conn-${ppi}_merged_z.nii.gz \
						-o ${out_meants}/sub-${sub}_run-0${run}_mask-${mask}.txt \
						-m ${maskfile}
				done
			elif [ "${ppi}" == "rightVS" ]; then
				for mask in conn_rightVS_dACC conn_rightVS_dPrecun conn_rightVS_vPrecun; do
					maskfile=${maindir}/masks/singletrial-masks/${mask}.nii.gz
					fslmeants -i ${zoutdir}/sub-${sub}_run-0${run}_conn-${ppi}_merged_z.nii.gz \
						-o ${out_meants}/sub-${sub}_run-0${run}_mask-${mask}.txt \
						-m ${maskfile}
				done
			else
				"error: mask not found"
			fi


		done
	done
done
