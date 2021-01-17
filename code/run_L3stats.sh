#!/bin/bash

# This run_* script is a wrapper for L3stats.sh, so it will loop over several
# copes and models. Note that Contrast N for PPI is always PHYS in these models.


# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"

# delete old logs
logs=$maindir/logs
rm -rf $logs/re-runL3.log

# this loop defines the different types of analyses that will go into the group comparisons
# for analysistype in type-nppi-dmn type-nppi-ecn type-act type-ppi_seed-TPJ type-ppi_seed-VLPFC; do
for analysisinfo in type-ppi_seed-bilateralVLPFC type-ppi_seed-leftVLPFC type-ppi_seed-rightVLPFC type-ppi_seed-preCun type-ppi_seed-bilateralVS type-ppi_seed-rightVS type-ppi_seed-leftVS; do

	# these define the cope number (copenum) and cope name (copename)
	for copeinfo in "1 R_vlpfc" "2 R_tpj" "3 P_vlpfc" "4 P_tpj" "5 R-P" "6 vlpfc-tpj" "7 R_vlpfc-tpj" "8 P_vlpfc-tpj" "9 interaction" "10 phys" "11 ppi_R_vlpfc" "12 ppi_R_tpj" "13 ppi_P_vlpfc" "14 ppi_P_tpj" "15 ppi_R-P" "16 ppi_vlpfc-tpj" "17 ppi_R_vlpfc-tpj" "18 ppi_P_vlpfc-tpj" "19 ppi_interaction"; do

		# split copeinfo variable
		set -- $copeinfo
		copenum=$1
		copename=$2

		# skip non-existent contrasts for activation analysis
		if [ "${analysistype}" == "type-act" ] && [ ${copenum} -gt 9 ]; then
			echo "skipping phys and ppi contrasts for activation since they do not exist..."
			continue
		fi

		NCORES=7
		SCRIPTNAME=${maindir}/code/L3stats.sh
		while [ $(ps -ef | grep -v grep | grep $SCRIPTNAME | wc -l) -ge $NCORES ]; do
			sleep 1s
		done
		bash $SCRIPTNAME $copenum $copename $analysistype &

	done
done
