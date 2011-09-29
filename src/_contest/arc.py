""" Script to initialize ARC using user parameters and start the repairing.

The user inputed parameters are taken into account, and used to initialize the
shared_info singleton object. The process first checks to ensure that the all
the tools and directories are present, only then will the repairing proceed.
"""
import sys
import subprocess
import contester
import os
import timeit

sys.path.append("..")
import config

def test_target():
  # Check that the target project can be executed and record the time taken
  process = subprocess.Popen( ['java', '-cp', config._PROJECT_CLASSPATH, 
                      config._PROJECT_TESTSUITE], stdout=subprocess.PIPE, 
                      shell=False)
  output,error = process.communicate()
  return error

def main():
  """Main function that parses the user input and stores them appropriately.
  Will also check to make sure the directories and tools are present. After
  these are checked, the shared_info object is created using the parameters
  and the healing process begins.
  """

  # Test to make sure the directories and tools are present
  directoriesPass = None
  toolsPass = None
  
  # Determine if the testsuite will execute correctly
  try:
    if (test_target() != None):
      raise Exception('ERROR', 'testsuite')

  except Exception as message:
    print (message.args)
    sys.exit()

  # Determine the average execution time for the test suite
  print "[INFO] Running testsuite {} times".format(config._TESTSUITE_AVG)
  timer = timeit.Timer("test_target()", "from arc import test_target")
  config._CONTEST_TIMEOUT_SET = timer.timeit(config._TESTSUITE_AVG) \
                                             / config._TESTSUITE_AVG
  print "[INFO] Testsuite took {}s".format(config._CONTEST_TIMEOUT_SET)

  # Determine that the required tools and configurations are correct
  try:
    directoriesPass = check_directories()
    toolsPass = check_tools()
  except Exception as message:
    print (message.args)
    sys.exit()

  if (directoriesPass and toolsPass):
    tester = contester.Contester()
    tester.begin_contesting()

def check_tools():
  """Check that the required tools are installed and present.

  Returns:
    A bool representing if the tools are present. True == present.
  """

  print "[INFO] Checking if txl is present"
  try:
    subprocess.check_call(["which", "txl"])
  except subprocess.CalledProcessError:
    raise Exception('ERROR MISSING TOOL' , 'txl')

  print "[INFO] Checking if ConTest is present"
  if (not os.path.exists(config._CONTEST_JAR)):
    raise Exception('ERROR MISSING TOOL' , 'ConTest')

  print "[INFO] Checking if ConTest's KingProperties is present"
  if (not os.path.exists(config._CONTEST_KINGPROPERTY)):
    raise Exception('ERROR MISSING CONFIGURATION' , 'KingProperties')

  print "[INFO] All Pass"
  return True

def check_directories():
  """Checks that the required directories are present.

  Returns:
    A bool representing if the directories are present. True == present.
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
  main()
