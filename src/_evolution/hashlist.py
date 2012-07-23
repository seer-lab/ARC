import subprocess
import os
import os.path
import sys
sys.path.append("..")  # To allow importing parent directory module

import zipfile
import config
import re
import tempfile
import logging
logger = logging.getLogger('arc')

# List of previously seen mutated projects that didn't contain a full fix
#prevSeenMutantProj = []

# A dictionary to hold the path of unique mutations by individual's and
# generation. The mapping is:
# hash => generation, member number
# For example:
# EIUERIWWI -> 12, 3

prevSeenMutantProj = {}

def generate_hash(generation, memberNum):

  workDir = estDir = config._TMP_DIR + str(generation) + os.sep + str(memberNum) + os.sep
  zipPath = workDir + 'project.zip'
  targetDir = workDir + 'project' + os.sep

  if not os.path.exists(targetDir):
    #logger.debug("{} doesn't exist".format(targetDir))
    return None
  #else:
    #logger.debug("{} exists".format(targetDir))

  os.chdir(workDir)
  zipdir(targetDir, zipPath)

  if not os.path.exists(zipPath):
    #logger.debug("{} wasn't created".format(zipPath))
    return None
  #else:
    #logger.debug("{} was created".format(zipPath))


  hashVal = hash(zipPath)
  return hashVal


def find_hash(hash):

  for listHash in prevSeenMutantProj:
    # TODO: Check this comparison is correct.  listHash is a string, hash is an int
    logger.debug("Comparing '{}' and '{}'".format(hash, listHash))
    if listHash == str(hash):
      return PrevSeenMutantProject[listHash]
  return (-1, -1)

def add_hash(hash, generation, memberNum):

  if not find_hash(hash):
    uniqueMutants[hash] = (generation, membernum)

# This bit of code comes from StackOverflow
def zipdir(dirPath=None, zipFilePath=None, includeDirInZip=True):

    if not zipFilePath:
        zipFilePath = dirPath + ".zip"
    if not os.path.isdir(dirPath):
        raise OSError("dirPath argument must point to a directory. "
            "'%s' does not." % dirPath)
    parentDir, dirToZip = os.path.split(dirPath)
    #Little nested function to prepare the proper archive path
    def trimPath(path):
        archivePath = path.replace(parentDir, "", 1)
        if parentDir:
            archivePath = archivePath.replace(os.path.sep, "", 1)
        if not includeDirInZip:
            archivePath = archivePath.replace(dirToZip + os.path.sep, "", 1)
        return os.path.normcase(archivePath)

    outFile = zipfile.ZipFile(zipFilePath, "w",
        compression=zipfile.ZIP_DEFLATED)
    for (archiveDirPath, dirNames, fileNames) in os.walk(dirPath):
        for fileName in fileNames:
            filePath = os.path.join(archiveDirPath, fileName)
            outFile.write(filePath, trimPath(filePath))
        #Make sure we get empty directories as well
        if not fileNames and not dirNames:
            zipInfo = zipfile.ZipInfo(trimPath(archiveDirPath) + "/")
            #some web sites suggest doing
            #zipInfo.external_attr = 16
            #or
            #zipInfo.external_attr = 48
            #Here to allow for inserting an empty directory.  Still TBD/TODO.
            outFile.writestr(zipInfo, "")
    outFile.close()

