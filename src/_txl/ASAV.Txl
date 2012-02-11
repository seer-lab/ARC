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
          [attr labelM] [asgn_stmt]
	| [attr labelM] [sync_asgn_stmt]
	| ...
end redefine

% How it looks when we started

define asgn_stmt
    % Assignment expression (From Java.grm)
    [unary_expression] [assignment_operator] [assignment_expression] ';
end define

% How it looks after

define sync_asgn_stmt
    /* 'MUTANT: [stringlit] */ 	[NL]
    'synchronized '( [expression] ')
    '{ [NL][IN]
	[unary_expression] [assignment_operator] [assignment_expression] '; [NL][EX]
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
		"ASAV"
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
		SyncStatement [synchronized_statement]

	deconstruct SyncStatement
		AsgnStatement [asgn_stmt]

	deconstruct AsgnStatement
    		UA [unary_expression]
		AO [assignment_operator]
		AE [assignment_expression] ';

	% export the old synchronized expression and reinsert it
	% once the mutant has been created and saved
	export AsgnStatement

	% create mutant comment to appear in source
	construct MutantString [stringlit]
		"ASAV (Added Sync Around Variable)"

	construct ThisExpr [expression]
		'this
	by
		% Replace with empty syncronized statement
		'MUTATED /* 'MUTANT: MutantString */
		'synchronized '( ThisExpr ')
    		'{
			UA AO AE ';
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
		SyncStatement [synchronized_statement]

	% Import the old expression
	import  AsgnStatement [asgn_stmt]

	% extract body
	deconstruct SyncStatement
		'MUTATED DoubleSync [sync_asgn_stmt]

	deconstruct DoubleSync
    		/* 'MUTANT: MutantStr1 [stringlit] */
		'synchronized '( ThisExpr [expression] ')
    		'{
    			UA [unary_expression]
			AO [assignment_operator]
			AE [assignment_expression] ';
    		'}
    		/* 'MUTANT: MutantStr2 [stringlit] */

	by
		% replace mutated synchronized block with original but
		% leave hidden attribute
		'MUTATED
			AsgnStatement
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
