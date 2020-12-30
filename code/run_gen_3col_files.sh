#!/bin/bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"
logs=$maindir/logs

# remove existing output and logs
rm -rf ${scriptdir}/runcount.tsv
rm -rf $logs/badformat_tsv.log
rm -rf $logs/missing_tsv.log

# loop through all the subjects
# missing sub-224? previously only had 1 run.
for sub in 189 203 207 208 209 210 211 212 213 214 215 216 217 218 219 220 221 222 225 227 228 230 231 232 234 226 233 235 236 237 238; do
	bash ${scriptdir}/gen_3col_files.sh $sub
done
