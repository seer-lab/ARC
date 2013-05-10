%***********************************************************
% RSM (Remove Sync around a Method Body from ConTest) Mutator for ARC
% (Automatic Repair of Concurrency Bugs)
%
% Copyright David Kelk and Kevin Jalbert, 2012
%           David Kelk, 2013
%
% Based on ASK by J.S. Bradbury
%
% Typical invocation:
% txl ManageAccountForRSM.java RSM.Txl - -outfile ManageAccount.java -outdir RSM/
%
% Notes:
% - Java files must be named _1.java, _2.java due to the fact that
%   the second invocation of mutant generation will overwrite the first.
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

% Before and after for the method (Where the mutant comments go)

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

% Before and after for the block (Where the synchronization goes)

redefine block
    '{                                        [NL][IN]
        [repeat declaration_or_statement]     [EX]
    '}
   |
    '{ [NL][IN]
        'synchronized '( [id] ') [NL]
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
		"RSM"
	export MutantOpName

  % Get the class and variable name from ConTest

  %import TXLargs [repeat stringlit]
  %  deconstruct * TXLargs
  %    "-class" clsNm [stringlit] "-var" varNm [stringlit] MoreOptions [repeat stringlit]

  %construct className [id]
  %  _ [unquote clsNm]

  %construct varName [id]
  %  _ [unquote varNm]

  %export className
  %export varName

	replace [program]
    P [program]

  by
    P [MutateSynchronizedInsert]
end function

%------------------------------------------------------------
% Match all methods that do have a synchronized modifier in their
% body and then perform the following 3 steps for each:
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
% Create an ASM method by adding a synchronized block surrounding
% all statements in a method
%------------------------------------------------------------
function doSynchronizedInsertMutation

  %import className [id]
  %import varName [id]

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
      'synchronized '( varName [id] ')
      '{
        DOS [repeat declaration_or_statement]
      '}
    '}

  % create new block
  construct NoSynchBlock [block]
    '{
      DOS
    '}

  construct NewBody [method_body]
    NoSynchBlock

  construct NewRemDecl [rest_of_method_declaration]
    MD OT NewBody

  construct NewMethodDecl [method_declaration]
    MethodModifiers TypeSpec NewRemDecl

  construct NewGenDecl [method_declaration]
    NewMethodDecl

  % create mutant comment to appear in source
  construct MutantString [stringlit]
    "RSM (Remove Sync around a Method Body from ConTest)"

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

%Include rules for writing mutants to files
include "WriteMutants.Txl"
