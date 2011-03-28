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
import time
import tester

class driver():

    """Class that drives the automatic repairing of concurrency bugs. 

    ConTest, TXL and the mutation aspect are all used here to find the best 
    solution to the inputed program.

    Attributes:
        _sharedInfo: The singleton object that is shared amongst all classes
    """

    _sharedInfo = None

    def __init__(self, sharedInfo):
        """Initializes the driver object and sets the sharedInfo object.

        Args:
            sharedInfo: reference to the singleton shared_info object
        """
        self._sharedInfo = sharedInfo  

    def begin_approach(self):
        """Starts the whole approach to automatically repair the program
        specified by the user.

        The approach is automated and will only stop when a satisfaction
        condition is met.
        """
        print ('\n----------Beginning Genetic Healing Process----------')

        # Initial ConTest run
        print ('\n~> Performing Initial Testing Runs...')
        self.run_contest()
        print ('~> Done')


        # Perform annotation of the source code
        print ('\n~> Performing Source Code Annotation...')
        self.annotate_with_TXL()
        print ('~> Done')

        count = 0
        # Keep on mutating the source code until a satisfied condition is met 
        while (not self.is_satisfied(count)):

            count += 1

            print ('\n-----Beginning Generation' + repr(count) + '-----')
            self._sharedInfo.reset_deadlock_count()
            self.run_contest() # TODO maybe run a set of test, oppose to single

            print ('~> Number of Deadlocked Runs: ' + repr(self._sharedInfo.get_deadlock_count()) + '/' + repr(self._sharedInfo.numOfRuns))
            print ('----Completed Generation ' + repr(count) + '-----')

        print ('\n----------Summary of Genetic Healing Process----------')
        print ('~> Number of Generations completed: ' + repr(count) + '/' + repr(self._sharedInfo.numOfGenerations))
        print ('~> Number of Test Runs in each Generation: ' + repr(self._sharedInfo.numOfRuns))

    def annotate_with_TXL(self):
        """TXL is used to annotate the source code of the targeted program with
        mutation annotations.
        """
        # TODO complete this method by calling TXL on the program for each mutation
        pass

    def run_contest(self):
        """ConTest is ran on the class files of the project so that they are
        instrumented according to the kingPropertyFile. The instrumented class
        files are then ran in individual testRunner (concurrently) to take
        advantage of multiple CPUs. A thread pool is used to manage the test
        runners.
        """
        # TODO possibly look at using python concurrent.futures
        # Array to keep track of the current test runners
        allTestRuns = []

        # Run the ConTest command as many times as needed
        for count in range(0, self._sharedInfo.numOfRuns):

            stillMore = True

            # Start the test runner for this ConTest process
            while (stillMore):
                if (self._sharedInfo.get_runner_count() > 0 ):
                    testRunner = tester.tester(count + 1, self._sharedInfo)
                    testRunner.start()
                    allTestRuns.append(testRunner)
                    stillMore = False

        # Wait to join on the runners
        done = False
        while (not done):
            time.sleep(2)
            done = True
            for testRunner in allTestRuns:
                if (testRunner.is_alive()):
                    done = False


    def is_satisfied(self, currentGenerations):
        """Checks to see if the process is satisfied in regards to terminating
        conditions.

        Checks to see if the currentGenerations exceeds the value of 
        numOfGenerations. Also check to see if there are no more bugs present.
        A check is done to see if there has been any improvement in the last
        few generations.

        Args:
            currentGenerations: the current generation count

        Returns:
            A bool representing if the satisfaction condition has been met
        """

        # Checks if the generation count exceeds limit
        if ( currentGenerations == self._sharedInfo.numOfGenerations): 
            return True

        percentWithNoBugs = 1 - (self._sharedInfo.get_deadlock_count() / self._sharedInfo.numOfRuns)

        # Checks to see if there are no bugs left
        if (percentWithNoBugs == 1):
            return True

        # TODO need to keep track of previous scores so that a terminating 
        #   condition can be used if no improvement has been made
