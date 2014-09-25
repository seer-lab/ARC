""" Perform a static analysis of the source to be fixed to gain
information about the classes, methods and variables used
concurrently.

Currently Chord is used. This unit can be adapted to other static,
dynamic or other analysis tools as needed.

Copyright David Kelk, 2012-13
"""

import subprocess
import os
import os.path
import sys
sys.path.append("..")  # To allow importing parent directory module
import zipfile
import config
import re
import tempfile
import shutil
import fileinput
import sys
import urllib2
from bs4 import BeautifulSoup
import ConfigParser
import logging
logger = logging.getLogger('output-log')

# The targeting of classes, methods and variables for mutation can be
# improved by finding which ones are used concurrently. There are different
# tools that can do this - like Chord, a static analysis tool and ConTest,
# which we use for noising. Different tools return different information -
# like the class and variable used concurrently or the class and method
# used concurrently.
# This file contains methods to collect the classes, methods and variables
# found with the ultimate goal of producing a list of (class, method,
# variable) (c, m , v) triples.
# If the (c, m, v) information isn't available, we may still have (c, m)
# or (c, v) information to work with.

_contestFoundVars = False

_classVar = []

_classMeth = []

_classMethVar = []

# Locking on primitive types (int, float, bool, ...) isn't allowed in
# Java. The analysis in this unit return all shared variables, including
# primitives. Removing them from the lists has multiple benefits: Less
# mutants generated (hard drive space, file IO is slow) and it is
# faster (mutant generation, compile time).
_primitiveVars = []

def setup():
  """Check if the directories and tools are present for the testing process."""

  try:
    logger.info("Checking for Chord")
    if (not os.path.exists(config._CHORD_JAR)):
      raise Exception('ERROR MISSING Chord TOOL', 'config._CHORD_JAR')

    logger.info("Checking for Chord's chord.properties")
    if (not os.path.exists(config._CHORD_PROPERTIES)):
      raise Exception('ERROR MISSING Chord CONFIGURATION', 'config._CHORD_PROPERTIES')
  except Exception as message:
    print (message.args)
    sys.exit()

# ------------------------ Chord ------------------------

def configure_chord():
  logger.info("Configuring Chord's chord.properties file")

  # Where we will place the properl configured chord.properties file (in input dir)
  chordLoc = config._PROJECT_DIR + 'chord.properties'

  if os.path.exists(chordLoc):
    os.remove(chordLoc)

  shutil.copy(config._CHORD_PROPERTIES, chordLoc)

  for line in fileinput.FileInput(chordLoc, inplace=1):
    if line.find("chord.class.path =") is 0:
      line = "chord.class.path = {} ".format(config._PROJECT_CLASS_DIR.replace(".", "/"))
    elif line.find("chord.src.path =") is 0:
      line = "chord.src.path = {} ".format(config._PROJECT_SRC_DIR)
    elif line.find("chord.main.class =") is 0:
      line = "chord.main.class = {} ".format(config._CHORD_MAIN)
    elif line.find("chord.args.0 =") is 0:
      line = "chord.args.0 = {} ".format(config._CHORD_COMMAND_LINE_ARGS)
    # For some reason the "e" of true is removed when the file is written to.  Add the space to stop it
    elif line.find("chord.print.results =") is 0:
      line = "chord.print.results = true "
    print(line[0:-1])  # Remove extra newlines


def run_chord_datarace():
  os.chdir(config._PROJECT_DIR)

  logger.info("Running Chord in datarace finding mode (This may take a while.)")

  outFile = tempfile.SpooledTemporaryFile()
  errFile = tempfile.SpooledTemporaryFile()

  # Chord is run by invoking the build.xml in Chord's dir. (lib\Chord\build.xml)
  process = subprocess.Popen(['ant', '-f', os.path.join(config._CHORD_DIR, 'build.xml') ,
    'run'], stdout=outFile, stderr=errFile, cwd=config._PROJECT_DIR, shell=False)

  process.wait()


