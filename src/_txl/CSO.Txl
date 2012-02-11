%***********************************************************
% CSO (Change Sync Order) Mutator for ARC
% (Automatic Repair of Concurrency Bugs)
%
% Kevin Jalbert and David Kelk, Sept. 2011
% SBSE Reading Course Project
%
% Based on ESP by J.S. Bradbury
%***********************************************************

%***********************************************************
% ESP (Exchange Synchronized Block) Mutator
% Jeremy S. Bradbury

% Copyright 2006 J.S. Bradbury

% Revision history:

% Description: This mutation operator exchanges the synchronization
% block parameters of two nested synchronization blocks.
%***********************************************************

% Base grammar, and grammar override files
include "Java.Grm"
include "JavaCommentOverrides.Grm"

% Local grammar overrides
redefine synchronized_statement
	[attr labelM]  [synchronized_statement2]
	| [attr labelM] /* 'MUTANT: [stringlit] */ [NL] [synchronized_statement2]
end redefine

define synch_expression
    [assignment_expression]
end define

define synchronized_statement2
    'synchronized '( [synch_expression] ')
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
		"CSO"
	export MutantOpName

	replace [program]
        		P [program]

    	by	% Exchange all nested synchronization block parameters
    		P [ExchangeSynchBlockParameter]
end function

%------------------------------------------------------------
% Match all methods that have nested synchronized blocks
% and then perform the following 3 steps for each:
%	1. Create mutant of program with synchronized block
%      parameters switched
%	2. Write mutant to a file
%	3. Switch back synchronized block  parameters
%------------------------------------------------------------
rule ExchangeSynchBlockParameter
	replace [program]
		P 	[program]

	% only proceed for methods that satisfy the exchange requirements
	where
		P 	[?doExchangeLocks]

	by
		P	% Create the mutant version of the program
			[doExchangeLocks]
			%[print]
			[writeToFile]
			% Undo mutation and return to original program
			[undoExchangeLocks]
end rule

%------------------------------------------------------------
% Create a mutant by switching synchronization block
% parameters.
%------------------------------------------------------------
function doExchangeLocks
	replace * [synchronized_statement]
		SynchStatement [synchronized_statement]

	deconstruct SynchStatement
		SynchStatement2 [synchronized_statement2]

	export SynchStatement2

	deconstruct SynchStatement2
	    'synchronized '(  SynchExpr [synch_expression] ')
        		SynchBody [statement]

	%Only switch the first synch statement
	deconstruct * [statement] SynchBody
		SynchStatementB [synchronized_statement]

	deconstruct SynchStatementB
		SynchStatementB2 [synchronized_statement2]

	deconstruct SynchStatementB2
	    'synchronized '(  SynchExprB [synch_expression] ')
        		SynchBodyB [statement]

	% Check that the inner and outer synchronized block
	%parameters are not the same
	where not
		SynchExpr [isSameParam SynchExprB]

	construct SynchStmt_new [synchronized_statement2]
	 	'synchronized '(  SynchExprB ')
        			SynchBody [replaceInnerLock SynchExpr]

	% create mutant comment to appear in source
	construct MutantString [stringlit]
		"CSO (Change Sync Order)"

	by
		'MUTATED /* 'MUTANT: MutantString */ SynchStmt_new
end function

%------------------------------------------------------------
% Check that outer parameter is not the same as
% inner parameter
%------------------------------------------------------------
rule isSameParam InnerParam [synch_expression]
	match * [synch_expression]
		InnerParam
end rule

%------------------------------------------------------------
% Replace the inner block parameter with outer parameter
%------------------------------------------------------------
function replaceInnerLock SynchExpr [synch_expression]
	replace * [synchronized_statement2]
		SStmt [synchronized_statement2]

	deconstruct SStmt
   		 'synchronized '(  SynchExpr2 [synch_expression] ')
        			SynchBody2 [statement]
	by
   		 'synchronized '(  SynchExpr ')
        			SynchBody2
end function

%------------------------------------------------------------
% Switch back the synchronization block parameters but leave the
% MUTATED attribute to indicate that the mutant has already
% been created.
%------------------------------------------------------------
function undoExchangeLocks
	replace * [synchronized_statement]
		'MUTATED /* 'MUTANT: MutantString [stringlit] */ SynchStatement [synchronized_statement2]

	import SynchStatement2 [synchronized_statement2]

	by
		'MUTATED SynchStatement2
end function

%------------------------------------------------------------
%Remove MUTATED attributes for another pass
%------------------------------------------------------------
rule Clean
	replace [synchronized_statement]
		LStmt [synchronized_statement]
	deconstruct LStmt
		'MUTATED LStmt2 [synchronized_statement2]
	by
		LStmt2
end rule

%Include rules for writing mutants to files
include "WriteMutants.Txl"
