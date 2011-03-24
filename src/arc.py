""" Script to initialize ARC using user parameters and start the repairing.

The user inputed parameters are taken into account, and used to initialize the
shared_info singleton object. The process first checks to ensure that the all
the tools and directories are present, only then will the repairing proceed.
"""
import argparse
import sys
import subprocess
import driver
import os
import shared_info

# Directories and files
_PARENT_DIR = os.getcwd() + os.sep + os.pardir + os.sep
_CONTEST_DIR = _PARENT_DIR + 'lib' + os.sep + 'ConTest'+ os.sep
_INPUT_DIR = _PARENT_DIR + 'input' + os.sep 
_SOURCE_DIR = _INPUT_DIR + 'source' + os.sep
_CLASS_DIR = _INPUT_DIR + 'class' + os.sep
_KINGPROPERTY_FILE = _CONTEST_DIR + 'KingProperties'
_CONTEST_FILE = _CONTEST_DIR + 'ConTest.jar'

def main():
    """Main function that parses the user input and stores them appropriately.
    Will also check to make sure the directories and tools are present. After
    these are checked, the shared_info object is created using the parameters
    and the healing process begins.
    """

    # Define the argument options to be parsed
    parser = argparse.ArgumentParser(
            description = 'ARC: Automatically Repair Concurrency bugs in Java <https://github.com/kevinjalbert/arc>', 
            version = 'ARC 0.01', 
            usage = 'python arc.py [OPTIONS] [-m MAINCLASS]') 
    parser.add_argument(
            '--verbose',
            action='store_true',
            default=False,
            dest='verbose',
            help='Displays additional information during execution')

    # Runtime arguments
    groupRun = parser.add_argument_group('Runtime Arguments')
    groupRun.add_argument(
            '-m',
            action='store',
            default=False,
            dest='mainClass',
            help='Main class of the input to be automatically repaired')
    groupRun.add_argument(
            '-g',
            action='store',
            type=int,
            dest='generations',
            default=10,
            help='Number of generations to perform [DEFAULT=10]')
    groupRun.add_argument(
            '-p',
            action='store',
            type=int,
            dest='period',
            default=5,
            help='Timeout period for a process, in seconds [DEFAULT=60]')
    groupRun.add_argument(
            '-r',
            action='store',
            type=int,
            dest='runs',
            default=5,
            help='Number of test runs to perform [DEFAULT=50]')   

    # Disable Mutation Operator arguments
    groupMut = parser.add_argument_group('Disable Mutation Operator Arguments:')
    groupMut.add_argument(
            '--disable-mut1',
            action='store_true',
            dest='disableMut1',
            default=False,
            help='Synchronize an unprotected shared resource')
    groupMut.add_argument(
            '--disable-mut2',
            action='store_true',
            dest='disableMut2',
            default=False,
            help='Expand synchronization regions to include unprotected code')
    groupMut.add_argument(
            '--disable-mut3',
            action='store_true',
            dest='disableMut3',
            default=False,
            help='Interchanging nested lock objects')

    # Parse the arguments passed from the shell
    options = parser.parse_args()

    # Test to make sure the directories and tools are present
    directoriesPass = None
    toolsPass = None
    try:
        directoriesPass = checkDirectories()
        toolsPass = checkTools()
    except Exception as message:
        print (message.args)

    # Only proceed if everything is ready
    if (directoriesPass and toolsPass ):
        sharedInfo = shared_info.shared_info()
        sharedInfo.kingPropertyFile = _KINGPROPERTY_FILE
        sharedInfo.conTestFile = _CONTEST_FILE
        sharedInfo.classPath = _CLASS_DIR
        sharedInfo.mainClass = options.mainClass
        sharedInfo.numOfRuns = options.runs
        sharedInfo.timeout = options.period
        sharedInfo.numOfGenerations = options.generations

        healingDriver = driver.driver(sharedInfo)
        healingDriver.beginApproach()
    else:
        # Exit; the program is not ready.
        sys.exit()

def checkTools():
    """Check that the required tools are installed and present.

    Returns:
        A bool representing if the tools are present. True == present.
    """

    # Check to make sure that TXL is installed
    try:
        subprocess.check_call(["which", "txl"])
    except subprocess.CalledProcessError:
        raise Exception('ERROR MISSING TOOL' , 'txl')

    # Check to make sure that ConTest is present
    if (not os.path.exists(_CONTEST_FILE)):
        raise Exception('ERROR MISSING TOOL' , 'ConTest')

    # Check to make sure that ConTest's configuration file is present
    if (not os.path.exists(_KINGPROPERTY_FILE)):
        raise Exception('ERROR MISSING CONFIGURATION' , 'KingProperties')

    return True

def checkDirectories():
    """Checks that the required directories are present.
    
    Returns:
        A bool representing if the directories are present. True == present.
    """

    if(not os.path.isdir(_SOURCE_DIR)):
        raise Exception('ERROR MISSING DIRECTORY', 'source')

    if(not os.path.isdir(_CLASS_DIR)):
        raise Exception('ERROR MISSING DIRECTORY', 'class')

    return True

# If this module is ran as main
if __name__ == '__main__':
    main()
