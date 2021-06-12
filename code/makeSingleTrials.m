clear; close all;

% set up dirs
codedir = pwd; % must run from code, so this is not a good solution
cd ..
maindir = pwd;
evdir = fullfile(maindir,'templates','EVfiles');

% load sub/run list
subrun = load(fullfile(codedir,'runcount.tsv'));

for s = 1:length(subrun)
    subnum = subrun(s,1);
    runs = subrun(s,2);
    for r = 1:runs
        
        % load evs and concatenate
        ev1 = load(fullfile(evdir,['sub-' num2str(subnum)],['run-0' num2str(r) '_punish_rtpj.txt']));
        ev2 = load(fullfile(evdir,['sub-' num2str(subnum)],['run-0' num2str(r) '_reward_rtpj.txt']));
        ev3 = load(fullfile(evdir,['sub-' num2str(subnum)],['run-0' num2str(r) '_punish_vlpfc.txt']));
        ev4 = load(fullfile(evdir,['sub-' num2str(subnum)],['run-0' num2str(r) '_reward_vlpfc.txt']));
        all_evs = [ev1; ev2; ev3; ev4];
        all_evs = sortrows(all_evs,1,'ascend');
        
        % check length of trials. everyone should have 64
        if length(all_evs) ~= 64
            disp('missing trials...')
            keyboard
        end
        
        % extract trials and write evs
        outdir = fullfile(evdir,['sub-' num2str(subnum)],'singletrial',['run-0' num2str(r) ]);
        if ~exist(outdir,'dir')
            mkdir(outdir);
        end
        for t = 1:length(all_evs)
            singletrial = all_evs(t,:);
            othertrials = all_evs;
            othertrials(t,:) = []; % delete trial
            
            % write out single trial
            fname = sprintf('run-0%d_SingleTrial%02d.txt',r,t);
            dlmwrite(fullfile(outdir,fname),singletrial,'delimiter','\t','precision','%.6f') 
            
            % write out other trials
            fname = sprintf('run-0%d_OtherTrials%02d.txt',r,t);
            dlmwrite(fullfile(outdir,fname),othertrials,'delimiter','\t','precision','%.6f') 
        end
            
    end
end
cd(codedir);



