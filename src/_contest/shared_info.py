"""A singleton class that is shared amongst the other classes to communicate.

A lot of the user parameters are necessary in other sections of the process,
thus a shared object is required. Additionally, the testing is done through
spawned shells, which will adjust this object asynchronously.
"""
import threading
import multiprocessing

class shared_info():

  """A singleton object that is accessible to all the classes, it contains
  shared information. 
  
  In particular, the number of deadlocks and available
  test runners are shared here amongst the multiple threads.

  Attributes:
    __avalibleRunners: Number of test runners currently available
    __deadlockCount: Number of deadlocks currently encountered
    numOfRuns: Number of runs to perform
    timeout: Timeout period for a test, in seconds
    numOfGenerations: Number of generations to perform
    kingPropertyFile: Location of the kingPropertyFile
    conTestFile: Location of the conTestFile
    classPath: The classPath to be used during testing
    mainClass: The mainClass to be used during the testing
  """

  __avalibleRunners = multiprocessing.cpu_count() * 4
  __deadlockCount = 0
  numOfRuns = 0
  timeout = 0
  numOfGenerations = 0
  kingPropertyFile = ''
  conTestFile = ''
  classPath = ''
  mainClass = ''
  __runnerLock = threading.Lock()
  __counterLock = threading.Lock()

  def __init__(self):
    """Initializes the shared_info object.
    """

  def inc_runner_count(self):
    """Increases the available runner count by 1.
    """
    self.__runnerLock.acquire()
    self.__avalibleRunners += 1
    self.__runnerLock.release()

  def inc_deadlock_count(self):
    """Increases the deadlock count by 1.
    """
    self.__counterLock.acquire()
    self.__deadlockCount += 1
    self.__counterLock.release()

  def dec_runner_count(self):
    """Decreases the available runner count by 1.
    """
    self.__runnerLock.acquire()
    self.__avalibleRunners -= 1
    self.__runnerLock.release()

  def dec_deadlock_count(self):
    """Decreases the deadlock count by 1.
    """
    self.__counterLock.acquire()
    self.__deadlockCount -= 1
    self.__counterLock.release()

  def reset_deadlock_count(self):
    """Resets the deadlock count back to 0.
    """
    self.__counterLock.acquire()
    self.__deadlockCount = 0
    self.__counterLock.release()

  def get_runner_count(self):
    """Returns the current number of available runners.

    Returns:
      The current number of available runners.
    """
    return self.__avalibleRunners

  def get_deadlock_count(self):
    """Returns the current number of deadlocks.

    Returns:
      The current number of deadlocks.
    """
    return self.__deadlockCount
