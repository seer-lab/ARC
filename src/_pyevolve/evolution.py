"""This module will start the evolution process for ARC.

This process makes heavy use of the Pyevole 0.6rc1 for the evolutionary part.
A new genome is used along with ConTest to evolve concurrent software into a
version that has a better functional and non-functional fitness.
"""

from __future__ import division
from random import randint
from random import uniform
import sys
from G2DVariableBinaryString import G2DVariableBinaryString

sys.path.append("..")  # To allow importing parent directory module
import config
from _contest import tester

def evaluate(genome):
  """Perform the actual evaluation of said individual using ConTest testing.

  The fitness is determined using functional and non-functional fitness values.
  """

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


def mutation(genome, **args):
  """A mutator for the 2D variable binary string genome using single mutation.

  This mutator will apply a single mutation in a random location within the
  genome.
  """

  print "Mutating individual {} on generation {}".format(genome.id, 
                                                         genome.generation)

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

def initialize():

  # The number of enabled mutation operators
  mutationOperators = 0
  for operator in config._MUTATIONS:
    if operator[1]:
      mutationOperators += 1

  # Create and initialize the population of individuals
  population = []
  for i in xrange(1, config._PYEVOLVE_POPULATION + 1):
    print "Creating individual {}".format(i)
    individual = G2DVariableBinaryString(mutationOperators, i)
    population.append(individual)

  return population

def start():
  """The actual starting process for ARC's evolutionary process.

  Basic configurations for Pyevolve are set here.
  """

  # Initialize the population
  population = initialize()

  # Evolve the population for the required generations
  generation = 1
  done = False
  while not done:

    # Evaluate each individual
    for individual in population:
      evaluate(individual)

    # Mutate each individual
    for individual in population:
      mutation(individual)
      individual.generation += 1

    # Check for terminating conditions
    for individual in population:
      if individual.lastSuccessRate == 1:
        print "Found best individual", individual.id
        done = True
        break
      if generation == config._PYEVOLVE_GENERATIONS:
        print "Exhausted all generations"
        done = True
        break

    generation += 1

  print population
