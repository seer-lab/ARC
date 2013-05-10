%***********************************************************
% CSO (Change Sync Order) Mutator for ARC
% (Automatic Repair of Concurrency Bugs)
%
% Copyright David Kelk and Kevin Jalbert, 2012
%           David Kelk, 2013
%
% Based on ESP by J.S. Bradbury
%
% Typical invocation:
% txl ManageAccount.java CSO.Txl - -outfile ManageAccount_1.java -outdir CSO/
%
% Notes:
% - Output directory must already exist.
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
	  [attr labelM] [double_sync_before]
	|
    [attr labelM] [double_sync_after]
end redefine

% How it looks before

define double_sync_before
  'synchronized '( [expression] ')
  '{ [NL][IN]
    'synchronized '( [expression] ')
    '{ [NL][IN]
      [repeat declaration_or_statement] [NL][EX]
     '} [NL]
  '} [NL]
end define

% How it looks after

define double_sync_after
  /* 'MUTANT: [stringlit] */ [NL]
  'synchronized '( [expression] ')
  '{ [NL][IN]
    'synchronized '( [expression] ')
    '{ [NL][IN]
      [repeat declaration_or_statement] [EX]
    '} [NL][EX]
  '} [NL]
  /* 'MUTANT: [stringlit] */ [NL]
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
%    with parameters switched
%	2. Write mutant to a file
%	3. Switch back synchronized block parameters
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
	    'synchronized '( OuterSynchExpr [expression] ')
      '{
        'synchronized '( InnerSynchExpr [expression] ')
        '{
            InnerSynchBody [repeat declaration_or_statement]
        '}
      '}

  export SynchStatement

	% Check that the inner and outer synchronized block
	%parameters are not the same
	where not
		OuterSynchExpr [isSameParam InnerSynchExpr]

  construct MutantString [stringlit]
    "CSO (Change Sync Order)"

	construct SynchStmtNew [synchronized_statement]
    'MUTATED /* 'MUTANT: MutantString */
	 	'synchronized '(  InnerSynchExpr ')
    '{
      'synchronized '( OuterSynchExpr ')
        '{
          InnerSynchBody
        '}
    '}
    /* 'MUTANT: MutantString */

	by
    SynchStmtNew

end function

%------------------------------------------------------------
% Check that outer parameter is not the same as the
% inner parameter
%------------------------------------------------------------
rule isSameParam InnerParam [expression]
	match * [expression]
		InnerParam
end rule

%------------------------------------------------------------
% Switch back the synchronization block parameters but leave the
% MUTATED attribute to indicate that the mutant has already
% been created.
%------------------------------------------------------------
rule undoExchangeLocks
	replace * [synchronized_statement]
    InStmt [synchronized_statement]

  deconstruct InStmt
    'MUTATED /* 'MUTANT: MutantString1 [stringlit] */
    'synchronized '(  InnerSynchExpr [expression] ')
    '{
      'synchronized '( OuterSynchExpr [expression] ')
      '{
        InnerSynchBody [repeat declaration_or_statement]
      '}
    '}
    /* 'MUTANT: MutantString2 [stringlit] */

	by
		'MUTATED 'synchronized '(  OuterSynchExpr ')
    '{
      'synchronized '( InnerSynchExpr ')
      '{
        InnerSynchBody
      '}
    '}
end rule

%Include rules for writing mutants to files
include "WriteMutants.Txl"
