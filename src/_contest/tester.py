"""The driver class that runs all the tests and manages the algorithm.

The running of ConTest and TXL occur from within this class, along with the 
choice of the next mutation.

The approach used in the driver is as follows:
  - ConTest is ran to acquire a list of shared variables
  - TXL is ran to annotate the source code with potential mutations
  - Based on test results and current state, apply next appropriate mutation
  - Test and score the new mutated program using ConTest
  - Evaluate scores and decide to keep or drop mutant
  - Test terminating condition
  - Repeat from third step
"""
import sys
import time
import subprocess
import tempfile
import re

sys.path.append("..")
import config

class Tester():

  """Class that drives the automatic repairing of concurrency bugs. 

  ConTest, TXL and the mutation aspect are all used here to find the best 
  solution to the inputed program.

  Attributes:
    _sharedInfo: The singleton object that is shared amongst all classes
  """

  _deadlocks = 0
  _timeouts = 0
  _successes = 0
  _dataraces = 0
  _errors = 0

  def begin_testing(self):
    """Starts the whole approach to automatically repair the program
    specified by the user.

    The approach is automated and will only stop when a satisfaction
    condition is met.
    """

    print "[INFO] Performing {} Test Runs...".format(config._CONTEST_RUNS)

    # Run the ConTest command as many times as needed
    for i in range(1, config._CONTEST_RUNS + 1):

      # To ensure stdout doesn't overflow or .poll() deadlocks
      outFile = tempfile.SpooledTemporaryFile()
      errFile = tempfile.SpooledTemporaryFile()

      # Start the test process
      process = subprocess.Popen( ['java',
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

    remainingTime = config._CONTEST_TIMEOUT_SEC

    # Set a timeout for the running process
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
        outFile.seek(0);
        errFile.seek(0);
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
        outFile.seek(0);
        errFile.seek(0);
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
    self._successes = 0
    self._timeouts = 0
    self._dataraces = 0
    self._deadlocks = 0
  
  def get_successes(self):
    return self._successes
    
  def get_timeouts(self):
    return self._timeouts

  def get_dataraces(self):
    return self._dataraces

  def get_deadlocks(self):
    return self._deadlocks

  def get_errors(self):
    return self._errors
