%***********************************************************
% WriteMutants.Txl
% Jeremy S. Bradbury

% Copyright 2006-2007 J.S. Bradbury

% Description: 
% Include rules for writing mutants to files

% Limitations:
% Currently only supports Linux not Windows files.
%***********************************************************

%------------------------------------------------------------
% Generate directory name for current mutant
%------------------------------------------------------------
function constructDirectory
	replace [stringlit]
		Directory [stringlit]

	construct slash [stringlit]
		"/"

	import TXLargs [repeat stringlit]
		deconstruct * TXLargs
			"-outfile" FileValue [stringlit] "-outdir" DirValue [stringlit]% MoreOptions [repeat stringlit]

	% get the current mutant count and update it.
	import MutantCount [number]
	export MutantCount
		MutantCount [+ 1]

	import MutantOpName [stringlit]

	construct sep [stringlit]
		"_" 

	% get the input file name
	import TXLinput [stringlit]
		
	by
		DirValue [+MutantOpName] [+ sep] [+ FileValue] [+ sep] [+ MutantCount] [print]
end function

%------------------------------------------------------------
% Write mutant to a file
%------------------------------------------------------------
function writeToFile 
	replace [program]
		P [program]
	
	% get the input file name
	import TXLinput [stringlit]

	import TXLargs [repeat stringlit]
		deconstruct * TXLargs
			"-outfile" FileValue [stringlit] "-outdir" DirValue [stringlit] % MoreOptions [repeat stringlit]

	construct slash [stringlit]
		"/"

	% get current mutant's  directory name
	construct dirname [stringlit]
		_ [ constructDirectory]

	% create new mutant directory
	construct mkdirCmd [stringlit]
		"mkdir " 

	construct mkdirCmd2 [stringlit]
		mkdirCmd [+ dirname]

	construct cdCmd [stringlit]
		"cd "

	construct cdCmd2 [stringlit]
		cdCmd [+ dirname]

	construct dirCmd [stringlit]
		"ls"

	construct filename [stringlit]
		dirname [+ slash] [+ FileValue]

	by 
		P 	[system mkdirCmd2]
			[system dirCmd]
			[system cdCmd2]
			[system dirCmd]
			[write filename]
end function