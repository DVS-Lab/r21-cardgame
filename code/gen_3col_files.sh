#!/bin/bash

# make everything relative to root of the GitHub repository
cd ..
maindir=`pwd`
baseout=${maindir}/derivatives/fsl/EVfiles
if [ ! -d ${baseout} ]; then
	mkdir -p $baseout
fi

sub=$1
nruns=`ls -1 ${maindir}/ds000001/sub-${sub}/func/sub-${sub}_task-cardgame_run-0?_events.tsv | wc -l`
echo -e "$sub\t$nruns" >> runcount.tsv
for run in `seq $nruns`; do
	bartfile=${maindir}/sourcedata/sub-${sub}/sub-${sub}_task-cardgame_run-0${run}_events.tsv
	if [ -e $bartfile ]; then
		nlines=`cat $bartfile | wc -l`
		if [ $nlines -gt 1 ]; then
			# replace HeuDiConv *.tsv with real *.tsv file
			input=${maindir}/ds000001/sub-${sub}/func/sub-${sub}_task-cardgame_run-0${run}_events.tsv
			cp $bartfile ${input}
			output=${baseout}/sub-${sub}
			mkdir -p $output
			if [ -e $input ]; then
				bash ${maindir}/code/BIDSto3col.sh $input ${output}/run-0${run}
			else
				echo "PATH ERROR: cannot locate ${input}"
				exit
			fi
		else
			#echo "not enough lines: ${bartfile}"
			echo "not enough lines: ${bartfile}" >> badformat_tsv.log
		fi
	else
		#echo "missing file: ${bartfile}"
		echo "missing file: ${bartfile}" >> missing_tsv.log
	fi
done