def did_chord_find_dataraces():
  # core/workarea/chord_output
  chordOutDir = os.path.join(config._PROJECT_DIR, 'chord_output')

  if not os.path.exists(chordOutDir):
    logger.error("Chord output directory, {}, not found".format(chordOutDir))
    return False

  # core/workarea/chord_output/dataraces_by_fld.html
  URL = os.path.join(chordOutDir, 'dataraces_by_fld.html')

  if not os.path.isfile(URL):
    logger.error("Chord output file, {}, not found".format(URL))
    return False

  # Back up the file
  shutil.copy(URL, os.path.join(config._TMP_DIR, 'dataraces_by_fld.html'))

  # A HTML page with 0 data races in it is 1,174 bytes in size. (For Chord 2.1)
  # (Attempts to find deadlocks resulted in 500MB files which were unuseable.)
  if os.path.getsize(URL) < 1200:
    logger.info("Chord didn't detect any data races (Or didn't run correctly.)")
    return False

  logger.info("Chord found data races")
  return True


def get_chord_targets():
  if not did_chord_find_dataraces():
    return False

  chordOutDir = os.path.join(config._PROJECT_DIR, 'chord_output')
  URL = os.path.join(chordOutDir, 'dataraces_by_fld.html')
  URL = 'file:' + URL
  page = urllib2.urlopen(URL)
  data = page.read()

  # Use BeautifulSoup to analyze the web page produced by Chord
  soup = BeautifulSoup(data)

  for (i, row) in enumerate(soup("tr")):
    # First 3 rows of the table in dataraces_by_fld.html are header information
    if i <= 2:
      continue

    tds = row.findAll("td")
    tdTxt = ''.join(tds[0].findAll(text=True))

    # 1. Look for "Dataraces on ... classname.varname"
    # eg:  <tr>
    #        <td class="head3" colspan="5">1. Dataraces on
    #                  <a href="null.html#0">Account.Balance</a></td>
    #     </tr>
    if tdTxt.find("Dataraces on") > 0:
      # Look for class.variable
      stmtOne = re.search("(\S+)\.(\S+)", tdTxt)
      if stmtOne is None:
        continue
      aClass = stmtOne.group(1)
      aVar = stmtOne.group(2)
      if aClass is None or aVar is None:
        continue
      if "$" in aClass:    # From classA$classB, keep classA
        aClass = aClass.split("$")[-2]
      aTuple = (aClass, aVar)
      if aTuple not in _classVar and not is_variable_primitive(aTuple):
        logger.debug("(Case 1) Adding {} to _classVar".format(aTuple))
        _classVar.append(aTuple)
      #else:
      #  logger.debug("{} was rejected because it is either in _classVar".format(aTuple))
      #  logger.debug("already, or the variable part is a primitive type.")

    # 2. Look for class.method(args), except for .main(java.lang.String[])
    # eg: <tr>
    #        <td><a href="race_TE0_TE1.html">1.1</a></td>
    #        <td><a href="null.html#-1">Account.run()</a></td>
    #        <td><a href="null.html#-1">Bank.Service(int,int)</a> (Wr)
    #        </td>
    #        <td><a href="null.html#-1">Bank.main(java.lang.String[])</a></td>
    #        <td><a href="null.html#-1">Bank.main(java.lang.String[])</a> (Rd)
    #        </td>
    #     </tr>
    elif tdTxt.find("race_TE") > 0:

      for j in range(1, 4):  # Always 4 tds
        tdStr = ''.join(tds[j].find(text=True))
        # Ignore anything containing ".main(java.lang.String[])"
        if tdStr.find(".main(java.lang.String[])") > 0:
          continue
        stmtTwo = re.search("(\S*)\.(\S*)\(\S*\)", tdStr)
        if stmtTwo is None:
          continue
        aClass = stmtTwo.group(1)
        aMeth = stmtTwo.group(2)
        if aClass is None or aMeth is None:
          continue
        if "$" in aClass:    # From classA$classB, keep classA
          aClass = aClass.split("$")[-2]
        aTuple = (aClass, aMeth)
        if aTuple not in _classMeth:
          logger.debug("(Case 2) Adding {} to _classMeth".format(aTuple))
          _classMeth.append(aTuple)
        #else:
        #  logger.debug("{} is already in _classMeth".format(aTuple))

  if len(_classVar) > 0:
    logger.debug("Populated class.variable list with Chord data")
  if len(_classMeth) > 0:
    logger.debug("Populated class.method list with Chord data")


