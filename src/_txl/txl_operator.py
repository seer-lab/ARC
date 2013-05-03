"""txl_operator.py contains functions related to:
- Generating mutants
- Creating local projects and copying mutants to them
- Resetting underperforming local projects by:
  - Copying the pristine project over of it
  - Copying a high-performing project over it
- Copying local projects to the work area
- Compiling work area projects
- Copying a correct project to the output directory
"""

import sys
import subprocess
import os
import os.path
import tempfile
import time
import shutil
import re
from _evolution import static
from shutil import ignore_patterns

sys.path.append("..")  # To allow importing parent directory module
import config

import logging
logger = logging.getLogger('arc')

# A dictionary to hold the path of unique mutations by individual's and
# generation. The mapping is:
# (generation, memberNum, txlOperator, mutantNum) => directory path
# For example:
# (2 4 EXCR 6) -> /home/myrikhan/workspace/arc/tmp/2/4/source/DeadlockDemo
#                 /EXCR/EXCR_DeadlockDemo.java_3/
uniqueMutants = {}


# -----------------------------------------------------------------------------
#
# Mutant related functions
#
# -----------------------------------------------------------------------------

def mutate_project(generation, memberNum, mutationOperators):
  """Create all of the mutants for a member of the genetic pool.  Mutants and
  projects are stored by generation and member. The source project depends on
  the generation:
  Gen 1: The source project is the original project in the input directory
  Gen >= 2: Source project is from generation -1, for the same memberNum

  Attributes:
  generation (int): Current generation of the evolutionary GA
  memberNum (int): Which member of the population we are mutating
  mutationOperators ([list]): one of {config._FUNCTIONAL_MUTATIONS,
    config._NONFUNCTIONAL_MUTATIONS}
  """

  # Optimization: For generation 1, all members of the population will
  #   have the same mutants as they are all mutating the base project
  #   in the /input directory. So, instead of creating the mutants N
  #   times, create them once (for member #1) and copy them to the
  #   other member directories.
  if generation == 1 and memberNum > 1:
    # tmp/1/1/source/
    srcDir = os.path.join(config._TMP_DIR, str(1), str(1),
             config._PROJECT_SRC_DIR.replace(config._PROJECT_DIR, ''))
    # tmp/1/2/source/
    destDir = os.path.join(config._TMP_DIR, str(1), str(memberNum),
              config._PROJECT_SRC_DIR.replace(config._PROJECT_DIR, ''))

    if os.path.exists(destDir):
      shutil.rmtree(destDir)
    shutil.copytree(srcDir, destDir)

    return

  #logger.debug("Arguments received: {} {} {}".format(generation, memberNum, mutationOperators))

  # source/
  codeDir = config._PROJECT_SRC_DIR.replace(config._PROJECT_DIR, '')

  # tmp/3/4/source
  destDir = os.path.join(config._TMP_DIR, str(generation), str(memberNum), codeDir)

  if generation == 1:
    # input/source/
    sourceDir = config._PROJECT_PRISTINE_SRC_DIR
  else:
    # tmp/2/4/project/source/
    sourceDir = os.path.join(config._TMP_DIR, str(generation - 1), str(memberNum),
                'project', codeDir)

  #logger.debug("---------------------------")
  #logger.debug("  generation: {}".format(generation))
  #logger.debug("  member num: {}".format(memberNum))
  #logger.debug("  operators: {}".format(mutationOperators))
  #logger.debug("  sourceDir:  {}".format(sourceDir))
  #logger.debug("  destDir:    {}".format(destDir))

  recursively_mutate_project(generation, memberNum, sourceDir, destDir,
                             mutationOperators)


