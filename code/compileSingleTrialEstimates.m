clear; close all;

% set up dirs
codedir = pwd; % must run from code, so this is not a good solution
cd ..
maindir = pwd;
roidir = fullfile(maindir,'derivatives','singletrial');
maskdir = fullfile(maindir,'masks','singletrial-masks');

subrun = load(fullfile(codedir,'runcount_excluded.tsv'));
corr_mat = nan(13,13,length(subrun)*3);
count = 0;
for i = 1:length(subrun)
    sub = subrun(i,1);
    nruns = subrun(i,2);
    for r = 1:nruns
        count = count + 1;
        % skip the bad runs
        if (sub == 217) && (r == 2)
            continue
        elseif (sub == 232) && (r == 3)
            continue
        end
        
        % loop through rois and make empty data matrix
        rois = dir(fullfile(maskdir,'*.nii.gz'));
        rois = struct2cell(rois);
        rois = rois(1,1:end);
        data_mat = zeros(64,length(rois)); % 64 trials and N rois
        for rr = 1:length(rois)
            roi = rois{rr}(:,1:end-7);
            roifile = fullfile(maindir,'derivatives','singletrial',['sub-' num2str(sub)],['sub-' num2str(sub) '_run-0' num2str(r) '_mask-' roi '.txt']);
            data_mat(:,rr) = load(roifile);
        end
        
        roi_list = [];
        d = dir(fullfile(maskdir,'*.nii.gz'));
        d = struct2cell(d);
        d = d(1,1:end);
        for j = 1:length(d)
            if j < length(d)
                roi_list = [roi_list d{:,j}(:,1:end-7) ','];
            else
                roi_list = [roi_list d{:,j}(:,1:end-7)];
            end
        end
        
        % store corr mat across all runs and subjects
        corr_mat(:,:,count) = corr(data_mat);
        
        % write output
        filename = sprintf('sub-%d_run-%d_singletrialestimates.csv',sub,r);
        outfile = fullfile(maindir,'derivatives','singletrial','compiled',filename);
        fid = fopen(outfile, 'wt');
        header = ['sub,run,trial,' roi_list '\n'];
        fprintf(fid, header);
        fclose(fid);
        trials = 1:64;
        dlmwrite(outfile,[sub*ones(64,1) r*ones(64,1) trials' data_mat],'delimiter',',','-append');
        
    end
end

mean_corr = nanmean(corr_mat,3);
figure,imagesc(mean_corr);
colorbar
title('Mean ROI*ROI correlation across subjects')
xlabel('ROI')
ylabel('ROI')
xticklabels(d)
yticklabels(d)

