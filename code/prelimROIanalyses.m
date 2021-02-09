clear; close all;

% set up dirs
codedir = pwd; % must run from code, so this is not a good solution
cd ..
maindir = pwd;
roidir = fullfile(maindir,'derivatives','imaging_plots');

% loop through rois for activation
rois = {'bilateralVLPFC', 'leftVLPFC', 'rightVLPFC', 'bilateralVS', 'leftVS', 'rightVS'};
for r = 1:length(rois)
    roi = rois{r};
    
    c1 = load(fullfile(roidir,[roi '_type-act_cope-01.txt']));
    c2 = load(fullfile(roidir,[roi '_type-act_cope-02.txt']));
    c3 = load(fullfile(roidir,[roi '_type-act_cope-03.txt']));
    c4 = load(fullfile(roidir,[roi '_type-act_cope-04.txt']));
    reward = [c1 c2];
    punish = [c3 c4];
    figure, barweb_dvs2([mean(reward); mean(punish)],[std(reward)/sqrt(length(reward)); std(punish)/sqrt(length(punish)) ])
    axis square
    outname = fullfile(maindir,'derivatives','imaging_plots',['act_' roi ]);
    cmd = ['print -depsc ' outname];
    eval(cmd);
    
end


% loop through rois for nppi
rois = {'DMNstriatal_conn'};
for r = 1:length(rois)
    roi = rois{r};
    
    c1 = load(fullfile(roidir,[roi '_type-nppi-dmn_cope-11.txt']));
    c2 = load(fullfile(roidir,[roi '_type-nppi-dmn_cope-12.txt']));
    c3 = load(fullfile(roidir,[roi '_type-nppi-dmn_cope-13.txt']));
    c4 = load(fullfile(roidir,[roi '_type-nppi-dmn_cope-14.txt']));
    reward = [c1 c2];
    punish = [c3 c4];
    figure, barweb_dvs2([mean(reward); mean(punish)],[std(reward)/sqrt(length(reward)); std(punish)/sqrt(length(punish)) ])
    axis square
    outname = fullfile(maindir,'derivatives','imaging_plots',['nppiDMN_' roi ]);
    cmd = ['print -depsc ' outname];
    eval(cmd);
    
end

% filename = ['summary_roi-' roi '.tsv'];
% fid = fopen(filename, 'wt');
% fprintf(fid, '%s\t%s\t%s\t%s\t%s\n', 'sub-num','Reward_VLPFC','Reward_TPJ','Punish_VLPFC','Punish_VLPFC');  % header
% fclose(fid);
% dlmwrite(filename,[goodsubs c1 c2 c3 c4],'delimiter','\t','precision','%f','-append');




