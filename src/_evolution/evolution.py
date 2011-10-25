"""This module will start the evolution process for ARC."""

from __future__ import division
from random import randint
from random import uniform
import sys
from individual import Individual
import math
import traceback

sys.path.append("..")  # To allow importing parent directory module
import config
from _contest import tester
from _txl import txl_operator

# For each generation, record the average and best fitness
averageFitness = []
bestFitness = []

def evaluate(individual):
  """Perform the actual evaluation of said individual using ConTest testing.

  The fitness is determined using functional and non-functional fitness values.
  """

  print "Evaluating individual {} on generation {}".format(individual.id,
                                                        individual.generation)

  # ConTest testing
  contest = tester.Tester()
  contest.begin_testing()

  success_rate = contest.get_successes() / config._CONTEST_RUNS
  timeout_rate = contest.get_timeouts() / config._CONTEST_RUNS
  datarace_rate = contest.get_dataraces() / config._CONTEST_RUNS
  deadlock_rate = contest.get_deadlocks() / config._CONTEST_RUNS
  error_rate = contest.get_errors() / config._CONTEST_RUNS

  individual.functionalScore.append((contest.get_successes() * \
                                config._SUCCESS_WEIGHT) + \
                                (contest.get_timeouts() * \
                                config._TIMEOUT_WEIGHT))

  # TODO (Less time and CPU == greater score)
  individual.nonFunctionalScore.append(randint(0,100))

  # Store achieve rates into genome
  individual.successRate.append(success_rate)
  individual.timeoutRate.append(timeout_rate)
  individual.dataraceRate.append(datarace_rate)
  individual.deadlockRate.append(deadlock_rate)
  individual.errorRate.append(error_rate)

  contest.clear_results()


def feedback_selection(individual, functionalPhase):
  """Given the individual this function will find the next operator to apply.

  The selection of the next operator takes into account the individual's last
  test execution as feedback. The feedback is used to heuristically guide what
  mutation operator to apply next.
  """

  # Acquire set of operators to use
  if functionalPhase:
    mutationOperators = config._FUNCTIONAL_MUTATIONS
  else:
    mutationOperators = config._NONFUNCTIONAL_MUTATIONS
    
  opType = 'race'
  # candidateChoices is a list of config._MUTATIONS
  candatateChoices = []

  # Acquire a random value that is less then the total of the bug rates
  totalBugRate = (individual.deadlockRate[len(individual.deadlockRate) - 1] 
                 + individual.dataraceRate[len(individual.dataraceRate) - 1])
  choice = uniform(0, totalBugRate)

  # Determine which it bug type to use
  if (individual.dataraceRate[len(individual.dataraceRate) - 1] > 
     individual.deadlockRate[len(individual.deadlockRate) - 1]):
    # If choice falls past the datarace range then type is lock
    if choice >= individual.dataraceRate[len(individual.dataraceRate) - 1]:
      opType = 'lock'
  else:
    # If choice falls under the deadlock range then type is lock
    if choice <= individual.deadlockRate[len(individual.deadlockRate) - 1]:
      opType = 'lock'

  # Select the appropriate operator based on enable/type/functional
  if opType is 'race':
    for operator in mutationOperators:
      if operator[1] and operator[2]:
        candatateChoices.append(operator)
  elif opType is 'lock':
    for operator in mutationOperators:
      if operator[1] and operator[3]:
        candatateChoices.append(operator)

  selectedOperator = candatateChoices[randint(0, len(candatateChoices) - 1)]

  return selectedOperator


def mutation(individual, functionalPhase):
  """A mutator for the individual using single mutation with feedback."""

  print "Mutating individual {} on generation {}".format(individual.id,
                                                         individual.generation)

  # Acquire set of operators to use
  if functionalPhase:
    mutationOperators = config._FUNCTIONAL_MUTATIONS
  else:
    mutationOperators = config._NONFUNCTIONAL_MUTATIONS

  # Repopulate the individual's genome with new possible mutation locations
  individual.repopulateGenome(functionalPhase)

  # Definite check to see if ANY mutants exists for an individual
  checkInd = -1
  mutantsExist = False
  for mutationOp in mutationOperators:
    if mutationOp[1]:
      checkInd += 1
      if len(individual.genome[checkInd]) != 0:
        mutantsExist = True

  # IF no mutants exist, reset and return
  if not mutantsExist:
    txl_operator.create_local_project(individual.generation, individual.id,
                                      True)
    return

  # Pick a mutation operator to apply
  limit = 100  # Number of attempts to find a valid mutation
  successfulCompile = False
  
  # Keep trying to find a successful mutant within the retry limits
  while limit is not 0 and not successfulCompile:

    # Acquire operator, one of config._MUTATIONS
    selectedOperator = feedback_selection(individual, functionalPhase)

    # Find the integer index of the selectedOperator
    operatorIndex = -1
    for mutationOp in mutationOperators:
      if mutationOp[1]:
        operatorIndex += 1
        if mutationOp is selectedOperator:
          break

    # Check if there are instances of the selected mutationOp
    if len(individual.genome[operatorIndex]) == 0:
      # print "Cannot mutate using this operator, trying again"
      limit -= 1
    else:

      # Represents the index of the mutation instance to work on
      index = randint(0, len(individual.genome[operatorIndex]) - 1)

      # Create local project then apply mutation
      # TODO: Doing this for every compile attempt is inefficient.
      #       Ideally we should create_local_project only once
      txl_operator.create_local_project(individual.generation, 
                                        individual.id, False)
      txl_operator.move_mutant_to_local_project(individual.generation,
                                                individual.id, 
                                                selectedOperator[0], index + 1)

      # Move the local project to the target's source
      txl_operator.move_local_project_to_original(individual.generation,
                                                  individual.id)

      # Compile target's source
      if txl_operator.compile_project():
        successfulCompile = True

        # Update individual
        individual.lastOperator = selectedOperator
        individual.appliedOperators.append(selectedOperator[0])

        # Switch the appropriate bit to 1 to record which instance is used
        individual.genome[operatorIndex][index] = 1
      else:
        limit -= 1
        print "[ERROR] Compiling failed, retrying another mutation"

  if not successfulCompile:
    # If not mutant was found we reset the project to it's pristine state
    # and start over
    txl_operator.create_local_project(individual.generation, individual.id, 
                                      True)