def recursively_mutate_project(generation, memberNum, sourceDir, destDir, mutationOperators):
  """For a given member and generation, generate all of the mutants for a
  project.  The source project depends on the generation:
  Gen 1: The source project is the original project from the input directory
  Gen >= 2: Source project is from generation -1, for the same memberNum
  Most of the work is farmed out to the generate_all_mutants function.
  These function exists for future flexibility.

  Attributes:
  generation (int): Current generation of the evolutionary strategy
  memberNum (int): Which member of the population we are mutating
  sourceDir (string): Where the project is coming from, depends on the generation
  destDir (string): Where the project is being copied to
  mutationOperators ([list]): one of {config._FUNCTIONAL_MUTATIONS,
    config._NONFUNCTIONAL_MUTATIONS}
  """

  #logger.debug("sourceDir    {}".format(sourceDir))

  # tmp/2/4/project/source or input/source/
  for root, dirs, files in os.walk(sourceDir):

    for aFile in files:
      if ("." in aFile and aFile.split(".")[1] == "java"):
        # arc/input/source/main/net/sf/cache4j/Cache.java or
        # tmp/1/3/source/main/net/sf/cache4j/Cache.java
        sourceFile = os.path.join(root, aFile)


        #logger.debug("files array:  {}".format(files))
        #logger.debug("file:         {}".format(aFile))
        #logger.debug("sourceFile:   {}".format(sourceFile))

        # We need to get the relative path of the source file and add it to the
        # destination directory. For example,
        # IF source dir = arc/input/source/main/net/sf/cache4j/
        # THEN the rel path = main/net/sf/cache4j/
        if generation == 1:
          # arc/input/source/
          subtr = config._PROJECT_PRISTINE_SRC_DIR
        else:
          # arc/tmp/2/4/project/source/
          subtr = os.path.join(config._TMP_DIR, str(generation - 1), str(memberNum),
                  'project', config._PROJECT_SRC_DIR.replace(config._PROJECT_DIR, ''))

        # main/net/sf/cache4j/
        reldir = root.replace(subtr, '')


        # Use a throw-away local variable to hold the destination directory
        # avoids problems with appending the relative directory more than once
        # or appending a different local directory onto an existing one
        # tmp/3/4/source
        localDestDir = destDir

        # only add the relative part on once :)
        if destDir.find(reldir) is -1:
          # tmp/3/4/source/main/net/sf/cache4j
          localDestDir = os.path.join(destDir, reldir)

        #logger.debug("--------------------------")
        #logger.debug("  sourceFile:   {}".format(sourceFile))
        #logger.debug("  destDir:      {}".format(destDir))
        #logger.debug("  subtr:        {}".format(subtr))
        #logger.debug("  reldir:       {}".format(reldir))
        #logger.debug("  localDestDir: {}".format(localDestDir))

        generate_all_mutants(generation, memberNum, sourceFile, localDestDir,
                             mutationOperators)


def generate_all_mutants(generation, memberNum, sourceFile, destDir, mutationOperators):
  """See comment for recursively_mutate_project."""

  #logger.debug("---------------------------")
  #logger.debug("  generation:      {}".format(generation))
  #logger.debug("  member num:      {}".format(memberNum))
  #logger.debug("  sourceFile:      {}".format(sourceFile))
  #logger.debug("  destDir:         {}".format(destDir))

  for operator in mutationOperators:
    if operator[1]:  # If enabled

      #logger.debug("operator:        {}".format(operator))

      generate_mutants(generation, memberNum, operator, sourceFile, destDir)


