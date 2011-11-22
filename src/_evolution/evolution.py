"""This module will start the evolution process for ARC."""

from __future__ import division
from random import randint
from random import uniform
import sys
from individual import Individual
import math
import traceback
import copy
from collections import Counter

sys.path.append("..")  # To allow importing parent directory module
import config
from _contest import tester
from _txl import txl_operator

import logging
logger = logging.getLogger('arc')


def evaluate(individual, functionalPhase, worstScore):
  """Perform the actual evaluation of said individual using ConTest testing.

  The fitness is determined using functional and non-functional fitness values.
  """

  logger.info("Evaluating individual {} on generation {}".format(individual.id,
                                                        individual.generation))

  # ConTest testing
  contest = tester.Tester()

  if functionalPhase:
    contest.begin_testing(functionalPhase)

    individual.score.append((contest.successes * \
                                  config._SUCCESS_WEIGHT) + \
                                  (contest.timeouts * \
                                  config._TIMEOUT_WEIGHT))

    # Store results into genome
    individual.successes.append(contest.successes)
    individual.timeouts.append(contest.timeouts)
    individual.dataraces.append(contest.dataraces)
    individual.deadlocks.append(contest.deadlocks)
    individual.errors.append(contest.errors)
  else:
    # Ensure functionality is still there
    if contest.begin_testing(functionalPhase, True):
      logger.debug("Functionality was unchanged")
      contest.clear_results()
      contest.begin_testing(functionalPhase)  # Measure performance
      individual.realTime.append(float(sum(contest.realTime)) / len(contest.realTime))
      individual.wallTime.append(float(sum(contest.wallTime)) / len(contest.wallTime))
      individual.voluntarySwitches.append(float(sum(contest.voluntarySwitches)) / len(contest.voluntarySwitches))
      individual.involuntarySwitches.append(float(sum(contest.involuntarySwitches)) / len(contest.involuntarySwitches))
      individual.percentCPU.append(float(sum(contest.percentCPU)) / len(contest.percentCPU))

      # Nonfunctional fitness
      individual.score.append(get_average_non_functional_score(individual))
    else:
      logger.debug("Functionality was broken by change")
      individual.score.append(-1)

      # Need to ensure that the project from the last generation is used again
      if individual.generation-1 is 0:
        # Restarting the mutant if at 0th generation
        logger.debug("Resetting back to pristine")
        txl_operator.create_local_project(individual.generation, individual.id, True)
      else:
        logger.debug("Resetting back to an earlier generation")
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

  Returns one of ASAV, ...
  """

  # Acquire set of operators to use
  if functionalPhase:
    mutationOperators = config._FUNCTIONAL_MUTATIONS
  else:
    mutationOperators = config._NONFUNCTIONAL_MUTATIONS

  opType = 'race'
  # candidateChoices is a list of config._MUTATIONS
  candatateChoices = []

  # Acquire the deadlock and datarace rates
  if len(individual.deadlocks) == 0:
    deadlockRate = .5
    dataraceRate = .5
  else:
    deadlockRate = individual.deadlocks[-1] / config._CONTEST_RUNS
    dataraceRate = individual.dataraces[-1] / config._CONTEST_RUNS

  # Acquire a random value that is less then the total of the bug rates
  totalBugRate = (deadlockRate + dataraceRate)
  choice = uniform(0, totalBugRate)

  # Determine which it bug type to use
  if (dataraceRate > deadlockRate):
    # If choice falls past the datarace range then type is lock
    if choice >= dataraceRate:
      opType = 'lock'
  else:
    # If choice falls under the deadlock range then type is lock
    if choice <= deadlockRate:
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

  logger.debug("selectedOperator: {}".format(selectedOperator))

  return selectedOperator


def mutation(individual, functionalPhase):
  """A mutator for the individual using single mutation with feedback."""

  logger.debug("Mutating individual {} at generation {}".format(individual.id,
                                                         individual.generation))

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

  # If no mutants exist, reset and return
  if not mutantsExist:
    logger.debug("No possible mutations for individual")
    txl_operator.create_local_project(individual.generation, individual.id,
                                      True)
    return

  # Pick a mutation operator to apply
  limit = 100  # Number of attempts to find a valid mutation
  successfulCompile = False

  # Keep trying to find a successful mutant within the retry limits
  while limit is not 0 and not successfulCompile:
    # Acquire operator, one of config._MUTATIONS (ASAV, ...)
    selectedOperator = feedback_selection(individual, functionalPhase)

    # Find the integer index of the selectedOperator
    # That is, the index of ASAV, ASM, ...
    operatorIndex = -1
    for mutationOp in mutationOperators:
      if mutationOp[1]:
        operatorIndex += 1
        if mutationOp is selectedOperator:
          break

    # The continue here is for efficiency sake
    if len(individual.genome[operatorIndex]) == 0:
      logger.debug("No mutations at operatorIndex {}".format(operatorIndex))
      limit -= 1
      continue

    txl_operator.create_local_project(individual.generation,
                                      individual.id, False)

    randomMutant = randint(0, len(individual.genome[operatorIndex]) - 1)

    txl_operator.move_mutant_to_local_project(individual.generation,
                                              individual.id,
                                              selectedOperator[0], randomMutant + 1)

    # Move the local project to the target's source
    txl_operator.move_local_project_to_original(individual.generation,
                                                individual.id)

    logger.debug("Attempting to compile...")

    # Compile target's source
    if txl_operator.compile_project():
      successfulCompile = True
      logger.debug("  Success!\n")

      # Update individual
      individual.lastOperator = selectedOperator
      individual.appliedOperators.append(selectedOperator[0])

      # Switch the appropriate bit to 1 to record which instance is used
      individual.genome[operatorIndex][randomMutant] = 1
    else:
      limit -= 1
      logger.error("  Compiling failed, retrying another mutation")

  if not successfulCompile:
    # If not mutant was found we reset the project to it's pristine state
    # and start over
    logger.error("Couldn't create a compilable mutant project.  Resetting to pristine project.")
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
      logger.debug("Creating individual {}".format(i))
      individual = Individual(mutationOperators, i)
    else:
      logger.debug("Cloning best functional individual {} into individual {}".format(
                                                          bestIndividual.id, i))
      individual = bestIndividual.clone(mutationOperators, i)
    population.append(individual)

  return population


def get_average_non_functional_score(individual, numberOfRuns = config._CONTEST_RUNS):

  # This individual's best generation should be the last one compiled
  contest = tester.Tester()
  contest.begin_testing(False, False, numberOfRuns)  # Measure performance

  # Get the average of realTime and voluntarySwitches
  avgRealTime = sum(contest.realTime, 0.0) / len(contest.realTime)
  avgVoluntarySwitches = sum(contest.voluntarySwitches, 0.0) / len(contest.voluntarySwitches)

  # Find the uncertainties in the measurements
  maxRT = max(contest.realTime)
  minRT = min(contest.realTime)
  maxVS = max(contest.voluntarySwitches) 
  minVS = min(contest.voluntarySwitches)
  uncRT = (maxRT - minRT) / avgRealTime
  uncVS = (maxVS - minVS) / avgVoluntarySwitches

  # Determine which one is more significant
  sigNum = 0.0
  sigUnc = 0.0
  otherNum = 0.0
  otherUnc = 0.0

  # Voluntary switches are more significant
  if (avgRealTime > avgVoluntarySwitches):
    sigNum = avgVoluntarySwitches
    sigUnc = uncVS
    otherNum = avgRealTime
    otherUnc = uncRT
  # Real time is most significant
  elif (avgRealTime < avgVoluntarySwitches):
    sigNum = avgRealTime
    sigUnc = uncRT
    otherNum = avgVoluntarySwitches
    otherUNC = uncVS
  else: # (avgRealTime == avgVoluntarySwitches):
    sigNum = 1
    sigUnc = uncVS
    otherNum = 1
    otherUnc = uncRT

  # Determine the fitness
  avgFitness = ((sigNum / otherNum) * (1 - sigUnc)) + ((otherNum/sigNum) * (1 - otherUnc))
  logger.debug("Nonfunctional fitness: {}".format(avgFitness))
  contest.clear_results()
  return avgFitness

def start():
  """The actual starting process for ARC's evolutionary process."""

  # Backup project
  txl_operator.backup_project()

  functionalPhase = True

  try:
    # Initialize the population
    logger.info("Creating and initializing the population")
    population = initialize(functionalPhase)

    # Evolve the population to find the best functional individual
    logger.info("Evolving population towards functional correctness")
    bestFunctional = evolve(population, functionalPhase, 0)

    # Check to see if bestFunctional is valid for progress to next phase
    if bestFunctional.successes[-1]/config._CONTEST_RUNS == 1.0:

      functionalPhase = False
      bestFunctional.switchGeneration = bestFunctional.generation
      print population

      # Reinitialize the population with the best functional individual
      logger.debug("Repopulating with best individual {} at generation {}".format(
                                  bestFunctional.id, bestFunctional.generation))
      population = initialize(functionalPhase, bestFunctional)
      for individual in population:
        if individual.id is not bestFunctional.id:
          txl_operator.copy_local_project_a_to_b(bestFunctional.generation,
                                              bestFunctional.id,
                                              bestFunctional.generation,
                                              individual.id)

      # Acquire worst possible non-functional score for best individual
      worstScore = get_average_non_functional_score(bestFunctional, config._CONTEST_RUNS * 3)

      # Evolve the population to find the best non-functional individual
      logger.info("Evolving population towards non-functional performance")
      bestNonFunctional = evolve(population, functionalPhase,
                                 bestFunctional.generation, worstScore)
      print population
      logger.info("Best Individual\n")
      print bestNonFunctional
    else:
      logger.info("No individual was found that functions correctly")

    # Restore project to original
  except:
    logger.error("Unexpected error:\n", traceback.print_exc(file=sys.stdout))
    txl_operator.restore_project()
  else:
    txl_operator.restore_project()