def initialize(bestIndividual=None):
  """Initialize the population of individuals."""

  # The number of enabled mutation operators
  mutationOperators = 0
  if bestIndividual is None:
    for operator in config._FUNCTIONAL_MUTATIONS:
      if operator[1]:
        mutationOperators += 1
  else:
    for operator in config._NONFUNCTIONAL_MUTATIONS:
      if operator[1]:
        mutationOperators += 1

  # Create and initialize the population of individuals
  population = []
  for i in xrange(1, config._EVOLUTION_POPULATION + 1):

    if bestIndividual is None:
      print "Creating individual {}".format(i)
      individual = Individual(mutationOperators, i)
    else:
      print "Cloning best functional individual {} into individual {}".format(
                                                          bestIndividual.id, i)
      individual = bestIndividual.clone(mutationOperators, i)
    population.append(individual)

  return population

def start():
  """The actual starting process for ARC's evolutionary process."""

  # Backup project
  txl_operator.backup_project()

  try:
    # Initialize the population
    population = initialize()

    # Evolve the population to find the best functional individual
    if config._EVOLUTION_FUNCTIONAL_PHASE:
      print "Evolving population towards functional correctness"
      bestFunctional = evolve(population, True)
      print population

      # Reinitialize the population with the best functional individual
      print "Repopulating population with best individual ({})".format(
                                                            bestFunctional.id)
      population = initialize(bestFunctional)

    print "Evolving population towards non-functional performance"
    # Evolve the population to find the best non-functional individual
    bestNonFunctional = evolve(population, False)
    print population

    # Restore project to original
  except:
    print "Unexpected error:\n", traceback.print_exc(file=sys.stdout)
    txl_operator.restore_project()
  else:
    txl_operator.restore_project()


def evolve(population, functionalPhase):
  generation = 0
  while True:
    generation += 1

    # Mutate each individual
    for individual in population:
      individual.generation = generation
      mutation(individual, functionalPhase)

    # Evaluate each individual
    for individual in population:
      evaluate(individual)

    # Calculate average and best fitness
    highestSoFar = -1
    highestID = -1
    runningSum = 0
    for individual in population:
      runningSum += individual.getFitness(functionalPhase)
      if individual.getFitness(functionalPhase) > highestSoFar:
        highestSoFar = individual.getFitness(functionalPhase)
        highestID = individual.id

    averageFitness.append(runningSum / config._EVOLUTION_POPULATION)
    bestFitness.append((highestSoFar, highestID))

    # Alternate termination criteria
    # - If average improvement in fitness is less than
    # _MINIMAL_FITNESS_IMPROVEMENT over
    # _GENERATIONAL_IMPROVEMENT_WINDOW
    avgFitTest = False
    maxFitTest = False
    if generation >= config._GENERATIONAL_IMPROVEMENT_WINDOW + 1:
      for i in xrange(generation - 
          config._GENERATIONAL_IMPROVEMENT_WINDOW + 1, generation):
        if (math.fabs(averageFitness[i] - averageFitness[i - 1]) >
           config._AVG_FITNESS_UP):
          avgFitTest = True 
        if (math.abs(bestFitness[i] - bestFitness[i - 1]) >
           config._BEST_FITNESS_UP):
          maxFitTest = True 

      if not avgFitTest:
        print ("Average fitness hasn't increased by {} in {} generations".
              format(config._AVG_FITNESS_UP,
              config._GENERATIONAL_IMPROVEMENT_WINDOW))
        return get_best_individual(population, bestFitness[-1][1])
      if not maxFitTest:
        print ("Maximum fitness hasn't increased by {} in {} generations".
              format(config._BEST_FITNESS_UP,
              config._GENERATIONAL_IMPROVEMENT_WINDOW))
        return get_best_individual(population, bestFitness[-1][1])

    # Check for terminating conditions
    for individual in population:
      if functionalPhase and individual.successRate[-1] == 1:
        print "Found best individual", individual.id
        return get_best_individual(population, bestFitness[-1][1])
      if generation == config._EVOLUTION_GENERATIONS:
        print "Exhausted all generations"
        return get_best_individual(population, bestFitness[-1][1])


def get_best_individual(population, bestID):
  for individual in population:
    if individual.id == bestID:
      return individual