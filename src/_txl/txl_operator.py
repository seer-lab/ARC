"""Run TXL to create the mutant programs.  Count the number of instances of
each and return the count in a list.
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

# A dictionary to hold the path of unique mutations per individual's generation
# The mapping is:
# (generation, memberNum, txlOperator, mutantNum) => directory path
# For example:
# (2 4 EXCR 6) -> /home/myrikhan/workspace/arc/tmp/2/4/source/DeadlockDemo/EXCR
#                 /EXCR_DeadlockDemo.java_3
uniqueMutants = {}


# -----------------------------------------------------------------------------
#
# Mutant related functions
#
# -----------------------------------------------------------------------------


# Create all of the mutants for a member of the genetic pool.  Mutants and
# projects are stored by generation and member

def mutate_project(generation, memberNum):
  destDir = config._TMP_DIR + str(generation) + os.sep + str(memberNum) + os.sep

  if generation == 1:
    sourceDir = config._PROJECT_SRC_DIR
  else:
    sourceDir = config._TMP_DIR + str(generation - 1) + os.sep + str(memberNum) + os.sep + 'project' + os.sep
 
  recursively_mutate_project(generation, memberNum, sourceDir, destDir)


# For a given member and generation, generate all of the mutants for a
# project.  The source project depends on the generation:
# Gen 1: The source project is the original project
# Gen >= 2: Source project is from generation -1, for the same memberNum

def recursively_mutate_project(generation, memberNum, sourceDir, destDir):
  for root, dirs, files in os.walk(sourceDir):
    for sourceSubDir in dirs:
      
      # Check to ensure the root is still within the dest dir
      # Weird error that occurs only on 1+ generations (root sometimes lies
      # outside of the actual sourceDir)
      if destDir in str(sourceDir) and generation is not 1:
        recursively_mutate_project(generation, memberNum, sourceSubDir, destDir)
      elif generation is 1:
        recursively_mutate_project(generation, memberNum, sourceSubDir, destDir)

    for aFile in files:
      if ("." in aFile and aFile.split(".")[1] == "java"):
        sourceFile = os.path.join(root, aFile)
        generate_all_mutants(generation, memberNum, sourceFile, destDir)


# See comment for recursively_mutate_project

def generate_all_mutants(generation, memberNum, sourceFile, destDir):
  # Loop over the selected operators in the config file
  for operator in config._MUTATIONS:
    if operator[1]:
      generate_mutants(generation, memberNum, operator, sourceFile, destDir)


# See comment for recursively_mutate_project.  The only new parameter here
# is the txlOperator to apply to a file

def generate_mutants(generation, memberNum, txlOperator, sourceName, destDir):
  sourceNoExt = os.path.splitext(sourceName)[0]
  sourceNoFileName = os.path.split(sourceNoExt)[0] + os.sep
  sourceNameOnly = os.path.split(sourceNoExt)[1]
  sourceExtOnly = os.path.splitext(sourceName)[1]

  sourceRelPath = ''
  if (generation == 1):
    sourceRelPath = sourceNoFileName.replace(config._PROJECT_SRC_DIR, '')
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

  process = subprocess.Popen(['txl', sourceName, txlOperator[6], '-',
            '-outfile', sourceNameOnly + sourceExtOnly, '-outdir', txlDestDir], 
            stdout=outFile, stderr=errFile, cwd=config._PROJECT_DIR, shell=False)
  process.wait()


# Generate the representation for a member.  It is a list of form:
#     mutation operator: boolean
# At the same time, generate the dictionary for use here.

def generate_representation(generation, memberNum):
  rep = {}
  for mutationOp in config._MUTATIONS:
    rep[mutationOp[0]] = 0
  
  # Recusive dir walk
  recurDir = config._TMP_DIR + str(generation) + os.sep + str(memberNum) + os.sep
  for root, dirs, files in os.walk(recurDir):
    for aDir in dirs:

      # Count mutant operator if present in dir name
      for mutationOp in config._MUTATIONS:

        if "{}_".format(mutationOp[0]) in str(aDir):  # TODO more unique match
          rep[mutationOp[0]] += 1

          # Store the unique instance's directory
          #print '(' + str(generation) + ' ' + str(memberNum) + ' ' + mutationOp[0] + ' ' + str(rep[mutationOp[0]])   + ')' + '->' + root + os.sep + aDir
          
          uniqueMutants[(generation, memberNum, mutationOp[0], 
                        rep[mutationOp[0]])] = root + os.sep + aDir

  return rep


# -----------------------------------------------------------------------------
#
# Project related functions
#
# -----------------------------------------------------------------------------


# Back up the remote, pristine projecft
# This has to be done as we copy mutant files to the project directory and
# compile them there.  We don't want to damage the original project!

def backup_project():
  if os.path.exists(config._PROJECT_BACKUP_DIR):
    shutil.rmtree(config._PROJECT_BACKUP_DIR)
  shutil.copytree(config._PROJECT_SRC_DIR, config._PROJECT_BACKUP_DIR)


# At the end of an ARC run, restore the project to it's pristine state

def restore_project():
  if os.path.exists(config._PROJECT_SRC_DIR):
    shutil.rmtree(config._PROJECT_SRC_DIR)
  shutil.copytree(config._PROJECT_BACKUP_DIR, config._PROJECT_SRC_DIR)


# After mutating the files above, create the local project for a member of
# a given generation.  The source of the project depends on the generation:
# Gen 1: Original project
# Gen >= 2: Source project is from generation - 1, for the same memberNum
# Note that if it is not possible to mutate a member further, or a member
# has shown no improvement over a number of generations, we have the option
# reset (restart) the member by overwriting the mutated project with the
# pristine original.

def create_local_project(generation, memberNum, restart):
  staticPart = os.sep + str(memberNum) + os.sep + 'project' + os.sep
  # If the indivudal is on the first or restarted, use the original
  if generation is 1 or restart:
    srcDir = config._PROJECT_SRC_DIR
  else:
    # Note: generation - 1 vs generation
    srcDir = config._TMP_DIR + str(generation - 1) + staticPart 

  destDir = config._TMP_DIR + str(generation) + staticPart

  # print 'clp srcDir:  ', srcDir, os.path.exists(srcDir)
  # print 'clp destDir: ', destDir,  os.path.exists(destDir)

  if os.path.exists(destDir):
    shutil.rmtree(destDir)
  shutil.copytree(srcDir, destDir)


# After the files have been mutated and the local project formed (by copying
# it in), move a mutated file to the local project

def move_mutant_to_local_project(generation, memberNum, txlOperator, mutantNum):
  # Use the dictionary defined at the top of the file
  sourceDir = uniqueMutants[(generation, memberNum, txlOperator, mutantNum)]

  pathNoFileName = os.path.split(os.path.split(sourceDir)[0])[0]

  basePath = config._TMP_DIR + str(generation) + os.sep + str(memberNum)

  if (pathNoFileName != basePath):
    relPath = pathNoFileName.replace(basePath, '')
    relPath = os.path.split(relPath)[0] + os.sep
  else:
    relPath = '/'

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

  shutil.copy(sourceDir, dst)


# When the mutants are generated, project assembled and mutant copied in, the final step
# is to copy the locak project back to the original directory and compile it. (See next.) 

def move_local_project_to_original(generation, memberNum):
  # Check for existence of a backup
  for root, dirs, files in os.walk(config._PROJECT_BACKUP_DIR):
    if files == [] and dirs == []:
      print '[ERROR] txl_operator.move_local_project_to_original: config._PROJECT_BACKUP_DIR is empty.  No backup means original files could be lost.  Move not completed.'
      return

  srcDir = config._TMP_DIR + str(generation) + os.sep + str(memberNum) + os.sep + 'project' + os.sep

  if os.path.exists(config._PROJECT_SRC_DIR):
    shutil.rmtree(config._PROJECT_SRC_DIR)
  shutil.copytree(srcDir, config._PROJECT_SRC_DIR)


# After the local project is copied back to the original, compile it.

def compile_project():
  if not os.path.isfile(config._PROJECT_DIR + 'build.xml'):
    print '[ERROR] txl_operator.compile_project: Ant build.xml not found in root directory.  Project wasn\'t compiled.'
  else:
    print "[INFO] Compiling new source files"

    outFile = tempfile.SpooledTemporaryFile()
    errFile = tempfile.SpooledTemporaryFile()

    # Make an ant call to compile the program
    antProcess = subprocess.Popen(['ant', 'compile'], stdout=outFile,
                        stderr=errFile, cwd=config._PROJECT_DIR, shell=False)
    antProcess.wait()


# -----------------------------------------------------------------------------
#
# Main
#
# -----------------------------------------------------------------------------

def main():
  gener = 1
  member = 4
  # Create the representation of a file (The array of numbers of mutants by type)
  testFile = config._PROJECT_SRC_DIR + 'DeadlockDemo.java'
  muties = []

  #backup_project()
  restore_project()

  mutate_project(gener, member)
  muties = generate_representation(gener, member)
  create_local_project(gener, member, False)
  move_mutant_to_local_project(gener, member, 'ASAS', 3)

  print 'Mutant numbers:'
  for i, v in enumerate(muties):
    print v

  mutate_project(2, member)
  muties = generate_representation(2, member)
  create_local_project(2, member, False)
  move_mutant_to_local_project(2, member, 'ASAS', 1)

  
  move_local_project_to_original(gener, member)

  compile_project()

if __name__ == "__main__":
  sys.exit(main())
