#!/bin/bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"

# remove existing output
rm -rf ${scriptdir}/runcount.tsv

# loop through all the subjects
for sub in 189 203 207 208 209 210 211 212 213 214 215 216 217 218 219 220 221 222 224 225 227 228 230 231 232 234 226 233 235 236 237 238; do
	bash ${scriptdir}/gen_3col_files.sh $sub
done
