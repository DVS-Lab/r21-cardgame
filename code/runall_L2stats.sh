#!/bin/bash


rm -rf ../check_L2.log

for ppi in TPJ VLPFC; do

	cat runcount.tsv | 
	while read a; do 
		set -- $a
		sub=$1
		nruns=$2
		if [ $sub -eq 224 ]; then
			continue
		fi
	
	  	#Manages the number of jobs and cores
	  	#SCRIPTNAME=L2_task-reward_model-01.sh
	  	SCRIPTNAME=L2_task-reward_model-01_ppi.sh
	  	#SCRIPTNAME=L2_task-reward_model-01_nppi.sh
	  	NCORES=32
	  	while [ $(ps -ef | grep -v grep | grep $SCRIPTNAME | wc -l) -ge $NCORES ]; do
	 		sleep 1s
	  	done
	  	bash $SCRIPTNAME $sub $nruns $ppi &
	  	sleep 5s
	  	
			
	done
done
