clear; close all;

%% set up dirs
scriptname = matlab.desktop.editor.getActiveFilename;
[codedir,~,~] = fileparts(scriptname);
[maindir,~,~] = fileparts(codedir);
addpath(codedir)
roidir = fullfile(maindir,'derivatives','imaging_plots');

%% load pupil data and covariates
% individual differences (exploratory)
P = readtable(fullfile(maindir,'derivatives','groupPupilData_covariate.csv'));
C = readtable(fullfile(maindir,'derivatives','mriqc-extractions','outliers_task-cardgame_covariates.tsv'),'FileType','text');
P.tsnr = C.tsnr;
P.fd_mean = C.fd_mean;
covs = [P.tsnr P.fd_mean];


%% build arrays and start counters
% outcome data (main text)
corr_mat_outcome = zeros(height(P),2);
regression_mat_outcome = zeros(height(P),6);

% guess data (supplement)
corr_mat_guess = zeros(height(P),2);
regression_mat_guess = zeros(height(P),6);

roi_array = cell(height(P),1);
count = 0;


%% loop through rois for activation
rois = {'rVLPFC', 'thalamus', 'IFG', 'lVLPFC', 'SMA', 'rightVS'};
for r = 1:length(rois)
    roi = rois{r};
    
    c1 = load(fullfile(roidir,['act_' roi '_type-act_cope-01.txt']));
    c2 = load(fullfile(roidir,['act_' roi '_type-act_cope-02.txt']));
    c3 = load(fullfile(roidir,['act_' roi '_type-act_cope-03.txt']));
    c4 = load(fullfile(roidir,['act_' roi '_type-act_cope-04.txt']));
    
    count = count + 1;
    figure(count)
    roi_array{count,1} = roi;
    
    myxlabel = 'Reward Outcome Pupil Effect';
    stats = drawsubplot(P.stim_reward_outcome,c1-c2,covs,1,roi,myxlabel);
    corr_mat_outcome(count,1) = stats.corrval;
    regression_mat_outcome(count,1) = stats.b;
    regression_mat_outcome(count,2) = stats.t;
    regression_mat_outcome(count,3) = stats.p;
    
    myxlabel = 'Reward Guess Pupil Effect';
    stats = drawsubplot(P.stim_reward_guess,c1-c2,covs,2,roi,myxlabel);
    corr_mat_guess(count,1) = stats.corrval;
    regression_mat_guess(count,1) = stats.b;
    regression_mat_guess(count,2) = stats.t;
    regression_mat_guess(count,3) = stats.p;
    
    myxlabel = 'Punish Outcome Pupil Effect';
    stats = drawsubplot(P.stim_punish_outcome,c3-c4,covs,3,roi,myxlabel);
    corr_mat_outcome(count,2) = stats.corrval;
    regression_mat_outcome(count,4) = stats.b;
    regression_mat_outcome(count,5) = stats.t;
    regression_mat_outcome(count,6) = stats.p;
    
    myxlabel = 'Punish Guess Pupil Effect';
    stats = drawsubplot(P.stim_punish_guess,c3-c4,covs,4,roi,myxlabel);
    corr_mat_guess(count,2) = stats.corrval;
    regression_mat_guess(count,4) = stats.b;
    regression_mat_guess(count,5) = stats.t;
    regression_mat_guess(count,6) = stats.p;
    
    roi_plotname = strrep(roi,'_',' ');
    reward = [c1 c2];
    punish = [c3 c4];
    %subplot(3,2,5),barweb_dvs2([mean(reward); mean(punish)],[std(reward)/sqrt(length(reward)); std(punish)/sqrt(length(punish)) ])
    figure(count+11),barweb_dvs2([mean(reward); mean(punish)],[std(reward)/sqrt(length(reward)); std(punish)/sqrt(length(punish)) ])
    xlabel('Task Condition')
    xticklabels({'Reward','Punishment'})
    ylabel([roi_plotname ' Activation (beta)'])
    legend({'VLPFC Stim', 'TPJ Stim'},'Location','northeast')
    axis square
    title([roi_plotname ' Activation'])
    outname = fullfile(maindir,'derivatives','imaging_plots',['act_' roi ]);
    saveas(gcf,[outname '.pdf'])
    
end



