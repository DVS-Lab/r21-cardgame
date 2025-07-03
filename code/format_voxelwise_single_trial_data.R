# format ROI data with both cortical and sub-cortical regions

# library(zoo)
library(RNifti)
library(XML)

# load data
# OLD:
# load("/Users/smweinst/Library/CloudStorage/OneDrive-TempleUniversity/research/collaborations/Smith_Lab/tACS/data/dat_single_trial_masked.RData")
# 
# subj_exclude = c("sub-235", # no pupil outcome data available (all NA)
#                  "sub-222", # no pupil outcome data available (all NA)
#                  "sub-238", # fmri data not available
#                  "sub-236" # no pupil outocme data available (all NA)
# )

# UPDATED (as of 01/03/2024):
load("/Users/smweinst/Library/CloudStorage/OneDrive-TempleUniversity/research/collaborations/Smith_Lab/tACS/data/dat_single_trial_masked01032024.RData")

subj_exclude = c("sub-212", # exclude due to head motion/data quality issues
                 "sub-218", # exclude due to head motion/data quality issues
                 "sub-238" # fmri data not available
                 )

fun_exclude = function(id_exclude){
  fmridat = dat$dat_fmri[-which(names(dat$dat_fmri) %in% id_exclude)]
  ptinfo = dat$pt_info[-which(dat$pt_info$participant_id %in% id_exclude),]
  # events64 = dat$events96[-which(names(dat$events96) %in% id_exclude)]
  events64 = dat$events64[-which(names(dat$events64) %in% id_exclude)]
  
  dat_include = list(pt_info = ptinfo,
                     dat_fmri = fmridat,
                     events64 = events64)
  return(dat_include)
}

# exclude subjects with problems data
dat_incl = fun_exclude(subj_exclude)

ids_include = dat_incl$pt_info$participant_id

n = length(dat_incl$dat_fmri)

# outcome measurements (pupil area)
events_dat = list()
#events_dat_all = list()
for (id in ids_include){
  events_dat[[id]] = lapply(1:length(dat_incl$events64[[id]]), FUN = function(r){ # events from each run
    events_r = dat_incl$events64[[id]][[r]]
    if (sum(is.na(events_r$outcomePupilArea))==64){
      return(NA) 
    }else{
      
      # OLD: previously did LOCF to deal with missingness; now just excluding those rows
      # events_r$outcomePupilArea = zoo::na.locf(events_r$outcomePupilArea, na.rm = F)
      # the following could be relevant if the pupil area in the first row was NA (since there was nothing to carry forward)
      ## temporary solution: carry it backward
      # events_r$outcomePupilArea[which(is.na( events_r$outcomePupilArea))] = events_r$outcomePupilArea[min(which(!is.na(events_r$outcomePupilArea)))]
      
      
      dat_out = data.frame(run = r,
                           trial = events_r$trial_type,
                           outcome = events_r$outcomePupilArea)
      
      # # new: exclude rows w/ missing outcomePupilArea observations
      # if (sum(is.na(events_r$outcomePupilArea)) > 0){
      #   dat_out = dat_out[-which(is.na(events_r$outcomePupilArea)),]
      # }
      # 
      # # also new: exclude negative values of outcomePupilArea (doesn't make sense?)
      # if (sum(dat_out$outcome < 0) > 0){
      #   dat_out = dat_out[-which(dat_out$outcome<0),]
      # }
      
      return(dat_out)
    }
    
  })
  
  events_dat[[id]] = do.call("rbind",  events_dat[[id]])
  if (length(which(is.na(events_dat[[id]]$run)>0))){
    events_dat[[id]] = events_dat[[id]][-which(is.na(events_dat[[id]]$run)),]
  }
  events_dat[[id]]$subj = which(ids_include == id)
  
}

events64_dat = do.call("rbind",events_dat)

# hist(events64_dat$outcome, breaks = 50, xlab = "outcomePupilArea", main = "outcomePupilArea", xlim = c(-40000, 10000), border = "white", col = "darkgrey")
# hist(events64_dat$outcome[events64_dat$outcome>0], xlab = "outcomePupilArea", main = "outcomePupilArea > 0", breaks = 50, xlim = c(0, 10000), border = "white", col = "darkgrey")

