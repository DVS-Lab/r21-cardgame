#!/bin/bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
basedir="$(dirname "$scriptdir")"
logs=$basedir/logs

# remove previous log. this is mainly useful when re-running everything to check for completion
rm -rf ${logs}/re-runL2.log

# analyses we are doing; these define input/output paths in the L2stats.sh script
for analysisinfo in "type-nppi-dmn 28" "type-nppi-ecn 28" "type-act 9" "type-ppi-TPJ 19" "type-ppi-VLPFC 19"; do
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
	  	bash $SCRIPTNAME $sub $nruns $analysis $ncopes &
	  	sleep 1s

	done
done