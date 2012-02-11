%***********************************************************
% EXSA (EXpand Sync region After) Mutator for ARC
% (Automatic Repair of Concurrency Bugs)
%
% Kevin Jalbert and David Kelk, Sept. 2011
% SBSE Reading Course Project
%
% Based on EXCR by J.S. Bradbury
%***********************************************************

%***********************************************************
% EXCR (Expand Criitical Region) Mutator
% Jeremy S. Bradbury

% Copyright 2006 J.S. Bradbury

% Revision history:

% Description: This mutation operator expands a critical region by including
% the statement directly above and below the existing region.

% Limitations: This operator currently expands only
% synchronized block critical regions. In the future
% we plan to extend the operator to shift critical regions
% created with explicit locks, etc.
%***********************************************************

% Base grammar, and grammar override files
include "Java.Grm"
include "JavaCommentOverrides.Grm"

% Local grammar overrides
redefine statement
        [synchronized_statement]
    | 	[other_statements]
    |   [block]
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
    |   [class_declaration]
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
	| [attr labelM] [expanded_synchronized_statement]
end redefine

define synchronized_statement_2
	'synchronized '( [expression] ')
	'{                                        [NL][IN]
    		[repeat declaration_or_statement]         [NL][EX]
	'}	[NL]
	[opt declaration_or_other_statements]   [NL]
end define

define expanded_synchronized_statement
    /* 'MUTANT: [stringlit] */ 				[NL]
	'synchronized '( [expression] ')
	'{                                        [NL][IN]
    		[repeat declaration_or_statement]         [NL][EX]
	'}	[NL]
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

	% initialize and export the name of the current mutant while
	% will be used for folder name generation
	construct MutantOpName [stringlit]
		"EXSA"
	export MutantOpName

	replace [program]
        		P [program]

    	by	% Expand all instances of synchronized blocks one at
		% a time
        		P [MutateExpandCriticalRegion]
end function

%------------------------------------------------------------
% Match all methods that have a synchronized block
% and then perform the following 3 steps for each:
%	1. Create mutant of program with synchronized block
%      expanded
%	2. Write mutant to a file
%	3. Shrink synchronized block that was expanded
%------------------------------------------------------------
rule MutateExpandCriticalRegion
	replace [program]
		P 	[program]

	% only proceed for methods that satisfy the requirements
	% (i.e. methods that have a synchronized modifier)
	where
		P 	[?doExpandCriticalRegion]

	by
		P	% Create the mutant version of the program
			[doExpandCriticalRegion]
			%[print]
			 [writeToFile]
			% Undo mutation and return to original form
			[undoExpandCriticalRegion]
end rule

%------------------------------------------------------------
% Create an EXCR mutant by expanding a critical region
%------------------------------------------------------------
function doExpandCriticalRegion
	replace * [synchronized_statement]
		SynchStatement [synchronized_statement]

	deconstruct SynchStatement
		SynchStatement2 [synchronized_statement_2]
	deconstruct SynchStatement2
		'synchronized '( Expr [expression] ') '{
			S2 [repeat declaration_or_statement]
		'}
		S3 [declaration_or_other_statements]

	export S2
	export S3

	construct S3_b [declaration_or_statement]
		S3

	% create mutant comment to appear in source
	construct MutantString [stringlit]
		"EXSA (Expand Synch. After)"

	by
		'MUTATED /* 'MUTANT: MutantString */
		'synchronized '( Expr ') '{
			S2 [. S3_b]
		'}
end function

%------------------------------------------------------------
% Shrink critical region back to original size but leave the
% MUTATED attribute to indicate that the mutant has already
% been created.
%------------------------------------------------------------
function undoExpandCriticalRegion
	replace * [synchronized_statement]
		SynchStatement [synchronized_statement]

	deconstruct SynchStatement
		'MUTATED
		ExpandedStatement [expanded_synchronized_statement]

	% Import the old body of synchronization block
	import S2 [repeat declaration_or_statement]
	import S3 [declaration_or_other_statements]

	% extract body
	deconstruct ExpandedStatement
		/* 'MUTANT: MutantString1[stringlit] */
		'synchronized '( Expr [expression] ') '{
			NewBody [repeat declaration_or_statement]
		'}

	by
		% replace mutated synchronized block with original but
		% leave hidden attribute
		'MUTATED 'synchronized '( Expr ') '{
        			S2
		'}
		S3
end function

%Include rules for writing mutants to files
include "WriteMutants.Txl"