M_list = list()
for (i in 1:n){
  
  which_runs = unique(events64_dat$run[which(events64_dat$subj==i)]) # subset fmri data according to which runs we have outcome data for
  M_list[[i]] = do.call("rbind", dat_incl$dat_fmri[[i]][which_runs])
  
  print(paste0("subj ", i), quote = F)
  
}

# exclude NA, exclude < 0
exclude = which(is.na(events64_dat$outcome) | events64_dat$outcome<0)
events64_dat = events64_dat[-exclude,]

M = do.call("rbind",M_list)
M = M[-exclude,]
X = as.factor(events64_dat$trial)
Y = events64_dat$outcome

#### HARVARD-OXFORD REGION LABELS
library(RNifti)
cort_labels = readNifti(file = "/Users/smweinst/Library/CloudStorage/OneDrive-TempleUniversity/research/collaborations/Smith_Lab/tACS/data/labels/HO-cort-3mm.nii")
sub_labels = readNifti(file = "/Users/smweinst/Library/CloudStorage/OneDrive-TempleUniversity/research/collaborations/Smith_Lab/tACS/data/labels/HO-sub-3mm.nii")
mask = readNifti("/Users/smweinst/Library/CloudStorage/OneDrive-TempleUniversity/research/collaborations/Smith_Lab/tACS/data/labels/mask.nii.gz")
mask_vec = c(mask)

# sub-cortical and cortical region labels
sub_names = c(
  "Left Cerebral White Matter",
  "Left Cerebral Cortex",
  "Left Lateral Ventricle",
  "Left Thalamus",
  "Left Caudate",
  "Left Putamen",
  "Left Pallidum",
  "Brain-Stem",
  "Left Hippocampus",
  "Left Amygdala",
  "Left Accumbens",
  "Right Cerebral White Matter",
  "Right Cerebral Cortex",
  "Right Lateral Ventricle",
  "Right Thalamus",
  "Right Caudate",
  "Right Putamen",
  "Right Pallidum",
  "Right Hippocampus",
  "Right Amygdala",
  "Right Accumbens"
)

cort_names = c(
  "Frontal Pole",
  "Insular Cortex",
  "Superior Frontal Gyrus",
  "Middle Frontal Gyrus",
  "Inferior Frontal Gyrus, pars triangularis",
  "Inferior Frontal Gyrus, pars opercularis",
  "Precentral Gyrus",
  "Temporal Pole",
  "Superior Temporal Gyrus, anterior division",
  "Superior Temporal Gyrus, posterior division",
  "Middle Temporal Gyrus, anterior division",
  "Middle Temporal Gyrus, posterior division",
  "Middle Temporal Gyrus, temporooccipital part",
  "Inferior Temporal Gyrus, anterior division",
  "Inferior Temporal Gyrus, posterior division",
  "Inferior Temporal Gyrus, temporooccipital part",
  "Postcentral Gyrus",
  "Superior Parietal Lobule",
  "Supramarginal Gyrus, anterior division",
  "Supramarginal Gyrus, posterior division",
  "Angular Gyrus",
  "Lateral Occipital Cortex, superior division",
  "Lateral Occipital Cortex, inferior division",
  "Intracalcarine Cortex",
  "Frontal Medial Cortex",
  "Juxtapositional Lobule Cortex (formerly Supplementary Motor Cortex)",
  "Subcallosal Cortex",
  "Paracingulate Gyrus",
  "Cingulate Gyrus, anterior division",
  "Cingulate Gyrus, posterior division",
  "Precuneous Cortex",
  "Cuneal Cortex",
  "Frontal Orbital Cortex",
  "Parahippocampal Gyrus, anterior division",
  "Parahippocampal Gyrus, posterior division",
  "Lingual Gyrus",
  "Temporal Fusiform Cortex, anterior division",
  "Temporal Fusiform Cortex, posterior division",
  "Temporal Occipital Fusiform Cortex",
  "Occipital Fusiform Gyrus",
  "Frontal Operculum Cortex",
  "Central Opercular Cortex",
  "Parietal Operculum Cortex",
  "Planum Polare",
  "Heschl's Gyrus (includes H1 and H2)",
  "Planum Temporale",
  "Supracalcarine Cortex",
  "Occipital Pole"
)

