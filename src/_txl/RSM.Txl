%***********************************************************
% RSM (Remove Sync around a Method) Mutator for ARC
% (Automatic Repair of Concurrency Bugs)
%
% Kevin Jalbert and David Kelk, Sept. 2011
% SBSE Reading Course Project
%
% Based on RSK by J.S. Bradbury
%***********************************************************

%***********************************************************
% RSK (Remove Synchronized Keyword from Method) Mutator
% Jeremy S. Bradbury

% Copyright 2006 J.S. Bradbury

% Description: This mutation operator removes the
% the synchronizied keyword from methods.
% We do not remove the synchronized keyword from constructors
% because a constructor method can not be synchronized.
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
		"RSM"
	export MutantOpName

	replace [program]
        		P [program]

    	by
		% Remove all instances of synchronized modifiers in
		%methods one at a time
        		P [MutateSynchronizedDel]
end function

%------------------------------------------------------------
% Match all methods that have both a synchronized keyword
% and then perform the following 3 steps for each:
%	1. Create mutant of program with synchronized modifier
%      removed
%	2. Write mutant to a file
%	3. Reinsert synchronized modifier that was removed
%------------------------------------------------------------
rule MutateSynchronizedDel
	replace [program]
		P 	[program]

	% only proceed for methods that satisfy the requirements
	% (i.e. methods that have a synchronized modifier)
	where
		P 	[?doSynchronizedDelMutation]

	by
		P
			% Create the mutant version of the program
			[doSynchronizedDelMutation]
			%[print]
			[writeToFile]
			% Undo mutation and return to original program
			[undoSynchronizedDelMutation]
end rule

%------------------------------------------------------------
% Create an RSK mutant by removing synchronized from the
% method modifier list
%------------------------------------------------------------
function doSynchronizedDelMutation
	replace * [method_or_constructor_declaration]
		GenDecl [method_or_constructor_declaration]
	deconstruct GenDecl
		MethodDecl [method_declaration]
	deconstruct MethodDecl
		MethodModifiers [repeat modifier]
		RemainingDelcaration [rest_of_method_declaration]

	% check that synchronized modifier is present
	where
		MethodModifiers [hasSynchronizedKeyword]

	% create empty list of modifiers
	construct NewMethodModifiers [repeat modifier]

	% export the old declaration and reinsert it
	% once the mutant has been created and saved
	export GenDecl

	% create mutant comment to appear in source
	construct MutantString [stringlit]
		"RSM (Removed Synch around a Method)"

	by
		% generate hidden attribute and comment
		'MUTATED /* 'MUTANT: MutantString */
		% populate new modifier list with all modifiers
		% except synchronized
		NewMethodModifiers [generateModifiers each MethodModifiers]
		% reinsert rest of method declaration
		RemainingDelcaration
end function

%------------------------------------------------------------
% Reinsert the orginal method declaration but leave the
% MUTATED attribute to indicate that the mutant has already
% been created.
%------------------------------------------------------------
function undoSynchronizedDelMutation
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
		% replace mutated declaration with original but
		% leave hidden attribute
		'MUTATED SavedMethodDecl
end function

%------------------------------------------------------------
% Check if method modifier list includes synchronized
%------------------------------------------------------------
rule hasSynchronizedKeyword
	match * [modifier]
		'synchronized
end rule

%------------------------------------------------------------
% Generate list of modifiers for a method from existing list
% but exclude the synchronized modifier.
%------------------------------------------------------------
function generateModifiers CurrModifier [modifier]
	% check that current modifier is not static
	where not
		CurrModifier [hasSynchronizedKeyword]

	% otherwise insert modifier into list
	replace [repeat modifier]
		Modifiers [repeat modifier]
	by
		Modifiers [. CurrModifier]
end function

%Include rules for writing mutants to files
include "WriteMutants.Txl"
