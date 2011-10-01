# System variables
_ROOT_DIR = "/home/jalbert/workspace/arc/"
_MAX_MEMORY_MB = 2000
_MAX_CORES = 2

# Target project variables
_PROJECT_DIR = _ROOT_DIR + "input/"
_PROJECT_SRC_DIR = _PROJECT_DIR + "source/"
_PROJECT_TEST_DIR = _PROJECT_DIR + "source/"
_PROJECT_CLASS_DIR = _PROJECT_DIR + "class/"
_PROJECT_PREFIX = ""
_PROJECT_TESTSUITE = "Deadlock2"
_PROJECT_CLASSPATH = _PROJECT_CLASS_DIR
_PROJECT_TEST_MB = 2000
# TODO auto figure classpath if Ant or MVN exist

# ConTest variables
_CONTEST_DIR = _ROOT_DIR + "lib/ConTest/"
_CONTEST_KINGPROPERTY = _CONTEST_DIR + "KingProperties"
_CONTEST_JAR = _CONTEST_DIR + "ConTest.jar"
_CONTEST_RUNS = 25
_CONTEST_TIMEOUT_SEC = 2  # Aim for around x2-3 desireable performance
_TESTSUITE_AVG = 20  # Number of test executions for finding the average time

# Mutation operator variables

# Pyevolve variables
