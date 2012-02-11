%***********************************************************
% SHSA (SHrink Sync region After) Mutator for ARC
% (Automatic Repair of Concurrency Bugs)
%
% Kevin Jalbert and David Kelk, Sept. 2011
% SBSE Reading Course Project
%
% Based on SKCR by J.S. Bradbury
%***********************************************************

%***********************************************************
% SKCR (Shrink Critical Region) Mutator
% Jeremy S. Bradbury

% Copyright 2006 J.S. Bradbury

% Revision history:

% Description: This mutation operator shrinks the
% the synchronizied block around a group of statements.
%***********************************************************

% Base grammar, and grammar override files
include "Java.Grm"
include "JavaCommentOverrides.Grm"

% Local grammar overrides

redefine statement
        	[synchronized_statement]
	| 	[other_statements]
   	|   	[block]
	|	[comment_NL]
end redefine

define other_statements
    	[label_statement]
    |   [empty_statement]
    |   [expression_statement]
    |   [if_statement]
    |   [switch_statement]
    |   [while_statement]
    |   [do_statement]
    |   [for_statement]
    |   [break_statement]
    |   [continue_statement]
    |   [return_statement]
    |   [throw_statement]
    |   [try_statement]
end define

define declaration_or_other_statements
        [local_variable_declaration]
%   |   [class_declaration]     DK
    |   [other_statements]
end define

redefine declaration_or_statement
	 	[synchronized_statement]
	|	[declaration_or_other_statements]
	|       [block]
	|	[comment_NL]
end redefine

redefine synchronized_statement
	[attr labelM] [synchronized_statement_2]
	| [attr labelM] [shrunk_synchronized_statement]
	| ...
end redefine

% How it looks when we started

define synchronized_statement_2
    'synchronized '( [expression] ')
    '{                                        [NL][IN]
	[repeat declaration_or_statement] [NL][EX]% DK
    '}	[NL]
end define

% How it looks after shrinking

define shrunk_synchronized_statement
        /* 'MUTANT: [stringlit] */ 				[NL]
	'synchronized '( [expression] ')
	'{                                        [NL][IN]
    		[repeat declaration_or_statement]         [EX]
	'}   [NL]
	[repeat declaration_or_statement]    [NL]   % DK
	/* 'MUTANT: [stringlit] */ 				[NL]

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

	% initialize and export the name of the current mutant that
	% will be used for folder name generation
	construct MutantOpName [stringlit]
		"SHSA"
	export MutantOpName

	replace [program]
        		P [program]

   	 by	% shrink all instances of synchronized blocks one at
		% a time
        		P [MutateShrinkCriticalRegion]
end function

%------------------------------------------------------------
% Match all methods that have a synchronized block
% and then perform the following 3 steps for each:
%	1. Create mutant of program with synchronized block
%          shrunk after (only)
%	2. Write mutant to a file
%	3. Expand synchronized block that was shrunk
%------------------------------------------------------------
rule MutateShrinkCriticalRegion
	replace [program]
		P 	[program]

	% only proceed for methods that satisfy the requirements
	% (i.e. methods that have a synchronized modifier)
	where
		P 	[?doShrinkCriticalRegion]

	by
		P	% Create the mutant version of the program
			[doShrinkCriticalRegion]
			%[print]
			[writeToFile]
			% Undo mutation and return to original program
			[undoShrinkCriticalRegion]
end rule

%------------------------------------------------------------
% Create an SHSA mutant by shrinking a critical region
% after.  That is, move the last line of code in the critical
% region outside (after) the critical region.
%------------------------------------------------------------
function doShrinkCriticalRegion

	replace * [synchronized_statement]
		SynchStatement [synchronized_statement]

	deconstruct SynchStatement
		SynchStatement2 [synchronized_statement_2]

	deconstruct SynchStatement2
	'synchronized '( Expr [expression] ') '{
                Body [repeat declaration_or_statement]
	'}

	% export the old body of the synchronized block
	export Body

	construct MiddleStatements
		[repeat declaration_or_statement]

	where MiddleStatements
		[? generateMiddle Body]

	construct M2
		[repeat declaration_or_statement]
		_ [generateMiddle Body]

	import Second [declaration_or_statement]

	% create mutant comment to appear in source
	construct MutantString [stringlit]
		"SHSA (Shrink Sync After)"

	by
		'MUTATED /* 'MUTANT: MutantString */
		'synchronized '( Expr ') '{
			M2
		'}
		Second
		/* 'MUTANT: MutantString */
end function

%------------------------------------------------------------
% Recursive function to generate new shrunk critical region
%------------------------------------------------------------
function generateMiddle Statement2 [repeat declaration_or_statement]

	deconstruct Statement2
		First [declaration_or_statement] Rest [repeat declaration_or_statement]

	deconstruct Rest
		Second [declaration_or_statement] More [repeat declaration_or_statement]

	export Second

	construct Temp [repeat declaration_or_statement]

	replace  [repeat declaration_or_statement]
		X [repeat declaration_or_statement]

	by
		First Temp [generateMiddle Rest]
end function

%------------------------------------------------------------
% Return mutated code to original form but leave the
% MUTATED attribute to indicate that the mutant has already
% been created.
%------------------------------------------------------------
function undoShrinkCriticalRegion
	replace * [synchronized_statement]
		SynchStatement [synchronized_statement]

	deconstruct SynchStatement
		'MUTATED
		ShrunkStatement [shrunk_synchronized_statement]

	% Import the old body of synchronization block
	import Body [repeat declaration_or_statement]

	% extract body
	deconstruct ShrunkStatement
		/* 'MUTANT: MutantString1[stringlit] */
		'synchronized '( Expr [expression] ') '{
			S2 [repeat declaration_or_statement]
		'}
		S1 [repeat declaration_or_statement]
		/* 'MUTANT: MutantString2[stringlit] */

	by
		% replace mutated synchronized block with original but
		% leave hidden attribute
		'MUTATED 'synchronized '( Expr ') '{
			Body
		'}
end function

%Include rules for writing mutants to files
include "WriteMutants.Txl"
