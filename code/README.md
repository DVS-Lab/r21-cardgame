# Analysis Code

## Overview and disclaimers
- run_* scripts loop through a list of subjects for a given script; e.g., run_L1stats.sh loops all subjects through the L1stats.sh script.
- paths to input/output data should work without error, but check package/software installation
- a subject/run list is contained in `runcount.tsv`. This file is created by `gen_3col_files.sh` and is used in other scripts.

## Imaging analyses  
1. Run [fmriprep][fmriprep] using and `bash fmriprep.sh $sub`.
1. Convert `*_events.tsv` files to 3-column files (compatible with FSL) using Tom Nichols' [BIDSto3col.sh](https://github.com/INCF/bidsutils) script. This script is wrapped into our pipeline using `bash gen_3col_files.sh $sub $nruns`
1. Run analyses in FSL. Analyses in FSL consist of three stages, which we call "Level 1" (L1) and "Level 2" (L2).
  - `L1stats.sh` -- initial time series analyses, relating brain responses to the task conditions in each run
  - `L2stats.sh` -- combines data across runs
  - `L3stats.sh` -- combines data across subjects



[fmriprep]: http://fmriprep.readthedocs.io/en/latest/index.html
