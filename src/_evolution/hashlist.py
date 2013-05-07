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

# A dictionary to hold the path of unique mutations by individual's and
# generation. The mapping is:
# hash => generation, member number
# For example:
# EIUERIWWI -> 12, 3

prevSeenMutantProj = {}

def generate_hash(generation, memberNum):
  """ Create a zip of the generation/memberNum/project/ directory
  in the generation/member/ directory and determine its hash
  """

  # tmp/3/4
  workDir = estDir = os.path.join(config._TMP_DIR, str(generation), str(memberNum))
  # tmp/3/4/project.zip
  zipPath = os.path.join(workDir, 'project.zip')
  # tmp/3/4/project/
  targetDir = os.path.join(workDir, 'project')

  if not os.path.exists(targetDir):
    logger.error("Hash generation, project {} doesn't exist".format(targetDir))
    return None
  #else:
    #logger.debug("{} exists".format(targetDir))

  os.chdir(workDir)
  # zipdir is defined further down in this file
  zipdir(targetDir, zipPath)

  if not os.path.exists(zipPath):
    logger.error("Hash generation, zip file {} wasn't created".format(zipPath))
    return None
  #else:
    #logger.debug("{} was created".format(zipPath))


  hashVal = hash(zipPath)
  return hashVal


def find_hash(newHash):
  """ Search for the hash of a project in the prevSeenMutantProj dictionary """

  for listHash in prevSeenMutantProj:
    # TODO: Check this comparison is correct.  listHash is a string, hash is an int
    logger.debug("Comparing '{}' and '{}'".format(newHash, listHash))
    if listHash == str(newHash):
      return prevSeenMutantProject[listHash]
  return (-1, -1)


def add_hash(newHash, generation, memberNum):
  """ Add (generation, memberNum) -> newHash to the dictionary """

  if not find_hash(newHash):
    uniqueMutants[newHash] = (generation, membernum)


# This bit of code came from StackOverflow
def zipdir(dirPath=None, zipFilePath=None, includeDirInZip=True):
  """ Create a new zip file of dirPath at zipFilePath
  """

  if not zipFilePath:
      zipFilePath = dirPath + ".zip"

  if not os.path.isdir(dirPath):
      raise OSError("dirPath argument must point to a directory. "
          "'%s' does not." % dirPath)

  parentDir, dirToZip = os.path.split(dirPath)

  # Little nested function to prepare the proper archive path
  def trimPath(path):
    archivePath = path.replace(parentDir, "", 1)
    if parentDir:
      archivePath = archivePath.replace(os.path.sep, "", 1)
    if not includeDirInZip:
      archivePath = archivePath.replace(dirToZip + os.path.sep, "", 1)
    return os.path.normcase(archivePath)

  outFile = zipfile.ZipFile(zipFilePath, "w", compression = zipfile.ZIP_DEFLATED)
  for (archiveDirPath, dirNames, fileNames) in os.walk(dirPath):
    for fileName in fileNames:
      # Don't include MAC's .DS_Store file.  It'll screw the hash
      if fileName is '.DS_Store':
        continue
      filePath = os.path.join(archiveDirPath, fileName)
      outFile.write(filePath, trimPath(filePath))
    # Make sure we get empty directories as well
    if not fileNames and not dirNames:
      zipInfo = zipfile.ZipInfo(os.path.join(trimPath(archiveDirPath), os.sep))
      outFile.writestr(zipInfo, "")

  outFile.close()

