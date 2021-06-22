clear; close all;

% set up dirs
codedir = pwd; % must run from code, so this is not a good solution
cd ..
maindir = pwd;
roidir = fullfile(maindir,'derivatives','singletrial');

subrun = load(fullfile(codedir,'runcount_excluded.tsv'));
for i = 1:length(subrun)
    sub = subrun(i,1);
    nruns = subrun(i,2);
    for r = 1:nruns
        
        % skip the bad runs
        if (sub == 217) && (r == 2)
            continue
        elseif (sub == 232) && (r == 4)
            continue
        end
        
        % skip for initial testing
        if sub > 225
            continue
        end
        
        % loop through rois (n = 13) and make empty data matrix
        rois = {'act-leftVLPFC', 'act-leftVS', 'act-rightVLPFC', 'act-rightVS', 'leftVLPFCconn-DLPFC', 'leftVLPFCconn-MPFC', 'leftVLPFCconn-PCC', 'ECNconn-MPFC', 'ECNconn-insula', 'DMNconn-leftVS', 'bilateralVLPFCconn-parietal', 'leftVSconn-visual', 'rightVSconn-DLPFC'};
        data_mat = zeros(64,13); % 64 trials and 13 rois
        for rr = 1:length(rois)
            roi = rois{rr};
            roifile = fullfile(maindir,'derivatives','singletrial',['sub-' num2str(sub)],['sub-' num2str(sub) '_run-0' num2str(r) '_mask-' roi '.txt']);
            data_mat(:,rr) = load(roifile);
        end
        
        % write output
        filename = sprintf('sub-%d_run-%d_singletrialestimates.csv',sub,r);
        outfile = fullfile(maindir,'derivatives','singletrial','compiled',filename);
        fid = fopen(outfile, 'wt');
        header = 'sub,run,trial,act-leftVLPFC,act-leftVS,act-rightVLPFC,act-rightVS,leftVLPFCconn-DLPFC,leftVLPFCconn-MPFC,leftVLPFCconn-PCC,ECNconn-MPFC,ECNconn-insula,DMNconn-leftVS,bilateralVLPFCconn-parietal,leftVSconn-visual,rightVSconn-DLPFC\n';
        fprintf(fid, header);
        fclose(fid);
        trials = 1:64;
        %dlmwrite(outfile,[sub*ones(64,1) sub*ones(64,1) trials' data_mat],'delimiter',',','precision','%f','-append');
        dlmwrite(outfile,[sub*ones(64,1) r*ones(64,1) trials' data_mat],'delimiter',',','-append');

    end
end