def generate_mutants(generation, memberNum, txlOperator, sourceFile, destDir):
  """See comment for recursively_mutate_project.  The only new parameter here
  is the txlOperator to apply to a file.

  Attributes:
  generation (int): Current generation of the evolutionary strategy
  memberNum (int): Which member of the population we are mutating
  txlOperator (string): One of _MUTATION_ASAT, etc... from config.py
  sourceFile (string): The specific file from the source project we are mutating
  destDir (string): Where the project is being copied to
  """

  #sourceFile:       /Users/kelk/workspace/arc/tmp/2/1/project/source/Bank.java
  #sourceNoExt:      /Users/kelk/workspace/arc/tmp/2/1/project/source/Bank
  #sourceNoFileName: /Users/kelk/workspace/arc/tmp/2/1/project/source/
  #sourceRelPath     source/
  #sourceNameOnly:   Bank
  #sourceExtOnly:    .java
  sourceNoExt = os.path.splitext(sourceFile)[0]
  sourceNoFileName = os.path.split(sourceNoExt)[0]
  sourceNameOnly = os.path.split(sourceNoExt)[1]
  sourceExtOnly = os.path.splitext(sourceFile)[1]

  # The relative path is computed from the directory structure of the project itself
  sourceRelPath = ''
  if (generation == 1):
    sourceRelPath = sourceNoFileName.replace(config._PROJECT_SRC_DIR, '')
  else:
    sourceRelPath = sourceNoFileName.replace(os.path.join(config._TMP_DIR,
                    str(generation - 1), str(memberNum)), '')


  txlDestDir = os.path.join(destDir, sourceNameOnly, txlOperator[0]) + os.sep

  # sourceFile:       source/BuggedProgram.java
  # destDir:          /Users/kelk/workspace/arc/tmp/1/1/
  # txlOperator:      ASAS
  # sourceNoExt:      source/BuggedProgram
  # sourceNoFileName: source/
  # sourceRelPath:    source/
  # sourceNameOnly:   BuggedProgram
  # sourceExtOnly:    .java
  # txlDestDir:       /Users/kelk/workspace/arc/tmp/1/1/source/BuggedProgram/ASAS/
  # txlOperator[4]:   /Users/kelk/workspace/arc/src/_txl/ASAS.Txl

  #logger.debug("---------------------------")
  #logger.debug("sourceFile:       {}".format(sourceFile))
  #logger.debug("destDir:          {}".format(destDir))
  #logger.debug("txlOperator:      {}".format(txlOperator[0]))
  #logger.debug("sourceNoExt:      {}".format(sourceNoExt))
  #logger.debug("sourceNoFileName: {}".format(sourceNoFileName))
  #logger.debug("sourceRelPath:    {}".format(sourceRelPath))
  #logger.debug("sourceNameOnly:   {}".format(sourceNameOnly))
  #logger.debug("sourceExtOnly:    {}".format(sourceExtOnly))
  #logger.debug("txlDestDir:       {}".format(txlDestDir))
  #logger.debug("txlOperator[4]:   {}".format(txlOperator[4]))

  # If the output directory doesn't exist, create it, otherwise clean subdirectories
  if os.path.exists(txlDestDir):
    shutil.rmtree(txlDestDir)
  os.makedirs(txlDestDir)

  # In static.py we put together a list of (class, method, variable) tuples in finalCMV
  # of the class.method.variable(s) involved in the bug.
  # Ideally we use that list to reduce the number of mutants generated.  BUT, the static
  # analysis may have failed and/or ConTest may have failed.  We have 3 + 1 cases to
  # consider:
  # The first 3 cases deal with targeting information for ASAT, ASM and ASIM:
  # 1. We have (class, method, variable) targeting information from ConTest and static
  #    analysis
  # 2. We have (class, variable) targeting information from ConTest (or static analysis?)
  # 3. We have no targeting information. (In effect we're doing random search.)
  # The fourth case deals with the other operators:
  # 4. Generate mutants for all other operators

  if txlOperator is config._MUTATION_ASAT or txlOperator is config._MUTATION_ASM \
    or txlOperator is config._MUTATION_ASIM:

    #logger.debug("Case 1: Add sync operators")

    counter = 1

    # 1. We have (class, method, variable) triples
    if static.do_we_have_triples():

      # logger.debug("Case 1-1: Add sync operators with triples")

      if txlOperator is config._MUTATION_ASAT or txlOperator is config._MUTATION_ASM:

        for line in static.finalCMV:
          variableName = line[-1]
          methodName = line[-2]
          className = line[-3]

          for line in static.finalCMV:
            syncVar = line[-1]
            mutantSource = sourceNameOnly + "_" + str(counter)

            # logger.debug("  '{}' '{}' '{}' '{}' '{}'".format(sourceFile,
            #   txlOperator[4], mutantSource + sourceExtOnly, txlDestDir,
            #   config._PROJECT_DIR))
            # logger.debug("Class: '{}' Method: '{}' Var: '{}' Syncvar: '{}'".format(className,
            #   methodName, variableName, syncVar))

            outFile = tempfile.SpooledTemporaryFile()
            errFile = tempfile.SpooledTemporaryFile()

            if txlOperator is config._MUTATION_ASAT:
              process = subprocess.Popen(['txl', sourceFile, txlOperator[4], '-',
                      '-outfile', mutantSource + sourceExtOnly, '-outdir', txlDestDir,
                      '-class', className, '-method', methodName, '-var', variableName,
                      '-syncvar', syncVar], stdout=outFile, stderr=errFile,
                      cwd=config._PROJECT_DIR, shell=False)
              process.wait()

            if txlOperator is config._MUTATION_ASM:
              process = subprocess.Popen(['txl', sourceFile, txlOperator[4], '-',
                      '-outfile', mutantSource + sourceExtOnly, '-outdir', txlDestDir,
                      '-class', className, '-method', methodName,
                      '-syncvar', syncVar], stdout=outFile, stderr=errFile,
                      cwd=config._PROJECT_DIR, shell=False)
              process.wait()

            # outFile.seek(0)
            # errFile.seek(0)
            # output = outFile.read()
            # error = errFile.read()
            # outFile.close()
            # errFile.close()
            # logger.debug("Mutant generation, Output text:\n")
            # logger.debug(output)
            # logger.debug("Mutant generation, Error text:\n")
            # logger.debug(error)

            counter += 1

      else: # txlOperator is config._MUTATION_ASIM:
        for line in static.finalCMV:
          variableName = line[-1]
          methodName = line[-2]
          className = line[-3]
          mutantSource = sourceNameOnly + "_" + str(counter)

          # logger.debug("  '{}' '{}' '{}' '{}' '{}'".format(sourceFile,
          #  txlOperator[4], mutantSource + sourceExtOnly, txlDestDir,
          #  config._PROJECT_DIR))
          # logger.debug("   '{}' '{}' '{}'".format(variableName, methodName, className))

          outFile = tempfile.SpooledTemporaryFile()
          errFile = tempfile.SpooledTemporaryFile()

          process = subprocess.Popen(['txl', sourceFile, txlOperator[4], '-',
                  '-outfile', mutantSource + sourceExtOnly, '-outdir', txlDestDir,
                  '-class', className, '-method', methodName], stdout=outFile,
                  stderr=errFile, cwd=config._PROJECT_DIR, shell=False)
          process.wait()

          # outFile.seek(0)
          # errFile.seek(0)
          # output = outFile.read()
          # error = errFile.read()
          # outFile.close()
          # errFile.close()
          # logger.debug("Mutant generation, Output text:\n")
          # logger.debug(output)
          # logger.debug("Mutant generation, Error text:\n")
          # logger.debug(error)

          counter += 1

    # 2. We have (class, variable) doubles
    elif static.do_we_have_merged_classVar():

      #logger.debug("Case 1-2: Add sync operators with doubles")

      # ASAT and ASM use syncVar (ASIM Doesn't)
      if txlOperator is config._MUTATION_ASAT or txlOperator is config._MUTATION_ASM:
        for line in static.mergedClassVar:
          variableName = line[-1]
          className = line[-2]

          for line in static.mergedClassVar:
            syncVar = line[-1]

            mutantSource = sourceNameOnly + "_" + str(counter)

            #logger.debug("  '{}' '{}' '{}' '{}' '{}'".format(sourceFile,
            #  txlOperator[4], mutantSource + sourceExtOnly, txlDestDir,
            #  config._PROJECT_DIR))
            #logger.debug("  '{}' '{}' 'No method' '{}'".format(syncVar,
            #  variableName, className))

            outFile = tempfile.SpooledTemporaryFile()
            errFile = tempfile.SpooledTemporaryFile()

            # Different operator when 2 args are available
            if txlOperator is config._MUTATION_ASAT:
              txlOpTwo = txlOperator[4].replace(".Txl", "_CV.Txl")
              process = subprocess.Popen(['txl', sourceFile, txlOpTwo, '-',
                      '-outfile', mutantSource + sourceExtOnly, '-outdir', txlDestDir,
                      '-class', className, '-var', variableName,
                      '-syncvar', syncVar], stdout=outFile, stderr=errFile,
                      cwd=config._PROJECT_DIR, shell=False)
              process.wait()
            elif txlOperator is config._MUTATION_ASM:
              txlOpTwo = txlOperator[4].replace(".Txl", "_C.Txl")
              process = subprocess.Popen(['txl', sourceFile, txlOpTwo, '-',
                      '-outfile', mutantSource + sourceExtOnly, '-outdir', txlDestDir,
                      '-class', className, '-syncvar', syncVar], stdout=outFile,
                      stderr=errFile, cwd=config._PROJECT_DIR, shell=False)
              process.wait()

            counter += 1

      else: # ASIM
        for line in static.mergedClassVar:
          variableName = line[-1]
          className = line[-2]

          mutantSource = sourceNameOnly + "_" + str(counter)

          #logger.debug("  '{}' '{}' '{}' '{}' '{}'".format(sourceFile,
          #  txlOperator[4], sourceExtOnly, txlDestDir,
          #  config._PROJECT_DIR))
          #logger.debug("  {}' 'No method' '{}'".format(variableName,
          #  className))

          outFile = tempfile.SpooledTemporaryFile()
          errFile = tempfile.SpooledTemporaryFile()

          txlOpTwo = txlOperator[4].replace(".Txl", "_C.Txl")
          process = subprocess.Popen(['txl', sourceFile, txlOpTwo, '-',
                  '-outfile', mutantSource + sourceExtOnly, '-outdir', txlDestDir,
                  '-class', className], stdout=outFile,
                  stderr=errFile, cwd=config._PROJECT_DIR, shell=False)
          process.wait()

          counter += 1

    # 3. We have no targeting information. Note the use of the '_RND' TXL operators
    else:

      #logger.debug("Case 1-3: Add sync operators with no targeting info (random)")

      # Random operator when no args are available
      # Change: /Users/kelk/workspace/arc/src/_txl/SHSB.Txl
      # To    : /Users/kelk/workspace/arc/src/_txl/SHSB_RND.Txl
      mutantSource = sourceNameOnly + "_" + str(counter)

      #logger.debug("  '{}' '{}' '{}' '{}' '{}'".format(sourceFile,
      #  txlOperator[4], mutantSource + sourceExtOnly, txlDestDir,
      #  config._PROJECT_DIR))

      outFile = tempfile.SpooledTemporaryFile()
      errFile = tempfile.SpooledTemporaryFile()

      # TODO: Can we generalize '-syncvar', '-this'

      # Different operator when 2 args are available
      if txlOperator is config._MUTATION_ASAT:
        txlOpRnd = txlOperator[4].replace("ASAT.Txl", "ASAT_RND.Txl")

        #logger.debug("{} {} {} {} '{}'".format(txlOperator[4], sourceFile, txlOpRnd,
        #  mutantSource+sourceExtOnly, txlDestDir, config._PROJECT_DIR))

        process = subprocess.Popen(['txl', sourceFile, txlOpRnd, '-',
          '-outfile', mutantSource + sourceExtOnly, '-outdir', txlDestDir,
          '-syncvar', 'this'], stdout=outFile, stderr=errFile, cwd=config._PROJECT_DIR,
          shell=False)
        process.wait()
      elif txlOperator is config._MUTATION_ASM:
        txlOpRnd = txlOperator[4].replace(".Txl", "_RND.Txl")
        process = subprocess.Popen(['txl', sourceFile, txlOpRnd, '-',
          '-outfile', mutantSource + sourceExtOnly, '-outdir', txlDestDir,
          '-syncvar', 'this'], stdout=outFile,
          stderr=errFile, cwd=config._PROJECT_DIR, shell=False)
        process.wait()
      else: # ASIM
        txlOpRnd = txlOperator[4].replace(".Txl", "_RND.Txl")
        process = subprocess.Popen(['txl', sourceFile, txlOpRnd, '-',
          '-outfile', mutantSource + sourceExtOnly, '-outdir', txlDestDir],
          stdout=outFile,
          stderr=errFile, cwd=config._PROJECT_DIR, shell=False)
        process.wait()

      counter += 1

  # 4. For the operators that shrink or remove synchronization, we don't target files
  #    used in concurrency.  (The txl invocation doesn't use the -class, etc.. args)
  else:

    #logger.debug("Case 2: Non-add sync operator")

    #logger.debug("  '{}' '{}' '{}' '{}' '{}'".format(sourceFile,
    #  txlOperator[4], sourceExtOnly, txlDestDir,
    #  config._PROJECT_DIR))

    outFile = tempfile.SpooledTemporaryFile()
    errFile = tempfile.SpooledTemporaryFile()

    process = subprocess.Popen(['txl', sourceFile, txlOperator[4], '-',
              '-outfile', sourceNameOnly + sourceExtOnly, '-outdir', txlDestDir],
              stdout=outFile, stderr=errFile, cwd=config._PROJECT_DIR, shell=False)
    process.wait()

  # Cleanup: Delete empty directories
  if sum((len(f) for _, _, f in os.walk(txlDestDir))) == 0:
    shutil.rmtree(txlDestDir)


