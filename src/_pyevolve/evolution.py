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


def G2DVariableBinaryStringSingleMutation(genome, **args):
  """A mutator for the 2D variable binary string genome using single mutation.

  This mutator will apply a single mutation in a random location within the
  genome.
  """

  # Repopulate the genome with new possible mutation locations
  genome.repopulateGenome()

  # Pick a mutation operator to apply
  op = randint(0, genome.height - 1)  # TODO use last execution's feedback
  genome.lastOperator = randint(0, 100)
  genome.appliedOperators = randint(0, 100)

  # Flip a random bit for the selected mutation operator
  if len(genome.genomeString[op]) == 0:
    print "No mutation instances for this operator, skipping"
  else:
    genome.genomeString[op][randint(0, len(genome.genomeString[op]) - 1)] = 1

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
  for operator in config._MUTATIONS_ENABLE:
    if config._MUTATIONS_ENABLE[operator]:
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
