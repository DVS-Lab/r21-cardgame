#!/usr/bin/env bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"


TASK=cardgame
sm=6

# analyses we are doing; these define input/output paths in the L1stats.sh script
for ppi in 0 bilateralVLPFC leftVLPFC leftVS rightVS ecn dmn; do # putting 0 first will indicate "activation"

	# loops through the subject/run list
	cat ${scriptdir}/runcount_excluded.tsv |
	while read subrun; do
		set -- ${subrun}
		sub=$1
		nruns=$2
		echo "running: sub-${sub} on conn-${ppi} at `date`..."

		# skip for initial testing
		if [ $sub -gt 222 ]; then
			continue
		fi
		
		for run in `seq ${nruns}`; do

			# skip the bad runs
			if [ $sub -eq 217 ] && [ $run -eq 2 ]; then
				continue
			elif [ $sub -eq 232 ] && [ $run -eq 4 ]; then
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
				for mask in act-leftVLPFC act-leftVS act-rightVLPFC act-rightVS; do
					maskfile=${maindir}/masks/singletrial-masks/${mask}.nii.gz
					fslmeants -i ${zoutdir}/sub-${sub}_run-0${run}_conn-${ppi}_merged_z.nii.gz \
						-o ${out_meants}/sub-${sub}_run-0${run}_mask-${mask}.txt \
						-m ${maskfile}
				done
			elif [ "${ppi}" == "leftVLPFC" ]; then
				for mask in leftVLPFCconn-DLPFC leftVLPFCconn-MPFC leftVLPFCconn-PCC; do
					maskfile=${maindir}/masks/singletrial-masks/${mask}.nii.gz
					fslmeants -i ${zoutdir}/sub-${sub}_run-0${run}_conn-${ppi}_merged_z.nii.gz \
						-o ${out_meants}/sub-${sub}_run-0${run}_mask-${mask}.txt \
						-m ${maskfile}
				done
			elif [ "${ppi}" == "ecn" ]; then
				for mask in ECNconn-MPFC ECNconn-insula; do
					maskfile=${maindir}/masks/singletrial-masks/${mask}.nii.gz
					fslmeants -i ${zoutdir}/sub-${sub}_run-0${run}_conn-${ppi}_merged_z.nii.gz \
						-o ${out_meants}/sub-${sub}_run-0${run}_mask-${mask}.txt \
						-m ${maskfile}
				done
			elif [ "${ppi}" == "dmn" ]; then
				mask=DMNconn-leftVS
				maskfile=${maindir}/masks/singletrial-masks/${mask}.nii.gz
				fslmeants -i ${zoutdir}/sub-${sub}_run-0${run}_conn-${ppi}_merged_z.nii.gz \
					-o ${out_meants}/sub-${sub}_run-0${run}_mask-${mask}.txt \
					-m ${maskfile}
			elif [ "${ppi}" == "bilateralVLPFC" ]; then
				mask=bilateralVLPFCconn-parietal
				maskfile=${maindir}/masks/singletrial-masks/${mask}.nii.gz
				fslmeants -i ${zoutdir}/sub-${sub}_run-0${run}_conn-${ppi}_merged_z.nii.gz \
					-o ${out_meants}/sub-${sub}_run-0${run}_mask-${mask}.txt \
					-m ${maskfile}
			elif [ "${ppi}" == "leftVS" ]; then
				mask=leftVSconn-visual
				maskfile=${maindir}/masks/singletrial-masks/${mask}.nii.gz
				fslmeants -i ${zoutdir}/sub-${sub}_run-0${run}_conn-${ppi}_merged_z.nii.gz \
					-o ${out_meants}/sub-${sub}_run-0${run}_mask-${mask}.txt \
					-m ${maskfile}
			elif [ "${ppi}" == "rightVS" ]; then
				mask=rightVSconn-DLPFC
				maskfile=${maindir}/masks/singletrial-masks/${mask}.nii.gz
				fslmeants -i ${zoutdir}/sub-${sub}_run-0${run}_conn-${ppi}_merged_z.nii.gz \
					-o ${out_meants}/sub-${sub}_run-0${run}_mask-${mask}.txt \
					-m ${maskfile}
			else
				"error: mask not found"
			fi


		done
	done
done
