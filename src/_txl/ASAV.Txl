%***********************************************************
% ASAV (Add Sync Around Variable from Contest) Mutator for ARC
% (Automatic Repair of Concurrency Bugs)
%
% Kevin Jalbert, David Kelk and Jeremy Bradbury, Mar. 2012
% SBSE Reading Course Project
%
% Based on ASK by J.S. Bradbury
%
% Typical invocation:
% txl ManageAccount.java ASAV.Txl - -outfile ManageAccount_1.java -outdir ASAV/
% -contestfile sharedVars.txt -class ManageAccount -var account
%
% Notes:
% - Only adds synchronization block around A := B statements
% - Java files must be named _1.java, _2.java due to the fact that
%   the second invocation of mutant generation will overwrite the first.
% - Output directory must already exist.
% - Class and variable name from ConTest are passed as arguments to TXL.
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
  | [other_statements]
  | [block]
  | [comment_NL]
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
  | [declaration_or_other_statements]
  | [block]
  | [comment_NL]
end redefine

% Our choices of sync statements for ASAV

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
  /* 'MUTANT: [stringlit] */  [NL]
  'synchronized '( [id] ')
  '{ [NL][IN]
    [unary_expression] [assignment_operator] [assignment_expression] '; [NL][EX]
  '}   [NL]
  /* 'MUTANT: [stringlit] */  [NL]
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

  % Read in name of class and variable from ConTest
  import TXLargs [repeat stringlit]
    deconstruct * TXLargs
      "-contestfile" contestFile [stringlit] "-class" clsNm [stringlit] "-var" varNm [stringlit] MoreOptions [repeat stringlit]

  construct className [id]
    _ [unquote clsNm]

  construct varName [id]
    _ [unquote varNm]

  export className
  export varName

  replace [program]
    P [program]

  by
    P [MutateSynchronizedInsert]
end function

%------------------------------------------------------------
% Add synchronization blocks around statments of the form, A := B
% and then perform the following 3 steps for each:
% 1. Create mutant of program with synchronized modifier added
% 2. Write mutant to a file
% 3. Remove synchronized modifier that was inserted
%------------------------------------------------------------
rule MutateSynchronizedInsert
  replace [program]
    P   [program]

  % only proceed for methods that satisfy the requirements
  where
    P   [?doSynchronizedInsertMutation]

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
% Create an ASAV mutant by synchronizing on an A := B statement
%------------------------------------------------------------
function doSynchronizedInsertMutation

  import className [id]
  import varName [id]

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

  by
    'MUTATED /* 'MUTANT: MutantString */
    'synchronized '( varName ')
    '{
      UA AO AE ';
    '}
    /* 'MUTANT: MutantString */
end function

%------------------------------------------------------------
% Reinsert the orginal statement declaration but leave the
% MUTATED attribute to indicate that the mutant has already
% been created.
%------------------------------------------------------------
function undoSynchronizedInsertMutation
  replace * [synchronized_statement]
    SyncStatement [synchronized_statement]

  % Import the old expression
  import AsgnStatement [asgn_stmt]

  % extract body
  deconstruct SyncStatement
    'MUTATED DoubleSync [sync_asgn_stmt]

  deconstruct DoubleSync
    /* 'MUTANT: MutantStr1 [stringlit] */
    'synchronized '( varName [id] ')
    '{
      UA [unary_expression]
      AO [assignment_operator]
      AE [assignment_expression] ';
    '}
    /* 'MUTANT: MutantStr2 [stringlit] */

  by
    % replace mutated statement with original but
    % leave hidden attribute
    'MUTATED
      AsgnStatement
end function

%Include rules for writing mutants to files
include "WriteMutants.Txl"
