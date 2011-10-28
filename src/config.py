"""This module holds all the configuration values that are used in ARC.

There are system, target project, ConTest, mutation operator and evolution
variables that are set in this file and are used all throughout ARC.
"""

import logging

# System variables
_ROOT_DIR = "/home/jalbert/workspace/arc/"
_MAX_MEMORY_MB = 2000
_MAX_CORES = 2
_TMP_DIR = _ROOT_DIR + "tmp/"
_TXL_DIR = _ROOT_DIR + "src/_txl/"
_JUNIT_JAR = _ROOT_DIR + "lib/junit-4.8.1.jar"
_VERBOSE = True

# Target project variables
_PROJECT_DIR = _ROOT_DIR + "input/"
_PROJECT_SRC_DIR = _PROJECT_DIR + "source/"
_PROJECT_TEST_DIR = _PROJECT_DIR + "source/"
_PROJECT_CLASS_DIR = _PROJECT_DIR + "class/"
_PROJECT_BACKUP_DIR = _ROOT_DIR + "project_backup/"
_PROJECT_PREFIX = ""
_PROJECT_TESTSUITE = "Deadlock2"
_PROJECT_CLASSPATH = _PROJECT_CLASS_DIR
_PROJECT_TEST_MB = 2000
# TODO Consider some automatic way to figure classpath if Ant or MVN exist

# ConTest variables
_CONTEST_DIR = _ROOT_DIR + "lib/ConTest/"
_CONTEST_KINGPROPERTY = _CONTEST_DIR + "KingProperties"
_CONTEST_JAR = _CONTEST_DIR + "ConTest.jar"
_CONTEST_RUNS = 5
_CONTEST_TIMEOUT_SEC = 2  # Aim for around x2-3 desirable performance
_TESTSUITE_AVG = 20  # Number of test executions for finding the average time

# Mutation operator variables
# [0]Name  [1]Enable  [2]DataRace  [3]Deadlock  [4]File
_MUTATION_ASAS = ['ASAS', True, True, True, _TXL_DIR + "ASAS.Txl"]
_MUTATION_ASAV = ['ASAV', True, True, True, _TXL_DIR + "ASAV.Txl"]
_MUTATION_ASM  = ['ASM', True, True, True, _TXL_DIR + "ASM.Txl"]
_MUTATION_CSO  = ['CSO', True, False, True, _TXL_DIR + "CSO.Txl"]
_MUTATION_EXSB = ['EXSB', True, True, True, _TXL_DIR + "EXSB.Txl"]
_MUTATION_EXSA = ['EXSA', True, True, True, _TXL_DIR + "EXSA.Txl"]
_MUTATION_RSAS = ['RSAS', True, True, True, _TXL_DIR + "RSAS.Txl"]
_MUTATION_RSAV = ['RSAV', True, True, True, _TXL_DIR + "RSAV.Txl"]
_MUTATION_RSB  = ['RSB', True, True, True, _TXL_DIR + "RSB.Txl"]
_MUTATION_RSM  = ['RSM', True, True, True, _TXL_DIR + "RSM.Txl"]
_MUTATION_SHSA = ['SHSA', True, True, True, _TXL_DIR + "SHSA.Txl"]
_MUTATION_SHSB = ['SHSB', True, True, True, _TXL_DIR + "SHSB.Txl"]
_FUNCTIONAL_MUTATIONS = [_MUTATION_ASAS, _MUTATION_ASAV, _MUTATION_ASM,
                         _MUTATION_CSO, _MUTATION_EXSB, _MUTATION_EXSA,
                         _MUTATION_RSAS, _MUTATION_RSAV, _MUTATION_RSB,
                         _MUTATION_RSM]
_NONFUNCTIONAL_MUTATIONS = [_MUTATION_RSAS, _MUTATION_RSAV, _MUTATION_RSB,
                            _MUTATION_RSM, _MUTATION_SHSA, _MUTATION_SHSB]

# Evolution variables
_EVOLUTION_GENERATIONS = 3
_EVOLUTION_POPULATION = 3
_EVOLUTION_REPLACE_LOWEST_PERCENT = 0
_EVOLUTION_REPLACE_AFTER_TURNS = 0
_EVOLUTION_REPLACE_WITH_BEST_PERCENT = 0

# Fitness evaluation variables
_SUCCESS_WEIGHT = 100
_TIMEOUT_WEIGHT = 50

_GENERATIONAL_IMPROVEMENT_WINDOW = 10
_AVG_FITNESS_UP = 50
_BEST_FITNESS_UP = 100

# Create logger
logger = logging.getLogger('arc')
handler = logging.StreamHandler()

if _VERBOSE:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(relativeCreated)d %(levelname)s [%(module)s.%(funcName)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
