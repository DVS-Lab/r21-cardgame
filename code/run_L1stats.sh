#!/bin/bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
basedir="$(dirname "$scriptdir")"

# create log file to record what we did and when
logs=$basedir/logs
logfile=${logs}/rerunL1_date-`date +"%FT%H%M"`.log

# analyses we are doing; these define input/output paths in the L1stats.sh script
for ppi in 0 striatum FPole interactionC1 interactionC2 interactionC3 interactionC4 interactionC5; do # putting 0 first will indicate "activation"

	# loops through the subject/run list
	cat ${scriptdir}/runcount.tsv |
	while read subrun; do
		set -- ${subrun}
		sub=$1
		nruns=$2

		for run in `seq ${nruns}`; do
	  	# Manages the number of jobs and cores
	  	SCRIPTNAME=${basedir}/code/L1stats.sh
	  	NCORES=25
	  	while [ $(ps -ef | grep -v grep | grep $SCRIPTNAME | wc -l) -ge $NCORES ]; do
	    		sleep 1s
	  	done
	  	bash $SCRIPTNAME $sub $run $ppi $logfile &
	  	sleep 1s
	  done

	done
done
