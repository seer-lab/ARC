"""txl_operator.py contains functions related to:
- Generating mutants
- Backing up and restoring the pristine project
- Creating local projects and copying mutants to them
- Resetting underperforming local projects by:
  - Copying the pristine project over of it
  - Copying a high-performing project over it
- Copying local projects to the global one
- Compiling (global) projects
"""

import sys
import subprocess
import os
import os.path
import tempfile
import time
import shutil

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
  projects are stored by generation and member.

  Attributes:
  generation (int): Current generation of the evolutionary strategy
  memberNum (int): Which member of the population we are mutating
  mutationOperators ([list]): one of {config._FUNCTIONAL_MUTATIONS,
    config._NONFUNCTIONAL_MUTATIONS}
  """

  #logger.debug("Arguments received: {} {} {}".format(generation, memberNum, mutationOperators))

  destDir = config._TMP_DIR + str(generation) + os.sep + str(memberNum) + os.sep

  if generation == 1:
    sourceDir = config._PROJECT_BACKUP_DIR
  else:
    sourceDir = (config._TMP_DIR + str(generation - 1) + os.sep + str(memberNum) \
                + os.sep + 'project' + os.sep)

  recursively_mutate_project(generation, memberNum, sourceDir, destDir,
                             mutationOperators)

def recursively_mutate_project(generation, memberNum, sourceDir, destDir,
                               mutationOperators):
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
    for sourceSubDir in dirs:

      # Check to ensure the root is still within the dest dir
      # Weird error that occurs only on 1+ generations (root sometimes lies
      # outside of the actual sourceDir)
      if destDir in str(sourceDir) and generation is not 1:
        recursively_mutate_project(generation, memberNum, sourceSubDir,
                                   destDir, mutationOperators)
      elif generation is 1:
        recursively_mutate_project(generation, memberNum, sourceSubDir,
                                   destDir, mutationOperators)

    for aFile in files:
      if ("." in aFile and aFile.split(".")[1] == "java"):
        sourceFile = os.path.join(root, aFile)
        generate_all_mutants(generation, memberNum, sourceFile, destDir,
                             mutationOperators)


def generate_all_mutants(generation, memberNum, sourceFile, destDir,
                         mutationOperators):
  """See comment for recursively_mutate_project."""

  # Loop over the selected operators
  for operator in mutationOperators:
    if operator[1]:
      generate_mutants(generation, memberNum, operator, sourceFile, destDir,
                       mutationOperators)


def generate_mutants(generation, memberNum, txlOperator, sourceFile, destDir,
                     mutationOperators):
  """See comment for recursively_mutate_project.  The only new parameter here
  is the txlOperator to apply to a file.

  Attributes:
  generation (int): Current generation of the evolutionary strategy
  memberNum (int): Which member of the population we are mutating
  txlOperator (string): One of _MUTATION_ASAS, etc... from config.py
  sourceFile (string): The specific file from the source project we are mutating
  destDir (string): Where the project is being copied to
  mutationOperators ([list]): one of {config._FUNCTIONAL_MUTATIONS,
    config._NONFUNCTIONAL_MUTATIONS}
  """

  sourceNoExt = os.path.splitext(sourceFile)[0]
  sourceNoFileName = os.path.split(sourceNoExt)[0] + os.sep
  sourceNameOnly = os.path.split(sourceNoExt)[1]
  sourceExtOnly = os.path.splitext(sourceFile)[1]

  sourceRelPath = ''
  if (generation == 1):
    sourceRelPath = sourceNoFileName.replace(config._PROJECT_BACKUP_DIR, '')
  else:
    sourceRelPath = sourceNoFileName.replace(config._TMP_DIR +
                    str(generation - 1) + os.sep + str(memberNum) + os.sep +
                    'project' + os.sep, '')

  if sourceRelPath == '':
    sourceRelPath = os.sep

  txlDestDir = "".join([destDir, sourceRelPath, sourceNameOnly, os.sep,
                       txlOperator[0], os.sep])

  # print '---------------------------'
  # print 'sourceName:       ' + sourceName
  # print 'destDir:          ' + destDir
  # print 'txlOperator:      ' + txlOperator[0]
  # print 'sourceNoExt:      ' + sourceNoExt
  # print 'sourceNoFileName: ' + sourceNoFileName
  # print 'sourceRelPath:    ' + sourceRelPath
  # print 'sourceNameOnly:   ' + sourceNameOnly
  # print 'sourceExtOnly:    ' + sourceExtOnly
  # print 'txlDestDir:       ' + txlDestDir

  # If it doesn't exist, create it
  if not os.path.exists(txlDestDir):
    os.makedirs(txlDestDir)

  # If it exists, delete any files and subdirectories in it
  else:
    shutil.rmtree(txlDestDir)
    os.makedirs(txlDestDir)

  outFile = tempfile.SpooledTemporaryFile()
  errFile = tempfile.SpooledTemporaryFile()

  #logger.debug("Generating mutant at: {}".format(txlDestDir))
  #logger.debug("sourceFile: {}".format(sourceFile))
  #logger.debug("txlOperator[4]: {}".format(txlOperator[4]))
  #logger.debug("sourceNameOnly + sourceExtOnly: {}".format(sourceNameOnly + sourceExtOnly))
  #logger.debug("txlDestDir: {}".format(txlDestDir))

  process = subprocess.Popen(['txl', sourceFile, txlOperator[4], '-',
            '-outfile', sourceNameOnly + sourceExtOnly, '-outdir', txlDestDir],
            stdout=outFile, stderr=errFile, cwd=config._PROJECT_DIR, shell=False)
  process.wait()

  #logger.debug("stdout: {}".format(outFile))
  #logger.debug("stderr: {}".format(errFile))


def generate_representation(generation, memberNum, mutationOperators):
  """Generate the representation for a member.
  Generate the dictionary for use here.
  Returns a list ints where each int corresponds to the number of mutations
  of one type.  eg: {5, 7, 3, ...} = 5 of type ASAS, 7 of type ASAV
  The order of the mutation types is the same as that in the two
  config.**_MUTATIONS.

  Attributes:
  generation (int): Current generation of the evolutionary strategy
  memberNum (int): Which member of the population we are mutating
  mutationOperators ([list]): one of {config._FUNCTIONAL_MUTATIONS,
    config._NONFUNCTIONAL_MUTATIONS}
  """

  logger.debug("Arguments received: {} {}".format(generation, memberNum))

  rep = {}
  for mutationOp in mutationOperators:
    rep[mutationOp[0]] = 0

  # Recusive dir walk
  recurDir = config._TMP_DIR + str(generation) + os.sep + str(memberNum) + os.sep
  for root, dirs, files in os.walk(recurDir):
    for aDir in dirs:
      #if (aDir == str('project'))
        # continue;
      # Count mutant operator if present in dir name
      for mutationOp in mutationOperators:

        if "{}_".format(mutationOp[0]) in str(aDir):  # TODO more unique match
          rep[mutationOp[0]] += 1

          #logger.debug("uniqueMutants at {}, {}, {}, {} = {}".format(generation,
          #           memberNum, mutationOp[0], rep[mutationOp[0]], root + os.sep + aDir))
          uniqueMutants[(generation, memberNum, mutationOp[0],
                      rep[mutationOp[0]])] = root + os.sep + aDir

  return rep


# -----------------------------------------------------------------------------
#
# Project related functions
#
# -----------------------------------------------------------------------------

# TODO: Split the project related functions into a separate file?

def backup_project():
  """Back up the remote, pristine project.
  This has to be done as we copy mutant files to the project directory and
  compile them there.  We don't want to damage the original project!
  """

  logger.debug("Backing up (global) project:")
  logger.debug("\nSrc: {} \nDst: {}".format(config._PROJECT_SRC_DIR,
    config._PROJECT_BACKUP_DIR))

  if os.path.exists(config._PROJECT_BACKUP_DIR):
    shutil.rmtree(config._PROJECT_BACKUP_DIR)
  shutil.copytree(config._PROJECT_SRC_DIR, config._PROJECT_BACKUP_DIR)


def restore_project():
  """At the end of an ARC run, restore the project to it's pristine state."""

  logger.debug("Restoring (global) project:")
  logger.debug("\nSrc: {} \nDst: {}".format(config._PROJECT_BACKUP_DIR,
    config._PROJECT_SRC_DIR))

  if os.path.exists(config._PROJECT_SRC_DIR):
    shutil.rmtree(config._PROJECT_SRC_DIR)
  shutil.copytree(config._PROJECT_BACKUP_DIR, config._PROJECT_SRC_DIR)


