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
# (generation, memberNum, txlOperator, mutantNum) => directory path
uniqueMutants = {}


# -----------------------------------------------------------------------------
#
# Mutant related functions
#
# -----------------------------------------------------------------------------


# Input : 42, 5
# Output: Mutants for every java file in the project
def mutate_project(generation, memberNum):

  if generation == 1:
    sourceDir = config._PROJECT_SRC_DIR
    destDir = config._TMP_DIR + str(generation) + os.sep + str(memberNum) + os.sep
  else:
    sourceDir = config._TMP_DIR + str(generation - 1) + os.sep + str(memberNum) + os.sep + 'project' + os.sep
    destDir = config._TMP_DIR + str(generation) + os.sep + str(memberNum) + os.sep

  recursively_mutate_project(generation, memberNum, sourceDir, destDir)


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


# Input : 1, 17, /project/somejava.java, /1/2/project/
# Output: Mutants by directory
def generate_all_mutants(generation, memberNum, sourceFile, destDir):
  # Loop over the selected operators in the config file
  for operator in config._MUTATIONS:
    if operator[1]:
      generate_mutants(generation, memberNum, operator, sourceFile, destDir)


# Input : 15, 39, ASAS, /subdir/JustDoIt.java, /4/7/
# Output: Mutations of one TXL operator, all in one directory
def generate_mutants(generation, memberNum, txlOperator, sourceName, destDir):

  # Start a TXL process to generate mutants in
  # /temp/[generation]/[member]/[OPNAME]

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

  #print '-----------------'
  #print 'sourceRelPath: ' + sourceRelPath

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

  #print 'TXL command line: '
  #print ['txl', '-v', sourceName, txlOperator[6], '-', '-outfile', sourceNameOnly + txlOperator[0] + sourceExtOnly, '-outdir', txlDestDir]

  process = subprocess.Popen(['txl', sourceName, txlOperator[6], '-',
          '-outfile', sourceNameOnly + sourceExtOnly, '-outdir', txlDestDir], stdout=outFile, stderr=errFile,
          cwd=config._PROJECT_DIR, shell=False)
  process.wait()


# Input : 1, 17
# Output: Dictionary of number of mutations by type, eg: OpName => # counted
def generate_representation(generation, memberNum):

  rep = {}
  for mutationOp in config._MUTATIONS:
    rep[mutationOp[0]] = 0
  
  # Recusive dir walk
  for root, dirs, files in os.walk(config._TMP_DIR + str(generation) + os.sep + str(memberNum) + os.sep):
    for aDir in dirs:
      # Count mutant operator if present in dir name
      for mutationOp in config._MUTATIONS:

        if "{}_".format(mutationOp[0]) in str(aDir):  # TODO more unique match
          rep[mutationOp[0]] += 1

          # Store the unique instance's directory
          uniqueMutants[(generation, memberNum, mutationOp[0], 
                          rep[mutationOp[0]])] = root + os.sep + aDir

  return rep


# -----------------------------------------------------------------------------
#
# Project related functions
#
# -----------------------------------------------------------------------------


# Output: Remote pristine project is backed up into ARC
def backup_project():

  if os.path.exists(config._PROJECT_BACKUP_DIR):
    shutil.rmtree(config._PROJECT_BACKUP_DIR)
  shutil.copytree(config._PROJECT_SRC_DIR, config._PROJECT_BACKUP_DIR)


# Output: Pristine project stored in ARC is restored to it's directory
def restore_project():

  if os.path.exists(config._PROJECT_SRC_DIR):
    shutil.rmtree(config._PROJECT_SRC_DIR)
  shutil.copytree(config._PROJECT_BACKUP_DIR, config._PROJECT_SRC_DIR)


# Input : Generation and member to create the local project for
# Output: Project, drawn from the pristine source if we are on generation 1,
#         or drawn from the local project of the same member from generation - 1
def create_local_project(generation, memberNum, restart):

  # If the indivudal is on the first or restarted, use the original
  if generation is 1 or restart:
    srcDir = config._PROJECT_SRC_DIR
  else:
    # Note: generation - 1 vs generation
    srcDir = config._TMP_DIR + str(generation - 1) + os.sep + str(memberNum) + os.sep + 'project' + os.sep

  destDir = config._TMP_DIR + str(generation) + os.sep + str(memberNum) + os.sep + 'project' + os.sep

  # print 'clp srcDir:  ', srcDir, os.path.exists(srcDir)
  # print 'clp destDir: ', destDir,  os.path.exists(destDir)

  if os.path.exists(destDir):
    shutil.rmtree(destDir)
  shutil.copytree(srcDir, destDir)


