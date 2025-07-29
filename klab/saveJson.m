function saveJson(str,file)
% Save json file with some newlines to improve readability
str = jsonencode(str);
str = strrep(str,'{',['{' 13]); % Improve readability with newlines
str = strrep(str,',',[',' 13]);
str = strrep(str,'}',['}' 13]);
fid  = fopen(file,'wt');
fprintf(fid,'%s',str);
fclose(fid);
end