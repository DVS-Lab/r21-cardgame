#!/bin/bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
basedir="$(dirname "$scriptdir")"

# create log file to record what we did and when
logs=$basedir/logs
logfile=${logs}/rerunL1-LSS_date-`date +"%FT%H%M"`.log

# loops through the subject/run list
cat ${scriptdir}/runcount_excluded.tsv |
while read subrun; do
	set -- ${subrun}
	sub=$1
	nruns=$2

	# analyses we are doing; these define input/output paths in the L1stats.sh script
	for ppi in 0; do # putting 0 first will indicate "activation"

		for run in `seq ${nruns}`; do

			# skip the bad runs
			if [ $sub -eq 217 ] && [ $run -eq 2 ]; then
				continue
			elif [ $sub -eq 232 ] && [ $run -eq 3 ]; then
				continue
			fi

			for trial in `seq 64`; do
			  	# Manages the number of jobs and cores
			  	SCRIPTNAME=${basedir}/code/L1statsLSS.sh
			  	NCORES=20
			  	while [ $(ps -ef | grep -v grep | grep $SCRIPTNAME | wc -l) -ge $NCORES ]; do
			    		sleep 1s
			  	done
			  	bash $SCRIPTNAME $sub $run $ppi $trial $logfile &
			done
	  done

	done
done
