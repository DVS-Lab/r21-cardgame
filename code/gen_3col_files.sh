#!/bin/bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"

# script input
sub=$1

# create output folder if it doesn't exist
baseout=${maindir}/derivatives/fsl/EVfiles
output=${baseout}/sub-${sub}
if [ ! -d $output ]; then
	mkdir -p $baseout
fi

# base bids directory (from Bart: https://github.com/klabhub/ds.tacsCardGame)
inputdir=/data/projects/ds.tacsCardGame

# count valid runs and append to runcount.tsv file
nruns=`ls -1 ${inputdir}/bids/sub-${sub}/func/sub-${sub}_task-cardgame_run-0?_events.tsv | wc -l`
echo -e "$sub\t$nruns" >> ${scriptdir}/runcount.tsv
for run in `seq $nruns`; do
	# use tsv file that Bart generated, but check to make sure it isn't empty
	bartfile=${inputdir}/bids/sub-${sub}/sub-${sub}_task-cardgame_run-0${run}_events.tsv
	if [ -e $bartfile ]; then
		nlines=`cat $bartfile | wc -l`
		if [ $nlines -gt 1 ]; then
			# You need BIDSto3col on your computer. Try git clone https://github.com/bids-standard/bidsutils
			bash /data/tools/bidsutils/BIDSto3col/BIDSto3col.sh $bartfile ${output}/run-0${run}
		else
			echo "not enough lines: ${bartfile}" >> badformat_tsv.log
		fi
	else
		echo "missing file: ${bartfile}" >> missing_tsv.log
	fi
done