def evolve(population, functionalPhase, generation=0, worstScore=0):

  # Keeps track of the number of votes per mutation operator (improvements)
  dataraceVotes = {}
  deadlocksVotes = {}
  nonFunctionalVotes = {}

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

    # Check the terminating conditions
    if convergence(generation, bestFitness, averageFitness):
      return get_best_individual(population, bestFitness)
    if terminate(population, generation, generationLimit, functionalPhase):
      return get_best_individual(population, bestFitness)

    # Check to see if we can replace the weakest individuals
    replace_lowest(population, functionalPhase)

    # Adjust weighting of mutation operators
    dataraceVotes, deadlocksVotes, nonFunctionalVotes = adjust_operator_weighting(population, functionalPhase, generation)


def adjust_operator_weighting(population, functionalPhase, generation):

  # Hashes of operator_name -> votes
  deadlockVotes = Counter()
  dataraceVotes = Counter()
  nonFunctionalVotes = Counter()

  # Consider that we are not pass the minimum sliding window value
  if generation <= config._DYNAMIC_RANKING_WINDOW:
    beginningGeneration = 1
  else:
    beginningGeneration = generation - config._DYNAMIC_RANKING_WINDOW

  logger.info("Operator weighting window of {} to {} generations".format(
              beginningGeneration, generation))

  for individual in population:
    # Only consider the generations we are conserned with
    for i in xrange(beginningGeneration-1,generation-1):
      # Figure if there was any improvement from the last generation
      if functionalPhase:
        if individual.deadlocks[i+1] < individual.deadlocks[i]:
          logger.info("Deadlock improvement from individual {} in generation {}".format(individual.id, i))
          deadlockVotes[individual.appliedOperators[i]] += 1
        if individual.dataraces[i+1] < individual.dataraces[i]:
          logger.info("Datarace improvement from individual {} in generation {}".format(individual.id, i))
          dataraceVotes[individual.appliedOperators[i]] += 1
      else:
        if individual.score[i+1] > individual.score[i]:
          logger.info("Non-functional improvement from individual {} in generation {}".format(individual.id, i))
          nonFunctionalVotes[individual.appliedOperators[i]] += 1

  return deadlockVotes, dataraceVotes, nonFunctionalVotes


