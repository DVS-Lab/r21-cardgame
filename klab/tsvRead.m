function T = tsvRead(filename,varargin)
% Read a table from a BIDS style TSV file.
%
% INPUT
% filename = full name of the file.
% 'format' : Textscan format to read the file (e.g. '%f%f%f%s%s'). Set to
% empty if the json sidecar file contains the corresponding tsvFormat
% property.  ['']
% 'group' : Set to true to group columns with the same name into a single
% column with row vector entries (parms_1 parms_2 -> parms with [. . ] 
% OUTPUT
% T = table 
%
% BK - Nov 2019
p=inputParser;
p.addParameter('format','');
p.addParameter('group',false);
p.parse(varargin{:});

if ~exist(filename,'file')
    error('No such file %s',filename);
end
[~,filenameOnly] =fileparts(filename);
if isempty(p.Results.format)
    % Retrieve format from JSON sidecar
    [pth,f] =fileparts(filename);
    jsonFile = fullfile(pth,[f '.json']);
    if exist(jsonFile,'file')
        allAsChar = fileread(jsonFile);
        json = jsondecode(allAsChar);        
        hasFormat = structfun(@(x) (isfield(x,'format')),json);
        nrColumns = numel(hasFormat);
        if all(hasFormat)
            fn = fieldnames(json);
            format = cell(1,nrColumns);
            for i=1:nrColumns % Loop over columns to extract format (structfund does not work with '%f' values
                format{i} = json.(fn{i}).format;
            end
            format = [format{:}];
        else
            warning(['No format specified, and the .json does not contain .format entries. Hoping for the best for ' filenameOnly]);
        end        
    else
        warning(['No format specified, and no .json found. Hoping for the best for ' filenameOnly]);
    end
else
    format = p.Results.format;    
end
if exist("format","var")
    T = readtable(filename,'ReadVariableNames',true,'Format',format,'FileType','text','TreatAsEmpty',{'n/a','N/A'},'Delimiter','\t');
else
    % Hope for the best
    T = readtable(filename,'ReadVariableNames',true,'FileType','text','TreatAsEmpty',{'n/a','N/A'},'Delimiter','\t');
end



if p.Results.group
    %Group columns with names like parms_1 parms_2 parms_3 into a single
    %column named parms, containing row vectors.
    match = find(~cellfun(@isempty,regexp(T.Properties.VariableNames,'(?<var>\w+)_(?<nr>\d+)','start')));
    [name,ia,ic] = unique(extractBefore(T.Properties.VariableNames(match),'_'));
    newT = removevars(T,match);
    for i=1:numel(name)
        keep = match(ia(i))+(0:(sum(ic==i)-1));
        this= T{:,keep};
        newT =addvars(newT,this,'newVariableNames',name{i});
    end
    T=newT;
end