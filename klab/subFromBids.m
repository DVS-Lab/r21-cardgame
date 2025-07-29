function sub = subFromBids(ix,bidsFolder)
% Convert a subject index to a subject number 
% by looking in the BIDS directory, sorting the sub-xxx folders and
% assigning ix =1  to the first in that sorted list.
%INPUT 
% ix = Index 
% bidsFolder = Top level BIDS folder . Defaults to dataRoot/bids
%
% BK - Oct 2019

if nargin<2
    bidsFolder = fullfile(dataRoot,'bids');
end

files= dir(fullfile(bidsFolder,'sub-*'));
files(~[files.isdir]) = [];
names={files.name};
names = sort(names);
nrSubjects =numel(names);
if any(ix<1 | ix >nrSubjects)
    error(['Subject index must be between 1 and ' num2str(nrSubjects)]);
else
    sub = names(ix);
    sub = cellfun(@(x) (str2double(x(end-2:end))),sub); % Last three of "sub-180"
end


    