# ----------------------- Utility -----------------------

def create_final_triple():
  """
  """
  if len(_classMeth) == 0 or len(_classVar) == 0:
    #logger.debug("Couldn't create the list of (class, method, variable) triples")
    #logger.debug("One or both of the static analysis and ConTest shared variable detection didn't")
    #logger.debug("find anything, or failed. As we are missing one (or both) of class.method and")
    #logger.debug("class.variable, config.finalCMV, the list of class-method-variable triples")
    #logger.debug("will be empty.")
    return False

  for cmTuple in _classMeth:
    for cvTuple in _classVar:
      if not cmTuple[-2] == cvTuple[-2]:  # Must be the same class
        continue
      aTriple = (cmTuple[-2], cmTuple[-1], cvTuple[-1]) # Class, method, variable
      if aTriple not in _classMethVar and not is_variable_primitive(aTriple):
        logger.debug("Adding triple {} to _classMethVar".format(aTriple))
        _classMethVar.append(aTriple)
      #else:
      #  logger.debug("{} was rejected because it is either in _classMethVar".format(aTriple))
      #  logger.debug("already, or the variable part is a primitive type.")

  #logger.info("Populated (class, method, variable) list with Chord and ConTest data")
  return True


def do_we_have_CV():
  return len(_classVar) > 0


def do_we_have_CM():
  return len(_classMeth) > 0


def do_we_have_CMV():
  return len(_classMethVar) > 0

# -------------- ConTest Related Functions ---------------

def did_contest_find_shared_variables():
  # Ensure that there is a shared variable file (From ConTest)
  if not os.path.exists(config._SHARED_VARS_FILE):
    #logger.debug("ConTest's config._SHARED_VARS_FILE doesn't exist")
    return False

  if os.path.getsize(config._SHARED_VARS_FILE) == 0:
    #logger.debug("ConTest didn't detect any shared variables (Or didn't run correctly.)")
    return False

  return True


def load_contest_list():
  """
  """

  global _contestFoundVars

  if _contestFoundVars:
    return True

  if not did_contest_find_shared_variables():
    return False

  for line in open(config._SHARED_VARS_FILE, 'r'):
    variableName = line.split('.')[-1].strip(' \t\n\r')
    className = line.split('.')[-2].strip(' \t\n\r')
    if "$" in className:    # From classA$classB, keep classA
      className = className.split("$")[-2]
    aTuple = (className, variableName)
    if aTuple not in _classVar and not is_variable_primitive(aTuple):
      logger.debug("Added {} to _classVar".format(aTuple))
      _classVar.append(aTuple)
    #else:
    #    logger.debug("{} was rejected because it is either in _classVar".format(aTuple))
    #    logger.debug("already, or the variable part is a primitive type.")

  logger.info("Populated _classVar list with ConTest data")
  _contestFoundVars = True
  create_final_triple()
  return True

# ---------------- JPF Related Functions -----------------

def add_JPF_race_list(JPFlist):
  """Add the new (class, method) tuples discovered by JPF to
  the list of (class, method) tuples involved in the race or
  deadlock.

  Arguments:
    JPFList (List (class, method) tuples): Tuples discovered
      by JPF
  """

  for aTuple in JPFlist:
    if aTuple not in _classMeth:
      if "$" in aTuple[-2]:    # From classA$classB, keep classA
        tempTuple = (aTuple[-2].split("$")[-2], aTuple[-1])
        aTuple = tempTuple
      _classMeth.append(aTuple)
      #logger.debug("{} is new. Adding it to _classMeth.".format(aTuple))
    #else:
    #  logger.debug("{} is already in _classMeth".format(aTuple))

  create_final_triple()


