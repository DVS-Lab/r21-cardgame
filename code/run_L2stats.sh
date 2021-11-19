#!/bin/bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
basedir="$(dirname "$scriptdir")"

# create log file to record what we did and when
logs=$basedir/logs
logfile=${logs}/rerunL2_date-`date +"%FT%H%M"`.log

# analyses we are doing; these define input/output paths in the L2stats.sh script
for analysisinfo in "type-act 9"; do
#for analysisinfo in "type-ppi_seed-bilateralVLPFC 19" "type-ppi_seed-leftVLPFC 19" "type-ppi_seed-rightVLPFC 19" "type-ppi_seed-preCun 19" "type-ppi_seed-bilateralVS 19" "type-ppi_seed-rightVS 19" "type-ppi_seed-leftVS 19"; do

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
