# Code

This folder stores all of the code for the project. 

1. We use HeuDiConv to convert to BIDS format. Output stored in `ds000000` folder
1. FMRIPREP and MRIQC are then run on these converted data. Output stored under `derivatives` folder
1. Prior to analyses, we move *_events.tsv files into the appropriate locations in the `ds000000` folder (this is the BIDS folder and it's pretty picky about formatting)
1. Analyses from FSL will be stored in the `derivatives` folder.