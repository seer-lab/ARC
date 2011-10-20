"""This module will start the evolution process for ARC."""

from __future__ import division
from random import randint
from random import uniform
import sys
from individual import Individual

sys.path.append("..")  # To allow importing parent directory module
import config
from _contest import tester
from _txl import txl_operator

def evaluate(individual):
  """Perform the actual evaluation of said individual using ConTest testing.

  The fitness is determined using functional and non-functional fitness values.
  """

  print "Evaluating individual {} on generation {}".format(individual.id,
                                                        individual.generation)

  # Move the local project to the target's source
  txl_operator.move_local_project_to_original(individual.generation,
                                              individual.id)

  # Compile target's source
  txl_operator.compile_project()

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
  individual.lastSuccessRate = success_rate
  individual.lastTimeoutRate = timeout_rate
  individual.lastDataraceRate = datarace_rate
  individual.lastDeadlockRate = deadlock_rate
  individual.lastErrorRate = error_rate

  contest.clear_results()


def feedback_selection(individual):
  """Given the individual this function will find the next operator to apply.

  The selection of the next operator takes into account the individual's last
  test execution as feedback. The feedback is used to heuristically guide what
  mutation operator to apply next.
  """

  opType = 'race'
  candatateChoices = []

  # Acquire a random value that is less then the total of the bug rates
  totalBugRate = individual.lastDeadlockRate + individual.lastDataraceRate
  choice = uniform(0, totalBugRate)

  # Determine which it bug type to use
  if individual.lastDataraceRate > individual.lastDeadlockRate:
    # If choice falls past the datarace range then type is lock
    if choice >= individual.lastDataraceRate:
      opType = 'lock'
  else:
    # If choice falls under the deadlock range then type is lock
    if choice <= individual.lastDeadlockRate:
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


def mutation(individual):
  """A mutator for the individual using single mutation with feedback."""

  print "Mutating individual {} on generation {}".format(individual.id, 
                                                         individual.generation)

  # Repopulate the individual's genome with new possible mutation locations
  individual.repopulateGenome()

  # Pick a mutation operator to apply
  index = -1
  limit = 100
  while index is -1 and limit is not 0:

    # Acquire operator and the index of that operator
    selectedOperator = feedback_selection(individual)
    operatorIndex = -1
    for mutationOp in config._MUTATIONS:
      if mutationOp[1]:
        operatorIndex += 1
        if mutationOp is selectedOperator:
          break;

    # Check if there are possible mutant instances
    if len(individual.genome[operatorIndex]) == 0:
      # print "Cannot mutate using this operator, trying again"
      limit -= 1;  
    else:
      index = randint(0, len(individual.genome[operatorIndex]) - 1)

  # If there 
  if limit is not 0:
    # Update individual
    individual.lastOperator = selectedOperator
    individual.appliedOperators.append(selectedOperator[0])
    individual.genome[operatorIndex][index] = 1

    # Create local project then apply mutation
    txl_operator.create_local_project(individual.generation, 
                                      individual.id, False)
    txl_operator.move_mutant_to_local_project(individual.generation,
                                              individual.id, 
                                              selectedOperator[0], index + 1)
  else:
    txl_operator.create_local_project(individual.generation, individual.id, 
                                      True)


def initialize():
  """Initialize the population of individuals with and id and values."""
  
  # The number of enabled mutation operators
  mutationOperators = 0
  for operator in config._MUTATIONS:
    if operator[1]:
      mutationOperators += 1

  # Create and initialize the population of individuals
  population = []
  for i in xrange(1, config._EVOLUTION_POPULATION + 1):
    print "Creating individual {}".format(i)
    individual = Individual(mutationOperators, i)
    population.append(individual)

  return population

def start():
  """The actual starting process for ARC's evolutionary process."""

  # Backup project
  txl_operator.backup_project()

  # Initialize the population
  population = initialize()

  # Evolve the population for the required generations
  generation = 0
  done = False
  while not done:

    generation += 1
    # Mutate each individual
    for individual in population:
      individual.generation = generation
      mutation(individual)

    # Evaluate each individual
    for individual in population:
      evaluate(individual)

    # Check for terminating conditions
    for individual in population:
      if individual.lastSuccessRate == 1:
        print "Found best individual", individual.id
        done = True
        break
      if generation == config._EVOLUTION_GENERATIONS:
        print "Exhausted all generations"
        done = True
        break


  print population

  # Restore project to original
  txl_operator.restore_project()
