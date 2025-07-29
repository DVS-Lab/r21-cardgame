%% tsvPanas.m
% This file contains the analysis for the PANAS scales.
%
% BK - Nov 2021, Jun 2025

%#ok<*UNRCH>

doSave  =true;
withBoldOnly    = true;         % false means use all available behavioral runs for analysis. true means use only those with QC passed BOLD data.
% Read the PANAS data from the TSV files.
[~,~,panasT] = tsvDataTable('useRunInfo',withBoldOnly,'subjects',1:31);
activity =panasT.Properties.VariableNames(contains(panasT.Properties.VariableNames','mean_act'));
connectivity = panasT.Properties.VariableNames(contains(panasT.Properties.VariableNames','mean_conn'));
activityTerms = reshape(char(strcat('+',strcat('fun1_',activity)))',1,[]);
connectivityTerms = reshape(char(strcat('+',strcat('fun1_',connectivity)))',1,[]);

nrBoot      = 10; % Bootstrap sample
nrWorkers   = 12;  % Parallel processing/parfor
%% DVS tsv cleanup  (not necessary if reading tsv files generated in 2025)
panasT{panasT.trialInBlock==4,"answer"} = NaN;
G = groupsummary(panasT,["subjectNr"],@(x)(sum(~isnan(x))),"answer")

%%

fprintf('**************** PANAS *********************************\n')
% Compute the PA and NA scores by splitting into positive and negative
% affect words.
    positive = {'interested','excited','strong','enthusiastic','proud','alert','inspired','determined','attentive','active'};
    isPositive =ismember(panasT.word,positive);
    panasT = addvars(panasT,isPositive);

    % Statistical analysis
    % Create a table that gives a score per block (i.e. based on 3 probes), but
    % rescale to 10 probes.
    panasMediators = [activity connectivity];
    groupPanasT= groupsummary(panasT,{'subjectNr','runNr','blockCntr','isPositive','prePanasReward','prePanasTarget'},@(x)(10*mean(x,1,"omitmissing")),cat(2,{'answer'},panasMediators));

    % Determine whether this score (fun1_anwswer) depends on the reward/punish status of
    % the preceding block and the stimulation in that block. Separately for PA
    % and NA.
    groupPanasPA = normalize(groupPanasT(groupPanasT.isPositive,:),'center','DataVariables',strcat('fun1_',panasMediators)); % Cannot use Exclude due to power analysis below.
    lmPA = fitglme(groupPanasPA ,'fun1_answer~prePanasReward*prePanasTarget+ (1|subjectNr:runNr)','DummyVarCoding','effects');
    groupPanasNA = normalize(groupPanasT(~groupPanasT.isPositive,:),'center','DataVariables',strcat('fun1_',panasMediators));
    lmNA = fitglme(groupPanasNA,'fun1_answer~prePanasReward*prePanasTarget+ (1|subjectNr:runNr)','DummyVarCoding','effects');
    fprintf('PANAS Subjects %d Scores %d (%d positive) from %d responses \n',numel(unique(panasT.subjectNr)),height(groupPanasT),sum(groupPanasT.isPositive),height(panasT));

    %Stepwise regression (two blocks of regressors; bold and FC)
    lmNoBoldPA = fitglme(groupPanasPA ,'fun1_answer~prePanasReward*prePanasTarget+ (1|subjectNr:runNr)','DummyVarCoding','effects');
    lmActPA = fitglme(groupPanasPA ,['fun1_answer~prePanasReward*prePanasTarget ' activityTerms '+ (1|subjectNr:runNr)'],'DummyVarCoding','effects');
    lmConnectPA =  fitglme(groupPanasPA ,['fun1_answer~prePanasReward*prePanasTarget ' connectivityTerms '+ (1|subjectNr:runNr)'],'DummyVarCoding','effects');
    lmActConnectPA = fitglme(groupPanasPA ,['fun1_answer~prePanasReward*prePanasTarget ' activityTerms connectivityTerms '+ (1|subjectNr:runNr)'],'DummyVarCoding','effects');
    c1PA = compare(lmNoBoldPA,lmActPA);
    c2PA = compare(lmNoBoldPA,lmConnectPA);
    c3PA = compare(lmActPA,lmActConnectPA);
    % Best model:
    lmActPA


    lmNoBoldNA = fitglme(groupPanasNA ,'fun1_answer~prePanasReward*prePanasTarget+ (1|subjectNr:runNr)','DummyVarCoding','effects');
    lmActNA = fitglme(groupPanasNA ,['fun1_answer~prePanasReward*prePanasTarget ' activityTerms '+ (1|subjectNr:runNr)'],'DummyVarCoding','effects');
    lmConnectNA =  fitglme(groupPanasNA ,['fun1_answer~prePanasReward*prePanasTarget ' connectivityTerms '+ (1|subjectNr:runNr)'],'DummyVarCoding','effects');
    lmActConnectNA = fitglme(groupPanasNA ,['fun1_answer~prePanasReward*prePanasTarget ' activityTerms connectivityTerms '+ (1|subjectNr:runNr)'],'DummyVarCoding','effects');
    c1NA = compare(lmNoBoldNA,lmActNA);
    c2NA = compare(lmNoBoldNA,lmConnectNA);
    c3NA = compare(lmActNA,lmActConnectNA);
    % Best model:
    lmActNA





%% Output

% LMM Models
lm.disp(lmPA,'','Intercept')
lm.disp(lmNA,'','Intercept')
%Stepwise
lm.dispCompare(c1PA)
lm.dispCompare(c2PA)
lm.dispCompare(c3PA)


lm.dispCompare(c1NA)
lm.dispCompare(c2NA)
lm.dispCompare(c3NA)

% Figure
groupPanasSummary= groupsummary(panasT,{'subjectNr','runNr','isPositive'},'mean','answer');
% Convert to scores on a 10 -item scale
pa = 10*groupPanasSummary.mean_answer(groupPanasSummary.isPositive);
na = 10*groupPanasSummary.mean_answer(~groupPanasSummary.isPositive);
% Compare with  the normative scores from Watson et al for "At this moment" for 10 items
normMean = [29.7 14.8];  %PA NA
normSd   = [7.9 5.4];
[hPA,pPA] = ztest(pa,normMean(1),normSd(1));
[hNA,pNA] = ztest(na,normMean(2),normSd(2));
%  Show in a figure
figure;clf
subplot(1,2,1)
edges = 0:5:100;
hold on
ax= gca;
hHist= histogram(pa,edges);
histogram(na,edges);
xlim([10 50])
maxN =30;
ylim([0 maxN])
x= repmat((10:50)',[1 2]);
y = max(ylim)*exp(-((x-normMean)./normSd).^2);
h = plot(x,y,':');
h(1).Color = ax.ColorOrder(1,:);
h(1).LineWidth = 2;
h(2).Color = ax.ColorOrder(2,:);
h(2).LineWidth = 2;

xlabel 'Score'
ylabel '#Runs'
legend('PA Score','NA Score')
fprintf('PANAS PA: %3.1f +/- %3.1f (p=%3.2g). NA: %3.1f +/- %3.1f (p=%3.2g)\n',mean(pa),std(pa),pPA,mean(na),std(na),pNA)

subplot(1,2,2)
hold on
% Need to double the effect to show the change from RTPJ (effects coding
% used)
pa      = 200*lmPA.Coefficients.Estimate(2:4)./lmPA.Coefficients.Estimate(1);
paLower = 200*lmPA.Coefficients.Lower(2:4)/lmPA.Coefficients.Estimate(1);
paUpper = 200*lmPA.Coefficients.Upper(2:4)/lmPA.Coefficients.Estimate(1);
na      = 200*lmNA.Coefficients.Estimate(2:4)/lmNA.Coefficients.Estimate(1);
naLower = 200*lmNA.Coefficients.Lower(2:4)/lmNA.Coefficients.Estimate(1);
naUpper = 200*lmNA.Coefficients.Upper(2:4)/lmNA.Coefficients.Estimate(1);

barh(3:-1:1,pa,'FaceColor',ax.ColorOrder(1,:),'FaceAlpha',hHist.FaceAlpha)
errorbar(pa,3:-1:1,pa-paLower,paUpper-pa,'.','horizontal','Color',ax.ColorOrder(1,:));
barh(3:-1:1,na,'FaceColor',ax.ColorOrder(2,:),'FaceAlpha',hHist.FaceAlpha)
errorbar(na,3:-1:1,na-naLower,naUpper-na,'.','horizontal','Color',ax.ColorOrder(2,:))
set(gca,'Ytick',1:3,'yTickLabel',fliplr({'reward','stim','reward:stim'}))
xlabel 'Change in PA/NA  (%)'
ylabel ''




%% Save the results for later reuse.
if doSave
   % Create a blockwise table of panas answers (scaled to the 10 questions)
    grpTable= groupsummary(panasT(~isnan(panasT.answer),:),{'subjectNr','runNr','blockCntr','isPositive','prePanasReward','prePanasTarget'},@(x)(10*mean(x,1,"omitmissing")),'answer');
    grpTable.Properties.VariableNames= {'subject','runNr','blockCntr','isPositive' 'isReward' 'target' ,'groupCount','answer'};
    trgFile = fullfile(dataRoot,'klab','groupPanasData.tsv');
    writetable(grpTable,trgFile,'Delimiter','\t','WriteVariableNames',true,'FileType','text');
    jsn.subject.Description='The unique subject identifier';
    jsn.runNr.Description='The run (i.e. scan) this corresponds to';
    jsn.blockNr.Description='The block (per run)';
    jsn.isPositive.Description='True if this corresponds to Positive Affect questions. False for Negative Affect';
    jsn.isReward.Description = {'True for measurements taken during a reward block'};
    jsn.isReward.Levels ={'True','False'};    
    jsn.target.Description='The stimulation target ';
    jsn.target.Levels = {'VLPFC','RTPJ'};
    jsn.groupCount.Description = {'The number of PANAS questions that the answer was based on.'};
    jsn.groupCount.Units = {'Arbitrary eye tracker units'};
    jsn.answer.Description = {'The answer given to the PANAS questions in this block.'};
    jsn.answer.Units = {'PANAS scale'};

    jsonFile = strrep(trgFile,'.tsv','.json');
    saveJson(jsn,jsonFile);

end