def generate_representation(generation, memberNum, mutationOperators):
  """Generate the representation for a member.
  Generate the dictionary for use here.
  Returns a list ints where each int corresponds to the number of mutations
  of one type.  eg: {5, 7, 3, ...} = 5 of type ASAT, 7 of type ...
  The order of the mutation types is the same as that in the two
  config.**_MUTATIONS.

  Attributes:
  generation (int): Current generation of the evolutionary strategy
  memberNum (int): Which member of the population we are mutating
  mutationOperators ([list]): one of {config._FUNCTIONAL_MUTATIONS,
    config._NONFUNCTIONAL_MUTATIONS}
  """

  #logger.debug("Arguments received: {} {}".format(generation, memberNum))

  rep = {}
  # Ordering is the same as in config.*_MUTATIONS ?
  for mutationOp in mutationOperators:
    rep[mutationOp[0]] = 0

  #logger.debug("Representation 1: {}".format(rep))

  # Recusive dir walk       tmp/1/1/source/
  recurDir = os.path.join(config._TMP_DIR, str(generation), str(memberNum),
                          config._PROJECT_SRC_DIR.replace(config._PROJECT_DIR, ''))

  return recursive_generate_representation(generation, memberNum, recurDir, rep, mutationOperators)


def recursive_generate_representation(generation, memberNum, recDir, representation, mutationOperators):
  """See the documentation for generate_representation
  """

  for root, dirs, files in os.walk(recDir):

    for aDir in dirs:
      #logger.debug("Dir:  {}".format(aDir))

      foundMutant = False

      # Count mutant operator if present in dir name
      for mutationOp in mutationOperators:

        if "{}_".format(mutationOp[0]) in str(aDir):
          representation[mutationOp[0]] += 1
          foundMutant = True
          # uniqueMutants at {1, 1, ASAT, 1} = /Users/kelk/workspace
          #  /ARC-Test-Suite/test_area/arc/tmp/1/1/Account/ASAT
          #  /ASAT_Account_1.java_1/
          #logger.debug("uniqueMutants at {}, {}, {}, {} = {}".format(generation,
          #           memberNum, mutationOp[0], rep[mutationOp[0]],
          #           os.path.join(root, aDir)))
          uniqueMutants[(generation, memberNum, mutationOp[0],
                      representation[mutationOp[0]])] = os.path.join(root, aDir)

          # Representation: {'RSM': 0, 'ASIM': 4, 'ASAT': 5, ...
          #logger.debug("Representation: {}".format(representation))

      if foundMutant:
        return representation
      else:
        representation = recursive_generate_representation(generation, memberNum,
                         os.path.join(recDir, aDir), representation, mutationOperators)

  #logger.debug("Representation at end: {}".format(representation))

  return representation


