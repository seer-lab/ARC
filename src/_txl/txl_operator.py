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

# For whatever reason, file names aren't tracked throughout ARC.
# So, we have to do it with a dictionary here.  This dic has the
# form: (generation, memberNum): directory
# directory points to the directory of the mutated file. eg:
# /home/myrikhan/workspace/arc/tmp/1/4/whatever/DeadlockDemo/
# The subdirectories of this directory are ASAS, RSAS, ...
mutationHistory = {}

# -----------------------------------------------------------------------------------------------
#
# Mutant related functions 
#
# -----------------------------------------------------------------------------------------------


# Input : /project/directory/, 42, 5
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
      recursively_mutate_project(generation, memberNum, sourceSubDir, destDir)
    for aFile in files:
      sourceFile = os.path.join(root, aFile)
      #print 'fName: ' + fName
      generate_all_mutants(generation, memberNum, sourceFile, destDir)


# Input : 1, 17, /subdir/DoSomething.java
# Output: Mutants by directory
def generate_all_mutants(generation, memberNum, sourceFile, destDir):
  # Loop over the selected operators in the config file
  for operator in config._MUTATIONS:
    if operator[1]:
      generate_mutants(generation, memberNum, operator, sourceFile, destDir)
  time.sleep(0.5)  # Small delay to allow directories/files to form


# Input : 15, 39, /subdir/JustDoIt.java, ASAS
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
    sourceRelPath = sourceNoFileName.replace(config._TMP_DIR + str(generation - 1) + os.sep + str(memberNum) + os.sep + 'project' + os.sep, '')

  sourceRelPath = sourceRelPath.replace(os.sep, '')

  #print '-----------------'
  #print 'sourceRelPath: ' + sourceRelPath

  #sourceRelPath = os.path.split(sourceRelPath)[1]
  if sourceRelPath == '':
    sourceRelPath = '.'

  txlDestDir = "".join([destDir, sourceRelPath, os.sep, sourceNameOnly, os.sep, txlOperator[0], os.sep])

  # Record the file mutated for each (generation, member) combination
  mutationHistory[(generation, memberNum)] = "".join([destDir, sourceRelPath, os.sep, sourceNameOnly, os.sep])

  #print '---------------------------'
  #print 'sourceName:       ' + sourceName
  #print 'destDir:          ' + destDir
  #print 'txlOperator:      ' + txlOperator[0]
  #print 'sourceNoExt:      ' + sourceNoExt
  #print 'sourceNoFileName: ' + sourceNoFileName
  #print 'sourceRelPath:    ' + sourceRelPath
  #print 'sourceNameOnly:   ' + sourceNameOnly
  #print 'sourceExtOnly:    ' + sourceExtOnly
  #print 'txlDestDir:       ' + txlDestDir

  # If it doesn't exist, create it
  if not os.path.exists(txlDestDir):
    os.makedirs(txlDestDir)

  # If it exists, delete any files and subdirectories in it
  else:
    for aFile in os.listdir(txlDestDir):
      txlPath = os.path.join(txlDestDir, aFile)
      try:
        if os.path.isfile(txlPath):
          os.unlink(txlPath)
        if os.path.isdir(txlPath):
          for killFile in os.listdir(txlPath):
            killFullPath = os.path.join(txlPath, killFile)
            try:
              if os.path.isfile(killFullPath):
                os.unlink(killFullPath)
            except Exception, f:
              print f
            os.rmdir(txlPath)
      except Exception, e:
        print e

  outFile = tempfile.SpooledTemporaryFile()
  errFile = tempfile.SpooledTemporaryFile()

  #print 'TXL command line: '
  #print ['txl', '-v', sourceName, txlOperator[6], '-', '-outfile', sourceNameOnly + txlOperator[0] + sourceExtOnly, '-outdir', txlDestDir]

  process = subprocess.Popen(['txl', '-v', sourceName, txlOperator[6], '-', '-outfile', sourceNameOnly + sourceExtOnly, '-outdir', txlDestDir], stdout=outFile, stderr=errFile, cwd=config._PROJECT_DIR, shell=False)


# Input : 1, 17, ASAS
# Output: Number of mutations generated by the operator
def count_mutants(generation, memberNum, txlOpName):
  # Look for a /temp/[generation]/[member]/[filename]/[txlopname]
  # directory.

  path = mutationHistory[(generation, memberNum)]


  mutantDir = "".join([path, txlOpName, os.sep])

  #print 'mutantDir:    ' + mutantDir

  if not os.path.exists(mutantDir):
    return -1

  numDirs = 0

  # Number of subdirectories
  for aFile in os.listdir(mutantDir):
    fullPath = os.path.join(mutantDir, aFile)
    try:
      if os.path.isdir(fullPath):
        numDirs = numDirs + 1
    except Exception, e:
      print e

  return numDirs


