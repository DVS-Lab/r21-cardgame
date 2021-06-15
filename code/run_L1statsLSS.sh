#!/bin/bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
basedir="$(dirname "$scriptdir")"
logs=$basedir/logs

# remove previous log. this is mainly useful when re-running everything to check for completion
rm -rf ${logs}/re-runL1.log

# loops through the subject/run list
cat ${scriptdir}/runcount.tsv |
while read subrun; do
	set -- ${subrun}
	sub=$1
	nruns=$2
		
	# analyses we are doing; these define input/output paths in the L1stats.sh script
	for ppi in 0 bilateralVLPFC leftVLPFC leftVS rightVS ecn dmn; do # putting 0 first will indicate "activation"

		for run in `seq ${nruns}`; do
			for trial in `seq 64`; do
			  	# Manages the number of jobs and cores
			  	SCRIPTNAME=${basedir}/code/L1statsLSS.sh
			  	NCORES=47
			  	while [ $(ps -ef | grep -v grep | grep $SCRIPTNAME | wc -l) -ge $NCORES ]; do
			    		sleep 1s
			  	done
			  	bash $SCRIPTNAME $sub $run $ppi $trial &
			  	sleep 1s
			done
	  done

	done
done
