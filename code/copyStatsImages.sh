#!/bin/bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
basedir="$(dirname "$scriptdir")"

sm=6
task=cardgame

# loops through the subject/run list
cat ${scriptdir}/runcount.tsv |
while read subruninfo; do
	set -- ${subruninfo}
	sub=$1
	nruns=$2

	for analysis in type-ppi_seed-VS type-act; do
		for con in 1 2 3 4; do # R_vlpfc, R_tpj, P_vlpfc, Ptpj

			MAINOUTPUT=${maindir}/derivatives/fsl/sub-${sub}
			neurovault_runlevel=${maindir}/derivatives/neurovault/runlevel/${analysis}
			mkdir -p $neurovault_runlevel
			neurovault_sublevel=${maindir}/derivatives/neurovault/sublevel/${analysis}
			mkdir -p $neurovault_sublevel

			# copy run-level stats, only for good runs
			if [ $sub -eq 217 ]; then
				for run in 1 3; do
					zstat_in_L1=${MAINOUTPUT}/L1_task-${task}_model-01_${analysis}_run-0${run}_sm-${sm}.feat/stats/zstat${con}.nii.gz
					zstat_out_L1=${neurovault_runlevel}/sub-${sub}_task-${task}_run-0${run}_con-${con}_zstat.nii.gz
					cp $zstat_in_L1 $zstat_out_L1
					cope_in_L1=${MAINOUTPUT}/L1_task-${task}_model-01_${analysis}_run-0${run}_sm-${sm}.feat/stats/cope${con}.nii.gz
					cope_out_L1=${neurovault_runlevel}/sub-${sub}_task-${task}_run-0${run}_con-${con}_cope.nii.gz
					cp $cope_in_L1 $cope_out_L1
				done
			elif [ $sub -eq 232 ]; then
				for run in 1 2 4; do
					zstat_in_L1=${MAINOUTPUT}/L1_task-${task}_model-01_${analysis}_run-0${run}_sm-${sm}.feat/stats/zstat${con}.nii.gz
					zstat_out_L1=${neurovault_runlevel}/sub-${sub}_task-${task}_run-0${run}_con-${con}_zstat.nii.gz
					cp $zstat_in_L1 $zstat_out_L1
					cope_in_L1=${MAINOUTPUT}/L1_task-${task}_model-01_${analysis}_run-0${run}_sm-${sm}.feat/stats/cope${con}.nii.gz
					cope_out_L1=${neurovault_runlevel}/sub-${sub}_task-${task}_run-0${run}_con-${con}_cope.nii.gz
					cp $cope_in_L1 $cope_out_L1
				done
			else
				for run in `seq $nruns`; do
					zstat_in_L1=${MAINOUTPUT}/L1_task-${task}_model-01_${analysis}_run-0${run}_sm-${sm}.feat/stats/zstat${con}.nii.gz
					zstat_out_L1=${neurovault_runlevel}/sub-${sub}_task-${task}_run-0${run}_con-${con}_zstat.nii.gz
					cp $zstat_in_L1 $zstat_out_L1
					cope_in_L1=${MAINOUTPUT}/L1_task-${task}_model-01_${analysis}_run-0${run}_sm-${sm}.feat/stats/cope${con}.nii.gz
					cope_out_L1=${neurovault_runlevel}/sub-${sub}_task-${task}_run-0${run}_con-${con}_cope.nii.gz
					cp $cope_in_L1 $cope_out_L1
				done
			fi

			# copy subject level stats
			zstat_in_L2=${MAINOUTPUT}/L2_task-${task}_model-01_${analysis}_sm-${sm}.gfeat/cope${con}.feat/stats/zstat1.nii.gz
			zstat_out_L2=${neurovault_sublevel}/sub-${sub}_task-${task}_con-${con}_zstat.nii.gz
			cp $zstat_in_L2 $zstat_out_L2
			cope_in_L2=${MAINOUTPUT}/L2_task-${task}_model-01_${analysis}_sm-${sm}.gfeat/cope${con}.feat/stats/cope1.nii.gz
			cope_out_L2=${neurovault_sublevel}/sub-${sub}_task-${task}_con-${con}_cope.nii.gz
			cp $cope_in_L2 $cope_out_L2

		done
	done
done
