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
  wallTime = []
  voluntarySwitches = []
  involuntarySwitches = []
  percentCPU = []
  goodRuns = []  # True || False

  def begin_testing(self, functional, nonFunctional=False,
                    runs=config._CONTEST_RUNS):
    """Begins the testing phase by creating the test processes."""

    print "[INFO] Performing {} Test Runs...".format(runs)
    for i in range(1, runs + 1):

      # To ensure stdout doesn't overflow because .poll() can deadlock
      outFile = tempfile.SpooledTemporaryFile()
      errFile = tempfile.SpooledTemporaryFile()

      # Start a test process
      if functional:
        process = subprocess.Popen(['java',
                          '-Xmx{}m'.format(config._PROJECT_TEST_MB), '-cp',
                          config._PROJECT_CLASSPATH, '-javaagent:' +
                          config._CONTEST_JAR, '-Dcontest.verbose=0',
                          config._PROJECT_TESTSUITE], stdout=outFile,
                          stderr=errFile, cwd=config._PROJECT_DIR, shell=False)
      else:
        process = subprocess.Popen(['/usr/bin/time', '-v', 'java',
                          '-Xmx{}m'.format(config._PROJECT_TEST_MB), '-cp',
                          config._PROJECT_CLASSPATH,
                          config._PROJECT_TESTSUITE], stdout=outFile,
                          stderr=errFile, cwd=config._PROJECT_DIR, shell=False)
      
      success = self.run_test(process, outFile, errFile, i, functional)
      
      # If last run was unsuccessful and we are in the non-functional, exit
      if nonFunctional and not self.goodRuns[-1]:
        print "Last run was unsuccesful functionally"
        return False

    print "[INFO] Test Runs Results..."
    print "[INFO] Successes ", self.successes
    print "[INFO] Timeouts ", self.timeouts
    print "[INFO] Dataraces ", self.dataraces
    print "[INFO] Deadlock ", self.deadlocks
    print "[INFO] Errors ", self.errors
    print "[INFO] Real Time ", self.realTime
    print "[INFO] Wall Time ", self.wallTime
    print "[INFO] Voluntary Switches ", self.voluntarySwitches
    print "[INFO] Involuntary Switches ", self.involuntarySwitches 
    print "[INFO] Percent CPU ", self.percentCPU
    print "[INFO] Good Runs ", self.goodRuns
    return True

  def run_test(self, process, outFile, errFile, i, functional):
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
          self.deadlocks += 1
        else:
          if functional:
            print "[INFO] Test {} - Timeout Encountered".format(i)
            self.timeouts += 1
          else:
            # If on non-functional, we cannot tell when deadlock thus assume it
            print "[INFO] Test {} - Deadlock/Timeout Encountered".format(i)
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
        faults = re.search("Tests run: \d+,  Failures: (\d+),  Errors: (\d+)", output)

        if faults is not None:
          # Check to see if any tests failed, and if so how many?
          totalFaults = int(faults.groups()[0]) + int(faults.groups()[1])
          print "[INFO] Test {} - Datarace Encountered ({} errors)".format(i,
                totalFaults)
          self.dataraces += 1
          self.goodRuns.append(False)
        else:
          # Check to see if ant test was successful
          if re.search("OK \((\d+) tests\)", output) is not None:
            print "[INFO] Test {} - Error in Execution".format(i)
            self.errors += 1
            self.goodRuns.append(False)
          else:
            print "[INFO] Test {} - Successful Execution".format(i)
            self.successes += 1
            self.goodRuns.append(True)

            if not functional:
              # Take the performance measures of exection
              userTime = re.search("User time \(seconds\): (\d+\.\d+)", error).groups()[0]
              systemTime = re.search("System time \(seconds\): (\d+\.\d+)", error).groups()[0]
              wallTime = 0  # TODO
              voluntarySwitches = re.search("Voluntary context switches: (\d+)", error).groups()[0]
              involuntarySwitches = re.search("Involuntary context switches: (\d+)", error).groups()[0]
              percentCPU = re.search("this job got: (\d+)%", error).groups()[0]
              self.realTime.append(float(userTime) + float(systemTime))
              self.wallTime.append(float(wallTime))
              self.voluntarySwitches.append(float(voluntarySwitches))
              self.involuntarySwitches.append(float(involuntarySwitches))
              self.percentCPU.append(float(percentCPU))

  def clear_results(self):
    """Clears the results of the test runs thus far."""

    self.successes = 0
    self.timeouts = 0
    self.dataraces = 0
    self.deadlocks = 0
    self.errors = 0
    del self.realTime[:]
    del self.wallTime [:]
    del self.voluntarySwitches [:]
    del self.involuntarySwitches [:]
    del self.percentCPU [:]
    del self.goodRuns [:]
