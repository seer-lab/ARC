%***********************************************************
% ASM (Add Sync around a Method) Mutator for ARC
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
redefine method_or_constructor_declaration
	[attr labelM] [method_declaration]
	| [attr labelM] /* 'MUTANT: [stringlit] */ [method_declaration]
	| [attr labelM] [constructor_declaration]
end redefine

define labelM
	'MUTATED
end define

redefine method_declaration
    	[NL] [repeat modifier] [rest_of_method_declaration]
end redefine

define rest_of_method_declaration
	[type_specifier] [method_declarator] [opt throws] [method_body]
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
		"ASM"
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
		"ASM (Add Sync around a Method)"
	by
		% generate hidden attribute and comment
		'MUTATED /* 'MUTANT: MutantString */
		% populate new modifier list with all existing modifiers
		% plus synchronized
		NewMethodModifiers
		% reinsert rest of method declaration
		RemainingDelcaration
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
		'MUTATED /* 'MUTANT: MutantString [stringlit] */
		CurrMethodDecl [method_declaration]

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
