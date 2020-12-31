#!/bin/bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
basedir="$(dirname "$scriptdir")"

# loop through all the subjects in the runcount.tsv file
cat ${scriptdir}/runcount.tsv |
while read subinfo; do
	set -- $subinfo
	sub=$1
	nruns=$2 # not used here

	# manage the number of concurrent job submissions
	script=${basedir}/code/fmriprep.sh
	NCORES=4 # ran into memory issues with 8 and aroma (odd? could've been 8 * 7ish runs)
	while [ $(ps -ef | grep -v grep | grep $script | wc -l) -ge $NCORES ]; do
		sleep 1s
	done
	bash $script $sub &
	sleep 5s
done
