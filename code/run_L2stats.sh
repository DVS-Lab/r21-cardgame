#!/bin/bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
basedir="$(dirname "$scriptdir")"

# create log file to record what we did and when
logs=$basedir/logs
logfile=${logs}/rerunL2_date-`date +"%FT%H%M"`.log

# analyses we are doing; these define input/output paths in the L2stats.sh script
#for analysisinfo in "type-act 9"; do
for analysisinfo in "type-ppi_seed-striatum 19" "type-ppi_seed-FPole 19" "type-ppi_seed-interactionC1 19" "type-ppi_seed-interactionC2 19" "type-ppi_seed-interactionC3 19" "type-ppi_seed-interactionC4 19" "type-ppi_seed-interactionC5 19"; do
	set -- ${analysisinfo}
	analysis=$1
	ncopes=$2

	# loops through the subject/run list
	cat ${scriptdir}/runcount.tsv |
	while read subruninfo; do
		set -- ${subruninfo}
		sub=$1
		nruns=$2

			# Manages the number of jobs and cores
	  	SCRIPTNAME=${basedir}/code/L2stats.sh
	  	NCORES=20
	  	while [ $(ps -ef | grep -v grep | grep $SCRIPTNAME | wc -l) -ge $NCORES ]; do
	    		sleep 1s
	  	done
	  	bash $SCRIPTNAME $sub $nruns $analysis $ncopes $logfile &
	  	sleep 1s

	done
done
