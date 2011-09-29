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

class Contester():

  """Class that drives the automatic repairing of concurrency bugs. 

  ConTest, TXL and the mutation aspect are all used here to find the best 
  solution to the inputed program.

  Attributes:
    _sharedInfo: The singleton object that is shared amongst all classes
  """

  _deadlocks = 0
  _timeouts = 0
  _succsesses = 0
  _dataraces = 0

  def begin_contesting(self):
    """Starts the whole approach to automatically repair the program
    specified by the user.

    The approach is automated and will only stop when a satisfaction
    condition is met.
    """

    # ConTest
    print "[INFO] Performing Testing Runs..."
    self.apply_contest()

    # Run the ConTest command as many times as needed
    for i in range(1, config._CONTEST_RUNS + 1):

      # To ensure stdout doesn't overflow or .poll() deadlocks
      outFile = tempfile.SpooledTemporaryFile()

      # Start the test process
      process = subprocess.Popen( ['java', 
                        '-Xmx{}m'.format(config._PROJECT_TEST_MB), '-cp',
                        config._PROJECT_CLASSPATH, config._PROJECT_TESTSUITE,
                        '-javaagent: ' + config._CONTEST_JAR,
                        '-Dcontest.verbose=0'], stdout=outFile,
                        cwd=config._PROJECT_DIR, shell=False)
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
          output = outFile.read()
          outFile.close()

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
          output = outFile.read()
          outFile.close()

          # Check to see if any tests failed, and if so how many?
          errors = re.search("There were (\d+) errors:", output)
          if errors is not None:
            print "[INFO] Test {} - Datarace Encountered ({} errors)".format(i, 
                  errors.groups()[0])
            self._dataraces += 1  
          else:
            print "[INFO] Test {} - Successful Execution".format(i)
            self._succsesses += 1

    print "[INFO] Testing Runs Results..."
    print "[INFO] Succsesses ", self._succsesses
    print "[INFO] Timeouts ", self._timeouts
    print "[INFO] Dataraces ", self._dataraces
    print "[INFO] Deadlock ", self._deadlocks

  def apply_contest(self):
    """ConTest is ran on the class files of the project so that they are
    instrumented according to the kingPropertyFile. The instrumented class
    files are then ran in individual testRunner (concurrently) to take
    advantage of multiple CPUs. A thread pool is used to manage the test
    runners.
    """
    pass