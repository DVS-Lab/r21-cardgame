%%  Cardgame Pupil Size Analysis
% This script contains the analysis of the pupil size data in the cardgame task
%
% BK - Oct 2021.

%#ok<*UNRCH>


doSave          = true;        % Save results to file
withBoldOnly    = false;         % false means use all available behavioral runs for analysis. true means use only those with QC passed BOLD data.

% Read the data from the TSV files.
[T] = tsvDataTable('useRunInfo',withBoldOnly,'subjects',1:31);
activityIx = startsWith(T.Properties.VariableNames,'act_');
activity = T.Properties.VariableNames(activityIx);
connIx = startsWith(T.Properties.VariableNames,'conn_');
connectivity = T.Properties.VariableNames(connIx);
activityTerms = reshape(char(strcat('+',activity))',1,[]);
connectivityTerms = reshape(char(strcat('+',connectivity))',1,[]);

%% **********************************************************************
% Pupil Size in the Guess period
% **********************************************************************

fprintf('**************** Guess Period Pupil *********************************\n')

lmGuessPsFull = fitglme(T,'guessPupilArea~isReward*target+(1|subjectNr:runNr)' ,'DummyVarCoding','Effects');
lmNoBoldGuess = fitglme(T,'guessPupilArea~target*isReward + (1|subjectNr:runNr)' ,'DummyVarCoding','Effects');
lmActGuess =  fitglme(T,['guessPupilArea~target*isReward ' activityTerms '+ (1|subjectNr:runNr)' ] ,'DummyVarCoding','Effects');
lmConnectGuess =  fitglme(T,['guessPupilArea~target*isReward ' connectivityTerms '+ (1|subjectNr:runNr) '] ,'DummyVarCoding','Effects');
lmActConnectGuess =fitglme(T,['guessPupilArea~target*isReward ' activityTerms connectivityTerms '+ (1|subjectNr:runNr) '] ,'DummyVarCoding','Effects');
c1Guess = compare(lmNoBoldGuess,lmActGuess);
c2Guess = compare(lmNoBoldGuess,lmConnectGuess);
c3Guess = compare(lmActGuess,lmActConnectGuess);
c4Guess = compare(lmConnectGuess,lmActGuess);


% Command line and figure output
lm.dispCompare(c1Guess);
lm.dispCompare(c2Guess);
lm.dispCompare(c3Guess);
lm.dispCompare(c4Guess);

lm.disp(lmGuessPsFull,'','intercept')
figure(1);clf
lm.plotCoefficients(lmGuessPsFull);

%% **********************************************************************
% Pupil Size in the Outcome period
% **********************************************************************
% Pupil area is smaller following reward, and larger with VLPFC
% stimulation.
%
fprintf('**************** Outcome Period Pupil *********************************\n')
lmOutcomePsFull = fitglme(T,'outcomePupilArea~target*correct*isReward + (1|subjectNr:runNr)' ,'DummyVarCoding','Effects');

% Does the BOLD activity per trial, or the FC per trial provide
% additional insight into the pupil? Removing correct variable as we
% expect only block level info in the BOLD signal
lmNoBoldOutcome = fitglme(T,'outcomePupilArea~target*isReward + (1|subjectNr:runNr)' ,'DummyVarCoding','Effects');
lmActOutcome =  fitglme(T,['outcomePupilArea~target*isReward ' activityTerms '+ (1|subjectNr:runNr)' ] ,'DummyVarCoding','Effects');
lmConnectOutcome =  fitglme(T,['outcomePupilArea~target*isReward ' connectivityTerms '+ (1|subjectNr:runNr) '] ,'DummyVarCoding','Effects');
lmActConnectOutcome =fitglme(T,['outcomePupilArea~target*isReward ' activityTerms connectivityTerms '+ (1|subjectNr:runNr) '] ,'DummyVarCoding','Effects');
c1Outcome = compare(lmNoBoldOutcome,lmActOutcome);
c2Outcome = compare(lmNoBoldOutcome,lmConnectOutcome);
c3Outcome  = compare(lmActOutcome,lmActConnectOutcome);
c4Outcome = compare(lmConnectOutcome,lmActOutcome);



% Command line and figure output
lm.dispCompare(c1Outcome);
lm.dispCompare(c2Outcome);
lm.dispCompare(c3Outcome);
lm.dispCompare(c4Outcome);

lm.disp(lmOutcomePsFull,'','intercept')
figure(4);clf
lm.plotCoefficients(lmOutcomePsFull,'',[],'Intercept');


%% Save the results for later reuse.
if doSave

    % Generate a table to do whole brain brain/behavior correlations across subjects,
    grpTable = groupsummary(T,{'subjectNr','target','isReward'},@(x)mean(x,'omitnan'),{'guessPupilArea','outcomePupilArea'});
    grpTable.Properties.VariableNames= {'subject','target','isReward','GroupCount','mean_guessPupilArea','mean_outcomePupilArea'};
    trgFile = fullfile(dataRoot,'klab','groupPupilData.tsv');
    writetable(grpTable,trgFile,'Delimiter','\t','WriteVariableNames',true,'FileType','text');
    jsn.subject.Description='The unique subject identifier';
    jsn.target.Description='The stimulation target ';
    jsn.target.Levels = {'VLPFC','RTPJ'};
    jsn.isReward.Description = {'True for measurements taken during a reward block'};
    jsn.isReward.Levels ={'True','False'};
    jsn.mean_guessPupilArea.Description = {'The mean pupil size during the guess period'};
    jsn.mean_guessPupilArea.Units = {'Arbitrary eye tracker units'};

    jsn.mean_outcomePupilArea.Description = {'The mean pupil size during the outcome period'};
    jsn.mean_outcomePupilArea.Units = {'Arbitrary eye tracker units'};

    jsonFile = strrep(trgFile,'.tsv','.json');
    saveJson(jsn,jsonFile);

end



%% Figure
figure(10);
clf
%colors = colororder;
colors = [1 1 1;1 1 1];
yl = [-10 5];
% Need to double the effect to show the change from RTPJ/Punish (effects coding
% used). Note the different order for guess compared to outcome
% (alphabetical..)
guessPs      = 200*lmGuessPsFull.Coefficients.Estimate([3 2 4])./lmGuessPsFull.Coefficients.Estimate(1);
guessPsLower = 200*lmGuessPsFull.Coefficients.Lower([3 2 4])/lmGuessPsFull.Coefficients.Estimate(1);
guessPsUpper = 200*lmGuessPsFull.Coefficients.Upper([3 2 4])/lmGuessPsFull.Coefficients.Estimate(1);
outcomePs    = 200*lmOutcomePsFull.Coefficients.Estimate([4 3 2 5:8])/lmOutcomePsFull.Coefficients.Estimate(1);
outcomePsLower = 200*lmOutcomePsFull.Coefficients.Lower([4 3 2 5:8])/lmOutcomePsFull.Coefficients.Estimate(1);
outcomePsUpper = 200*lmOutcomePsFull.Coefficients.Upper([4 3 2 5:8])/lmOutcomePsFull.Coefficients.Estimate(1);
outcomeX = 1:7;
subplot(2,1,1)
hold on
bar(1:3,guessPs,'FaceColor',colors(1,:),'FaceAlpha',0.5)
errorbar(1:3,guessPs,guessPs-guessPsLower,guessPsUpper-guessPs,'.','Color','k');
set(gca,'xtick',1:3,'xTickLabel',{'rewardBlock','stim','reward:stim'},'YLim',yl)
xlabel ''
ylabel 'Change in Pupil Size (%)'
title 'Guess Period'
subplot(2,1,2)
hold on
bar(outcomeX,outcomePs,'FaceColor',colors(2,:),'FaceAlpha',0.5)
errorbar(outcomeX,outcomePs,outcomePs-outcomePsLower,outcomePsUpper-outcomePs,'.','Color','k')
set(gca,'xtick',outcomeX,'xTickLabel',{'rewardBlock','stim','correct','correct:stim','correct:rewardBlock','stim:rewardBlock','correct:stim:rewardBlock'},'yLim',yl)
title 'Outcome Period'
ylabel 'Change in Pupil Size (%)'
xlabel ''