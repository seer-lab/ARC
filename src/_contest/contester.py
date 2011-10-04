"""This module that the ConTest testing can occur then starts the approach.

The setup() method should be called first to ensure that the testsuite and
ConTest are setup correctly. The run_contest() method will start the testing
approach using tester.py.
"""

import sys
import subprocess
import tester
import os
import timeit
import tempfile

sys.path.append("..")  # To allow importing parent directory module
import config


def test_execution(runs):
  """Test the testsuite to ensure it can run successfully at least once.

  The testsuite will run through the tester.py test process to ensure that the
  testsuite can actually run successfully.

  Args:
    runs (int): the number of runs the testsuite will be tested for
  """

  testRunner = tester.Tester()
  print "[INFO] Check if testsuite runs with ConTest (will retry if needed)"
  try:
    for i in range(1, runs + 1):

      # Testsuite with ConTest noise (to ensure timeout parameter is alright)
      outFile = tempfile.SpooledTemporaryFile()
      errFile = tempfile.SpooledTemporaryFile()
      testSuite = subprocess.Popen(['java',
                        '-Xmx{}m'.format(config._PROJECT_TEST_MB), '-cp',
                        config._PROJECT_CLASSPATH, '-javaagent:' +
                        config._CONTEST_JAR, '-Dcontest.verbose=0',
                        config._PROJECT_TESTSUITE], stdout=outFile,
                        stderr=errFile, cwd=config._PROJECT_DIR, shell=False)

      testRunner.run_test(testSuite, outFile, errFile, i)

    print "[INFO] Testing Runs Results..."
    print "[INFO] Successes ", testRunner.get_successes()
    print "[INFO] Timeouts ", testRunner.get_timeouts()
    print "[INFO] Dataraces ", testRunner.get_dataraces()
    print "[INFO] Deadlock ", testRunner.get_deadlocks()
    print "[INFO] Errors ", testRunner.get_errors()

    if (testRunner.get_errors() >= 1):
      raise Exception('ERROR', 'testsuite')
    elif (testRunner.get_timeouts() >= 1):
      raise Exception('ERROR', 'config._CONTEST_TIMEOUT_SEC is too low')
    elif (testRunner.get_successes() >= 1):
      print "[INFO] Capable of a successful execution of the testsuite"
    else:
      raise Exception('ERROR', 'No successful runs, try again or fix code')

  except Exception as message:
    print (message.args)
    sys.exit()


def setup():
  """Check if the directories and tools are present for testing process."""

  try:
    _check_directories()
    _check_tools()
  except Exception as message:
    print (message.args)
    sys.exit()

  # Check if the testsuite can successfully execute with the set parameters
  print "[INFO] Practice testsuite run {} times".format(config._TESTSUITE_AVG)
  cmd = "test_execution({})".format(config._TESTSUITE_AVG)
  timer = timeit.Timer(cmd, "from _contest.contester import test_execution")

  averageTime = timer.timeit(1) / config._TESTSUITE_AVG
  print "[INFO] Practice testsuite runs took {}s as an AVG".format(averageTime)


def run_contest():
  """Run the testsuite with ConTest using the approach in tester.py."""
  testRunner = tester.Tester()
  testRunner.begin_testing()


def _check_tools():
  """Check that the required tools are installed and present.

  Returns:
    bool: if the tools are present, then True
  """

  print "[INFO] Checking if txl is present"
  try:
    subprocess.check_call(["which", "txl"])
  except subprocess.CalledProcessError:
    raise Exception('ERROR MISSING TOOL', 'txl')

  print "[INFO] Checking if ConTest is present"
  if (not os.path.exists(config._CONTEST_JAR)):
    raise Exception('ERROR MISSING TOOL', 'ConTest')

  print "[INFO] Checking if ConTest's KingProperties is present"
  if (not os.path.exists(config._CONTEST_KINGPROPERTY)):
    raise Exception('ERROR MISSING CONFIGURATION', 'KingProperties')

  print "[INFO] All Pass"
  return True


def _check_directories():
  """Checks that the required directories are present.

  Returns:
    bool: if the directories are present. then True
  """

  if(not os.path.isdir(config._PROJECT_SRC_DIR)):
    raise Exception('ERROR MISSING DIRECTORY', 'source')

  if(not os.path.isdir(config._PROJECT_TEST_DIR)):
    raise Exception('ERROR MISSING DIRECTORY', 'test')

  if(not os.path.isdir(config._PROJECT_CLASS_DIR)):
    raise Exception('ERROR MISSING DIRECTORY', 'class')

  return True

# If this module is ran as main
if __name__ == '__main__':
  setup()
  run_contest()
