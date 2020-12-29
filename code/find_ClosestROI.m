function roi_num = find_ClosestROI(in_coord)
load('power_coords.mat');

%{
NOTES:
Let's go with MNIxyz?=?[?39, 35, ?10] for VLPFC (peak of the cluster that NeuroVault image).
And for TPJ, we could use MNIxyz = [54, -52, 18], which is pretty close to the peak response for "TPJ" in Neurosynth.
%}

%vlpfc = [-39 35 -10];
%tpj = [54 -52 18];

dx_list = zeros(length(power_coords),1);
for i = 1:length(dx_list);
    
    p = in_coord;
    x = power_coords(i,2);
    y = power_coords(i,3);
    z = power_coords(i,4);
    
    %compute distance from origin using Pythagorean theorem
    dx_list(i,1) = sqrt((p(1)-x)^2+(p(2)-y)^2+(p(3)-z)^2 );
end

roi_num = find(dx_list==min(dx_list));