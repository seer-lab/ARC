%***********************************************************
% ASAS (Add Sync Around Sync) Mutator for ARC
% (Automatic Repair of Concurrency Bugs)
%
% Kevin Jalbert and David Kelk, Sept. 2011
% SBSE Reading Course Project
%
% Based on ASK by J.S. Bradbury
%***********************************************************

%***********************************************************
% ASK (Add Synchronized Keyword To a Method) Mutator
% Jeremy S. Bradbury

% Copyright 2006 J.S. Bradbury

% Description: This mutation operator adds the synchronized
% keyword to any method that is not synchronized. We do
% not consider constructors because a constructor method
% can not be synchronized.

% NOTE: This operator generates a number of equivalent
% mutants. In the future we plan to restrict the ASK mutator
% to add a synchronized modifier ONLY to methods that
% have synchronized blocks (with the objective to cause
% a deadlock bug)
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
	| [attr labelM] [double_sync]
	| ...
end redefine

% How it looks when we started

define single_sync
    'synchronized '( [expression] ')
    '{ [NL][IN]
	[repeat declaration_or_statement] [NL][EX]
    '}   [NL]
end define

% How it looks after removing

define double_sync
    /* 'MUTANT: [stringlit] */ 	[NL]
    'synchronized '( [expression] ')
    '{ [NL][IN]
	'synchronized '( [expression] ')
 	'{ [NL][IN]
		[repeat declaration_or_statement] [NL][EX]
	'}   [NL]
    '}   [NL]
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
		"ASAS"
	export MutantOpName

	replace [program]
        		P [program]

    	by
		% Add synchronized modifier to all non-synchronized
		% methods one at a time
        		P [MutateSynchronizedInsert]
end function

%------------------------------------------------------------
% Match all methods that do not have a synchronized modifier
% and then perform the following 3 steps for each:
%	1. Create mutant of program with synchronized modifier added
%	2. Write mutant to a file
%	3. Remove synchronized modifier that was inserted
%------------------------------------------------------------
rule MutateSynchronizedInsert
	replace [program]
		P 	[program]

	% only proceed for methods that satisfy the requirements
	% (i.e. methods that are not synchronized)
	where
		P 	[?doSynchronizedInsertMutation]

	by
		P
			% Create the mutant version of the program
			[doSynchronizedInsertMutation]
			% [print]
			[writeToFile]
			% Undo mutation and return to original program
			[undoSynchronizedInsertMutation]
end rule

%------------------------------------------------------------
% Create an ASK mutant by adding synchronized to the method
% modifier list of a method that is not synchronized
%------------------------------------------------------------
function doSynchronizedInsertMutation
	replace * [synchronized_statement]
		SynchStatement [synchronized_statement]

	deconstruct SynchStatement
		SynchStatement2 [single_sync]

	deconstruct SynchStatement2
    		'synchronized '( InnerExpr [expression] ')
    		'{
			InnerBody [repeat declaration_or_statement]
    		'}

	where not InnerExpr [isThis]

	% export the old synchronized expression and reinsert it
	% once the mutant has been created and saved
	export InnerExpr
	export InnerBody

	% create mutant comment to appear in source
	construct MutantString [stringlit]
		"ASAS (Added Sync Around Sync)"

	construct ThisExpr [expression]
		'this

	by
		% Replace with empty syncronized statement
		'MUTATED /* 'MUTANT: MutantString */
		'synchronized '( ThisExpr ')
    		'{
			'synchronized '( InnerExpr ')
 			'{
				InnerBody
			'}
    		'}
		/* 'MUTANT: MutantString */
end function

%------------------------------------------------------------
% Reinsert the orginal method declaration but leave the
% MUTATED attribute to indicate that the mutant has already
% been created.
%------------------------------------------------------------
function undoSynchronizedInsertMutation
	replace * [synchronized_statement]
		SynchStatement [synchronized_statement]

	% Import the old expression
	import InnerExpr [expression]
	import InnerBody [repeat declaration_or_statement]

	% extract body
	deconstruct SynchStatement
		'MUTATED DoubleSync [double_sync]

	deconstruct DoubleSync
    		/* 'MUTANT: MutantStr1 [stringlit] */
		'synchronized '( ThisExpr [expression] ')
    		'{
			'synchronized '( IE [expression] ')
 			'{
				IB [repeat declaration_or_statement]
			'}
    		'}
    		/* 'MUTANT: MutantStr2 [stringlit] */

	by
		% replace mutated synchronized block with original but
		% leave hidden attribute
		'MUTATED
		'synchronized '( InnerExpr ')
 		'{
			InnerBody
		'}
end function

%------------------------------------------------------------
% Check if current parameter is "this"
%------------------------------------------------------------
rule isThis
	match [expression]
		'this
end rule

%Include rules for writing mutants to files
include "WriteMutants.Txl"
