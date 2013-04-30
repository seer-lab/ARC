"""txl_operator.py contains functions related to:
- Generating mutants
- Backing up and restoring the pristine project
- Creating local projects and copying mutants to them
- Resetting underperforming local projects by:
  - Copying the pristine project over of it
  - Copying a high-performing project over it
- Copying local projects to the work area
- Compiling work area projects
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
#                 /EXCR/EXCR_DeadlockDemo.java_3
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
  Gen 1: The source project is the original project
  Gen >= 2: Source project is from generation -1, for the same memberNum

  Attributes:
  generation (int): Current generation of the evolutionary strategy
  memberNum (int): Which member of the population we are mutating
  mutationOperators ([list]): one of {config._FUNCTIONAL_MUTATIONS,
    config._NONFUNCTIONAL_MUTATIONS}
  """

  #logger.debug("Arguments received: {} {} {}".format(generation, memberNum, mutationOperators))

  destDir = config._TMP_DIR + str(generation) + os.sep + str(memberNum) + os.sep

  if generation == 1:
    sourceDir = config._PROJECT_PRISTINE_SRC_DIR
  else:
    sourceDir = (config._TMP_DIR + str(generation - 1) + os.sep + str(memberNum) \
                + os.sep + 'project' + os.sep)

  #logger.debug("---------------------------")
  #logger.debug("generation:      {}".format(generation))
  #logger.debug("member num:      {}".format(memberNum))
  #logger.debug("operators:       {}".format(mutationOperators))
  #logger.debug("sourceDir:       {}".format(sourceDir))
  #logger.debug("destDir:         {}".format(destDir))

  recursively_mutate_project(generation, memberNum, sourceDir, destDir,
                             mutationOperators)


