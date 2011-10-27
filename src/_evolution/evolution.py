"""This module will start the evolution process for ARC."""

from __future__ import division
from random import randint
from random import uniform
import sys
from individual import Individual
import math
import traceback
import copy

sys.path.append("..")  # To allow importing parent directory module
import config
from _contest import tester
from _txl import txl_operator


def evaluate(individual, functionalPhase, worstScore):
  """Perform the actual evaluation of said individual using ConTest testing.

  The fitness is determined using functional and non-functional fitness values.
  """

  print "Evaluating individual {} on generation {}".format(individual.id,
                                                        individual.generation)

  # ConTest testing
  contest = tester.Tester()

  if functionalPhase:
    contest.begin_testing(functionalPhase)
    success_rate = contest.successes / config._CONTEST_RUNS
    timeout_rate = contest.timeouts / config._CONTEST_RUNS
    datarace_rate = contest.dataraces / config._CONTEST_RUNS
    deadlock_rate = contest.deadlocks / config._CONTEST_RUNS
    error_rate = contest.errors / config._CONTEST_RUNS

    individual.score.append((contest.successes * \
                                  config._SUCCESS_WEIGHT) + \
                                  (contest.timeouts * \
                                  config._TIMEOUT_WEIGHT))

    # Store achieve rates into genome
    individual.successRate.append(success_rate)
    individual.timeoutRate.append(timeout_rate)
    individual.dataraceRate.append(datarace_rate)
    individual.deadlockRate.append(deadlock_rate)
    individual.errorRate.append(error_rate)
  else:
    # Ensure functionality is still there
    if contest.begin_testing(functionalPhase, True):  
      print "[INFO] Functionality was unchanged"
      contest.clear_results()
      contest.begin_testing(functionalPhase)  # Measure performance
      individual.realTime.append(float(sum(contest.realTime)) / len(contest.realTime))
      individual.wallTime.append(float(sum(contest.wallTime)) / len(contest.wallTime))
      individual.voluntarySwitches.append(float(sum(contest.voluntarySwitches)) / len(contest.voluntarySwitches))
      individual.involuntarySwitches.append(float(sum(contest.involuntarySwitches)) / len(contest.involuntarySwitches))
      individual.percentCPU.append(float(sum(contest.percentCPU)) / len(contest.percentCPU))

      # TODO Need proper equation
      individual.score.append(worstScore / (contest.realTime[-1] + contest.wallTime[-1] + contest.voluntarySwitches[-1] + contest.involuntarySwitches[-1] + contest.percentCPU[-1]))
    else:
      print "[INFO] Functionality was broken by change"
      individual.score.append(-1)

      # Need to ensure that the project from the last generation is used again
      if individual.generation-1 is 0:
        # Restarting the mutant if at 0th generation
        txl_operator.create_local_project(individual.generation, individual.id, True)
      else:
        txl_operator.copy_local_project_a_to_b(individual.generation-1,
                                              individual.id,
                                              individual.generation,
                                              individual.id)
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
  totalBugRate = (individual.deadlockRate[-1] + individual.dataraceRate[-1])
  choice = uniform(0, totalBugRate)

  # Determine which it bug type to use
  if (individual.dataraceRate[-1] > individual.deadlockRate[-1]):
    # If choice falls past the datarace range then type is lock
    if choice >= individual.dataraceRate[-1]:
      opType = 'lock'
  else:
    # If choice falls under the deadlock range then type is lock
    if choice <= individual.deadlockRate[-1]:
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


def initialize(functionalPhase, bestIndividual=None):
  """Initialize the population of individuals."""

  # The number of enabled mutation operators
  mutationOperators = 0
  if functionalPhase:
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


def get_worst_non_functional_score(individual):

  # This individual's best generation should be the last one compiled
  contest = tester.Tester()
  contest.begin_testing(False, False, 20)  # Measure performance

  # TODO Still need appropriate equation
  worstScore = (max(contest.realTime) + max(contest.wallTime) + max(contest.voluntarySwitches) + max(contest.involuntarySwitches) + max(contest.percentCPU))
  contest.clear_results()
  return worstScore


def start():
  """The actual starting process for ARC's evolutionary process."""

  # Backup project
  txl_operator.backup_project()

  functionalPhase = True

  try:
    # Initialize the population
    population = initialize(functionalPhase)

    # Evolve the population to find the best functional individual
    print "Evolving population towards functional correctness"
    bestFunctional = evolve(population, functionalPhase, 0)

    # Check to see if bestFunctional is valid for progress to next phase
    if bestFunctional.successRate[-1] == 1.0:

      functionalPhase = False
      bestFunctional.switchGeneration = bestFunctional.generation
      print population

      # Reinitialize the population with the best functional individual
      print "Repopulating with best individual {} at generation {}".format(
                                  bestFunctional.id, bestFunctional.generation)
      population = initialize(functionalPhase, bestFunctional)
      for individual in population:
        if individual.id is not bestFunctional.id:
          txl_operator.copy_local_project_a_to_b(bestFunctional.generation,
                                              bestFunctional.id,
                                              bestFunctional.generation,
                                              individual.id)
    
      # Acquire worst possible non-functional score for best individual
      worstScore = get_worst_non_functional_score(bestFunctional)

      # Evolve the population to find the best non-functional individual
      print "Evolving population towards non-functional performance"
      bestNonFunctional = evolve(population, functionalPhase,
                                 bestFunctional.generation, worstScore)
      print population
      print "\nBest Individual\n"
      print bestNonFunctional
    else:
      print "[INFO] No individual was found that functions correctly"

    # Restore project to original
  except:
    print "Unexpected error:\n", traceback.print_exc(file=sys.stdout)
    txl_operator.restore_project()
  else:
    txl_operator.restore_project()


