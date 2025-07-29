function [T,mediationT,panasT] = tsvDataTable(varargin)
% Reads TSV behavioral and single trial BOLD data, removes outliers based
% on RT, compute some derived variables.
% INPUT
% 'useRunInfo' - [true] Use the QC runInfo file to determine which files to
%                       include. When set to false, all runs
%                       /files/subjects are used  (for instance, when
%                       analyzing behavior only, without BOLD).
% OUTPUT
% T = Table with all releveant data from behavioral and bold analysis
% mediationT =Table with the same data, just ordered differently for
%                       reference coded mediation analysis
% panasT = Table with data from PANAS blocks.
%
% BK - Sept 2021

p =inputParser;
p.addParameter('useRunInfo',true,@islogical);
p.addParameter('subjects',1:31,@isnumeric);
p.parse(varargin{:});


derivativesRoot = fullfile(dataRoot,'derivatives');  
bidsRoot = fullfile(dataRoot,'bids');  
subjects = subFromBids(p.Results.subjects,bidsRoot);

% Outlier definition
MINRT           = 160;        % ms
MAXRT           = 1490;     % ms

MAXRUNSAVAILABLE = 4;
MINNRRUNS        = 2;
T=table;
boldT= table;
panasT = table;

warning('OFF','MATLAB:table:ModifiedAndSavedVarnames');
warning('off','backtrace')
% Read QC runinfo file; based on the QC, runs are excluded from the BOLD analysis, and, for consistency,
% we have the option to exclude them from the behavioral analysis too.
runinfo = tsvRead(fullfile(derivativesRoot,'mriqc-extractions','outliers_task-cardgame_runinfo.tsv'),'Format','%s%s%f%f%f%s');
for sub = subjects(:)'
    subStay = strcmpi(runinfo.Sub,sprintf('sub-%d',sub)) & strcmpi(runinfo.outlier_run_Custom1,'False');
    if sum(subStay)<MINNRRUNS && p.Results.useRunInfo
        fprintf('Skipping subject %d. Too few runs \n',sub);
        continue;
    end
    for run=1:MAXRUNSAVAILABLE
        stay = subStay & runinfo.run==run ;
        if ~any(stay) && p.Results.useRunInfo
            fprintf(' Skipping subject %d , run %d based on RunInfo BOLD QC\n',sub,run);
            continue;
        end
        filename = sprintf('%s/sub-%03d/func/sub-%03d_task-cardgame_run-%02d_events.tsv',bidsRoot,sub,sub,run);
        if exist(filename,'file')
            try
                thisBehaviorT =tsvRead(filename);
            catch me
                disp(['Error reading '  filename ' (' me.message '). Skipped.'])
                continue;
            end
            
            singleTrialBoldFilename = sprintf('%s/singletrial/compiled/sub-%03d_run-%1d_singletrialestimates.csv',derivativesRoot,sub,run);
            if exist(singleTrialBoldFilename ,'file')
                thisBoldT= readtable(singleTrialBoldFilename);
                boldTableNames = thisBoldT.Properties.VariableNames;
            else
                disp(['No BOLD results for ' singleTrialBoldFilename '. Using behavior only']);
                nrRois = numel(boldTableNames);
                thisBoldT = table('Size',[64 nrRois],'VariableTypes', repmat({'double'},[1 nrRois]),'VariableNames',boldTableNames);
                thisBoldT.sub = repmat(sub,[64 1]);
                thisBoldT.run = repmat(run,[64 1]);
                thisBoldT.trial = (1:64)';
                [thisBoldT{:,4:end}] =deal(NaN);
            end
            
            % Separate out the Panas trials
            prePanas  =   find(diff(thisBehaviorT.isPanas)>0);
            prePanasReward = reshape(repmat(thisBehaviorT{prePanas,'isReward'}',[4 1]),[32 1]);
            prePanasTarget  = reshape(repmat(thisBehaviorT{prePanas,'target'}',[4 1]),[32 1]);
            prePanasBold  =table;
            for blk = 1:numel(prePanas)
                prePanasBold = [prePanasBold; varfun(@mean,thisBoldT(thisBoldT.trial<=prePanas(blk),:),"OutputFormat","table")]; %#ok<AGROW>
            end
            
            repIx = reshape(repmat(1:8,[4 1]),[32 1]);
            try
            panasT = [panasT; [thisBehaviorT(thisBehaviorT.isPanas==1,:) table(prePanasTarget,prePanasReward)] prePanasBold(repIx,:)]; %#ok<AGROW>
            % Concatenate across runs.
            thisBehaviorT= thisBehaviorT(~thisBehaviorT.isPanas,:);
            thisBehaviorT.trial = (1:64)'; % Sequential number the trials to match boldT
            T = [T;thisBehaviorT]; %#ok<AGROW>
            boldT = [boldT ; thisBoldT]; %#ok<AGROW>
            catch
                disp(['Skipping' filename ' ']);
            end
            
        elseif run<4  % 3 runs typical. 
            disp([filename ' not found?']);
        end
        
        
    end
end

%% Rearrange
T.subjectNr= categorical(T.subjectNr);
T.runNr= categorical(T.runNr);
T.trial  = categorical(T.trial);
previousCorrect = [NaN; T.correct(1:end-1)];
previousCorrect(T.trial==categorical(1))=NaN;
previousCorrect = categorical(previousCorrect);
T=addvars(T,previousCorrect);

boldT.sub = categorical(boldT.sub);
boldT.run = categorical(boldT.run);
boldT.trial = categorical(boldT.trial);


% Remove outlier reaction times
out = T.reactionTime <MINRT | T.reactionTime>MAXRT;
fprintf('Removing %.0f%% of trials as outlier RT. \n',100*mean(out));
T = T(~out,:);
% Add potentially informative variables
surprise = xor(T.correct==1,T.isReward==1); % Correct in punish block or Incorrect in reward block
T = addvars(T,reordercats(categorical(surprise),{'true','false'}),'NewVariableNames',{'surprise'});

% Join behavior and BOLD. If useRunInfo is false (i.e. not using BOLD QC to
% select runs) then some boldT will have NaNs. Subsequent analyses will
% ignore those.
T= innerjoin(T,boldT,'LeftKeys',{'subjectNr','trial','runNr'},'RightKeys',{'sub','trial','run'});

% Rearrange for easier output
% To interpret the lmm anova p-values, need effects coding and this will
% remove the last category. To make output more readable, we order the
% categories such that correct=0 is last,RTPJ is last, and isReward=0 is
% last.
T.correct = reordercats(categorical(T.correct),{'1','-1'});
T.trialInBlock =double(T.trialInBlock); % A linear dependence on trailInBlcock results in AIC better models than a categorical (using the interaction isReward:trialInBlock)
T.isReward = reordercats(categorical(T.isReward),{'1','0'});
T.target = reordercats(categorical(T.target),{'VLPFC','RTPJ'});


panasT.prePanasReward = reordercats(categorical(panasT.prePanasReward),{'1','0'});
panasT.subjectNr= categorical(panasT.subjectNr);
panasT.runNr= categorical(panasT.runNr);
panasT.prePanasTarget = reordercats(categorical(panasT.prePanasTarget),{'VLPFC','RTPJ'});

% Center the BOLD data
varsToNormalize = boldTableNames(4:end);
T =normalize(T,'center','DataVariables',varsToNormalize);
panasT = normalize(panasT,'center','DataVariables',strcat('mean_',varsToNormalize));


nrTrials = groupsummary(T,'subjectNr');

fprintf('#Trials Min: %d Max :%d Mean %d Total %d\n',min(nrTrials.GroupCount),max(nrTrials.GroupCount),round(mean(nrTrials.GroupCount)),sum(nrTrials.GroupCount))


% Using  reference coding with punish/tpj as the reference helps phrasing the
% results for Mediation analysi, but doesn't affect the interpretation with these dichotomous
% moderators and treatments.)
mediationT  = T;
mediationT.isReward = reordercats(T.isReward,{'0','1'});
mediationT.target = reordercats(T.target,{'RTPJ','VLPFC'});
mediationT.correct= reordercats(T.correct,{'-1','1'});
end