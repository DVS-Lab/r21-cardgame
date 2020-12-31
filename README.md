# Alpha-tACS and Reward-Related Corticostriatal Connectivity
This project has been carried out in collaboration with Bart Krekelberg (Rutgers-Newark). This repository contains much of the imaging code related to our project and will be merged with Bart's code prior to publication. Imaging data will be shared via [OpenNeuro][openneuro] when the manuscript is posted on bioRxiv or accepted for publication.


## A few prerequisites and recommendations
- Understand BIDS and be comfortable navigating Linux
- Install [FSL](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FslInstallation)
- Install [miniconda or anaconda](https://stackoverflow.com/questions/45421163/anaconda-vs-miniconda)
- Make singularity container for fmriprep (version: 20.1.0).


## Notes on repository organization and files
- Some of the contents of this repository are not tracked (.gitignore) because the files are large and we do not yet have a nice workflow for datalad. These folders include derivatives/fsl and derivatives/fmriprep.
- Tracked folders and their contents:
  - `code`: analysis code
  - `templates`: fsf template files used for FSL analyses
  - `masks`: images used as masks, networks, and seed regions in analyses
  - `logs`: various logs and notes created by some of our analysis code


## Basic commands to reproduce our analyses
```
# get code and data (TBD)
git clone https://github.com/DVS-Lab/r21-cardgame
cd r21-cardgame
datalad install <TBD url> # get bids data (will need to rename to bids to match script)

# run preprocessing and generate confounds and timing files for analyses
bash code/run_fmriprep.sh
python code/MakeConfounds.py --fmriprepDir="derivatives/fmriprep"
bash code/run_gen3colfiles.sh

# run statistics
bash code/run_L1stats.sh
bash code/run_L2stats.sh
bash code/run_L3stats.sh
```


## Acknowledgments
This work was supported, in part, by a grant from the National Institutes of Health (R21-MH113917). DVS was a Research Fellow of the Public Policy Lab at Temple University during the course of this project (2019-2020 academic year).

[openneuro]: https://openneuro.org/
