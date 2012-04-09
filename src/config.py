"""This module holds all the configuration values that are used in ARC.

There are system, target project, ConTest, mutation operator and evolution
variables that are set in this file and are used all throughout ARC.
"""

import logging

# System variables
_ROOT_DIR = "/home/dkelk/workspace/arc/"
_MAX_MEMORY_MB = 2000
_MAX_CORES = 2
_TMP_DIR = _ROOT_DIR + "tmp/"
_TXL_DIR = _ROOT_DIR + "src/_txl/"
_JUNIT_JAR = _ROOT_DIR + "lib/junit-4.8.1.jar"
_VERBOSE = True
_LOG_FILE = "log.txt"  # If None then use stdout, otherwise specify a file
_RANDOM_SEED = None  # None means use the system time, non-zero is fixed

# Target project variables
_PROJECT_DIR = _ROOT_DIR + "input/airline/"
_PROJECT_SRC_DIR = _PROJECT_DIR + "source/"
_PROJECT_TEST_DIR = _PROJECT_DIR + "test/"
_PROJECT_CLASS_DIR = _PROJECT_DIR + "class/"
_PROJECT_BACKUP_DIR = _ROOT_DIR + "project_backup/"
_PROJECT_OUTPUT_DIR = _ROOT_DIR + "output/"
_PROJECT_PREFIX = "org.example.project,AirlineBug"  # Comma separated fully-qualifying class names or package prefixes
_PROJECT_TESTSUITE = "AirlineTest"
_PROJECT_COMPILE = "compile"
_PROJECT_TEST = "test"
_PROJECT_CLASSPATH = None  # Automatically acquired using ant test if None
_PROJECT_TEST_MB = 2000
_SHARED_VARS_FILE = _PROJECT_DIR + "com_ibm_contest/sharedVars.txt"
# TODO Consider some automatic way to figure classpath if Ant or MVN exist

# ConTest variables
_CONTEST_DIR = _ROOT_DIR + "lib/ConTest/"
_CONTEST_KINGPROPERTY = _CONTEST_DIR + "KingProperties"
_CONTEST_JAR = _CONTEST_DIR + "ConTest.jar"
_CONTEST_RUNS = 10
_CONTEST_TIMEOUT_SEC = 30 # Default timeout, it is adjusted dynamically
_CONTEST_TIMEOUT_MULTIPLIER = 3  # The average execution time (with conTest) is multiplied by this
_CONTEST_VALIDATION_MULTIPLIER = 10  # Allows for validation of functionality

# Mutation operator variables
# [0]Name  [1]Enable  [2]DataRace  [3]Deadlock  [4]File
_MUTATION_ASAS = ['ASAS', True, True, True, _TXL_DIR + "ASAS.Txl"]
_MUTATION_ASAV = ['ASAV', True, True, True, _TXL_DIR + "ASAV.Txl"]
_MUTATION_ASIM = ['ASIM', True, True, True, _TXL_DIR + "ASIM.Txl"]
_MUTATION_ASM  = ['ASM', True, True, True, _TXL_DIR + "ASM.Txl"]
_MUTATION_CSO  = ['CSO', True, False, True, _TXL_DIR + "CSO.Txl"]
_MUTATION_EXSB = ['EXSB', True, True, True, _TXL_DIR + "EXSB.Txl"]
_MUTATION_EXSA = ['EXSA', True, True, True, _TXL_DIR + "EXSA.Txl"]
_MUTATION_RSAS = ['RSAS', True, True, True, _TXL_DIR + "RSAS.Txl"]
_MUTATION_RSAV = ['RSAV', True, True, True, _TXL_DIR + "RSAV.Txl"]
_MUTATION_RSIM = ['RSIM', True, True, True, _TXL_DIR + "RSIM.Txl"]
_MUTATION_RSM  = ['RSM', True, True, True, _TXL_DIR + "RSM.Txl"]
_MUTATION_SHSA = ['SHSA', True, True, True, _TXL_DIR + "SHSA.Txl"]
_MUTATION_SHSB = ['SHSB', True, True, True, _TXL_DIR + "SHSB.Txl"]
_FUNCTIONAL_MUTATIONS = [_MUTATION_ASAS, _MUTATION_ASAV, _MUTATION_ASIM,
                         _MUTATION_ASM, _MUTATION_CSO, _MUTATION_EXSB,
                         _MUTATION_EXSA, _MUTATION_RSAS, _MUTATION_RSAV,
                         _MUTATION_RSIM, _MUTATION_RSM]
_NONFUNCTIONAL_MUTATIONS = [_MUTATION_RSAS, _MUTATION_RSAV, _MUTATION_RSIM,
                            _MUTATION_RSM, _MUTATION_SHSA, _MUTATION_SHSB]
_ALL_MUTATIONS = [_MUTATION_ASAS, _MUTATION_ASAV, _MUTATION_ASIM,
                         _MUTATION_ASM, _MUTATION_CSO, _MUTATION_EXSB,
                         _MUTATION_EXSA, _MUTATION_RSAS, _MUTATION_RSAV,
                         _MUTATION_RSIM, _MUTATION_RSM, _MUTATION_SHSA,
                         _MUTATION_SHSB]

# Enable random mutation
_RANDOM_MUTATION = False

# Evolution variables
_EVOLUTION_GENERATIONS = 20
_EVOLUTION_POPULATION = 10
_EVOLUTION_REPLACE_LOWEST_PERCENT = 10
_EVOLUTION_REPLACE_INTERVAL = 2  # Consider replacement on this generational interval
_EVOLUTION_REPLACE_WEAK_MIN_TURNS = 1  # Min number of turns of underperforming before replacement
_EVOLUTION_REPLACE_WITH_BEST_PERCENT = 80

# Dynamic ranking window (number of generations to consider)
_DYNAMIC_RANKING_WINDOW = 20

# Fitness evaluation variables
_SUCCESS_WEIGHT = 100
_TIMEOUT_WEIGHT = 50

# Convergence criteria, considering the window size ensure there is at least
# a fitness score movement of delta
_GENERATIONAL_IMPROVEMENT_WINDOW = 20
_AVG_FITNESS_MIN_DELTA = 0.01
_BEST_FITNESS_MIN_DELTA = 0.01

# Create logger
logger = logging.getLogger('arc')
if _LOG_FILE is None:
  handler = logging.StreamHandler()
else:
  handler = logging.FileHandler(_LOG_FILE, "w");

if _VERBOSE:
  logger.setLevel(logging.DEBUG)
else:
  logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(relativeCreated)d %(levelname)s [%(module)s.%(funcName)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