def evolve(population, functionalPhase, generation=0, worstScore=0):

  # For each generation, record the average and best fitness
  averageFitness = []
  bestFitness = []  # (score, id)

  # Accounts for the possibility of spilling over the limit in the second phase
  if generation is 0:
    generationLimit = config._EVOLUTION_GENERATIONS
  else:
    generationLimit = config._EVOLUTION_GENERATIONS + generation

  while True:
    generation += 1

    # Mutate each individual
    for individual in population:
      individual.generation = generation
      mutation(individual, functionalPhase)

    # Evaluate each individual
    for individual in population:
      evaluate(individual, functionalPhase, worstScore)

    # Calculate average and best fitness
    highestSoFar = -1
    highestID = -1
    runningSum = 0
    for individual in population:
      runningSum += individual.score[-1]
      if individual.score[-1] > highestSoFar:
        highestSoFar = individual.score[-1]
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
        if (math.fabs(bestFitness[i][0] - bestFitness[i - 1][0]) >
            config._BEST_FITNESS_UP):
          maxFitTest = True

      if not avgFitTest:
        print ("Average fitness hasn't increased by {} in {} generations".
              format(config._AVG_FITNESS_UP,
              config._GENERATIONAL_IMPROVEMENT_WINDOW))
        return get_best_individual(population, bestFitness)
      if not maxFitTest:
        print ("Maximum fitness hasn't increased by {} in {} generations".
              format(config._BEST_FITNESS_UP,
              config._GENERATIONAL_IMPROVEMENT_WINDOW))
        return get_best_individual(population, bestFitness)

    # Check for terminating conditions
    for individual in population:
      if functionalPhase and individual.successRate[-1] == 1:
        print "Found potential best individual", individual.id
        if tester.Tester().begin_testing(True, True, config._CONTEST_RUNS * 2):
          print "Found best individual", individual.id
          return get_best_individual(population, bestFitness)
        else:
          print "Potential best individual still has errors"
      if generation == generationLimit:
        print "Exhausted all generations"
        return get_best_individual(population, bestFitness)

    # print "[INFO] Calling replace lowest"
    replace_lowest(population, functionalPhase)


def get_best_individual(population, bestFitness):
  
  # Acquire the pair with the highest fitness
  bestID = -1
  highestScore = -1
  for score, id_ in bestFitness:
    if score >= highestScore:
      bestID = id_
      highestScore = score

  for individual in population:
    if individual.id == bestID:
      return individual


def replace_lowest(population, functionalPhase):
  """Replace underperforming members with high-performing members or the
  original buggy program.
  """

  # Acquire set of operators to use
  if functionalPhase:
    mutationOperators = config._FUNCTIONAL_MUTATIONS
  else:
    mutationOperators = config._NONFUNCTIONAL_MUTATIONS

  # Determine the number of members to look at for underperforming
  numUnder = int((config._EVOLUTION_POPULATION * config._EVOLUTION_REPLACE_LOWEST_PERCENT)/100)
  if numUnder < 1:
    numUnder = 1

  # Sort population by fitness
  sortedMembers = sorted(population, key=lambda individual: individual.score[-1])

  # The first numUnder members have their turnsUnderperforming variable incremented
  # as they are the worst performing
  for i in xrange(0, numUnder):
    sortedMembers[i].turnsUnderperforming += 1
 
  # Replace or restart members who have underperformed for too long
  for i in xrange(0, numUnder):
    if (sortedMembers[i].turnsUnderperforming < 
        config._EVOLUTION_REPLACE_AFTER_TURNS):
      continue

    randomNum = randint(1, 100)

    # Case 1: Replace an underperforming member with a fit member
    if randomNum <= config._EVOLUTION_REPLACE_WITH_BEST_PERCENT:
      # Take a member from the top 10% of the population
      highMember =  randint(int(config._EVOLUTION_POPULATION * 0.9),
                        config._EVOLUTION_POPULATION) - 1
      # Keep the id of the original member
      lowId = sortedMembers[i].id
      # print "[INFO] Replacing ID: {} with {}".format(lowId, sortedMembers[highMember].id)
      sortedMembers[i] = copy.deepcopy(sortedMembers[highMember])
      sortedMembers[i].id = lowId

      txl_operator.copy_local_project_a_to_b(sortedMembers[i].generation,
                                             sortedMembers[highMember].id,
                                             sortedMembers[i].generation,
                                             sortedMembers[i].id)

    # Case 2: Restart the member
    # Code copy-pasted from initialize()
    else:
      # The number of enabled mutation operators
      numOfOperators = 0
      for operator in mutationOperators:
        if operator[1]:
          numOfOperators += 1

      # print "[INFO] Restarting underperforming member ID: {}".format(sortedMembers[i].id)
      # TODO We don't know in the timeline, when an individual is restarted
      # If in functional restart off of local, otherwise off of best individual
      if functionalPhase:
        # Reset the local project
        txl_operator.create_local_project(sortedMembers[i].generation, sortedMembers[i].id, True)
      else:
        # Reset to best individual
        print "Reseting Ind{}.{} back to Ind{}.{}".format(sortedMembers[i].id, sortedMembers[i].generation, sortedMembers[i].id, sortedMembers[i].switchGeneration )
        txl_operator.copy_local_project_a_to_b(sortedMembers[i].switchGeneration,
                                              sortedMembers[i].id,
                                              sortedMembers[i].generation,
                                              sortedMembers[i].id)

    # Resort the population by ID and reassign it to the original variable
    population = sorted(sortedMembers, key=lambda individual: individual.id)