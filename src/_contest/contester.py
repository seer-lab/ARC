"""Configure ConTest for this run.

The setup() method should be called first to ensure that the testsuite and
ConTest are setup correctly. The run_contest() method will start the testing
approach using tester.py.

Copyright David Kelk and Kevin Jalbert, 2012
          David Kelk, 2013
"""

import sys
import subprocess
import tester
import os
import timeit
import tempfile
import fileinput

sys.path.append("..")  # To allow importing parent directory module
import config

import logging
logger = logging.getLogger('arc')


def setup():
  """Check if the directories and tools are present for the testing process."""

  try:
    _check_directories()
    _check_tools()
  except Exception as message:
    print (message.args)
    sys.exit()

  # Configure KingProperties file
  logger.info("Configuring ConTest's KingProperties file")
  for line in fileinput.FileInput(config._CONTEST_KINGPROPERTY, inplace=1):
    if line.find("targetClasses =") is 0:
      # change "." to "/" - as required by ConTest and remove any spaces introduced by
      # formatting the project prefix in config.py
      line = "targetClasses = {} ".format(config._PROJECT_PREFIX.replace(".", "/").replace(" ", ""))
    elif line.find("sourceDirs =") is 0:
      line = "sourceDirs = {} ".format(config._PROJECT_SRC_DIR)
    elif line.find("keepBackup =") is 0:
      line = "keepBackup = false "
    print(line[0:-1])  # Remove extra newlines (a trailing-space must exists in modified lines)

def _check_directories():
  """Checks that the required directories are present.

  Returns:
    bool: if the directories are present, True
  """

  # TODO: Should this be removed now that we are using the new input-workarea-output
  #       directory structure?
  logger.info("Checking for project source and test directories")
  if(not os.path.isdir(config._PROJECT_SRC_DIR)):
    raise Exception('ERROR MISSING DIRECTORY', 'config._PROJECT_SRC_DIR')

  if(not os.path.isdir(config._PROJECT_TEST_DIR)):
    raise Exception('ERROR MISSING DIRECTORY', 'config._PROJECT_TEST_DIR')

  return True

def _check_tools():
  """Check that the required tools are installed and present.

  Returns:
    bool: if the tools are present, True
  """

  logger.info("Checking for TXL")
  try:
    subprocess.check_call(["which", "txl"])
  except subprocess.CalledProcessError:
    raise Exception('ERROR MISSING TOOL', 'txl')

  logger.info("Checking for ANT")
  try:
    subprocess.check_call(["which", "ant"])
  except subprocess.CalledProcessError:
    raise Exception('ERROR MISSING TOOL', 'ant')

  logger.info("Checking for ConTest")
  if (not os.path.exists(config._CONTEST_JAR)):
    raise Exception('ERROR MISSING ConTest TOOL', 'config._CONTEST_JAR')

  logger.info("Checking for ConTest's KingProperties config file")
  if (not os.path.exists(config._CONTEST_KINGPROPERTY)):
    raise Exception('ERROR MISSING ConTest CONFIGURATION', 'config._CONTEST_KINGPROPERTY')

  logger.info("All Pass")
  return True

def run_test_execution(runs):
  # Check if the testsuite can successfully execute with the set parameters
  logger.debug("Practice test suite run {} times".format(runs))
  cmd = "test_execution({})".format(runs)
  timer = timeit.Timer(cmd, "from _contest.contester import test_execution")

  averageTime = timer.timeit(1) / runs
  logger.debug("Practice test suite runs took on average {}s".format(averageTime))
  return averageTime

def test_execution(runs):
  """Test the testsuite to ensure it can run successfully at least once.

  The testsuite will run through the tester.py test process to ensure that the
  testsuite can actually run successfully.

  Args:
    runs (int): the number of runs the testsuite will be tested for
  """

  testRunner = tester.Tester()
  try:
    testRunner.begin_testing(True, False, runs=runs)

    #logger.info("Testing Runs Results...")
    #logger.info("Successes: {}".format(testRunner.successes))
    #logger.info("Timeouts: {}".format(testRunner.timeouts))
    #logger.info("Dataraces: {}".format(testRunner.dataraces))
    #logger.info("Deadlock: {}".format(testRunner.deadlocks))
    #logger.info("Errors: {}".format(testRunner.errors))

    if (testRunner.errors >= 1):
      raise Exception('ERROR', 'testsuite')
    elif (testRunner.timeouts >= 1):
      raise Exception('ERROR', 'config._CONTEST_TIMEOUT_SEC is too low')
    elif (testRunner.dataraces >= 1):
      logger.info("Data races were encountered")
    elif (testRunner.deadlocks >= 1):
      logger.info("Deadlocks were encountered")
    elif (testRunner.successes >= 1):
      logger.info("Test suite execution successful")
    else:
      logger.warn("The test suite wasn't executed successfully")

  except Exception as message:
    print (message.args)
    sys.exit()


def run_contest():
  """Run the testsuite with ConTest using the approach in tester.py."""
  testRunner = tester.Tester()
  testRunner.begin_testing(True, False)







# If this module is ran as main
if __name__ == '__main__':
  setup()
  run_contest()
