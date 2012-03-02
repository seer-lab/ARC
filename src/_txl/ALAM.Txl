%***********************************************************
% ALAM (Add Lock Around a Method) Mutator for ARC
% (Automatic Repair of Concurrency Bugs)
%
% Kevin Jalbert and David Kelk, March 2012
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

define ARCLock
  'static 'Object 'ARCLock '= 'new 'Object() ';
end define

define ARCLockSynch
  'synchronized '( 'ARCLock ')
end define

redefine class_or_interface_body
    '{                                    [NL][IN]
       [repeat class_body_declaration]    [EX]
    '} [opt ';]
  |
    '{                                    [NL][IN]
       [attr labelM] /* 'MUTANT: [stringlit] */ [NL]
       [ARCLock] [NL]
       /* 'MUTANT: [stringlit] */         [NL]
       [repeat class_body_declaration]    [EX]
    '} [opt ';]                           [NL][NL]
end define

redefine method_or_constructor_declaration
    [attr labelM] [method_declaration]
  |
    [attr labelM] /* 'MUTANT: [stringlit] */
    [method_declaration]
    /* 'MUTANT: [stringlit] */ [NL]
  |
    [attr labelM] [constructor_declaration]
end redefine

define labelM
  'MUTATED
end define

redefine method_declaration
  [NL] [repeat modifier] [type_specifier] [rest_of_method_declaration]
end redefine

define rest_of_method_declaration
  [method_declarator] [opt throws] [method_body]
end define

redefine block
    '{                                        [NL][IN]
        [repeat declaration_or_statement]     [EX]
    '}
   |
    '{ [NL][IN]
        'synchronized '( 'ARCLock ') [NL]
        '{ [NL][IN]
          [repeat declaration_or_statement]     [EX]
        '}
    '}
end redefine

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
    "ALAM"
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
% 1. Create mutant of program with synchronized modifier added
% 2. Write mutant to a file
% 3. Remove synchronized modifier that was inserted
%------------------------------------------------------------
rule MutateSynchronizedInsert
  replace [program]
    P   [program]

  % only proceed for methods that satisfy the requirements
  % (i.e. methods that are not synchronized)
  where
    P   [?doSynchronizedInsertMutation]

  by
    P
      % Create the mutant version of the program
      [doInsertStaticLock]
      [doSynchronizedInsertMutation]
      % [print]
      [writeToFile]
      % Undo mutation and return to original program
      [undoSynchronizedInsertMutation]
end rule

%------------------------------------------------------------
% Insert the lock as a static object at the class level.
%
%------------------------------------------------------------
function doInsertStaticLock
  replace * [class_or_interface_body]
    ClassBody [class_or_interface_body]

  deconstruct ClassBody
    '{
       ClassBodyDec [repeat class_body_declaration]
    '}

  % Check if this has been done already
  where ClassBodyDec [hasLockAlready]

  % create mutant comment to appear in source
  construct MutantString [stringlit]
    "ALAM (Add Lock Around a Method)"

  by
    % generate hidden attribute and comment
    '{
       'MUTATED /* 'MUTANT: MutantString */
       'static 'Object 'ARCLock '= 'new 'Object() ';
       /* 'MUTANT: MutantString */
       ClassBodyDec
    '}
end function

%------------------------------------------------------------
% Create an ASK mutant by adding synchronized to the method
% modifier list of a method that is not synchronized
%------------------------------------------------------------
function doSynchronizedInsertMutation
  replace * [method_or_constructor_declaration]
    GenDecl [method_or_constructor_declaration]

  deconstruct GenDecl
    MethodDecl [method_declaration]

  % export the old declaration and reinsert it
  % once the mutant has been created and saved
  export GenDecl

  deconstruct MethodDecl
    MethodModifiers [repeat modifier]
    TypeSpec [type_specifier]
    RemainingDeclaration [rest_of_method_declaration]

  deconstruct RemainingDeclaration
    MD [method_declarator]
    OT [opt throws]
    MB [method_body]

  deconstruct MB
    BL [block]

  deconstruct BL
    '{
        DOS [repeat declaration_or_statement]
    '}

  % check if this operator has been applied before
    DOS [IsALAMAlready]

  % create new block
  construct SynchBlock [block]
    '{
      'synchronized '( 'ARCLock ')
      '{
        DOS
      '}
    '}

  construct NewBody [method_body]
    SynchBlock

  construct NewRemDecl [rest_of_method_declaration]
    MD OT NewBody

  construct NewMethodDecl [method_declaration]
    MethodModifiers TypeSpec NewRemDecl

  construct NewGenDecl [method_declaration]
    NewMethodDecl

  % create mutant comment to appear in source
  construct MutantString [stringlit]
    "ASM (Add Sync around a Method)"

  by
    % generate hidden attribute and comment
    'MUTATED /* 'MUTANT: MutantString */
    NewMethodDecl
    /* 'MUTANT: MutantString */
end function

%------------------------------------------------------------
% Reinsert the orginal method declaration but leave the
% MUTATED attribute to indicate that the mutant has already
% been created.
%------------------------------------------------------------
function undoSynchronizedInsertMutation
  replace * [method_or_constructor_declaration]
    CurrGenDecl [method_or_constructor_declaration]

  % Import the old declaration
  import GenDecl [method_or_constructor_declaration]

  % extract method declaration
  deconstruct GenDecl
    SavedMethodDecl [method_declaration]

  deconstruct CurrGenDecl
    'MUTATED /* 'MUTANT: MutStr1 [stringlit] */
    CurMethDecl [method_declaration]
    /* 'MUTANT: MutStr2 [stringlit] */

  by
    % replace mutated declaration with original
    % but leave hidden attribute
    'MUTATED SavedMethodDecl

end function

%------------------------------------------------------------
% Check if the ARCLock variable has already been added to
% the class
%------------------------------------------------------------
rule hasLockAlready
  match * [ARCLock]
    'static 'Object 'ARCLock '= 'new 'Object() ';
end rule

%------------------------------------------------------------
% Check if the method has already been synchronized by this op
%------------------------------------------------------------
rule IsALAMAlready
  match * [ARCLockSynch]
    'synchronized '( 'ARCLock ')

end rule

%Include rules for writing mutants to files
include "WriteMutants.Txl"
