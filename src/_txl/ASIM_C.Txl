%***********************************************************
% ASIM_C (Add Sync in Method Header) Mutator for ARC
% (Automatic Repair of Concurrency Bugs)
% Only class targeting information (_C) is available
%
% Copyright David Kelk and Kevin Jalbert, 2012
%           David Kelk, 2013
%
% Based on ASK by J.S. Bradbury
%
% Typical invocation:
% txl ManageAccount.java ASIM.Txl - -outfile ManageAccount_1.java
% -outdir ASIM/ -class ManageAccount
%
% Notes:
% - Java files must be named _1.java, _2.java due to the fact
%   that the second invocation of mutant generation will
%   overwrite the first.
% - Output directory must already exist.
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
redefine method_or_constructor_declaration
    [attr labelM] [method_declaration]
  | [attr labelM] /* 'MUTANT: [stringlit] */ [method_declaration] /* 'MUTANT: [stringlit] */
  | [attr labelM] [constructor_declaration]
end redefine

redefine method_declaration
  [NL] [repeat modifier] [rest_of_method_declaration]
end redefine

define rest_of_method_declaration
  [type_specifier] [method_declarator] [opt throws] [method_body]
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
    "ASIM_C"
  export MutantOpName

  % Read in name of class and variable from ConTest
  import TXLargs [repeat stringlit]
    deconstruct * TXLargs
      "-class" clsNm [stringlit] MoreOptions [repeat stringlit]

  construct className [id]
    _ [unquote clsNm]
  export className

  replace [program]
    P [program]
  by
    P [ProcessSynchronizeStatementMutations]
end function

%------------------------------------------------------------
% Start the mutation process at the global level.
% - IdentifyMutationClass limits the scope to the required
%   class (className)
% - The other classes are skipped over
% - Print/WriteToFile has to be at this level so that ALL
%   classes appear in the mutated file
%------------------------------------------------------------
rule ProcessSynchronizeStatementMutations
  replace [program]
    P [program]
  where
    P [?IdentifyMutationClass]
  by
    P [IdentifyMutationClass]
      %[print]
      [writeToFile]
      % Undo mutation and return to original program
      [undoSynchronizeStatementMutation]
end rule

%------------------------------------------------------------
% Start by matching the class name
% - Deconstruct a class declaration to get the [class_name]
% - Efficiency: Don't import a variable [className] until it
%   is needed
% - Efficiency: Don't call [?IdentifyMutationMethod]
%   until the proper class has been identified
%------------------------------------------------------------
function IdentifyMutationClass
  replace * [class_declaration]
    AClass [class_declaration]

  deconstruct AClass
    AClassHead [class_header] AClassBody [class_body]

  deconstruct AClassHead
      Mod [repeat modifier] 'class AClassName [class_name]
      EC [opt extends_clause] IM [opt implements_clause]

  import className [id]

  where
    AClassName [isSameClass className]

  where
    AClass [?doSynchronizeStatementMutation]

  by
    AClass [doSynchronizeStatementMutation]
end function

%---------------------
% Match the class name
%---------------------

rule isSameClass ClsName [id]
  match * [id]
    ClsName
end rule

%------------------------------------------------------------
%
%------------------------------------------------------------
function doSynchronizeStatementMutation
  replace * [method_or_constructor_declaration]
    GenDecl [method_or_constructor_declaration]

  deconstruct GenDecl
    MethodDecl [method_declaration]

  deconstruct MethodDecl
    MethodModifiers [repeat modifier]
    RemainingDelcaration [rest_of_method_declaration]

  % check that the synchronized modifier is not present
  where not
    MethodModifiers [hasSynchronizedKeyword]

  % create new list of modifiers
  construct SynchronizedModifier [modifier]
    'synchronized
  construct NewMethodModifiers [repeat modifier]
    MethodModifiers [. SynchronizedModifier]

  % export the old declaration and reinsert it
  % once the mutant has been created and saved
  export GenDecl

  % create mutant comment to appear in source
  construct MutantString [stringlit]
    "ASIM (Add Sync In Method declaration)"
  by
    % generate hidden attribute and comment
    'MUTATED /* 'MUTANT: MutantString */
    % populate new modifier list with all existing modifiers
    % plus synchronized
    NewMethodModifiers
    % reinsert rest of method declaration
    RemainingDelcaration
    /* 'MUTANT: MutantString */
end function

%------------------------------------------------------------
%
%------------------------------------------------------------
function undoSynchronizeStatementMutation
  replace * [method_or_constructor_declaration]
    CurrGenDecl [method_or_constructor_declaration]

  % Import the old declaration
  import GenDecl [method_or_constructor_declaration]

  % extract method declaration
  deconstruct GenDecl
    SavedMethodDecl [method_declaration]

  deconstruct CurrGenDecl
    'MUTATED /* 'MUTANT: MutantString1 [stringlit] */
    CurrMethodDecl [method_declaration]
    /* 'MUTANT: MutantString2 [stringlit] */
  by
    % replace mutated declaration with original
    % but leave hidden attribute
    'MUTATED SavedMethodDecl
end function

%------------------------------------------------------------
% Check if method modifier list includes synchronized
%------------------------------------------------------------
rule hasSynchronizedKeyword
  match * [modifier]
    'synchronized
end rule

%Include rules for writing mutants to files
include "WriteMutants.Txl"
