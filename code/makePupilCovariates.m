clear; close all;

% set up dirs
codedir = pwd; % must run from code, so this is not a good solution
cd ..
maindir = pwd;
datadir = fullfile(maindir,'derivatives');

subrun = load(fullfile(codedir,'runcount_excluded.tsv'));



% ds = dataset('File',fullfile(datadir,'groupPupilData_indicator.tsv'),'Delimiter','\t');
ds = readtable(fullfile(datadir,'groupPupilData_indicator.tsv'),'FileType','delimitedtext','Delimiter','\t');
exclusions = setdiff(ds.subject,subrun(:,1));
for i = 1:length(exclusions)
    ds = ds(ds.subject ~=  exclusions(i),:);
end
    
ds_outcome = ds(:,{'subject','condition','mean_outcomePupilArea'});
ds_guess = ds(:,{'subject','condition','mean_guessPupilArea'});

ds_outcome = unstack(ds_outcome,'mean_outcomePupilArea','condition');
ds_guess = unstack(ds_guess,'mean_guessPupilArea','condition');


% convert to percent change
stim_reward_outcome = (ds_outcome.VLPFC_reward-ds_outcome.RTPJ_reward)./ds_outcome.RTPJ_reward;
stim_punish_outcome = (ds_outcome.VLPFC_punish-ds_outcome.RTPJ_punish)./ds_outcome.RTPJ_punish;
stim_reward_guess = (ds_guess.VLPFC_reward-ds_guess.RTPJ_reward)./ds_guess.RTPJ_reward;
stim_punish_guess = (ds_guess.VLPFC_punish-ds_guess.RTPJ_punish)./ds_guess.RTPJ_punish;

% demean variables
stim_reward_outcome = stim_reward_outcome - mean(stim_reward_outcome);
stim_punish_outcome = stim_punish_outcome - mean(stim_punish_outcome);
stim_reward_guess = stim_reward_guess - mean(stim_reward_guess);
stim_punish_guess = stim_punish_guess - mean(stim_punish_guess);

% write out table
subjects = ds_guess.subject;
outT = table(subjects,stim_reward_outcome,stim_punish_outcome,stim_reward_guess,stim_punish_guess);
writetable(outT,fullfile(datadir,'groupPupilData_covariate.csv'),'FileType','text','Delimiter',',');
cd(codedir);