# Input : 1, 17
# Output: List of numer of mutations by type, eg:  [5, 3, 7, ...]
def generate_representation(generation, memberNum):
  rep = []
  # Loop over the selected operators in the config file
  for operator in config._MUTATIONS:
    if operator[1]:
      rep.append(count_mutants(generation, memberNum, operator[0]))

  return rep

# -----------------------------------------------------------------------------------------------
#
# Project related functions 
#
# -----------------------------------------------------------------------------------------------


# Input : Directory of project to save (Once ARC begins)
# Output: Remote pristine project is backed up into ARC
def backup_project(startDir):

  for root, dirs, files in os.walk(startDir):
    for aDir in dirs:
      backup_project(aDir)
    for aFile in files:
      fName = os.path.join(root, aFile)
      pathNoFileName = os.path.split(fName)[0]
      #print 'bp fName:           ' + fName
      #print 'bp pathNoFileName   ' + pathNoFileName
      if ((pathNoFileName + '/') != startDir):
        relPath = pathNoFileName.replace(startDir, '')
      else:
        relPath = ''

      dst = config._PROJECT_BACKUP_DIR + relPath + os.sep

      #print 'backup_project dst    :' + dst
      if not os.path.exists(dst):
        os.makedirs(dst)

      shutil.copy(fName, dst)


# Input : Directory of project to restore (Once ARC has completed)
# Output: Pristine project stored in ARC is restored to it's directory
def restore_project(startDir):

  for root, dirs, files in os.walk(startDir + os.sep):
    for aDir in dirs:
      restore_project(aDir)
    for aFile in files:
      fName = os.path.join(root, aFile).replace(os.sep + os.sep, os.sep)
      pathNoFileName = os.path.split(fName)[0]
      if ((pathNoFileName + os.sep) != startDir):
        relPath = pathNoFileName.replace(startDir, '') + os.sep
      else:
        relPath = ''

      dst = config._PROJECT_DIR + relPath

      #print 'resto_p   root:    ' + root
      #print 'resto_p   aFile:   ' + aFile
      #print 'resto_p   fName:   ' + fName
      #print 'resto_p   relPath: ' + relPath
      #print 'resto_p   dst:     ' + dst

      #print 'restore_project dst    :' + dst
      if not os.path.exists(dst):
        os.makedirs(dst)

      shutil.copy(fName, dst)


# Input : Generation and member to create the local project for
# Output: Project, drawn from the pristine source if we are on generation 1,
#         or drawn from the local project of the same member from generation - 1
def create_local_project(generation, memberNum):

  if generation == 1:
    srcDir = config._PROJECT_SRC_DIR
  else:
    # Note: generation - 1 vs generation
    srcDir = config._TMP_DIR + str(generation - 1) + os.sep + str(memberNum) + os.sep + 'project' + os.sep

  destDir = config._TMP_DIR + str(generation) + os.sep + str(memberNum) + os.sep + 'project' + os.sep

  #print 'clp srcDir:  ' + srcDir
  #print 'clp destDir: ' + destDir

  recurse_create_local_project(srcDir, srcDir, destDir)


# Input : Source and destination for copying
# Output: Recursively copy files from source to destination
def recurse_create_local_project(pristineDir, srcDir, destDir):

  for root, dirs, files in os.walk(srcDir):
    for aDir in dirs:
      recurse_create_local_project(pristineDir, aDir, destDir)
    for aFile in files:
      fName = os.path.join(root, aFile).replace(os.sep + os.sep, os.sep)
      pathNoFileName = os.path.split(fName)[0]

      #print '---------------------'
      #print 'rclp pathNoFileName: ' + pathNoFileName
      #print 'rclp pristineDir:    ' + pristineDir

      if ((pathNoFileName + os.sep) != pristineDir):
        relPath = pathNoFileName.replace(pristineDir, '') + os.sep
      else:
        relPath = ''

      dst = (destDir + relPath).replace(os.sep + os.sep, os.sep)

      #print 'rclp relPath  ' + relPath
      #print 'rclp fName:   ' + fName
      #print 'rclp destDir  ' + destDir
      #print 'rclp dst      ' + dst
      
      if not os.path.exists(dst):
        os.makedirs(dst)

      shutil.copy(fName, dst)


