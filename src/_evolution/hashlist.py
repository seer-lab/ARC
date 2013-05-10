"""Calculate hashes of projects so we can detect duplicate mutants and
avoid the efford of running them through ConTest a second time.

Copyright David Kelk 2012-13
"""

import os
import os.path
import sys
sys.path.append("..")  # To allow importing parent directory module
import zipfile
import config
import logging
import hashlib
import shutil

logger = logging.getLogger('arc')

# A dictionary to hold the path of unique mutations by individual's and
# generation. The mapping is:
# md5sum => generation, member number
# For example:
# EIUERIWWI -> 12, 3

prevSeenMutantProj = {}

def generate_hash(generation, memberNum):
  """ Create a zip of the generation/memberNum/project/ directory
  in the generation/member/ directory and determine its md5 hash
  """

  # tmp/3/4/project.zip
  zipLoc = os.path.join(config._TMP_DIR, str(generation), str(memberNum), 'project.zip')
  # tmp/3/4/project/
  sourceDir = os.path.join(config._TMP_DIR, str(generation), str(memberNum), 'project',
              config._PROJECT_SRC_DIR.replace(config._PROJECT_DIR, ''))


  if not os.path.exists(sourceDir):
    logger.error("Hash generation, project {} doesn't exist".format(commonCodeDir))
    return None

  return GetHashofDirs(sourceDir, 0)


def find_hash(newHash):
  """ Search for the hash of a project in the prevSeenMutantProj dictionary """

  #for listHash in prevSeenMutantProj:
  #  logger.debug("Comparing '{}' and '{}'".format(newHash, listHash))

  if prevSeenMutantProj.has_key(newHash):
    return prevSeenMutantProj[(newHash)]
  else:
    return (-1, -1)



def add_hash(newHash, generation, memberNum):
  """ Add (generation, memberNum) -> newHash to the dictionary """

  if find_hash(newHash) == (-1, -1):
    prevSeenMutantProj[(newHash)] = (generation, memberNum)
    logger.debug("Added {} -> ({}, {}) to hash list".format(newHash,generation, memberNum))


# From http://code.activestate.com/recipes/576973-getting-the-sha-1-or-md5-hash-of-a-directory/

def GetHashofDirs(directory, verbose=0):
  SHAhash = hashlib.sha1()
  if not os.path.exists (directory):
    return -1

  try:
    for root, dirs, files in os.walk(directory):
      for names in files:
        #if verbose == 1:
          #print 'Hashing', names
        filepath = os.path.join(root,names)
        try:
          f1 = open(filepath, 'rb')
        except:
          # You can't open the file for some reason
          f1.close()
          continue

        while True:
          # Read file in as little chunks
          buf = f1.read(4096)
          if not buf : break
          SHAhash.update(hashlib.sha1(buf).hexdigest())
        f1.close()

  except:
    import traceback
    # Print the stack traceback
    traceback.print_exc()
    return -2

  return SHAhash.hexdigest()