def add_JPF_lock_list(JPFList):
  """Combine the list of classes involved with the deadlocks
  discovered by JPF with the methods already found in the
  _classMeth tuples and adds them to _classMeth.

  Arguments
    JPFList (List string): List of classes involved in deadlocks
  """

  for aItem in JPFList:
    if "$" in aItem:    # From classA$classB, keep classA
      aItem = aItem.split("$")[-2]
    for aTuple in _classMeth:
      newTuple = (aItem, aTuple[-1])
      logger.debug("From class {} and classmeth tuple {}, adding {} to classmeth'") \
        .format(aItem, aTuple, newTuple)
      if newTuple not in _classMeth:
        _classMeth.append(newTuple)
        logger.debug("{} is new. Adding it to _classMeth.".format(aTuple))
      #else:
      #  logger.debug("{} is already in _classMeth".format(aTuple))

  create_final_triple()

# ------------ Static analysis database file ---------------

def find_static_in_db(projectName):
  """Look in src/staticDB.txt to see if the static analysis of this project
  has been done already. If so, re-use it.

  """

  dbFileIn = os.path.join(config._ROOT_DIR , "src", "staticDB.txt")
  if not os.path.exists(dbFileIn):
    open(dbFileIn, 'a').close()
    return False

  configDBIn = ConfigParser.ConfigParser()
  configDBIn.readfp(open(dbFileIn))

  if not configDBIn.has_section(projectName):
    return False

  _classVar      = configDBIn.get(projectName, "_classVar")
  _classMeth     = configDBIn.get(projectName, "_classMeth")
  _classMethVar  = configDBIn.get(projectName, "_classMethVar")
  _primitiveVars = configDBIn.get(projectName, "_primitiveVars")
  #logger.debug("Read _classVar : {}".format(_classVar))
  #logger.debug("Read _classMeth: {}".format(_classMeth))
  #logger.debug("Read _classMethVar: {}".format(_classMethVar))
  #logger.debug("Read _primitiveVars: {}".format(_primitiveVars))
  return True


def write_static_to_db(projectName):
  """Write the values of the static analysis to src/staticDB.txt.
  This is done twice:
  - At the beginning. If the run crashes or is interrupted we dont'
    lose it.
  - At the end. Write any new classes, methods or variables used
    concurrently that were found by the techniques used (noising,
    model checking, ...)

  """

  dbFileOut = os.path.join(config._ROOT_DIR , "src", "staticDB.txt")
  if not os.path.exists(dbFileOut):
    open(dbFileOut, 'a').close()

  #inData = open(dbFileOut, 'r')
  configDBOut = ConfigParser.ConfigParser()
  configDBOut.readfp(open(dbFileOut))

  if not configDBOut.has_section(projectName):
    configDBOut.add_section(projectName)

  configDBOut.set(projectName, "_classVar", _classVar)
  configDBOut.set(projectName, "_classMeth", _classMeth)
  configDBOut.set(projectName, "_classMethVar", _classMethVar)
  configDBOut.set(projectName, "_primitiveVars", _primitiveVars)

  outData = open(dbFileOut, 'w')
  configDBOut.write(outData)


# ------------- Primitive Type Elimination ---------------

def eliminate_primitives():
  """Java program cannot synchronize on primitive types.  An optimization
  is to remove them from the list of variables CORE uses to synchronize
  on.
  """
  # As we are removing this from the list, we must traverse it in reverse
  # order to access all items.
  for aTuple in reversed(_classVar):
    #logger.debug("Checking if {} from _classVar is primitive.".format(aTuple))
    if search_files_for_primitives(aTuple):
      #logger.debug("Removing {} from _classVar".format(aTuple))
      _classVar.remove(aTuple)

  #logger.debug("Before _classMethVar: {}".format(_classMethVar))
  for aTuple in reversed(_classMethVar):
    #logger.debug("Checking if {} from _classMethVar is primitive.".format(aTuple))
    if search_files_for_primitives(aTuple):
      #logger.debug("Removing {} from _classMethVar".format(aTuple))
      _classMethVar.remove(aTuple)