# Input : 1, 16, ASAS, 2
# Output: Copy a mutant file in to the local project for this generation and member
def move_mutant_to_local_project(generation, memberNum, txlOperator, mutantNum):

  fileName = mutationHistory[(generation, memberNum)]

  pathNoFileName = os.path.split(os.path.split(fileName)[0])[0]
  if (pathNoFileName != config._TMP_DIR + str(generation) + os.sep + str(memberNum)):
    relPath = pathNoFileName.replace(config._TMP_DIR + str(generation) + os.sep + str(memberNum), '') + os.sep
  else:
    relPath = ''
  fileNameOnly = os.path.split(os.path.split(fileName)[0])[1]
  
  mutDir = txlOperator + '_' + fileNameOnly + '.java_' + str(mutantNum)

  src = "".join([fileName, txlOperator, os.sep, mutDir, os.sep, fileNameOnly + '.java'])

  dst = config._TMP_DIR + str(generation) + os.sep + str(memberNum) + os.sep + 'project' + relPath 

  if not os.path.exists(dst):
    os.makedirs(dst)

  dst2 = dst + fileNameOnly + '.java'

  #print '---------------------------'
  #print 'mmtlp fileName:       ' + fileName
  #print 'mmtlp txlOperator:    ' + txlOperator
  #print 'mmtlp pathNoFileName: ' + pathNoFileName
  #print 'mmtlp relPath:        ' + relPath
  #print 'mmtlp fileNameOnly:   ' + fileNameOnly
  #print 'mmtlp mutDir:         ' + mutDir
  #print 'mmtlp src:            ' + src
  #print 'mmtlp dst:            ' + dst
  #print 'mmtlp dst2:           ' + dst2

  shutil.copy(src, dst2)


# Input : 1, 7, \1\7\project\
#         (Be sure to back up the original project first!)
# Output: Files in original project overwritten
def move_local_project_to_original(generation, memberNum):

  # Check for existence of a backup
  if len([item for item in os.listdir(config._PROJECT_BACKUP_DIR) if os.path.isfile(item)]) == 0:
    print '[ERROR] txl_operator.move_local_project_to_original: config._PROJECT_BACKUP_DIR is empty.  No backup means original files could be lost.  Move not completed.'
    return

  #projectTitle = os.path.split(config._PROJECT_DIR)[1]
  mutantDir = config._TMP_DIR + str(generation) + os.sep + str(memberNum) + os.sep + 'project' + os.sep

  recurse_move_local_project_to_original(generation, memberNum, mutantDir, mutantDir)


def recurse_move_local_project_to_original(generation, memberNum, pristineMutantDir, mutantDir):

  for root, dirs, files in os.walk(mutantDir):
    for aDir in dirs:
      recurse_move_local_project_to_original(generation, memberNum, pristineMutantDir, aDir)
    for aFile in files:
      fName = os.path.join(root, aFile)
      pathNoFileName = os.path.split(fName)[0]
      if pathNoFileName + os.sep != pristineMutantDir:
        relPath = pathNoFileName.replace(pristineMutantDir, '') + os.sep 
      else:
        relPath = ''

      dst = config._PROJECT_SRC_DIR + relPath + aFile
  
      # print 'to_orig   pathNoFileName:   ' + fName
      # print 'to_orig   relPath:          ' + relPath
      # print 'to_orig   dst:              ' + dst

      if not os.path.exists(dst):
        os.makedirs(dst)

      shutil.copy(fName, dst)

# Input : Look for an Ant build.xml in the project directory (ant.apache.org)
# Output: Run build.xml if it is found. 'ant compile' and 'ant build' are tried  
def compile_project():

  os.chdir(config._PROJECT_DIR)
  
  if not os.path.isfile(config._PROJECT_DIR + 'build.xml'):
    print '[ERROR] txl_operator.compile_project: Ant build.xml not found in root directory.  Project wasn\'t compiled.'
  else:
    outFile = tempfile.SpooledTemporaryFile()
    errFile = tempfile.SpooledTemporaryFile()
    
    # Hackish: One of these calls should succeed
    antProcess = subprocess.Popen(['ant', 'compile'], stdout=outFile, stderr=errFile, cwd=config._PROJECT_DIR, shell=False)    
    antProcess = subprocess.Popen(['ant', 'build'], stdout=outFile, stderr=errFile, cwd=config._PROJECT_DIR, shell=False)    


# ------------------------------------------------------------------------------------------------
#
# Main
#
# ------------------------------------------------------------------------------------------------

# Input: None
# Output: None
def main():
  gener = 1
  member = 4

  backup_project(config._PROJECT_DIR)
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

  #  mutatedProject = config._TMP_DIR + str(gener) + os.sep + str(member) + os.sep + 'project' + os.sep
  #move_local_project_to_original(1, 4, mutatedProject)

if __name__ == "__main__":
  sys.exit(main())
