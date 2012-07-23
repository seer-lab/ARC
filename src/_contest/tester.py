"""This module is responsible for running and recording test results

The Tester class will run a testsuite using ConTest to introduce random thread
sleep() and yeild() into the executing testsuite.
"""

from __future__ import division
import sys
import time
import subprocess
import tempfile
import re

sys.path.append("..")  # To allow importing parent directory module
import config

import logging
logger = logging.getLogger('arc')


class Tester():
  """Class that drives the process of running the testsuite a number of times.

  ConTest is used in conjunction with the test executions in an attempt to
  explore more of the thread interleavings. Due to the non-deterministic nature
  of concurrent programs, the testsuite must be ran many times to find
  concurrency bugs. This class will perform the testing and record the result
  of the test.

  Attributes:
    successes (int): number of test executions that resulted in a success
    timeouts (int): number of test executions that resulted in a timeout
    dataraces (int): number of test executions that resulted in a datarace
    deadlocks (int): number of test executions that resulted in a deadlock
    errors (int): number of test executions that resulted in an error
  """

  successes = 0
  timeouts = 0
  dataraces = 0
  deadlocks = 0
  errors = 0

  realTime = []
  voluntarySwitches = []
  goodRuns = []  # True || False


  def begin_testing(self, functional, nonFunctional=False,
                    runs=config._CONTEST_RUNS):
    """Begins the testing phase by creating the test processes."""

    logger.debug("Performing {} Test Runs...".format(runs))
    for i in range(1, runs + 1):

      # To ensure stdout doesn't overflow because .poll() can deadlock
      outFile = tempfile.SpooledTemporaryFile()
      errFile = tempfile.SpooledTemporaryFile()

      # Start a test process
      if functional:
        process = subprocess.Popen(['java', '-Xmx{}m'.format(config._PROJECT_TEST_MB),
          '-cp', config._PROJECT_CLASSPATH + ":" + config._JUNIT_JAR , '-javaagent:' + config._CONTEST_JAR,
                    '-Dcontest.verbose=0',  'org.junit.runner.JUnitCore',
                    config._PROJECT_TESTSUITE], stdout=outFile,
                    stderr=errFile, cwd=config._PROJECT_DIR, shell=False)
      else:
        # MAC uses a different time argument then Linux
        # http://developer.apple.com/library/mac/#documentation/Darwin/Reference/ManPages/man1/time.1.html
        if config._OS is 'MAC':
          timeArg = '-lp' # BSD-style
        else:
          timeArg = '-v'  # Linux-style

        process = subprocess.Popen(['/usr/bin/time', timeArg, 'java',
                    '-Xmx{}m'.format(config._PROJECT_TEST_MB), '-cp',
                    config._PROJECT_CLASSPATH + ":" + config._JUNIT_JAR, 'org.junit.runner.JUnitCore',
                    config._PROJECT_TESTSUITE],
                    stdout=outFile, stderr=errFile, cwd=config._PROJECT_DIR,
                    shell=False)

      success = self.run_test(process, outFile, errFile, i, functional)

      # If last run was unsuccessful and we are in the non-functional, exit
      if len(self.goodRuns) > 0:
        if nonFunctional and not self.goodRuns[-1]:
          logger.debug("Non-functional testing: A bug exists in the program")
          return False

    logger.debug("Test Runs Results...")
    logger.debug("Successes: {}".format(self.successes))
    logger.debug("Timeouts: {}".format(self.timeouts))
    logger.debug("Dataraces: {}".format(self.dataraces))
    logger.debug("Deadlock: {}".format(self.deadlocks))
    logger.debug("Errors: {}".format(self.errors))
    logger.debug("Real Time: {}".format(self.realTime))
    logger.debug("Voluntary Switches: {}".format(self.voluntarySwitches))
    logger.debug("Good Runs: {}".format(self.goodRuns))
    return True

  def run_test(self, process, outFile, errFile, i, functional):
    """Runs a single test process.

    The test process is run with a timeout mechanism in place to determine if
    the process is timing out or just deadlocked. The results of a test is
    either:
     * Success - the testsuite had no errors
     * Timeout - the testsuite  didn't finished in time
     * Datarace - the testsuite had at least one failing test case
     * Deadlock - the testsuite timed out, and the JVM dump showed a deadlock
     * Error - the testsuite didn't run correctly

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
          logger.info("Test {} - Deadlock Encountered (Java-level deadlock)".format(i))
          self.deadlocks += 1
        else:
          if functional:
            logger.info("Test {} - Timeout Encountered".format(i))
            self.timeouts += 1
          else:
            # If on non-functional, we cannot tell when deadlock thus assume it
            logger.info("Test {} - Deadlock/Timeout Encountered".format(i))
            self.deadlocks += 1
        self.goodRuns.append(False)

      # If the process finished in time
      elif process.poll() is not None:

        # Acquire the stdout information
        outFile.seek(0)
        errFile.seek(0)
        output = outFile.read()
        error = errFile.read()
        outFile.close()
        errFile.close()

        # Acquire the number of faults (accoring to ant test)
        #logger.debug("Test, Output text:\n")
        #logger.debug(output)
        #logger.debug("Test, Error text:\n")
        #logger.debug(error)

        numTests = 0
        numFailures = 0
        numSuccesses = 0

        faultTests = re.search("Tests run: (\d+),\s+Failures: (\d+)", output)
        if faultTests is not None:
          numTests = faultTests.group(1)
          numFailures = faultTests.group(2)

        successTests = re.search("OK \((\d+) test", output)
        if successTests is not None:
            numSuccesses = successTests.group(1)

        # Some tests have failed
        if numTests > 0 and numFailures > 0:
          totalFaults = numFailures
          logger.info("Test {} - Datarace Encountered ({} errors)".format(i,
                                                                  totalFaults))
          self.dataraces += 1
          self.goodRuns.append(False)

        # Tests have no faults and no successes
        elif numTests is 0 and numSuccesses is 0:
          logger.info("Test {} - Deadlock Encountered".format(i))
          self.deadlocks += 1
          self.goodRuns.append(False)

        # Tests have successes
        elif numSuccesses > 0 or (numTests > 0 and numFailures is 0):
          if numTests > 0:
            totalSuccesses = numTests
          else:
            totalSuccesses = numSuccesses

          # No tests were ran, thus some error occurred
          if totalSuccesses is 0:
            logger.info("Test {} - Error, no tests ran".format(i))
            self.errors += 1
            self.goodRuns.append(False)

          # Successful tests were encounted
          else:
            logger.info("Test {} - Successful Execution".format(i))
            self.successes += 1
            self.goodRuns.append(True)

            if not functional:
              # Take the performance measures of exection
              if config._OS is 'MAC':
                userTime = re.search("user \s+ (\d+\.\d+)", error).groups()[0]
                systemTime = re.search("sys \s+ (\d+\.\d+)", error).groups()[0]
                # TODO: Investigate why 'voluntary context switches' is 0 on MAC
                #       All 0 causes a division by zero error in
                #       function evolution.py.get_average_non_functional_score
                #       Is involuntary context switches valid? Think about this!
                # Note: The MAC is used for development only.
                #       Using involuntary switches on the MAC for now
                voluntarySwitches = re.search("(\d+)\s+ involuntary context switches", error).groups()[0]
              else: # Linux
                userTime = re.search("User time \(seconds\): (\d+\.\d+)", error).groups()[0]
                systemTime = re.search("System time \(seconds\): (\d+\.\d+)", error).groups()[0]
                voluntarySwitches = re.search("Voluntary context switches: (\d+)", error).groups()[0]

              self.realTime.append(float(userTime) + float(systemTime))
              self.voluntarySwitches.append(float(voluntarySwitches))


  def clear_results(self):
    """Clears the results of the test runs thus far."""

    self.successes = 0
    self.timeouts = 0
    self.dataraces = 0
    self.deadlocks = 0
    self.errors = 0
    del self.realTime [:]
    del self.voluntarySwitches [:]
    del self.goodRuns [:]
