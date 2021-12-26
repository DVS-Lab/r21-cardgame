clear; close all;

% set up dirs
codedir = pwd; % must run from code, so this is not a good solution
addpath(codedir)
cd ..
maindir = pwd;
roidir = fullfile(maindir,'derivatives','imaging_plots');

% load individual differences
% cov-3: reward+
% cov-4: reward-
% cov-5: punish+
% cov-6: punish-
% cov-7: reward-punish
% cov-8: punish-reward


% loop through rois for activation
rois = {'bilateralVLPFC', 'bilateralVS'};
for r = 1:length(rois)
    roi = rois{r};
    
    c1 = load(fullfile(roidir,[roi '_type-act_cope-01.txt']));
    c2 = load(fullfile(roidir,[roi '_type-act_cope-02.txt']));
    c3 = load(fullfile(roidir,[roi '_type-act_cope-03.txt']));
    c4 = load(fullfile(roidir,[roi '_type-act_cope-04.txt']));
    reward = [c1 c2];
    punish = [c3 c4];
    figure, barweb_dvs2([mean(reward); mean(punish)],[std(reward)/sqrt(length(reward)); std(punish)/sqrt(length(punish)) ])
    xlabel('Task Condition')
    xticklabels({'Reward','Punishment'})
    ylabel('BOLD Response')
    legend({'VLPFC Stim', 'TPJ Stim'},'Location','northeast')
    axis square
    title(roi)
    outname = fullfile(maindir,'derivatives','imaging_plots',['act_' roi ]);
    cmd = ['print -depsc ' outname];
    eval(cmd);
    
end



% loop through rois for seed-based ppi
rois = {'rightVSconn-DLPFC'};
for r = 1:length(rois)
    roi = rois{r};
    
    c1 = load(fullfile(roidir,[roi '_type-ppi_seed-rightVS_cope-11.txt']));
    c2 = load(fullfile(roidir,[roi '_type-ppi_seed-rightVS_cope-12.txt']));
    c3 = load(fullfile(roidir,[roi '_type-ppi_seed-rightVS_cope-13.txt']));
    c4 = load(fullfile(roidir,[roi '_type-ppi_seed-rightVS_cope-14.txt']));
    reward = [c1 c2];
    punish = [c3 c4];
    figure, barweb_dvs2([mean(reward); mean(punish)],[std(reward)/sqrt(length(reward)); std(punish)/sqrt(length(punish)) ])
    xlabel('Task Condition')
    xticklabels({'Reward','Punishment'})
    ylabel('BOLD Response')
    legend({'VLPFC Stim', 'TPJ Stim'},'Location','northeast')
    axis square
    title(roi)
    outname = fullfile(maindir,'derivatives','imaging_plots',['ppiRightVS_' roi ]);
    cmd = ['print -depsc ' outname];
    eval(cmd);
    
end

% T = readtable('participants.csv');
% T.C_pun = c1;
% T.C_rew = c2;
% T.F_pun = c3;
% T.F_rew = c4;
% T.S_pun = c5;
% T.S_rew = c6;
% writetable(T,fullfile(roidir,['summary_ROI-' roi '_zimg.csv']))