def create_local_project(generation, memberNum, restart):
  """After mutating the files above, create the local project for a member of
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

  logger.debug("Input arguments:  Gen: {}, Mem: {} and Restart: {}".format(generation, memberNum, restart))

  staticPart = os.sep + str(memberNum) + os.sep + 'project' + os.sep
  # If the indivudal is on the first or restarted, use the original
  if generation is 1 or restart:
    srcDir = config._PROJECT_BACKUP_DIR
  else:
    # Note: generation - 1 vs generation
    srcDir = config._TMP_DIR + str(generation - 1) + staticPart

  destDir = config._TMP_DIR + str(generation) + staticPart

  # print 'clp srcDir:  ', srcDir, os.path.exists(srcDir)
  # print 'clp destDir: ', destDir,  os.path.exists(destDir)

  logger.debug("Creating local project:")
  logger.debug("\nSrc: {}\nDst: {}".format(srcDir, destDir))

  if os.path.exists(destDir):
    shutil.rmtree(destDir)
  shutil.copytree(srcDir, destDir)


def copy_local_project_a_to_b(generationSrc, memberNumSrc, generationDst,
                              memberNumDst):
  """When an underperforming member is replaced by a higher performing one
  we have to replace their local project with the higher performing project

  Attributes:
  generationSrc (int): Source generation
  memberNumSrc (int): Source member
  generationDst (int): Destination generation
  memberNumDst (int): Destination member
  """

  logger.debug("Gen: {} Mem: {}  ->  Gen: {} Mem: {} ".format(generationSrc,
                                memberNumSrc, generationDst, memberNumDst))

  staticPart = os.sep + 'project' + os.sep

  srcDir = (config._TMP_DIR + str(generationSrc) + os.sep + str(memberNumSrc)
            + staticPart)

  destDir = (config._TMP_DIR + str(generationDst) + os.sep + str(memberNumDst)
            + staticPart)

  logger.debug("Copying a local project from A to B:")
  logger.debug("\nSrc: {}\nDst: {}".format(srcDir, destDir))

  if os.path.exists(destDir):
    shutil.rmtree(destDir)
  shutil.copytree(srcDir, destDir)


def move_mutant_to_local_project(generation, memberNum, txlOperator, mutantNum):
  """After the files have been mutated and the local project formed (by copying
  it in), move a mutated file to the local project

  Attributes:
  generation (int): Current generation of the evolutionary strategy
  memberNum (int): Which member of the population we are dealing with
  txlOperator (string): Selected TXL operator (eg: ASAS)
  mutantNum (int): Mutant number selected from the mutant dir
  """

  logger.debug("Op: {} -> Gen: {} Mem: {} ".format(txlOperator, generation, memberNum))

  # Use the dictionary defined at the top of the file
  sourceDir = uniqueMutants[(generation, memberNum, txlOperator, mutantNum)]

  pathNoFileName = os.path.split(os.path.split(sourceDir)[0])[0]

  basePath = config._TMP_DIR + str(generation) + os.sep + str(memberNum)

  if (pathNoFileName != basePath):
    relPath = pathNoFileName.replace(basePath, '')
    relPath = os.path.split(relPath)[0] #+ os.sep
  #else:
  #  relPath = '/'

  for root, dirs, files in os.walk(sourceDir):
      for aFile in files:
        dst = basePath + os.sep + 'project' + relPath + aFile
        sourceDir += os.sep + aFile
        break

  # print '---------------------------'
  # print 'mmtlp txlOperator:    ' + txlOperator
  # print 'mmtlp pathNoFileName: ' + pathNoFileName
  # print 'mmtlp relPath:        ' + relPath
  # print 'mmtlp src:            ' + sourceDir
  # print 'mmtlp dst:            ' + dst

  if not os.path.exists(dst):
    os.makedirs(dst)

  # logger.debug("Moving mutant to local project:")
  logger.debug("\nSrc: {} \nDst: {}".format(sourceDir, dst))

  shutil.copy(sourceDir, dst)


def move_local_project_to_original(generation, memberNum):
  """When the mutants are generated, project assembled and mutant copied
  in, the final step is to copy the local project back to the original
  directory and compile it.

  Attributes:
  generation (int): Current generation of the evolutionary strategy
  memberNum (int): Which member of the population we are dealing with
  """

  # Check for existence of a backup
  for root, dirs, files in os.walk(config._PROJECT_BACKUP_DIR):
    if files == [] and dirs == []:
      logger.error("No backup for original project found")
      return

  srcDir = (config._TMP_DIR + str(generation) + os.sep + str(memberNum) + os.sep \
            + 'project' + os.sep)

  logger.debug("Moving local project to original:")
  logger.debug("\nSrc: {}\nDst: {}".format(srcDir, config._PROJECT_SRC_DIR))


  if os.path.exists(config._PROJECT_SRC_DIR):
    shutil.rmtree(config._PROJECT_SRC_DIR)
  shutil.copytree(srcDir, config._PROJECT_SRC_DIR)

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

def compile_project():
  """After the local project is copied back to the original, compile it."""

  if not os.path.isfile(config._PROJECT_DIR + 'build.xml'):
    logger.error("No ant build.xml file found in project under test's directory")
  else:
    logger.debug("Compiling new source files")

    outFile = tempfile.SpooledTemporaryFile()
    errFile = tempfile.SpooledTemporaryFile()

    if os.path.exists(config._PROJECT_CLASS_DIR):
      shutil.rmtree(config._PROJECT_CLASS_DIR)
    os.mkdir(config._PROJECT_CLASS_DIR)

    # Make an ant call to compile the program
    #os.chdir(config._PROJECT_DIR)
    antProcess = subprocess.Popen(['ant', config._PROJECT_COMPILE], stdout=outFile,
                        stderr=errFile, cwd=config._PROJECT_DIR, shell=False)
    antProcess.wait()

    # Look for a compilation error
    errFile.seek(0)
    errorText = errFile.read().lower()
    errFile.close()

    if (errorText.find("build failed") >= 0):
      logger.error("ant 'compile' command failed, could not compile (global) project")
      return False
    else:
      return True

# -----------------------------------------------------------------------------
#
# Main
#
# -----------------------------------------------------------------------------

# def main():
#   gener = 1
#   member = 4
#   # Create the representation of a file (The array of numbers of mutants by type)
#   testFile = config._PROJECT_SRC_DIR + 'DeadlockDemo.java'
#   muties = []

#   #backup_project()
#   restore_project()

#   mutate_project(gener, member, config._FUNCTIONAL_MUTATIONS)
#   muties = generate_representation(gener, member, config._FUNCTIONAL_MUTATIONS)
#   create_local_project(gener, member, False)
#   move_mutant_to_local_project(gener, member, 'ASAS', 3)

#   print 'Mutant numbers:'
#   for i, v in enumerate(muties):
#     print v

#   mutate_project(2, member)
#   muties = generate_representation(2, member)
#   create_local_project(2, member, False)
#   move_mutant_to_local_project(2, member, 'ASAS', 1)

#   move_local_project_to_original(gener, member)

#   compile_project()

# if __name__ == "__main__":
#   sys.exit(main())
