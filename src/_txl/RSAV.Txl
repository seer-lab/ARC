%***********************************************************
% RSAV (Remove Sync Around Variable) Mutator for ARC
% (Automatic Repair of Concurrency Bugs)
%
% Kevin Jalbert and David Kelk, Sept. 2011
% SBSE Reading Course Project
%
% Based on RSB by J.S. Bradbury
%***********************************************************

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

% Our choices of sync statements for RSAS

redefine synchronized_statement
          [attr labelM] [single_sync]
	| [attr labelM] [single_sync_removed]
	| ...
end redefine

% How it looks when we started

define single_sync
	'synchronized '( [expression] ')
 	'{ [NL][IN]
		[unary_expression] [assignment_operator] [assignment_expression] [NL]
	'}   [NL]
end define

% How it looks after removing

define single_sync_removed
    /* 'MUTANT: [stringlit] */ 	[NL]
    [unary_expression] [assignment_operator] [assignment_expression] '; [NL]
    /* 'MUTANT: [stringlit] */ 	[NL]
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
		"RSAV"
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
% Create an RSAS mutant by removing a synchronized keyword
% from around a synchronized block
%------------------------------------------------------------
function doSynchronizedDelMutation
	replace * [synchronized_statement]
		SyncStatement [synchronized_statement]

	deconstruct SyncStatement
		'synchronized '( SyncExpr [expression] ')
		'{
	    		UA [unary_expression]
			AO [assignment_operator]
			AE [assignment_expression] ';
		'}


	% export the old synchronized expression and reinsert it
	% once the mutant has been created and saved
	export UA
	export AO
	export AE
	export SyncExpr

	% create mutant comment to appear in source
	construct MutantString [stringlit]
		"RSAV (Removed Sync Around Variable)"

	by
		% Replace with empty syncronized statement
		'MUTATED /* 'MUTANT: MutantString */
		UA AO AE ';
		/* 'MUTANT: MutantString */
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
	import UA [unary_expression]
	import AO [assignment_operator]
	import AE [assignment_expression]
	import SyncExpr [expression]
	% extract body
	deconstruct SynchStatement
		'MUTATED SyncRemoved [single_sync_removed]
	deconstruct SyncRemoved
    		/* 'MUTANT: MutantStr1 [stringlit] */
	    		UA2 [unary_expression]
			AO2 [assignment_operator]
			AE2 [assignment_expression] ';
    		/* 'MUTANT: MutantStr2 [stringlit] */

	by
		% replace mutated synchronized block with original but
		% leave hidden attribute
		'MUTATED
		'synchronized '( SyncExpr ')
		'{
			UA AO AE
		'}
end function

%Include rules for writing mutants to files
include "WriteMutants.Txl"
