"""This module will start the evolution process for ARC.

This process makes heavy use of the Pyevole 0.6rc1 for the evolutionary part.
A new genome is used along with ConTest to evolve concurrent software into a
version that has a better functional and non-functional fitness.
"""

from __future__ import division
from pyevolve import GSimpleGA
from pyevolve import DBAdapters
from pyevolve import Consts
from random import randint
from random import uniform
import sys
from G2DVariableBinaryString import G2DVariableBinaryString

sys.path.append("..")  # To allow importing parent directory module
import config
from _contest import tester

def evaluation(genome):
  """Perform the actual evaluation of said individual using ConTest testing.

  The fitness is determined using functional and non-functional fitness values.
  """

  fitness = 0.0

  print "Evaluating individual {} on generation {}".format(genome.id, 
                                                           genome.generation)

  # ConTest testing
  contest = tester.Tester()
  contest.begin_testing()

  success_rate = contest.get_successes() / config._CONTEST_RUNS
  timeout_rate = contest.get_timeouts() / config._CONTEST_RUNS
  datarace_rate = contest.get_dataraces() / config._CONTEST_RUNS
  deadlock_rate = contest.get_deadlocks() / config._CONTEST_RUNS
  error_rate = contest.get_errors() / config._CONTEST_RUNS

  # TODO Functional fitness
  # TODO Non-Functional fitness

  # Store achieve rates into genome
  genome.lastSuccessRate = success_rate
  genome.lastTimeoutRate = timeout_rate
  genome.lastDataraceRate = datarace_rate
  genome.lastDeadlockRate = deadlock_rate
  genome.lastErrorRate = error_rate

  contest.clear_results()

  return success_rate


def G2DVariableBinaryStringInitializator(genome, **args):
  """An initializer for the 2D variable binary string genome."""

  # Perform the population
  genome.repopulateGenome()


def feedback_selection(genome):
  """Given the genome this function will find the next operator to apply.

  The selection of the next operator takes into account the individual's last
  test execution as feedback. The feedback is used to heuristically guide what
  mutation operator to apply next.
  """

  opType = 'race'
  candatateChoices = []

  # Acquire a random value that is less then the total of the bug rates
  totalBugRate = genome.lastDeadlockRate + genome.lastDataraceRate
  choice = uniform(0, totalBugRate)

  # Determine which it bug type to use
  if genome.lastDataraceRate > genome.lastDeadlockRate:
    # If choice falls past the datarace range then type is lock
    if choice >= genome.lastDataraceRate:
      opType = 'lock'
  else:
    # If choice falls under the deadlock range then type is lock
    if choice <= genome.lastDeadlockRate:
      opType = 'lock'

  # Select the appropriate operator based on enable/type/functional
  if opType is 'race':
    for operator in config._MUTATIONS:
      if operator[1] and operator[2] and operator[4]:
        candatateChoices.append(operator)
  elif opType is 'lock':
    for operator in config._MUTATIONS:
      if operator[1] and operator[3] and operator[4]:
        candatateChoices.append(operator)

  selectedOperator = candatateChoices[randint(0, len(candatateChoices) - 1)]

  return selectedOperator


def G2DVariableBinaryStringSingleMutation(genome, **args):
  """A mutator for the 2D variable binary string genome using single mutation.

  This mutator will apply a single mutation in a random location within the
  genome.
  """

  # Repopulate the genome with new possible mutation locations
  genome.repopulateGenome()

  # Pick a mutation operator to apply
  index = -1
  while index is -1:

    # Acquire operator
    selectedOperator = feedback_selection(genome)
    operatorIndex = config._MUTATIONS.index(selectedOperator)

    # Check if there are possible mutant instances
    if len(genome.genomeString[operatorIndex]) == 0:
      print "Cannot mutate using this operator, trying again"
    else:
      index = randint(0, len(genome.genomeString[operatorIndex]) - 1)

  # Update genome
  genome.lastOperator = selectedOperator
  genome.appliedOperators.append(selectedOperator[0])
  genome.genomeString[operatorIndex][index] = 1

  # TODO Apply TXL mutation

  return 1


def start():
  """The actual starting process for ARC's evolutionary process.

  Basic configurations for Pyevolve are set here.
  """

  Consts.CDefGACrossoverRate = 0.0  # Enforce no crossover
  Consts.CDefGAMutationRate = 1.0  # Enforce 100% mutations

  Consts.CDefGAGenerations = config._PYEVOLVE_GENERATIONS
  Consts.CDefGAPopulationSize = config._PYEVOLVE_POPULATION
  Consts.CDefGAElitismReplacement = config._PYEVOLVE_ELITISM

  # The number of enabled mutation operators
  mutationOperators = 0
  for operator in config._MUTATIONS:
    if operator[1]:
      mutationOperators += 1

  genome = G2DVariableBinaryString(mutationOperators)
  genome.evaluator.set(evaluation)
  genome.initializator.set(G2DVariableBinaryStringInitializator)
  genome.mutator.set(G2DVariableBinaryStringSingleMutation)

  ga = GSimpleGA.GSimpleGA(genome, config._PYEVOLVE_SEED)

  # Attach sqlite DB to Pyevolve if enabled within config.py
  if config._PYEVOLVE_SQLITE:
    sqlite = DBAdapters.DBSQLite(identify=config._PYEVOLVE_EXECUTION_ID)
    ga.setDBAdapter(sqlite)

  # Attach VPython statistics to Pyevolve if enabled within config.py
  if config._PYEVOLVE_VPYTHON:
    vpython = DBAdapters.DBVPythonGraph(identify=config._PYEVOLVE_EXECUTION_ID,
                                      frequency=config._PYEVOLVE_VPYTHON_FREQ)
    ga.setDBAdapter(vpython)

  ga.evolve(freq_stats=config._PYEVOLVE_FREQ_UPDATE)
  print ga.bestIndividual()