# -----------------------------------------------------------------------------
#
# Project related functions
#
# -----------------------------------------------------------------------------

# TODO: Split the project related functions into a separate file?

def create_local_project(generation, memberNum, restart, switchGeneration=0):
  """After mutating the files, create the project for a member of
  a given generation.  The source of the project depends on the generation:
  Gen 1: Original (pristine) project
  Gen >= 2: Source project is from generation - 1, for the same memberNum.
  Note that if it is not possible to mutate a member further, or a member
  has shown no improvement over a number of generations, we have the option
  to reset (restart) the member by overwriting the mutated project with the
  pristine original.  This is the 'restart' parameter - a boolean.

  Attributes:
  generation (int): Current generation of the evolutionary strategy
  memberNum (int): Which member of the population we are dealing with
  restart (boolean): Do we want to reset the member project back to the pristine one?
  """

  #logger.debug("Input arguments:  Gen: {}, Mem: {} and Restart: {}".format(generation, memberNum, restart))

  # 3/project
  staticPart = os.path.join(str(memberNum), 'project')

  # If the indivudal is on the first or restarted, use the original (or switch gen for non-functional)
  if generation is 1 or restart:
    if switchGeneration > 0:
      # tmp/1/3/project
      srcDir = os.path.join(config._TMP_DIR, str(switchGeneration), staticPart)
    else:
      # /input
      srcDir = config._PROJECT_PRISTINE_DIR
  else:
    # Note: generation - 1 vs generation
    # tmp/2/3/project
    srcDir = os.path.join(config._TMP_DIR, str(generation - 1), staticPart)

  # tmp/3/3/project
  destDir = os.path.join(config._TMP_DIR, str(generation), staticPart)

  #logger.debug("---------------------------")
  #logger.debug("staticPart: {} {}".format(staticPart,  os.path.exists(destDir)))
  #logger.debug("srcDir:     {} {}".format(srcDir, os.path.exists(srcDir)))
  #logger.debug("destDir:    {} {}".format(destDir,  os.path.exists(destDir)))

  if os.path.exists(destDir):
    shutil.rmtree(destDir)
  shutil.copytree(srcDir, destDir, ignore=ignore_patterns('java.*'))


