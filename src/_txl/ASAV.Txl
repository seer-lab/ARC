%***********************************************************
% ASAV (Add Sync Around Variable with Class and Variable
% targeting) Mutator for ARC
% (Automatic Repair of Concurrency Bugs)
%
% Kevin Jalbert, David Kelk and Jeremy Bradbury, Mar. 2012
% SBSE Reading Course Project
%
% Based on ASK by J.S. Bradbury
%
% Typical invocation:
% txl ManageAccount.java ASAV.Txl - -outfile ManageAccount_1.java -outdir ASAV/
% -class ManageAccount -var account
%
% Notes:
% - Method targeting doesn't work.  Jim Cordy pointed out on the TXL forum
%   that TXL is about (global) transformation, not search/replace
% - Java files must be named _1.java, _2.java due to the fact that
%   the second invocation of mutant generation will overwrite the first.
% - Output directory must already exist.
% - Class and variable name are passed as arguments to TXL.
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

% Our choices of sync statements for ASAV

redefine synchronized_statement
    [attr labelM] [asgn_stmt]
  | [attr labelM] [sync_asgn_stmt]
  | ...
end redefine

% How it looks when we started

define asgn_stmt
    [other_statements]
end define

% How it looks after mutation

define sync_asgn_stmt
  /* 'MUTANT: [stringlit] */  [NL]
  'synchronized '( [id] ')
  '{ [NL][IN]
    [other_statements]
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
      "-class" clsNm [stringlit] "-var" varNm [stringlit] MoreOptions [repeat stringlit]

  construct className [id]
    _ [unquote clsNm]

  construct variableName [id]
    _ [unquote varNm]

  export className
  export variableName

  replace [program]
    P [program]

  by
    P [MutateSynchronizedInsert]
end function

%------------------------------------------------------------
% Add synchronization blocks around statments
% and then perform the following 3 steps for each:
% 1. Create mutant of program with synchronized modifier added
% 2. Write mutant to a file
% 3. Remove synchronized modifier that was inserted
%------------------------------------------------------------
rule MutateSynchronizedInsert
  replace [program]
    P   [program]

  % only proceed for methods that satisfy the requirements
  where all
    P   [?matchClassName]
        [?doSynchronizedInsertMutation]
  by
    P
      % Create the mutant version of the program
      [matchClassName]
      [doSynchronizedInsertMutation]
      % [print]
      [writeToFile]
      % Undo mutation and return to original program
      [undoSynchronizedInsertMutation]
end rule

%------------------------------------------------------------
% Create an ASAV mutant by synchronizing on variableName
%------------------------------------------------------------
function doSynchronizedInsertMutation

  %import className [id]
  import variableName [id]

  replace * [synchronized_statement]
    SyncStatement [synchronized_statement]

    deconstruct SyncStatement
      OtherStatements [other_statements]

    % Check variable here
    where
      OtherStatements [isSameVariable variableName]

    % export the old synchronized expression and reinsert it
    % once the mutant has been created and saved
    export OtherStatements

    % create mutant comment to appear in source
    construct MutantString [stringlit]
      "ASAV (Added Sync Around Variable)"

  by
    'MUTATED /* 'MUTANT: MutantString */
    'synchronized '( variableName ')
    '{
      OtherStatements
    '}
    /* 'MUTANT: MutantString */
end function

%------------------------------------------------------------
% Match class name
%------------------------------------------------------------
function matchClassName

  import className [id]

  replace * [class_name]
    clsName [class_name]

  where
    clsName [isSameClass className]
  by
    clsName
end function

rule isSameClass ClsName [id]
  match * [id]
    ClsName
end rule

%------------------------------------------------------------
% Match variable name
%------------------------------------------------------------

rule isSameVariable VarName [id]
  match * [id]
    VarName
end rule

%------------------------------------------------------------
% Reinsert the orginal statement declaration but leave the
% MUTATED attribute to indicate that the mutant has already
% been created.
%------------------------------------------------------------
function undoSynchronizedInsertMutation
  replace * [synchronized_statement]
    SyncStatement [synchronized_statement]

  % Import the old expression
  import OtherStatements [other_statements]

  % extract body
  deconstruct SyncStatement
    'MUTATED DoubleSync [sync_asgn_stmt]

  deconstruct DoubleSync
    /* 'MUTANT: MutantStr1 [stringlit] */
    'synchronized '( variableName [id] ')
    '{
      OthStmt [other_statements]
    '}
    /* 'MUTANT: MutantStr2 [stringlit] */

  by
    % replace mutated statement with original but
    % leave hidden attribute
    'MUTATED
      OtherStatements
end function

%Include rules for writing mutants to files
include "WriteMutants.Txl"
