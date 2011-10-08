%***********************************************************
% RSB (Remove Synchronized Block) Mutator
% Jeremy S. Bradbury

% Copyright 2006 J.S. Bradbury

% Description: This mutation operator removes the 
% the synchronizied block around a group of statements.
%***********************************************************

% Base grammar, and grammar override files
include "Java.Grm"
include "JavaCommentOverrides.Grm"

% Local grammar overrides
redefine synchronized_statement
	[attr labelM] [non_synchronized_statement] 
	| [attr labelM] [synchronized_statement_2]
end redefine

define non_synchronized_statement
    	; /* 'MUTANT: [stringlit] */
        	[statement]                  [NL]
end define

define synchronized_statement_2
    	'synchronized '( [expression] ')
        		[statement]                  [NL]
end define

define labelM
	'MUTATED
end define

%------------------------------------------------------------
% Main rule, followed by other rules in topological order
%------------------------------------------------------------
function main
	% initialize and export a mutant count that will be used in 
	% file name / folder name generation
    	construct MutantCount [number]
		0
    	export MutantCount

	% initialize and export the name of the current mutant which
	% will be used for folder name generation
	construct MutantOpName [stringlit]
		"RSB"
	export MutantOpName

	replace [program] 
        		P [program]

    	by
		% Remove all instances of synchronized blocks one at 
		% a time
        		P [MutateSynchronizedDel]
end function

%------------------------------------------------------------
% Match all methods that have a synchronized block 
% and then perform the following 3 steps for each:
%	1. Create mutant of program with synchronized block
%      removed
%	2. Write mutant to a file
%	3. Reinsert synchronized block that was removed
%------------------------------------------------------------
rule MutateSynchronizedDel
	replace [program]
		P 	[program]

	% only proceed for methods that satisfy the requirements
	% (i.e. methods that have a synchronized modifier)
	where
		P 	[?doSynchronizedDelMutation]
	
	by 
		P	
			% Create the mutant version of the program
			[doSynchronizedDelMutation] 
			%[print] 	
			 [writeToFile]
			% Undo mutation and return to original program
			[undoSynchronizedDelMutation]
end rule

%------------------------------------------------------------
% Create an RSB mutant by removing a synchronized keyword
% from around a synchronized block
%------------------------------------------------------------
function doSynchronizedDelMutation
	replace * [synchronized_statement]
		SynchStatement [synchronized_statement]
	deconstruct SynchStatement
		SynchStatement2 [synchronized_statement_2]
	deconstruct SynchStatement2
		'synchronized '( Expr [expression] ')
        Body [statement]

	% export the old synchronized expression and reinsert it 
	% once the mutant has been created and saved
	export Expr

	% create mutant comment to appear in source
	construct MutantString [stringlit]
		"RSB (Removed Synchronized Block)"

	by
		% Replace with empty syncronized statement
		'MUTATED ; /* 'MUTANT: MutantString */
		Body
end function

%------------------------------------------------------------
% Reinsert the orginal method declaration but leave the 
% MUTATED attribute to indicate that the mutant has already
% been created.
%------------------------------------------------------------
function undoSynchronizedDelMutation
	replace * [synchronized_statement]
		SynchStatement [synchronized_statement]

	% Import the old expression
	import Expr [expression]

	% extract body
	deconstruct SynchStatement
		'MUTATED NonSynchStatement [non_synchronized_statement]	
	deconstruct NonSynchStatement
		; /* 'MUTANT: MutantString [stringlit] */
		Body [statement]

	by 
		% replace mutated synchronized block with original but 
		% leave hidden attribute
		'MUTATED 'synchronized '( Expr ')
        		Body
end function

%Include rules for writing mutants to files
include "WriteMutants.Txl"
