"""This module is responsible for running and recording test results

The Tester class will run a testsuite using ConTest to introduce random thread
sleep() and yeild() into the executing testsuite.
"""

import sys
import time
import subprocess
import tempfile
import re

sys.path.append("..")  # To allow importing parent directory module
import config


class Tester():
  """Class that drives the process of running the testsuite a number of times.

  ConTest is used in conjunction with the test executions in an attempt to
  explore more of the thread interleavings. Due to the non-deterministic nature
  of concurrent programs, the testsuite must be ran many times to find
  concurrency bugs. This class will perform the testing and record the result
  of the test.

  Attributes:
    _successes (int): number of test executions that resulted in a success
    _timeouts (int): number of test executions that resulted in a timeout
    _dataraces (int): number of test executions that resulted in a datarace
    _deadlocks (int): number of test executions that resulted in a deadlock
    _errors (int): number of test executions that resulted in an error
  """

  _successes = 0
  _timeouts = 0
  _dataraces = 0
  _deadlocks = 0
  _errors = 0

  def begin_testing(self):
    """Begins the testing phase by creating the test processes."""

    print "[INFO] Performing {} Test Runs...".format(config._CONTEST_RUNS)
    for i in range(1, config._CONTEST_RUNS + 1):

      # To ensure stdout doesn't overflow because .poll() can deadlock
      outFile = tempfile.SpooledTemporaryFile()
      errFile = tempfile.SpooledTemporaryFile()

      # Start a test process
      process = subprocess.Popen(['java',
                        '-Xmx{}m'.format(config._PROJECT_TEST_MB), '-cp',
                        config._PROJECT_CLASSPATH, '-javaagent:' +
                        config._CONTEST_JAR, '-Dcontest.verbose=0',
                        config._PROJECT_TESTSUITE], stdout=outFile,
                        stderr=errFile, cwd=config._PROJECT_DIR, shell=False)
      self.run_test(process, outFile, errFile, i)

    print "[INFO] Test Runs Results..."
    print "[INFO] Successes ", self._successes
    print "[INFO] Timeouts ", self._timeouts
    print "[INFO] Dataraces ", self._dataraces
    print "[INFO] Deadlock ", self._deadlocks
    print "[INFO] Errors ", self._errors

  def run_test(self, process, outFile, errFile, i):
    """Runs a single test process.

    The test process is ran with a timeout mechanism in place to determine if
    the process is timing out or just deadlocked. The results of a test is
    either:
     * Success - the testsuite had no errors
     * Timeout - the testsuite  never finished in time
     * Datarace - the testsuite had at least one failing test case
     * Deadlock - the testsuite timed out, and the JVM dump showed a deadlock
     * Error - the testsuite was unable to run correctly

    Args:
      process (Popen): testsuite execution process
      outFile (SpooledTemporaryFile): temporary file to hold stdout output
      errFile (SpooledTemporaryFile): temporary file to hold stderr output
      i (int): current test execution number
    """

    # Set a timeout for the running process
    remainingTime = config._CONTEST_TIMEOUT_SEC
    while process.poll() is None and remainingTime > 0:
      time.sleep(0.1)
      remainingTime -= 0.1

      # If the process did not finish in time
      if process.poll() is None and remainingTime <= 0:

        # Send the Quit signal to get thread dump information from JVM
        process.send_signal(3)

        # Sleep for a second to let std finish, then send terminate command
        time.sleep(1)
        process.terminate()

        # Acquire the stdout information
        outFile.seek(0)
        errFile.seek(0)
        output = outFile.read()
        error = errFile.read()
        outFile.close()
        errFile.close()

        # Check if there is any deadlock using "Java-level deadlock:"
        if (output.find(b"Java-level deadlock:") >= 0):
          print "[INFO] Test {} - Deadlock Encountered".format(i)
          self._deadlocks += 1
        else:
          print "[INFO] Test {} - Timeout Encountered".format(i)
          self._timeouts += 1

      # If the process finished in time
      elif process.poll() is not None:

        # Acquire the stdout information
        outFile.seek(0)
        errFile.seek(0)
        output = outFile.read()
        error = errFile.read()
        outFile.close()
        errFile.close()

        # Check to see if the testsuite itself has an error
        if (len(error) > 0):
          print "[INFO] Test {} - Error in Execution".format(i)
          self._errors += 1
        else:
          # Check to see if any tests failed, and if so how many?
          errors = re.search("There were (\d+) errors:", output)
          if errors is not None:
            print "[INFO] Test {} - Datarace Encountered ({} errors)".format(i,
                  errors.groups()[0])
            self._dataraces += 1
          else:
            print "[INFO] Test {} - Successful Execution".format(i)
            self._successes += 1

  def clear_results(self):
    """Clears the results of the test runs thus far."""

    self._successes = 0
    self._timeouts = 0
    self._dataraces = 0
    self._deadlocks = 0
    self._errors = 0

  def get_successes(self):
    """Returns the number of successful test runs.

    Returns:
      int: the number of successful test runs
    """

    return self._successes

  def get_timeouts(self):
    """Returns the number of test runs that timed out.

    Returns:
      int: the number of timeout test runs
    """
    return self._timeouts

  def get_dataraces(self):
    """Returns the number of test runs that had a datarace.

    Returns:
      int: the number of datarace test runs
    """
    return self._dataraces

  def get_deadlocks(self):
    """Returns the number of test runs that had a deadlock.

    Returns:
      int: the number of deadlock test runs
    """
    return self._deadlocks

  def get_errors(self):
    """Returns the number of test runs that had an error.

    Returns:
      int: the number of error test runs
    """
    return self._errors
