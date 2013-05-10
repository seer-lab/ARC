%***********************************************************
% RSAV (Remove Sync Around Variable) Mutator for ARC
% (Automatic Repair of Concurrency Bugs)
%
% Copyright David Kelk and Kevin Jalbert, 2012
%           David Kelk, 2013
%
% Based on RSB by J.S. Bradbury
%
% Typical invocation:
% txl ManageAccount.java RSAV.Txl - -outfile ManageAccount.java -outdir RSAV/
%
% Notes:
% - Output directory must already exist.
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
	| [other_statements]
  | [block]
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
  | [other_statements]
end define

redefine declaration_or_statement
	 	[synchronized_statement]
	|	[declaration_or_other_statements]
	| [block]
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
    [repeat statement] [NL]
	'}   [NL]
end define

% How it looks after removing

define single_sync_removed
  /* 'MUTANT: [stringlit] */ 	[NL]
  [repeat statement] [NL]
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
		% Remove all instances of synchronized blocks around variables
    % one at a time
    P [MutateSynchronizedDel]
end function

%------------------------------------------------------------
% Match all variables that have a synchronized block
% and then perform the following 3 steps for each:
%	1. Create mutant of program with synchronized block
%    removed
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
% Create an RSAV mutant by removing a synchronized block
% around an assignment statement
%------------------------------------------------------------
function doSynchronizedDelMutation
	replace * [synchronized_statement]
		SyncStatement [synchronized_statement]

	deconstruct SyncStatement
		'synchronized '( SyncExpr [expression] ')
		'{
      Stm [repeat statement]
		'}


	% export the old synchronized expression and reinsert it
	% once the mutant has been created and saved
  export Stm
	export SyncExpr

	% create mutant comment to appear in source
	construct MutantString [stringlit]
		"RSAV (Removed Sync Around Variable)"

	by
		% Replace with empty syncronized statement
		'MUTATED /* 'MUTANT: MutantString */
    Stm
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
	import Stm [repeat statement]
  import SyncExpr [expression]

	% extract body
	deconstruct SynchStatement
		'MUTATED SyncRemoved [single_sync_removed]

	deconstruct SyncRemoved
    /* 'MUTANT: MutantStr1 [stringlit] */
	  Stm
    /* 'MUTANT: MutantStr2 [stringlit] */

	by
		% replace mutated synchronized block with original but
		% leave hidden attribute
		'MUTATED
		'synchronized '( SyncExpr ')
		'{
      Stm
		'}
end function

%Include rules for writing mutants to files
include "WriteMutants.Txl"