def copy_local_project_a_to_b(generationSrc, memberNumSrc, generationDst, memberNumDst):
  """When an underperforming member is replaced by a higher performing one
  we have to replace their local project with the higher performing project

  Attributes:
  generationSrc (int): Source generation
  memberNumSrc (int): Source member
  generationDst (int): Destination generation
  memberNumDst (int): Destination member"""

  #logger.debug("Gen: {} Mem: {}  ->  Gen: {} Mem: {} ".format(generationSrc,
  #                              memberNumSrc, generationDst, memberNumDst))

  srcDir = os.path.join(config._TMP_DIR, str(generationSrc), str(memberNumSrc),
           'project')

  destDir = os.path.join(config._TMP_DIR, str(generationDst), str(memberNumDst),
            'project')

  #logger.debug("Copying a local project from A to B:")
  #logger.debug("\nSrc: {}\nDst: {}".format(srcDir, destDir))

  if os.path.exists(destDir):
    shutil.rmtree(destDir)
  shutil.copytree(srcDir, destDir)


def move_mutant_to_local_project(generation, memberNum, txlOperator, mutantNum):
  """After the files have been mutated and the local project formed (by copying
  it into tmp/gen/member/project/), move a mutated file to the local project

  Attributes:
  generation (int): Current generation of the evolutionary strategy
  memberNum (int): Which member of the population we are dealing with
  txlOperator (string): Selected TXL operator (eg: ASAT)
  mutantNum (int): Mutant number selected from the mutant dir
  """

  #logger.debug("Op: {} -> Gen: {} Mem: {} ".format(txlOperator, generation, memberNum))

  # Use the dictionary defined at the top of the file
  # to find the DIRECTORY containing the mutant

  # tmp/3/4/source/main/net/sf/cache4j/CacheCleaner/ASAT/
  #   ASAT_CacheCleaner_1.java_1/CacheCleaner_1.java/
  sourceDir = uniqueMutants[(generation, memberNum, txlOperator, mutantNum)]

  fileName = ''
  # Find the FILE NAME of the mutant
  for files in os.listdir(sourceDir):
    if files.endswith(".java"):
      # CacheCleaner_1.java
      fileName = files
      break

  #logger.debug("fileName:    {}".format(fileName))

  # tmp/3/4/source/main/net/sf/cache4j/CacheCleaner/ASAT/
  #   ASAT_CacheCleaner_1.java_1/CacheCleaner_1.java/CacheCleaner_1.java
  sourceFile = os.path.join(sourceDir, fileName)

  # Put together the destination DIRECTORY of the mutant
  # tmp/3/4/project/source/
  baseDestPath = os.path.join(config._TMP_DIR, str(generation), str(memberNum),
                'project', config._PROJECT_SRC_DIR.replace(config._PROJECT_DIR, ''))

  # Compute the relative part of the directory
  # Given:
  # tmp/3/4/source/main/net/sf/cache4j/CacheCleaner/ASAT/
  #   ASAT_CacheCleaner_1.java_1/CacheCleaner_1.java
  #
  # The relative part is: main/net/sf/cache4j
  #

  # 1. Remove the tmp/3/4/source/ prefix to get
  #    main/net/sf/cache4j/CacheCleaner/ASAT/ASAT_CacheCleaner_1.java_1/
  #    CacheCleaner_1.java
  relPart = sourceFile.replace(os.path.join(config._TMP_DIR, str(generation),
            str(memberNum), config._PROJECT_SRC_DIR.replace(
            config._PROJECT_DIR, '')), '')

  # 2. Chop off the file name and the last three directories to get
  #    main/net/sf/cache4j
  relPart = os.path.split(relPart)[0]
  relPart = os.path.split(relPart)[0]
  relPart = os.path.split(relPart)[0]
  relPart = os.path.split(relPart)[0]

  # For the destination file name, remove any ASAT_ prefix or
  # _NN suffix
  cleanFileName = fileName
  if txlOperator in ["ASAT", "ASM", "ASIM"]:
    cleanFileName = re.sub("_\d+.java", ".java", cleanFileName)
    cleanFileName = cleanFileName.replace("ASAT_", "")
    cleanFileName = cleanFileName.replace("ASM_", "")
    cleanFileName = cleanFileName.replace("ASIM_", "")

  # Full path of the destination of the mutant
  # tmp/3/4/project/source/main/net/sf/cache4j
  destPath = os.path.join(baseDestPath, relPart)
  # tmp/3/4/project/source/main/net/sf/cache4j/CacheCleaner.java
  destFile = os.path.join(destPath, cleanFileName)

  #logger.debug("---------------------------")
  #logger.debug("  txlOperator:   {}".format(txlOperator))
  #logger.debug("  basePath:      {}".format(baseDstPath))
  #logger.debug("  relPart:       {}".format(relPart))
  #logger.debug("  cleanFileName: {}".format(cleanFileName))

  if not os.path.exists(destPath):
    os.makedirs(destPath)

  logger.debug("Moving mutant to local project:")
  logger.debug("  sourceFile: {}".format(sourceFile))
  logger.debug("  destFile:   {}".format(destFile))

  shutil.copy(sourceFile, destFile)


