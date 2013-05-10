%***********************************************************
% WriteMutants.Txl for CORE and ARC
%
% Copyright D David Kelk, 2013
%
% Based on WriteMutants.Txl by J.S. Bradbury
%***********************************************************
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

  % outdir / DirValue  : tmp/3/4/source/main/net/sf/cache4j/Cache/ASAT
  % outfile / FileValue: account_1.java
	import TXLargs [repeat stringlit]
		deconstruct * TXLargs
			"-outfile" FileValue [stringlit] "-outdir" DirValue [stringlit]
			otherarge [repeat stringlit] %"-contestfile"
			 %ConFile [stringlit] "-class" TheClass [stringlit] "-var"
			  %VarName [stringlit]

	% get the current mutant count and update it.
	import MutantCount [number]
	export MutantCount
		MutantCount [+ 1]

	import MutantOpName [stringlit]

	construct sep [stringlit]
		"_"

  construct javaext [stringlit]
    ".java"

	% get the input file name
	import TXLinput [stringlit]

	by
    % outdir / DirValue  : tmp/3/4/source/main/net/sf/cache4j/Cache/ASAT
    % outfile / FileValue: account_1.java
	  % 1_Account_1.java
	  % tmp/3/4/source/main/net/sf/cache4j/Cache/ASAT/1_Account_1.java
		% DirValue [+MutantOpName] [+ sep] [+ FileValue] [+ sep] [+ MutantCount] [print]
    % _ [+MutantOpName] [+ sep] [+ FileValue] [+ sep] [+ MutantCount] [print]
    _   [+ FileValue] [+ sep] [+ MutantCount] [+ javaext] [print]
end function

%------------------------------------------------------------
% Write mutant to a file
%------------------------------------------------------------
function writeToFile
	replace [program]
		P [program]

	% get the input file name
	import TXLinput [stringlit]

  % outdir / DirValue  : tmp/3/4/source/main/net/sf/cache4j/Cache/ASAT
  % outfile / FileValue: account_1.java
	import TXLargs [repeat stringlit]
		deconstruct * TXLargs
			"-outfile" FileValue [stringlit] "-outdir" DirValue [stringlit] otherarge [repeat stringlit]

	construct slash [stringlit]
		"/"

	% tmp/3/4/source/main/net/sf/cache4j/Cache/ASAT/1_Account_1.java
	% get current mutant's  directory name
	construct newFileName [stringlit]
		_ [constructDirectory]

	% create new mutant directory
	construct mkdirCmd [stringlit]
		"mkdir "

	% mkdir tmp/3/4/source/main/net/sf/cache4j/Cache/ASAT/
	construct mkdirCmd2 [stringlit]
	%	mkdirCmd [+ dirname]
    mkdirCmd [+ DirValue]

	construct cdCmd [stringlit]
		"cd "

	construct cdCmd2 [stringlit]
	%	cdCmd [+ dirname]
    cdCmd [+ DirValue]

	construct dirCmd [stringlit]
		"ls"

	construct filename [stringlit]
		DirValue [+ slash] [+ newFileName]

	by
		P
		  [system mkdirCmd2]
			%[system dirCmd]
			[system cdCmd2]
			%[system dirCmd]
			[write filename]
end function
