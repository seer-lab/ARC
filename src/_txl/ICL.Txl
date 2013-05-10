%***********************************************************
% Import concurrency library for ARC
% (Automatic Repair of Concurrency Bugs)
%
% Copyright David Kelk and Kevin Jalbert, 2012
%           David Kelk, 2013
%
% Based on ASK by J.S. Bradbury
%
% Typical invocation:
% txl ManageAccount.java ICL.Txl - -outfile ManageAccount.java -outdir ICL/
%
% Notes:
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

define ImportConcur
  'import 'java.util.concurrent.* ';
end define

% How it looks - before and after

redefine package_declaration
    [opt package_header]
    [repeat import_declaration]
    [repeat type_declaration]
  |
    [opt package_header]
    [attr labelM] /* 'MUTANT: [stringlit] */ [NL]
    [ImportConcur] [NL]
    [repeat import_declaration]
    /* 'MUTANT: [stringlit] */ [NL]
    [repeat type_declaration]
end redefine

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
    "ICL"
  export MutantOpName

  replace [program]
    P [program]

  by
    % Add synchronized modifier to all non-synchronized
    % methods one at a time
    P [MutateSynchronizedInsert]
end function

%------------------------------------------------------------
%
%------------------------------------------------------------
rule MutateSynchronizedInsert
  replace [program]
    P   [program]

  % only proceed for methods that satisfy the requirements
  % (i.e. methods that are not synchronized)
  where
    P   [?doInsertSynchroniztionLibrary]

  by
    P
      % Create the mutant version of the program
      [doInsertSynchroniztionLibrary]
      [writeToFile]
end rule

%------------------------------------------------------------
% If the java file doesn't import the concurrency library,
% add the import for it
%------------------------------------------------------------
function doInsertSynchroniztionLibrary
  replace * [program]
    ICLPRO [program]

  deconstruct ICLPRO
    PKGDEC [package_declaration]

  deconstruct PKGDEC
    OPTPHD [opt package_header]
    RPTIDC [repeat import_declaration]
    RPTTYD [repeat type_declaration]

  % create mutant comment to appear in source
  construct MutantString [stringlit]
    "ICL (Import Concurrency Library)"

  % generate hidden attribute and comment
  construct PKGDECNEW [package_declaration]
    OPTPHD
    'MUTATED /* 'MUTANT: MutantString */
    'import 'java.util.concurrent.* ';
    RPTIDC
    /* 'MUTANT: MutantString */
    RPTTYD

  construct PROGRAMNEW [program]
    PKGDECNEW

  % Check if this has been done already
  where not
     RPTIDC [hasImportAlready]
  by
    PROGRAMNEW

end function

%------------------------------------------------------------
% Check if the library has already been added to the class
%------------------------------------------------------------
rule hasImportAlready
  match [repeat import_declaration]
      'import 'java.util.concurrent.* ';
end rule

%Include rules for writing mutants to files
include "WriteMutants.Txl"