# Important note: The src/_evolution/test_primitive subdirectory contains
#                 a test program for the regular expressions below. See
#                 primitive-tester.py for details.

def search_files_for_primitives(primTuple):
  """
  """
  #logger.debug("The input variable is {}.".format(primTuple))

  for root, dirs, files in os.walk(config._PROJECT_PRISTINE_SRC_DIR):

    for aFile in files:
      if ("." not in aFile and aFile.split(".")[1] != "java"):
        continue
      #logger.debug("Looking in {}".format(aFile))
      lines = None
      with open(os.path.join(root, aFile)) as fileHnd:
        lines = fileHnd.read().splitlines()

      for line in lines:
        if line.find("//") > 0:
          line = line[:line.find("//")]
        aTuple = None
        primVar = primTuple[-1]
        # Someone with a better knowledge of regular expressions should rewrite
        # this. See also primitive_tester/primitive-tester.py
        if   re.search("int (.*) (" + primVar + ")(?!\[)(?!\.)(?![a-zA-Z0-9])", line) is not None \
          or re.search("int (" + primVar + ")(?!\[)(?!\.)(?![a-zA-Z0-9])", line) is not None \
          or re.search("boolean .* (" + primVar + ")(?!\[)(?!\.)(?![a-zA-Z0-9])", line) is not None \
          or re.search("boolean (" + primVar + ")(?!\[)(?!\.)(?![a-zA-Z0-9])", line) is not None \
          or re.search("string .* (" + primVar + ")(?!\[)(?!\.)(?![a-zA-Z0-9])", line) is not None \
          or re.search("string (" + primVar + ")(?!\[)(?!\.)(?![a-zA-Z0-9])", line) is not None \
          or re.search("long .* (" + primVar + ")(?!\[)(?!\.)(?![a-zA-Z0-9])", line) is not None \
          or re.search("long (" + primVar + ")(?!\[)(?!\.)(?![a-zA-Z0-9])", line) is not None \
          or re.search("float .* (" + primVar + ")(?!\[)(?!\.)(?![a-zA-Z0-9])", line) is not None \
          or re.search("float (" + primVar + ")(?!\[)(?!\.)(?![a-zA-Z0-9])", line) is not None \
          or re.search("double .* (" + primVar + ")(?!\[)(?!\.)(?![a-zA-Z0-9])", line) is not None \
          or re.search("double (" + primVar + ")(?!\[)(?!\.)(?![a-zA-Z0-9])", line) is not None \
          or re.search("char .* (" + primVar + ")(?!\[)(?!\.)(?![a-zA-Z0-9])", line) is not None \
          or re.search("char (" + primVar + ")(?!\[)(?!\.)(?![a-zA-Z0-9])", line) is not None \
          or re.search("short .* (" + primVar + ")(?!\[)(?!\.)(?![a-zA-Z0-9])", line) is not None \
          or re.search("short (" + primVar + ")(?!\[)(?!\.)(?![a-zA-Z0-9])", line) is not None:
          #logger.debug("{} was found to be of primitive type on line".format(primVar))
          #logger.debug("{}".format(line))
          #logger.debug("in file {}".format(aFile))
          aTuple = primTuple

        if aTuple is None:
          continue
        #logger.debug("Found tuple, {}.".format(aTuple))
        if aTuple in _primitiveVars:
          continue

        #logger.debug("Adding tuple {} (from {}) to _primitiveVars.".format(aTuple, aFile))
        _primitiveVars.append(aTuple)
        return True

  return False


def is_variable_primitive(thisVar):
  for aTuple in _primitiveVars:
    #logger.debug("Comparing primitive {} to {}".format(aTuple[-1], thisVar[-1]))
    #logger.debug("For tuples {} and {}".format(aTuple, thisVar))
    if aTuple[-1] is thisVar[-1]:
      return True

  return False