%% loop through rois for seed-based ppi
seeds = {'rightVS', 'leftVS'};
for s = 1:length(seeds)
    seed = seeds{s};
    if strcmp(seed,'leftVS')
        rois = {'dACC', 'LPFC', 'visual'};
    else
        rois = {'vPrecun', 'dPrecun', 'dACC'};
    end
    for r = 1:length(rois)
        roi = rois{r};
        
        
        c1 = load(fullfile(roidir,[roi '_type-ppi_seed-' seed '_cope-11.txt']));
        c2 = load(fullfile(roidir,[roi '_type-ppi_seed-' seed '_cope-12.txt']));
        c3 = load(fullfile(roidir,[roi '_type-ppi_seed-' seed '_cope-13.txt']));
        c4 = load(fullfile(roidir,[roi '_type-ppi_seed-' seed '_cope-14.txt']));
        
        count = count + 1;
        figure(count)
        roi_array{count,1} = [seed '_' roi];
        
        
        myxlabel = 'Reward Outcome Pupil Effect';
        stats = drawsubplot(P.stim_reward_outcome,c1-c2,covs,1,roi,myxlabel);
        corr_mat_outcome(count,1) = stats.corrval;
        regression_mat_outcome(count,1) = stats.b;
        regression_mat_outcome(count,2) = stats.t;
        regression_mat_outcome(count,3) = stats.p;
        
        myxlabel = 'Reward Guess Pupil Effect';
        stats = drawsubplot(P.stim_reward_guess,c1-c2,covs,2,roi,myxlabel);
        corr_mat_guess(count,1) = stats.corrval;
        regression_mat_guess(count,1) = stats.b;
        regression_mat_guess(count,2) = stats.t;
        regression_mat_guess(count,3) = stats.p;
        
        myxlabel = 'Punish Outcome Pupil Effect';
        stats = drawsubplot(P.stim_punish_outcome,c3-c4,covs,3,roi,myxlabel);
        corr_mat_outcome(count,2) = stats.corrval;
        regression_mat_outcome(count,4) = stats.b;
        regression_mat_outcome(count,5) = stats.t;
        regression_mat_outcome(count,6) = stats.p;
        
        myxlabel = 'Punish Guess Pupil Effect';
        stats = drawsubplot(P.stim_punish_guess,c3-c4,covs,4,roi,myxlabel);
        corr_mat_guess(count,2) = stats.corrval;
        regression_mat_guess(count,4) = stats.b;
        regression_mat_guess(count,5) = stats.t;
        regression_mat_guess(count,6) = stats.p;
        
        
        roi_plotname = strrep(roi_array{count,1},'_',' ');
        reward = [c1 c2];
        punish = [c3 c4];
        %subplot(3,2,5), barweb_dvs2([mean(reward); mean(punish)],[std(reward)/sqrt(length(reward)); std(punish)/sqrt(length(punish)) ])
        figure(count+11), barweb_dvs2([mean(reward); mean(punish)],[std(reward)/sqrt(length(reward)); std(punish)/sqrt(length(punish)) ])
        xlabel('Task Condition')
        xticklabels({'Reward','Punishment'})
        ylabel([roi_plotname ' Connectivity (PPI beta)'])
        legend({'VLPFC Stim', 'TPJ Stim'},'Location','northeast')
        axis square
        title([roi_plotname ' Connectivity'])
        outname = fullfile(maindir,'derivatives','imaging_plots',['ppi_seed-' seed '_' roi ]);
        %cmd = ['print -depsc ' outname];
        %eval(cmd);
        saveas(gcf,[outname '.pdf'])
        
    end
end

%% output summaries
% write outcome phase (main text)
R = array2table(corr_mat_outcome,'VariableNames',{'stim_reward_outcome','stim_punish_outcome'});
R.ROIs = roi_array;
RR = [R(:,3) R(:,1:2)];
RR(cellfun(@isempty,RR.ROIs(:,1)),:) = [];
regtable = array2table(regression_mat_outcome,'VariableNames', ...
    {'stim_reward_outcome_beta','stim_reward_outcome_t','stim_reward_outcome_p', ...
    'stim_punish_outcome_beta','stim_punish_outcome_t','stim_punish_outcome_p'});
regtable.ROIs = roi_array;
regtable(cellfun(@isempty,regtable.ROIs(:,1)),:) = [];
outT = join(RR,regtable);
outfile = fullfile(maindir,'derivatives','ROIstats-outcome.csv');
writetable(outT,outfile,'Delimiter',',')

% write guess phase (supplement)
R = array2table(corr_mat_guess,'VariableNames',{'stim_reward_guess','stim_punish_guess'});
R.ROIs = roi_array;
RR = [R(:,3) R(:,1:2)];
RR(cellfun(@isempty,RR.ROIs(:,1)),:) = [];
regtable = array2table(regression_mat_guess,'VariableNames', ...
    {'stim_reward_guess_beta','stim_reward_guess_t','stim_reward_guess_p', ...
    'stim_punish_guess_beta','stim_punish_guess_t','stim_punish_guess_p'});
regtable.ROIs = roi_array;
regtable(cellfun(@isempty,regtable.ROIs(:,1)),:) = [];
outT = join(RR,regtable);
outfile = fullfile(maindir,'derivatives','ROIstats-guess.csv');
writetable(outT,outfile,'Delimiter',',')


%% functions
function stats = drawsubplot(x,y,covs,p,roi,myxlabel)
stats.corrval = corr(x,y);
roi_plotname = strrep(roi,'_',' ');
subplot(2,2,p)
%p = polyfit(x, y, 1);
%px = [min(x) max(x)];
%py = polyval(p, px);
scatter(x, y, 'filled')
hold on
%plot(px, py, 'LineWidth', 2);
[brob,s] = robustfit([x covs],y);
stats.b = brob(2);
stats.t = s.t(2);
stats.p = s.p(2);
plot(x, brob(1)+brob(2)*x, 'LineWidth', 2);
xlabel(myxlabel)
ylabel([roi_plotname ' (beta)'])
txt = {['t = ' num2str(stats.t) ],['p = ' num2str(stats.p) ]};
text(max(x),max(y),txt)

%axis square
end

