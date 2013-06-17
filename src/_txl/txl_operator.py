"""txl_operator.py contains functions related to: - Generating mutants
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
# Send2Trash from https://pypi.python.org/pypi/Send2Trash
# See arc.py for more details
from send2trash import send2trash

# A dictionary to hold the path of unique mutations by individual's and
# generation. The mapping is:
# (generation, memberNum, txlOperator, mutantNum) => mutant file
# For example:
# (2 4 EXCR 6) -> /home/myrikhan/workspace/arc/tmp/2/4/source/DeadlockDemo
#                 /EXCR/EXCR_DeadlockDemo_1.java_3
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
  #   other member directories for generation 1.
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

  # sourceFile: tmp/1/3/source/main/net/sf/cache4j/Cache.java
  # destDir   : tmp/3/4/source/main/net/sf/cache4j

  # Cache
  sourceNameOnly = os.path.split(os.path.splitext(sourceFile)[0])[1]

  # tmp/3/4/source/main/net/sf/cache4j/Cache/ASAT/
  txlDestDir = os.path.join(destDir, sourceNameOnly, txlOperator[0]) + os.sep

  # If the output directory doesn't exist, create it, otherwise clean subdirectories
  # arc/tmp/1/1/source/BuggedProgram/ASAS/
  if os.path.exists(txlDestDir):
    shutil.rmtree(txlDestDir)
  os.makedirs(txlDestDir)

  counter = 1

  # ----- ASM -----
  if txlOperator is config._MUTATION_ASM:
    if static.do_we_have_triples():
      for lineCMV in static.finalCMV:

        # Only make mutants where the variable is within scope of the class
        # If ('SynchronizedCache', 'someMethod', '_memorySize') and
        #    ('CacheObject', 'someOtherMethod', '_objSize') are in static.finalCMV,
        # when line[-3] is CacheObject, only the second line is in scope
        if sourceNameOnly != lineCMV[-3]:
          continue

        variableName = lineCMV[-1]
        outFile = tempfile.SpooledTemporaryFile()
        errFile = tempfile.SpooledTemporaryFile()
        mutantSource = sourceNameOnly + "_" + str(counter)

        process = subprocess.Popen(['txl', sourceFile, config._TXL_DIR +
                'ASM_RND.Txl', '-', '-outfile', mutantSource, '-outdir',
                txlDestDir, '-syncvar', variableName], stdout=outFile,
                stderr=errFile, cwd=config._PROJECT_DIR, shell=False)
        process.wait()

        # Note to self: Keep this snipped for debugging purposes
        #
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


    #  We have class, variable information
    if static.do_we_have_merged_classVar():
      for lineMCV in static.mergedClassVar:
        # See comment above
        if sourceNameOnly != lineMCV[-2]:
          continue

        variableName = lineMCV[-1]
        mutantSource = sourceNameOnly + "_" + str(counter)
        outFile = tempfile.SpooledTemporaryFile()
        errFile = tempfile.SpooledTemporaryFile()

        process = subprocess.Popen(['txl', sourceFile, config._TXL_DIR +
                'ASM_RND.Txl', '-', '-outfile', mutantSource,
                '-outdir', txlDestDir, '-syncvar', variableName],
                stdout=outFile, stderr=errFile, cwd=config._PROJECT_DIR, shell=False)
        process.wait()

        counter += 1

    # No targeting information, so fall back on the 'this' variable
    else:
      outFile = tempfile.SpooledTemporaryFile()
      errFile = tempfile.SpooledTemporaryFile()
      mutantSource = sourceNameOnly + "_" + str(counter)

      process = subprocess.Popen(['txl', sourceFile, config._TXL_DIR +
              'ASM_RND.Txl', '-', '-outfile', mutantSource, '-outdir',
              txlDestDir, '-syncvar', 'this'],
              stdout=outFile, stderr=errFile, cwd=config._PROJECT_DIR, shell=False)
      process.wait()

      counter += 1

  # ----- ASIM -----
  elif txlOperator is config._MUTATION_ASIM:
    outFile = tempfile.SpooledTemporaryFile()
    errFile = tempfile.SpooledTemporaryFile()
    mutantSource = sourceNameOnly + "_" + str(counter)

    process = subprocess.Popen(['txl', sourceFile, config._TXL_DIR +
            'ASIM_RND.Txl', '-', '-outfile', mutantSource, '-outdir',
            txlDestDir,],
            stdout=outFile, stderr=errFile, cwd=config._PROJECT_DIR, shell=False)
    process.wait()

    counter += 1

  # ----- ASAT ------
  elif txlOperator is config._MUTATION_ASAT:
    # Case 1: We have the (class, method, variable) triples
    if static.do_we_have_triples():
      for lineCMV in static.finalCMV:
        if sourceNameOnly != lineCMV[-3]:
          continue

        variableName = lineCMV[-1]
        methodName = lineCMV[-2]
        className = lineCMV[-3]

        for lineCMV2 in static.finalCMV:

          syncVar = lineCMV2[-1]

          mutantSource = sourceNameOnly + "_" + str(counter)
          outFile = tempfile.SpooledTemporaryFile()
          errFile = tempfile.SpooledTemporaryFile()

          process = subprocess.Popen(['txl', sourceFile, config._TXL_DIR +
                  'ASAT.Txl', '-', '-outfile', mutantSource, '-outdir',
                  txlDestDir, '-class', className, '-method', methodName,
                  '-var', variableName, '-syncvar', syncVar],
                  stdout=outFile, stderr=errFile, cwd=config._PROJECT_DIR,
                  shell=False)
          process.wait()

          counter += 1

    # Case 2:
    # Two subcases to consider:
    # a. We have doubles, but not triples
    # b. We have triples, but no mutants were produced, so try doubles
    if (static.do_we_have_merged_classVar() and not static.do_we_have_triples()) or (not os.listdir(txlDestDir) and static.do_we_have_triples() and static.do_we_have_merged_classVar()):
      for lineMCV in static.mergedClassVar:
        if sourceNameOnly != lineMCV[-2]:
          continue

        variableName = lineMCV[-1]
        className = lineMCV[-2]

        for lineMCV2 in static.mergedClassVar:
          syncVar = lineMCV2[-1]
          mutantSource = sourceNameOnly + "_" + str(counter)
          outFile = tempfile.SpooledTemporaryFile()
          errFile = tempfile.SpooledTemporaryFile()

          # Different operator when 2 args are available
          process = subprocess.Popen(['txl', sourceFile, config._TXL_DIR +
                  'ASAT_CV.Txl', '-', '-outfile', mutantSource, '-outdir',
                  txlDestDir, '-class', className, '-var', variableName,
                  '-syncvar', syncVar], stdout=outFile, stderr=errFile,
                  cwd=config._PROJECT_DIR, shell=False)
          process.wait()

          counter += 1

    # Case 3: No targeting information for ASAT. Fall back on the 'this' variable
    else:
      mutantSource = sourceNameOnly + "_" + str(counter)
      outFile = tempfile.SpooledTemporaryFile()
      errFile = tempfile.SpooledTemporaryFile()

      process = subprocess.Popen(['txl', sourceFile, config._TXL_DIR +
                'ASAT_RND.Txl', '-', '-outfile', mutantSource,
                '-outdir', txlDestDir, '-syncvar', 'this'], stdout=outFile,
                stderr=errFile, cwd=config._PROJECT_DIR, shell=False)
      process.wait()

      counter += 1

  # ----- Other operators -----
  # For the operators that shrink or remove synchronization, we don't target files
  # used in concurrency.  (The txl invocation doesn't use the -class, etc.. args)
  else:
    mutantSource = sourceNameOnly + "_" + str(counter)
    outFile = tempfile.SpooledTemporaryFile()
    errFile = tempfile.SpooledTemporaryFile()

    process = subprocess.Popen(['txl', sourceFile, txlOperator[4], '-',
              '-outfile', mutantSource, '-outdir', txlDestDir],
              stdout=outFile, stderr=errFile, cwd=config._PROJECT_DIR, shell=False)
    process.wait()

    counter += 1


  # Cleanup: Delete empty directories
  # tmp/3/4/source/main/net/sf/cache4j/Cache/ASAT
  if sum((len(f) for _, _, f in os.walk(txlDestDir))) == 0:
    shutil.rmtree(txlDestDir)

  # tmp/3/4/source/main/net/sf/cache4j/Cache
  sourceDestDir = os.path.join(destDir, sourceNameOnly)
  if sum((len(f) for _, _, f in os.walk(sourceDestDir))) == 0:
    shutil.rmtree(sourceDestDir)


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

    #for aDir in dirs:
      #logger.debug("Dir:  {}".format(aDir))
      #representation = recursive_generate_representation(generation, memberNum,
      #                  os.path.join(recDir, aDir), representation, mutationOperators)

    for aFile in files:
      # Find the operator
      for mutationOp in mutationOperators:

        representation[mutationOp[0]] += 1
        # uniqueMutants at {1, 1, ASAT, 1} = /Users/kelk/workspace
        #  /ARC-Test-Suite/test_area/arc/tmp/1/1/Account/ASAT
        #  /ASAT_Account_1.java_1
        #logger.debug("uniqueMutants at {}, {}, {}, {} = {}".format(generation,
        #           memberNum, mutationOp[0], rep[mutationOp[0]],
        #           os.path.join(root, aDir)))
        uniqueMutants[(generation, memberNum, mutationOp[0],
                    representation[mutationOp[0]])] = os.path.join(root, aFile)

        # Representation: {'RSM': 0, 'ASIM': 4, 'ASAT': 5, ...
        #logger.debug("Representation at file step: {}".format(representation))

  #logger.debug("Representation at end: {}".format(representation))

  return representation

def clean_up_mutants(generation, memberNum):
  """Once a project has been successfully compiled, delete all of the mutants
  for that member. This should help cull the prolem of taking up gigabytes of
  space and generating million(s) of files.

  Attributes:
  generation (int): Current generation of the evolutionary strategy
  memberNum (int): Which member of the population we are mutating
  mutationOperators ([list]): one of {config._FUNCTIONAL_MUTATIONS,
    config._NONFUNCTIONAL_MUTATIONS}
  """

  cleanDir = os.path.join(config._TMP_DIR, str(generation), str(memberNum))

  for root, dirs, files in os.walk(cleanDir):
    for aDir in dirs:
      if aDir <> "project":
        send2trash(os.path.join(root, aDir))

# -----------------------------------------------------------------------------
#
# Project related functions
#
# -----------------------------------------------------------------------------

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

  #logger.debug("Input arguments:  Gen: {}, Mem: {} and Restart: {}".format
  #  (generation, memberNum, restart))

  # 3/project
  staticPart = os.path.join(str(memberNum), 'project')

  # If the indivudal is on the first or restarted, use the original (or switch
  # gen for non-functional)
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

  # tmp/3/4/source/main/net/sf/cache4j/CacheCleaner/ASAT/CacheCleaner_1_1.java
  sourceFile = uniqueMutants[(generation, memberNum, txlOperator, mutantNum)]

  # Put together the destination DIRECTORY of the mutant
  # tmp/3/4/project/source/
  baseDestPath = os.path.join(config._TMP_DIR, str(generation), str(memberNum),
                'project', config._PROJECT_SRC_DIR.replace(config._PROJECT_DIR, ''))

  # Compute the relative part of the directory
  # Given:
  # tmp/3/4/source/main/net/sf/cache4j/CacheCleaner/ASAT/CacheCleaner_1_1.java
  #
  # The relative part is: main/net/sf/cache4j
  #
  # 1. Remove the tmp/3/4/source/ prefix to get
  #    main/net/sf/cache4j/CacheCleaner/ASAT/CacheCleaner_1_1.java
  relPart = sourceFile.replace(os.path.join(config._TMP_DIR, str(generation),
            str(memberNum), config._PROJECT_SRC_DIR.replace(
            config._PROJECT_DIR, '')), '')

  # 2. Chop off the file name and the last two directories to get
  #    main/net/sf/cache4j
  relPart = os.path.split(relPart)[0]
  relPart = os.path.split(relPart)[0]
  relPart = os.path.split(relPart)[0]

  # For the destination file name, remove the _NN_NN suffix
  cleanFileName = os.path.split(sourceFile)[1]

  # _1_1.java -> .java
  cleanFileName = re.sub("_\d+_\d+.java", ".java", cleanFileName)

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