sub_name_labels = data.frame(name = sub_names,
                             label = 1:21)

cort_name_labels = data.frame(name = cort_names,
                              label = 1:48)

cort_labels_vec = c(cort_labels)
sub_labels_vec = c(sub_labels)

tab_cort_labels = table(cort_labels_vec, useNA = "ifany")
names(tab_cort_labels)[which(names(tab_cort_labels) %in% cort_name_labels$label)] = paste0(cort_name_labels$label[which(cort_name_labels$label %in% names(tab_cort_labels))], ": ", cort_name_labels$name[which(cort_name_labels$label %in% names(tab_cort_labels))])

tab_sub_labels = table(sub_labels_vec, useNA = "ifany")
names(tab_sub_labels)[which(names(tab_sub_labels) %in% sub_name_labels$label)] = paste0(sub_name_labels$label[which(sub_name_labels$label %in% names(tab_sub_labels))], ": ", sub_name_labels$name[which(sub_name_labels$label %in% names(tab_sub_labels))])

# apply mask to cortical and sub-cortical labels
cort_labels_vec_masked = cort_labels_vec[-which(mask_vec==0)]
sub_labels_masked = sub_labels_vec[-which(mask_vec==0)]

tab_cort_labels_masked = table(cort_labels_vec_masked, useNA = "ifany")
names(tab_cort_labels_masked)[which(names(tab_cort_labels_masked) %in% cort_name_labels$label)] = paste0(cort_name_labels$label[which(cort_name_labels$label %in% names(tab_cort_labels_masked))], ": ", cort_name_labels$name[which(cort_name_labels$label %in% names(tab_cort_labels_masked))])

tab_sub_labels_masked = table(sub_labels_masked, useNA = "ifany")
names(tab_sub_labels_masked)[which(names(tab_sub_labels_masked) %in% sub_name_labels$label)] = paste0(sub_name_labels$label[which(sub_name_labels$label %in% names(tab_sub_labels_masked))], ": ", sub_name_labels$name[which(sub_name_labels$label %in% names(tab_sub_labels_masked))])

# voxels to exclude (white matter, ventricles labeled in subcortical atlas)
wm_vent_ind_exclude = which(sub_labels_masked %in% c(1,3,12,14)) # based on sub-cortical labels
cort_labels_vec_masked[wm_vent_ind_exclude] = NA
sub_labels_masked[wm_vent_ind_exclude] = NA
table(sub_labels_masked[cort_labels_vec_masked>0])
table(cort_labels_vec_masked[sub_labels_masked>0])

# voxels to set to NA in cortical atlas-- 0, 100, 200 (all were originally 0's, 100 and 200 are just 0's by hemisphere)
cort_labels_vec_masked[which(cort_labels_vec_masked == 0)] = NA

# voxels to set to NA in subcortical atlas-- 2, 13 (cerebral cortex)
sub_labels_masked[which(sub_labels_masked %in% c(2,13))] = NA

# set subcortical label 0 to NA (what does this correspond to?)
sub_labels_masked[which(sub_labels_masked==0)] = NA

# no more overlapping voxels between the two
table(sub_labels_masked[which(cort_labels_vec_masked>=0)]) 
table(cort_labels_vec_masked[which(sub_labels_masked>=0)])

cortical_and_subcortical_voxelwise_labels = cbind(cort_lab = cort_labels_vec_masked,
                                                  sub_lab = sub_labels_masked)

voxels_exclude = ifelse(is.na(cortical_and_subcortical_voxelwise_labels[,1]) & is.na(cortical_and_subcortical_voxelwise_labels[,2]), 1, 0)

# number of remaining voxels:
length(voxels_exclude)-sum(voxels_exclude) # 15457

# remove columns corresponding to voxels_exclude == 1 from M
M = M[,-which(voxels_exclude==1)]

cortical_and_subcortical_voxelwise_labels_included = cortical_and_subcortical_voxelwise_labels[-which(voxels_exclude==1),]

dat = list(X = X, M = M, Y = Y, subj_run = events64_dat[,c("subj","run")],
           M_voxelwise_labels = cortical_and_subcortical_voxelwise_labels_included,
           label_names = list(sub = names(tab_sub_labels_masked),
                              cort = names(tab_cort_labels_masked)))


