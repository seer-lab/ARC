"""The tester class will spawn a single execution of ConTest on the desired
program, and take note of the execution outcome.

Running a test is done by spawning a thread that execute the Java ConTest
process. 
"""
import threading
import time
import subprocess

class tester(threading.Thread):

    """Creates a single process that will run as a separate thread to test the
    mutated program using ConTest.

    Attributes:
        process: The spawned process that is running the mutated program
        testID: The ID value of the current test
        _sharedInfo: The singleton object that is shared amongst all classes
        _lock: A lock to ensure that output does not get interleaved
    """

    process = None
    testId = None
    _sharedInfo = None
    _lock = threading.Lock()

    def __init__(self, testID, sharedInfo):
        """Initializes the tester object and sets the current testID and
        the sharedInfo object.
        """
        self._sharedInfo = sharedInfo
        self._sharedInfo.dec_runner_count()

        # Spawn a ConTest process to test the mutated program
        threading.Thread.__init__(self)
        self.process = subprocess.Popen( ['java',
                '-cp', self._sharedInfo.classPath,
                self._sharedInfo.mainClass,
                '-javaagent: ' + self._sharedInfo.conTestFile,
                '-Dcontest.verbose=0'], 
                stdout=subprocess.PIPE, 
                shell=False)
        self.testID = testID

    def run(self):
        """Waits for the testing to complete, or timeout and then handles the
        results.

        The results of the test will be placed into the sharedInfo object.
        """
        # Wait the timeout period
        time.sleep(self._sharedInfo.timeout)

        # Check to see if the process is still working if so then force quit it
        if (self.process.poll() == None):

            # Send the Quit signal to get thread dump information from JVM
            self.process.send_signal(3)

            # Sleep for a tenth-of-a-second to let std finish
            time.sleep(0.1)

            # Send the terminate command
            self.process.terminate()

            # Acquire the stdout information
            output,error = self.process.communicate()

            # Check to see if there is any deadlock found using "Java-level deadlock:"
            if (output.find(b'Java-level deadlock:') >= 0):
                self._lock.acquire()
                print ('\t~> RUN ' + repr(self.testID) + '...\n\t Result: Deadlock Encountered')
                self._lock.release()
                self._sharedInfo.inc_deadlock_count()
                self._sharedInfo.inc_runner_count()
            else:
                self._lock.acquire()
                print ('\t~> RUN ' + repr(self.testID) + '..\n\t Result: Undesirable Performance Encountered')
                self._lock.release()
                # TODO have some measure related to performance
                self._sharedInfo.inc_runner_count()
        else:
            self._lock.acquire()
            print ('\t~> RUN ' + repr(self.testID) + '...\n\t Result: Terminated Normally')
            self._lock.release()
            self._sharedInfo.inc_runner_count()
