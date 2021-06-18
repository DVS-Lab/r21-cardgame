#!/usr/bin/env bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"


TASK=cardgame
TYPE=act
sm=6

# analyses we are doing; these define input/output paths in the L1stats.sh script
for ppi in 0 bilateralVLPFC leftVLPFC leftVS rightVS ecn dmn; do # putting 0 first will indicate "activation"

	# loops through the subject/run list
	cat ${scriptdir}/runcount_excluded.tsv |
	while read subrun; do
		set -- ${subrun}
		sub=$1
		nruns=$2

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
			fslmerge -t sub-${sub}_run0-${run}_merged_z zstat_trial-*.nii.gz
			#fslmeants -i $DATA -o ${outputdir}/${ROI}_type-${TYPE}_cope-${cnum_padded}.txt -m ${MASK}

		done
	done
done
