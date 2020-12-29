clear; close all;
load sfn_subs.mat


roi = 'PCC_func_cope-17_n27'; % ppi reward: vlpfc > tpj
c1 = load([roi '_type-ppi_cope-11.txt']);
c2 = load([roi '_type-ppi_cope-12.txt']);
c3 = load([roi '_type-ppi_cope-13.txt']);
c4 = load([roi '_type-ppi_cope-14.txt']);
reward = [c1 c2];
punish = [c3 c4];
figure, barweb_dvs2([mean(reward); mean(punish)],[std(reward)/sqrt(length(reward)); std(punish)/sqrt(length(punish)) ])
axis square
cmd = ['print -depsc ppi_' roi];
eval(cmd);

% R_VLPFC = c1;
% R_TPJ = c2;
% P_VLPFC = c3;
% P_TPJ = c4;

filename = ['summary_roi-' roi '.tsv'];
fid = fopen(filename, 'wt');
fprintf(fid, '%s\t%s\t%s\t%s\t%s\n', 'sub-num','Reward_VLPFC','Reward_TPJ','Punish_VLPFC','Punish_VLPFC');  % header
fclose(fid);
dlmwrite(filename,[goodsubs c1 c2 c3 c4],'delimiter','\t','precision','%f','-append');





roi = 'leftVS_func_cope-16_n27'; % ppi vlpfc > tpj
c1 = load([roi '_type-ppi_cope-11.txt']);
c2 = load([roi '_type-ppi_cope-12.txt']);
c3 = load([roi '_type-ppi_cope-13.txt']);
c4 = load([roi '_type-ppi_cope-14.txt']);
reward = [c1 c2];
punish = [c3 c4];
figure, barweb_dvs2([mean(reward); mean(punish)],[std(reward)/sqrt(length(reward)); std(punish)/sqrt(length(punish)) ])
axis square
cmd = ['print -depsc ppi_' roi];
eval(cmd);


filename = ['summary_roi-' roi '.tsv'];
fid = fopen(filename, 'wt');
fprintf(fid, '%s\t%s\t%s\t%s\t%s\n', 'sub-num','Reward_VLPFC','Reward_TPJ','Punish_VLPFC','Punish_VLPFC');  % header
fclose(fid);
dlmwrite(filename,[goodsubs c1 c2 c3 c4],'delimiter','\t','precision','%f','-append');




roi = 'TPJ';
c1 = load([roi '_type-act_cope-01.txt']);
c2 = load([roi '_type-act_cope-02.txt']);
c3 = load([roi '_type-act_cope-03.txt']);
c4 = load([roi '_type-act_cope-04.txt']);
reward = [c1 c2];
punish = [c3 c4];
figure, barweb_dvs2([mean(reward); mean(punish)],[std(reward)/sqrt(length(reward)); std(punish)/sqrt(length(punish)) ])
axis square
cmd = ['print -depsc act_' roi];
eval(cmd);


filename = ['summary_roi-' roi '.tsv'];
fid = fopen(filename, 'wt');
fprintf(fid, '%s\t%s\t%s\t%s\t%s\n', 'sub-num','Reward_VLPFC','Reward_TPJ','Punish_VLPFC','Punish_VLPFC');  % header
fclose(fid);
dlmwrite(filename,[goodsubs c1 c2 c3 c4],'delimiter','\t','precision','%f','-append');




roi = 'VLPFC';
c1 = load([roi '_type-act_cope-01.txt']);
c2 = load([roi '_type-act_cope-02.txt']);
c3 = load([roi '_type-act_cope-03.txt']);
c4 = load([roi '_type-act_cope-04.txt']);
reward = [c1 c2];
punish = [c3 c4];
figure, barweb_dvs2([mean(reward); mean(punish)],[std(reward)/sqrt(length(reward)); std(punish)/sqrt(length(punish)) ])
axis square
cmd = ['print -depsc act_' roi];
eval(cmd);



filename = ['summary_roi-' roi '.tsv'];
fid = fopen(filename, 'wt');
fprintf(fid, '%s\t%s\t%s\t%s\t%s\n', 'sub-num','Reward_VLPFC','Reward_TPJ','Punish_VLPFC','Punish_VLPFC');  % header
fclose(fid);
dlmwrite(filename,[goodsubs c1 c2 c3 c4],'delimiter','\t','precision','%f','-append');




roi = 'VS_func_n27';
c1 = load([roi '_type-act_cope-01.txt']);
c2 = load([roi '_type-act_cope-02.txt']);
c3 = load([roi '_type-act_cope-03.txt']);
c4 = load([roi '_type-act_cope-04.txt']);
reward = [c1 c2];
punish = [c3 c4];
figure, barweb_dvs2([mean(reward); mean(punish)],[std(reward)/sqrt(length(reward)); std(punish)/sqrt(length(punish)) ])
axis square
cmd = ['print -depsc act_' roi];
eval(cmd);



filename = ['summary_roi-' roi '.tsv'];
fid = fopen(filename, 'wt');
fprintf(fid, '%s\t%s\t%s\t%s\t%s\n', 'sub-num','Reward_VLPFC','Reward_TPJ','Punish_VLPFC','Punish_VLPFC');  % header
fclose(fid);
dlmwrite(filename,[goodsubs c1 c2 c3 c4],'delimiter','\t','precision','%f','-append');




