# import packages
import numpy as np
import json
import pandas as pd
import os
from scipy.stats import zscore
import re # re will let us parse text in a nice way

# set paths and build file lists
mriqc_dir = "/data/projects/ds.tacsCardGame/derivatives/mriqc/"
derivatives_path = "/data/projects/r21-cardgame/derivatives"
bids_dir = "/data/projects/ds.tacsCardGame/bids"
all_subs = [s for s in os.listdir(bids_dir) if s.startswith('sub')]
j_files = [os.path.join(root, f) for root,dirs,files in os.walk(mriqc_dir)
         for f in files if f.endswith('bold.json')]

# build dfs for later
keys=['tsnr','fd_mean'] # the IQM's we might care about
sr=['Sub','task','run'] # other pieces of the data frame

# Open an empty array and fill it with actual data.
row=[]
for i in range(len(j_files)):
    sub=re.search('/mriqc/(.*)/func', j_files[i]).group(1) # this will parse the text for a string that looks like sub-###
    task=re.search('task-(.*)_run',j_files[i]).group(1)
    run=re.search('_run-(.*)_bold.json', j_files[i]).group(1) # this is parsed just as # so we have to put in the run text ourselves if we want later
    with open(j_files[i]) as f: #we load the j_son file and extract the dictionary ingo
        data = json.load(f)
    now=[sub,task,run]+[data[x]for x in keys] #the currently created row in the loop
    row.append(now) #through that row on the end

# create full dataframe
df_full=pd.DataFrame(row,columns=sr+keys) # imaybe later try to do multi-indexing later with sub and run as the index?

for task in df_full.task.unique():
    df=df_full[df_full['task']==task]
    mriqc_subs = np.setdiff1d(all_subs,df.Sub.unique())
    # yields the elements in `list_2` that are NOT in `list_1`
    print("%s are missing MRIQC OUTPUT"%(mriqc_subs))

    #find the interquartile range and define fences for boxplot
    Q1=df[keys].quantile(0.25)
    Q3=df[keys].quantile(0.75)
    IQR = Q3 - Q1
    lower=Q1 - 1.5 * IQR
    upper=Q3 + 1.5 * IQR
    upper.tsnr=upper.tsnr*100 # so we don't exclude runs with "too good" signal-noise ratio
    print(lower.to_frame(name='lower').join(upper.to_frame(name='upper')))

    outList=(df[keys]<upper)&(df[keys]>lower)#Here we make comparisons
    df['outlier_run_Custom1']=~outList.all(axis='columns')


    # generate output files
    outdir=derivatives_path+"mriqc-extractions"
    if not os.path.exists(outdir):
    	os.makedirs(outdir)

    # These are the identities of outlier runs
    outfile="outliers_task-%s_runinfo.tsv"%(task)
    output=outdir+outfile
    print(df[df['outlier_run_Custom1']==True])
    df.to_csv(output,sep='\t',index=False)

    # separate good subjects (GS) and bad subject (BS)
    GS=df[df['outlier_run_Custom1']==False]
    GS=list(GS.Sub.value_counts().reset_index(name="count").query("count > 1")['index'])
    BS=df[~df.Sub.isin(GS)]['Sub']

    # output covariates for group-level models
    df_cov=df[df.Sub.isin(GS)]
    df_cov=df_cov[df_cov['outlier_run_Custom1']==False]
    df_cov=df_cov.groupby(by='Sub').mean().reset_index().rename(columns={'index':'Sub'})
    df_cov=df_cov[['Sub']+keys]
    df_cov[['tsnr','fd_mean']]=df_cov[['tsnr','fd_mean']].apply(zscore)
    outfile="outliers_task-%s_covariates.tsv"%(task)
    output=outdir+outfile
    df_cov.to_csv(output,sep='\t',index=False)

    # output custom covariates
    df_out=df[df.Sub.isin(BS)]
    df_out=df_out.Sub.value_counts().reset_index().rename(columns={'index':'Sub_num'})
    df_out=df_out.sort_values(by='Sub_num')
    outfile="outliers_task-%s_customSubOutlier.tsv"%(task)
    output=outdir+outfile
    df_out.to_csv(outfile,sep='\t',index=False)