def recursively_mutate_project(generation, memberNum, sourceDir, destDir, mutationOperators):
  """For a given member and generation, generate all of the mutants for a
  project.  The source project depends on the generation:
  Gen 1: The source project is the original project
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

  for root, dirs, files in os.walk(sourceDir):
    # Here we are interested in subdirectories only
    for sourceSubDir in dirs:
      recursively_mutate_project(generation, memberNum, sourceSubDir, destDir, mutationOperators)


    for aFile in files:
      if ("." in aFile and aFile.split(".")[1] == "java"):
        sourceFile = os.path.join(root, aFile)

        generate_all_mutants(generation, memberNum, sourceFile, destDir,
                             mutationOperators)


def generate_all_mutants(generation, memberNum, sourceFile, destDir, mutationOperators):
  """See comment for recursively_mutate_project."""

  #logger.debug("---------------------------")
  #logger.debug("generation:      {}".format(generation))
  #logger.debug("member num:      {}".format(memberNum))
  #logger.debug("sourceFile:      {}".format(sourceFile))
  #logger.debug("destDir:         {}".format(destDir))

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
  sourceNoFileName = os.path.split(sourceNoExt)[0] + os.sep
  sourceNameOnly = os.path.split(sourceNoExt)[1]
  sourceExtOnly = os.path.splitext(sourceFile)[1]

  # The relative path is computed from the directory structure of the project itself
  sourceRelPath = ''
  if (generation == 1):
    sourceRelPath = sourceNoFileName.replace(config._PROJECT_SRC_DIR, '')
  else:
    sourceRelPath = sourceNoFileName.replace(config._TMP_DIR + str(generation - 1) + os.sep
                    + str(memberNum) + os.sep, '')


  txlDestDir = "".join([destDir, sourceNameOnly, os.sep, txlOperator[0], os.sep])

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
        logger.debug("{} {} {} {} '{}'".format(txlOperator[4], sourceFile, txlOpRnd,
          mutantSource+sourceExtOnly, txlDestDir, config._PROJECT_DIR))
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

  # Recusive dir walk       tmp/1/1/
  recurDir = config._TMP_DIR + str(generation) + os.sep + str(memberNum) + os.sep
  for root, dirs, files in os.walk(recurDir):
    for aDir in dirs:

      # Count mutant operator if present in dir name
      for mutationOp in mutationOperators:

        if "{}_".format(mutationOp[0]) in str(aDir):  # TODO more unique match
          rep[mutationOp[0]] += 1

          # uniqueMutants at 1, 1, ASAT, 1 = /Users/kelk/workspace/ARC-Test-Suite
          #  /test_area/arc/tmp/1/1/Account/ASAT/ASAT_Account_1.java_1
          #logger.debug("uniqueMutants at {}, {}, {}, {} = {}".format(generation,
          #           memberNum, mutationOp[0], rep[mutationOp[0]], root + os.sep + aDir))
          uniqueMutants[(generation, memberNum, mutationOp[0],
                      rep[mutationOp[0]])] = root + os.sep + aDir

  # Representation: {'RSM': 0, 'ASIM': 4, 'ASAT': 5,
  #logger.debug("Representation 2: {}".format(rep))
  return rep


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

  staticPart = os.sep + str(memberNum) + os.sep + 'project' + os.sep

  # If the indivudal is on the first or restarted, use the original (or switch gen for non-functional)
  if generation is 1 or restart:
    if switchGeneration > 0:
      srcDir = config._TMP_DIR + str(switchGeneration) + staticPart
    else:
      srcDir = config._PROJECT_PRISTINE_DIR
  else:
    # Note: generation - 1 vs generation
    srcDir = config._TMP_DIR + str(generation - 1) + staticPart

  destDir = config._TMP_DIR + str(generation) + staticPart

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

  staticPart = os.sep + 'project' + os.sep

  srcDir = (config._TMP_DIR + str(generationSrc) + os.sep + str(memberNumSrc)
            + staticPart)

  destDir = (config._TMP_DIR + str(generationDst) + os.sep + str(memberNumDst)
            + staticPart)

  #logger.debug("Copying a local project from A to B:")
  #logger.debug("\nSrc: {}\nDst: {}".format(srcDir, destDir))

  if os.path.exists(destDir):
    shutil.rmtree(destDir)
  shutil.copytree(srcDir, destDir)


def move_mutant_to_local_project(generation, memberNum, txlOperator, mutantNum):
  """After the files have been mutated and the local project formed (by copying
  it in), move a mutated file to the local project

  Attributes:
  generation (int): Current generation of the evolutionary strategy
  memberNum (int): Which member of the population we are dealing with
  txlOperator (string): Selected TXL operator (eg: ASAT)
  mutantNum (int): Mutant number selected from the mutant dir
  """

  logger.debug("Op: {} -> Gen: {} Mem: {} ".format(txlOperator, generation, memberNum))

  # Use the dictionary defined at the top of the file
  # to find the DIRECTORY containing the mutant
  sourceDir = uniqueMutants[(generation, memberNum, txlOperator, mutantNum)]

  fileName = ''
  # Find the FILE NAME of the mutant
  for files in os.listdir(sourceDir):
    if files.endswith(".java"):
      fileName = files
      break

  # Put together the full path of the source of the mutant
  sourceFile = sourceDir + os.sep + fileName

  # Put together the destination DIRECTORY of the mutant
  baseDstPath = config._TMP_DIR + str(generation) + os.sep + str(memberNum)
  relDstPath = config._PROJECT_SRC_DIR.replace(config._PROJECT_DIR, '')
  dstPath = baseDstPath + os.sep + 'project' + os.sep + relDstPath

  # For the destination file name, remove any ASAT_ prefix or
  # _NN suffix
  cleanFileName = fileName
  if txlOperator in ["ASAT", "ASM", "ASIM"]:
    cleanFileName = re.sub("_\d+.java", ".java", cleanFileName)
    cleanFileName = cleanFileName.replace("ASAT_", "")
    cleanFileName = cleanFileName.replace("ASM_", "")
    cleanFileName = cleanFileName.replace("ASIM_", "")

  # Full path of the destination of the mutant
  dstFile = dstPath + cleanFileName

  #logger.debug("---------------------------")
  #logger.debug("txlOperator:    {}".format(txlOperator))
  #logger.debug("sourceDir:     {}".format(sourceDir))
  #logger.debug("fileName:       {}".format(fileName))
  #logger.debug("sourceFile:     {}".format(sourceFile))
  #logger.debug("basePath:       {}".format(baseDstPath))
  #logger.debug("relPath:        {}".format(relDstPath))
  #logger.debug("dstPath:        {}".format(dstPath))
  #logger.debug("cleanFileName:  {}".format(cleanFileName))
  #logger.debug("dstFile         {}".format(dstFile))

  if not os.path.exists(dstPath):
    os.makedirs(dstPath)

  #logger.debug("Moving mutant to local project:")
  #logger.debug("\nSrc: {} \nDst: {}".format(sourceDir, dst))

  shutil.copy(sourceFile, dstFile)


def move_local_project_to_workarea(generation, memberNum):
  """When the mutants are generated, project assembled and mutant copied
  in, the final step is to copy the local project to the work area
  directory and compile it.

  Attributes:
  generation (int): Current generation of the evolutionary strategy
  memberNum (int): Which member of the population we are dealing with
  """

  srcDir = (config._TMP_DIR + str(generation) + os.sep + str(memberNum) + os.sep \
            + 'project' + os.sep)

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

  srcDir = (config._TMP_DIR + str(generation) + os.sep + str(memberNum) + os.sep \
            + 'project' + os.sep)

  logger.debug("Moving local project to output:")
  logger.debug("\nSrc: {}\nDst: {}".format(srcDir, config._PROJECT_OUTPUT_DIR))

  if os.path.exists(config._PROJECT_OUTPUT_DIR):
    shutil.rmtree(config._PROJECT_OUTPUT_DIR)
  shutil.copytree(srcDir, config._PROJECT_OUTPUT_DIR)