def move_local_project_to_workarea(generation, memberNum):
  """When the mutants are generated, project assembled and mutant copied
  in, the final step is to copy the local project to the work area
  directory and compile it.

  Attributes:
  generation (int): Current generation of the evolutionary strategy
  memberNum (int): Which member of the population we are dealing with
  """

  srcDir = os.path.join(config._TMP_DIR, str(generation), str(memberNum),
           'project')

  #logger.debug("Moving local project to work area:")
  #logger.debug("\nSrc: {}\nDst: {}".format(srcDir, config._PROJECT_DIR))

  if os.path.exists(config._PROJECT_DIR):
    shutil.rmtree(config._PROJECT_DIR)
  shutil.copytree(srcDir, config._PROJECT_DIR)


def compile_project():
  """After the local project is copied to the work area, compile it."""

  if not os.path.isfile(config._PROJECT_DIR + 'build.xml'):
    logger.error("No ant build.xml file found in workarea directory")
    return False
  #else:
  #  logger.debug("Compiling new source files")

  outFile = tempfile.SpooledTemporaryFile()
  errFile = tempfile.SpooledTemporaryFile()

  if os.path.exists(config._PROJECT_CLASS_DIR):
    shutil.rmtree(config._PROJECT_CLASS_DIR)
  os.mkdir(config._PROJECT_CLASS_DIR)

  # Make an ant call to compile the program
  antProcess = subprocess.Popen(['ant', config._PROJECT_COMPILE], stdout=outFile,
                      stderr=errFile, cwd=config._PROJECT_DIR, shell=False)
  antProcess.wait()

  # Look for a compilation error
  outFile.seek(0)
  outText = outFile.read().lower()
  outFile.close()
  errFile.seek(0)
  errText = errFile.read().lower()
  errFile.close()

  #logger.debug("Compile, Output text:\n")
  #logger.debug(outText)
  #logger.debug("Compile, Error text:\n")
  #logger.debug(errText)

  if (outText.find("build failed") >= 0 or errText.find("build failed") >= 0):
    logger.debug("Ant 'compile' command failed, could not compile project in work area")
    return False
  else:
    return True


def move_best_project_to_output(generation, memberNum):
  """At the end of the process, copy the correct mutant program to the output
  directory

  Attributes:
  generation (int): Generation of the best solution
  memberNum (int): Which member of the population
  """

  srcDir = os.path.join(config._TMP_DIR, str(generation), str(memberNum),
           'project')

  logger.debug("Moving local project to output:")
  logger.debug("\nSrc: {}\nDst: {}".format(srcDir, config._PROJECT_OUTPUT_DIR))

  if os.path.exists(config._PROJECT_OUTPUT_DIR):
    shutil.rmtree(config._PROJECT_OUTPUT_DIR)
  shutil.copytree(srcDir, config._PROJECT_OUTPUT_DIR)