# ------------- Get variables from functions ---------------

# Important note: The src/_evolution/test_function subdirectory contains
#                 a test program for the regular expressions below. See
#                 function-tester.py for details.

def get_synch_vars_from_functions():
  for root, dirs, files in os.walk(config._PROJECT_PRISTINE_SRC_DIR):
    for aFile in files:
      if not ("." in aFile and aFile.split(".")[1] == "java"):
        continue
      # core/input/source/main/net/sf/cache4j/Cache.java
      sourceFile = os.path.join(root, aFile)
      #logger.debug("Source file: {}".format(sourceFile))

      with open(sourceFile) as f:
        lines = f.read().splitlines()

      for line in lines:
        # Skip similar looking lines that don't have brackets
        if line.find("(") < 0:
          continue

        # Remove comments (b/c then can contain code)
        if line.find("//") > 0:
          line = line[:line.find("//")]
          #logger.debug("After removing comments: '{}'".format(line))

        # Remove leading and trailing spaces
        line = line.strip()


        # Search for function declarations
        headerSearch = re.search("public|protected|private|synchronized|\s \w+ +\w+ *\(.*\)", line)
        if headerSearch is None:
          continue

        #logger.debug("Found function declaration {}".format(line))

        namePart = line[:line.find("(")]
        namePart = namePart.strip()
        namePart = namePart[namePart.rfind(" "):]
        namePart = namePart.strip()

        #logger.debug("Function name: {}".format(namePart))

        # We don't want to add constructors to the lists
        #if aFile.split(".")[0].compare(namePart) is 0:
        #  logger.debug("This is a constructor. Skipping it.")
        #  continue

        # Extract the part in brackets
        if line.find("("):
          line = line[line.find("("):line.rfind(")")]

        # remove the opening bracket and commas so we have lines that look
        # like
        # int offset float f
        line = re.sub("\(", "", line)
        line = re.sub(",", " ", line) # spaces around commas
        line = re.sub("\[", "", line)
        line = re.sub("\]", "", line)

        #logger.debug("Processing arguments {}".format(line))

        # extract each variable and type
        aVar = re.search("(\S+)\ (\S+)", line)
        while aVar is not None:
          # group(1) is the type, group(2) is the variable name
          # don't add primitive types
          if aVar.group(1).lower() == "int" or aVar.group(1).lower() == "boolean" or \
            aVar.group(1).lower() == "long" or aVar.group(1).lower() == "float" or \
            aVar.group(1).lower() == "double" or aVar.group(1).lower() == "char" or \
            aVar.group(1).lower() == "short" or aVar.group(1).lower() == "string":
            line = re.sub(aVar.group(1) + " " + aVar.group(2), "", line)
            aVar = re.search("(\S+)\ (\S+)", line)
            continue

          # Here we use the class and variables names to add them to the
          # _classVar list
          # By assuming the file name = class name, we're ignoring inner
          # classes
          aTuple = (aFile.split(".")[0], aVar.group(2)) # (class, variable)
          # Finally, add the tuple to the list
          if aTuple not in _classVar and not is_variable_primitive(aTuple):
            #logger.debug("Adding {} to _classVar".format(aTuple))
            if aTuple not in _classVar:
              _classVar.append(aTuple)


          # We also have the function name so we can and the triple to the
          # _classMethVar list
          if namePart is not None:
            aTriple = (aFile.split(".")[0], namePart, aVar.group(2)) # (class, method, variable)
            # Finally, add the triple to the list
            if aTriple not in _classMethVar and not is_variable_primitive(aTuple):
              #logger.debug("Adding {} to _classMethVar".format(aTriple))
              if aTriple not in _classMethVar:
                _classMethVar.append(aTriple)

          # remove the just found variable and move on to the next one
          # for the while statement
          #logger.debug("Before var removal: '{}'".format(line))
          line = re.sub(aVar.group(1) + " " + aVar.group(2), "", line)
          aVar = re.search("(\S+)\ (\S+)", line)