def convergence(generation, bestFitness, averageFitness):

  # Alternate termination criteria to check for convergence
  avgFitTest = False
  maxFitTest = False
  if generation >= config._GENERATIONAL_IMPROVEMENT_WINDOW + 1:
    if max(averageFitness) - min(averageFitness) > config._AVG_FITNESS_MIN_DELTA:
      avgFitTest = True
    if max(bestFitness, key=lambda x:x[0])[0] - min(bestFitness,
        key=lambda x:x[0])[0] > config._BEST_FITNESS_MIN_DELTA:
      maxFitTest = True

    if not avgFitTest:
      logger.info("Average fitness hasn't moved by {} in {} generations".
            format(config._AVG_FITNESS_MIN_DELTA,
            config._GENERATIONAL_IMPROVEMENT_WINDOW))
      return True
    if not maxFitTest:
      logger.info("Maximum fitness hasn't moved by {} in {} generations".
            format(config._BEST_FITNESS_MIN_DELTA,
            config._GENERATIONAL_IMPROVEMENT_WINDOW))
      return True
  return False

def terminate(population, generation, generationLimit, functionalPhase):

  # Check for terminating conditions
  for individual in population:
    if functionalPhase and individual.successes[-1]/config._CONTEST_RUNS == 1:
      logger.info("Found potential best individual {}".format(individual.id))

      if tester.Tester().begin_testing(True, True, config._CONTEST_RUNS * 2):
        tester.Tester().clear_results()
        logger.info("Found best individual {}".format(individual.id))
        return True
      else:
        logger.info("Potential best individual still has errors")
    if generation == generationLimit:
      logger.info("Exhausted all generations")
      return True
  return False


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

      logger.debug("Case 1: Replacing a low performer with a high performer")
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
        # Reset the local project to it's pristine state
        logger.debug("Case 2: Reseting ID {} generation {} back to the pristine project".format(sortedMembers[i].id, sortedMembers[i].generation))
        txl_operator.create_local_project(sortedMembers[i].generation, sortedMembers[i].id, True)
      else:
        # Reset to best individual
        logger.debug("Case 3: Replacing a low performer with a high performer")
        txl_operator.copy_local_project_a_to_b(sortedMembers[i].switchGeneration,
                                              sortedMembers[i].id,
                                              sortedMembers[i].generation,
                                              sortedMembers[i].id)

    # Resort the population by ID and reassign it to the original variable
    population = sorted(sortedMembers, key=lambda individual: individual.id)
