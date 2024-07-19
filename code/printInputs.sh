#!/bin/bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"

# setting inputs and common variables; these define paths below
sm=6
task=cardgame

# loops through the subject/run list
cat ${scriptdir}/runcount_excluded.tsv |
while read subruninfo; do
	set -- ${subruninfo}
	sub=$1

	# set exclusions/exceptions
	# sub-232	cardgame	4	27.80231285	0.710906355	TRUE --> 4 runs originally
	# sub-217	cardgame	2	30.16802406	0.520016119	TRUE --> 3 runs originally
	# subjects have a max of 4 runs
	
	if [ $sub -eq 217 ]; then
		INPUT1=sub-${sub}_task-${task}_run-01
		INPUT2=sub-${sub}_task-${task}_run-03
	elif [ $sub -eq 232 ]; then
		INPUT1=sub-${sub}_task-${task}_run-01
		INPUT2=sub-${sub}_task-${task}_run-02
		INPUT3=sub-${sub}_task-${task}_run-04
	else
		INPUT1=sub-${sub}_task-${task}_run-01
		INPUT2=sub-${sub}_task-${task}_run-02
		INPUT3=sub-${sub}_task-${task}_run-03
		INPUT4=sub-${sub}_task-${task}_run-04
	fi
	
	echo ${INPUT1}
	echo ${INPUT2}
	echo ${INPUT3}
	echo ${INPUT4}
	
done