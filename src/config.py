"""This module holds all the configuration values that are used in ARC.

There are system, target project, ConTest, mutation operator and Pyevolve
variables that are set in this file and are used all throughout ARC.
"""

# System variables
_ROOT_DIR = "/home/jalbert/workspace/arc/"
_MAX_MEMORY_MB = 2000
_MAX_CORES = 2

# Target project variables
_PROJECT_DIR = _ROOT_DIR + "input/"
_PROJECT_SRC_DIR = _PROJECT_DIR + "source/"
_PROJECT_TEST_DIR = _PROJECT_DIR + "source/"
_PROJECT_CLASS_DIR = _PROJECT_DIR + "class/"
_PROJECT_TEMP_DIR = _PROJECT_DIR + "temp/"
_PROJECT_PREFIX = ""
_PROJECT_TESTSUITE = "Deadlock2"
_PROJECT_CLASSPATH = _PROJECT_CLASS_DIR
_PROJECT_TEST_MB = 2000
# TODO Consider some automatic way to figure classpath if Ant or MVN exist

# ConTest variables
_CONTEST_DIR = _ROOT_DIR + "lib/ConTest/"
_CONTEST_KINGPROPERTY = _CONTEST_DIR + "KingProperties"
_CONTEST_JAR = _CONTEST_DIR + "ConTest.jar"
_CONTEST_RUNS = 25
_CONTEST_TIMEOUT_SEC = 2  # Aim for around x2-3 desirable performance
_TESTSUITE_AVG = 20  # Number of test executions for finding the average time

# Mutation operator variables (True == considered as an operator)
_MUTATIONS_ENABLE = {'ASAS': True,
                     'ASAV': True,
                     'ASM': True,
                     'CSO': True,
                     'EXCR': True,
                     'EXSA': True,
                     'RSAS': True,
                     'RSAV': True,
                     'RSB': True,
                     'RSM': True,
                     'SHSA': True,
                     'SHSB': True}
_MUTATIONS_FILE = {'ASAS': _ROOT_DIR + "src/_txl/ASAS.Txl",
                   'ASAV': _ROOT_DIR + "src/_txl/ASAV.Txl",
                   'ASM': _ROOT_DIR + "src/_txl/ASM.Txl",
                   'CSO': _ROOT_DIR + "src/_txl/CSO.Txl",
                   'EXCR': _ROOT_DIR + "src/_txl/EXCR.Txl",
                   'EXSA': _ROOT_DIR + "src/_txl/EXSA.Txl",
                   'RSAS': _ROOT_DIR + "src/_txl/RSAS.Txl",
                   'RSAV': _ROOT_DIR + "src/_txl/RSAV.Txl",
                   'RSB': _ROOT_DIR + "src/_txl/RSB.Txl",
                   'RSM': _ROOT_DIR + "src/_txl/RSM.Txl",
                   'SHSA': _ROOT_DIR + "src/_txl/SHSA.Txl",
                   'SHSB': _ROOT_DIR + "src/_txl/SHSB.Txl"}

# Pyevolve variables
