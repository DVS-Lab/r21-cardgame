function rootDir= dataRoot
% This function returns the root folder of the dataset 
% All access to folders in the data set (e.g. bids, derivatives)
% should use this function to make the code portable across 
% OS and installs.

[pathToCode] = fileparts(mfilename('fullpath'));
rootDir=fullfile(pathToCode,'../');