# Input : 1, 16, ASAS, 2
# Output: Copy a mutant file in to the local project for this generation and member
def move_mutant_to_local_project(generation, memberNum, txlOperator, mutantNum):

  sourceDir = uniqueMutants[(generation, memberNum, txlOperator, mutantNum)]

  pathNoFileName = os.path.split(os.path.split(sourceDir)[0])[0]
  print pathNoFileName
  if (pathNoFileName != config._TMP_DIR + str(generation) + os.sep + str(memberNum)):
    relPath = pathNoFileName.replace(config._TMP_DIR + str(generation) + os.sep + str(memberNum), '')
    relPath = os.path.split(relPath)[0] + os.sep
  else:
    relPath = '/'

  for root, dirs, files in os.walk(sourceDir):
      for aFile in files:
        dst = config._TMP_DIR + str(generation) + os.sep + str(memberNum) + os.sep + 'project' + relPath + aFile
        sourceDir += os.sep + aFile
        break

  if not os.path.exists(dst):
    os.makedirs(dst)

  # print '---------------------------'
  # print 'mmtlp txlOperator:    ' + txlOperator
  # print 'mmtlp pathNoFileName: ' + pathNoFileName
  # print 'mmtlp relPath:        ' + relPath
  # print 'mmtlp src:            ' + sourceDir
  # print 'mmtlp dst:            ' + dst

  shutil.copy(sourceDir, dst)


# Input : 1, 7, \1\7\project\
#         (Be sure to back up the original project first!)
# Output: Files in original project overwritten
def move_local_project_to_original(generation, memberNum):

  # Check for existence of a backup
  for root, dirs, files in os.walk(config._PROJECT_BACKUP_DIR):
    if files == [] and dirs == []:
      print '[ERROR] txl_operator.move_local_project_to_original: config._PROJECT_BACKUP_DIR is empty.  No backup means original files could be lost.  Move not completed.'
      return

  srcDir = config._TMP_DIR + str(generation) + os.sep + str(memberNum) + os.sep + 'project' + os.sep
  # print "src", srcDir, os.path.exists(srcDir)
  # print "dst", config._PROJECT_SRC_DIR, os.path.exists(config._PROJECT_SRC_DIR)

  if os.path.exists(config._PROJECT_SRC_DIR):
    shutil.rmtree(config._PROJECT_SRC_DIR)
  shutil.copytree(srcDir, config._PROJECT_SRC_DIR)


# Input : Look for an Ant build.xml in the project directory (ant.apache.org)
# Output: Run build.xml if it is found. 'ant compile' and 'ant build' are tried
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
    # antProcess = subprocess.Popen(['ant', 'build'], stdout=outFile,
    #                     stderr=errFile cwd=config._PROJECT_DIR, shell=False)
    antProcess.wait()


# -----------------------------------------------------------------------------
#
# Main
#
# -----------------------------------------------------------------------------


# Input : Everything
# Output: Nothing
def main():
  gener = 1
  member = 4

  #backup_project(config._PROJECT_DIR)
  restore_project(config._PROJECT_BACKUP_DIR)

  mutate_project(gener, member)
  create_local_project(1, 4)
  move_mutant_to_local_project(1, 4, 'ASAS', 3)

  # Create the representation of a file (The array of numbers of mutants by type)
  testFile = config._PROJECT_SRC_DIR + 'DeadlockDemo.java'
  muties = []
  muties = generate_representation(gener, member)

  print 'Mutant numbers:'
  for i, v in enumerate(muties):
    print v #muties[i]

  mutate_project(2, member)
  create_local_project(2, 4)
  move_mutant_to_local_project(2, 4, 'ASAS', 3)

  move_local_project_to_original(1, 4)

  compile_project()

if __name__ == "__main__":
  sys.exit(main())
