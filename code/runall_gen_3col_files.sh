#!/bin/bash

# leaving out 210 for now
# skipping 179 (pilot subject)
# skipping 180 (only one good run, first pilot subject)
for sub in 189 203 207 208 209 210 211 212 213 214 215 216 217 218 219 220 221 222 224 225 227 228 230 231 232 234 226 233 235 236 237 238; do
#for sub in 226 233 235 237 238; do
	bash gen_3col_files.sh $sub

done
