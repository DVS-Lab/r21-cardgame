#!/usr/bin/env bash

# make everything relative to root of the GitHub repository
cd ..
maindir=`pwd`

sub=$1
run=$2
TASK=cardgame

#sub-189_task-cardgame_run-01_AROMAnoiseICs.csv
#sub-189_task-cardgame_run-01_desc-confounds_regressors.tsv
#sub-189/func/sub-189_task-cardgame_run-01_desc-MELODIC_mixing.tsv
#sub-189/func/sub-189_task-cardgame_run-01_space-MNI152NLin2009cAsym_boldref.nii.gz
#sub-189/func/sub-189_task-cardgame_run-01_space-MNI152NLin2009cAsym_desc-brain_mask.nii.gz
#sub-189/func/sub-189_task-cardgame_run-01_space-MNI152NLin2009cAsym_desc-preproc_bold.nii.gz
#sub-189/func/sub-189_task-cardgame_run-01_space-MNI152NLin2009cAsym_desc-smoothAROMAnonaggr_bold.nii.gz


# denoise data, if it doesn't exist
DATADIR=${maindir}/derivatives/fmriprep/sub-${sub}/func
INDATA=${DATADIR}/sub-${sub}_task-${TASK}_run-0${run}_space-MNI152NLin2009cAsym_desc-preproc_bold.nii.gz
OUTDATA=${DATADIR}/sub-${sub}_task-${TASK}_run-0${run}_space-MNI152NLin2009cAsym_desc-unsmoothedAROMAnonaggr_preproc_bold.nii.gz
if [ ! -e $OUTDATA ]; then
	echo "denoising $INDATA"
	fsl_regfilt -i $INDATA \
	    -f $(cat ${DATADIR}/sub-${sub}_task-${TASK}_run-0${run}_AROMAnoiseICs.csv) \
	    -d ${DATADIR}/sub-${sub}_task-${TASK}_run-0${run}_desc-MELODIC_mixing.tsv \
	    -o $OUTDATA
fi


# delete incomplete output
MAINOUTPUT=${maindir}/derivatives/fsl/sub-${sub}
mkdir -p $MAINOUTPUT
OUTPUT=${MAINOUTPUT}/L1_task-${TASK}_model-01_type-act_run-0${run}_sm-6
if [ -e ${OUTPUT}.feat/cluster_mask_zstat1.nii.gz ]; then
	exit
else
	rm -rf ${OUTPUT}.feat
	echo ${OUTPUT} >> check_L1.log
fi

EVDIR=${maindir}/derivatives/fsl/EVfiles/sub-${sub}/run-0${run}
NVOLUMES=`fslnvols ${OUTDATA}`


ITEMPLATE=${maindir}/code/templates/L1_template-m01.fsf
OTEMPLATE=${MAINOUTPUT}/L1_task-${TASK}_model-01_type-act_run-0${run}.fsf
sed -e 's@OUTPUT@'$OUTPUT'@g' \
-e 's@DATA@'$OUTDATA'@g' \
-e 's@EVDIR@'$EVDIR'@g' \
-e 's@NVOLUMES@'$NVOLUMES'@g' \
<$ITEMPLATE> $OTEMPLATE

# runs feat on output template
feat $OTEMPLATE

# fix registration as per NeuroStars post:
# https://neurostars.org/t/performing-full-glm-analysis-with-fsl-on-the-bold-images-preprocessed-by-fmriprep-without-re-registering-the-data-to-the-mni-space/784/3
mkdir -p ${OUTPUT}.feat/reg
ln -s $FSLDIR/etc/flirtsch/ident.mat ${OUTPUT}.feat/reg/example_func2standard.mat
ln -s $FSLDIR/etc/flirtsch/ident.mat ${OUTPUT}.feat/reg/standard2example_func.mat
ln -s ${OUTPUT}.feat/mean_func.nii.gz ${OUTPUT}.feat/reg/standard.nii.gz

# delete unused files
# not deleting filtered_func_data bc that's input for PPI
rm -rf ${OUTPUT}.feat/stats/res4d.nii.gz
rm -rf ${OUTPUT}.feat/stats/corrections.nii.gz
rm -rf ${OUTPUT}.feat/stats/threshac1.nii.gz
