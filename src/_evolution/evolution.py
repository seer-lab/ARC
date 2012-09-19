"""This module will start the evolution process for ARC."""

from __future__ import division
import random
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
import hashlist
import static

import logging
logger = logging.getLogger('arc')

# Set random's seed
if config._RANDOM_SEED is None:
  seed = random.randint(0, sys.maxint)
  logger.info("RANDOM SEED = {}".format(seed))
  random.seed(seed)
else:
  logger.info("RANDOM SEED = {}".format(config._RANDOM_SEED))
  random.seed(config._RANDOM_SEED)


# Global population to avoid passing it around
_population = []

# Global FunctionalPhase to avoid passing it around
_functionalPhase = True

def initialize(bestIndividual=None):
  """Initialize the population of individuals."""

  global _population
  global _functionalPhase

  # If we are testing against random, we use all operators
  if config._RANDOM_MUTATION:
    setOfOperators = config._ALL_MUTATIONS
  elif _functionalPhase:
    setOfOperators = config._FUNCTIONAL_MUTATIONS
  else:
    setOfOperators = config._NONFUNCTIONAL_MUTATIONS
    _population = []  # Reset population if on next phase

  # The number of enabled mutation operators
  mutationOperators = 0
  for operator in setOfOperators:
    if operator[1]:
      mutationOperators += 1

  # Create and initialize the population of individuals
  for i in xrange(1, config._EVOLUTION_POPULATION + 1):

    if bestIndividual is None:  # Functional phase
      logger.debug("Creating individual {}".format(i))
      individual = Individual(mutationOperators, i)
    else:  # Non-functional phase
      logger.debug("Cloning best functional individual {} into individual {}".format(
                                                          bestIndividual.id, i))
      individual = bestIndividual.clone(mutationOperators, i)
    _population.append(individual)


def start():
  """The actual starting process for ARC's evolutionary process."""

  global _population
  global _functionalPhase

  # Backup project
  #txl_operator.backup_project()

  try:
    # Initialize the population
    logger.info("Creating and initializing the population")
    initialize()

    # Evolve the population to find the best functional individual
    logger.info("**************************************************")
    logger.info("Evolving population towards functional correctness")
    logger.info("**************************************************")
    bestFunctional, bestFunctionalGeneration = evolve(0)

    # Check to see if bestFunctional is valid for progress to next phase
    # (That is, if a fix was found during the functional phase)
    if bestFunctional.successes[-1]/config._CONTEST_RUNS == 1.0 and bestFunctional.validated:

      # Proceed with the non-functional phase if enabled
      if not config._ONLY_FUNCTIONAL:

        _functionalPhase = False
        bestFunctional.switchGeneration = bestFunctional.generation

        logger.info("**************************************************")
        logger.info("Best individual found during the bug fixing phase:")
        logger.info("**************************************************")
        logger.info(bestFunctional)
        logger.info("")

        # Reinitialize the population with the best functional individual
        logger.debug("Repopulating with best individual {} at generation {}".format(
                                    bestFunctional.id, bestFunctional.generation))
        initialize(bestFunctional)
        for individual in _population:
          if individual.id is not bestFunctional.id:
            txl_operator.copy_local_project_a_to_b(bestFunctional.generation,
                                                bestFunctional.id,
                                                bestFunctional.generation,
                                                individual.id)

        # Acquire worst possible non-functional score for best individual.
        # Here "worst" is the average of a large number of executions
        txl_operator.move_local_project_to_workarea(bestFunctional.generation,
                                                    bestFunctional.id)
        txl_operator.compile_project()
        logger.debug("Acquiring Non-Functional worst score")
        contest = tester.Tester()
        contest.begin_testing(False, False, config._CONTEST_RUNS * config._CONTEST_VALIDATION_MULTIPLIER)  # Measure performance
        worstScore = get_average_non_functional_score(contest, bestFunctional,
          config._CONTEST_RUNS * config._CONTEST_VALIDATION_MULTIPLIER)

        # Evolve the population to find the best non-functional individual
        logger.info("*****************************************************************")
        logger.info("Evolving population towards optimizing non-functional performance")
        logger.info("*****************************************************************")
        #logger.debug("BUG HUNT: BestFunctional generation: {}  Worst score: {}".format(bestFunctional.generation, worstScore))
        bestNonFunctional, bestNonFunctionalGeneration = evolve(bestFunctional.generation, worstScore)
        #logger.debug("BUG HUNT: BestNonFunctional: {}  Best NonFunctional generation: {}".format(bestNonFunctional, bestNonFunctionalGeneration))

        logger.info("******************************************************")
        logger.info("Best individual found during the non-functional phase:")
        logger.info("******************************************************")
        logger.info(bestNonFunctional)
        logger.info("")

      else:
        bestNonFunctional = bestFunctional
        bestNonFunctionalGeneration = bestFunctionalGeneration

      logger.info("******************************************************")
      logger.info("Copying fixed project Individual:{} Generation:{} to {}".format(bestNonFunctional.id, bestNonFunctionalGeneration, config._PROJECT_OUTPUT_DIR))
      logger.info("******************************************************")
      txl_operator.move_best_project_to_output(bestNonFunctionalGeneration,
        bestNonFunctional.id)


    else:
      logger.info("No individual was found that functions correctly")

    #logger.info("------------------------------")
    #logger.info("Here is the entire population:")
    #logger.info(_population)
    #logger.info("------------------------------")
    #logger.info("Note: Results of the run can be found before the listing of the population.")
    #logger.info("(Scroll up)")

  except:
    logger.error("Unexpected error:\n", traceback.print_exc(file=sys.stdout))


def evolve(generation=0, worstScore=0):

  global _population
  global _functionalPhase

  # Keeps track of the number of votes per mutation operator (improvements)
  dataraceVotes = {}
  deadlockVotes = {}
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
    moreMutations = False
    highestSoFar = -1
    highestID = -1
    runningSum = 0

    for individual in _population:
      individual.generation = generation
      # Mutate an individual, then evaluate it right away
      mutationSuccess = mutation(individual, deadlockVotes, dataraceVotes, nonFunctionalVotes)

      if mutationSuccess:
        moreMutations = True
        evaluate(individual, worstScore)
        individual.wasRestarted.append(False)
        individual.wasReplaced.append(False)
        runningSum += individual.score[-1]
        if individual.score[-1] >= highestSoFar:
          highestSoFar = individual.score[-1]
          highestID = individual.id

        terminating, bestIndividual = terminate(individual, generation, generationLimit)
        if terminating:
          if bestIndividual is None:
            return get_best_individual()
          else:
            return bestIndividual, generation

      elif not mutationSuccess and not _functionalPhase:
        # No more possible mutations in non-functional phase, time to terminate
        return get_best_individual(True)

    averageFitness.append(runningSum / config._EVOLUTION_POPULATION)
    bestFitness.append((highestSoFar, highestID))

    # Check the terminating conditions
    if not _functionalPhase:
      #logger.debug("BUG HUNT: Convergence {} {} {}".format(generation, bestFitness, averageFitness))
      if convergence(generation, bestFitness, averageFitness):
        return get_best_individual()

    # If there are no more mutations, this process cannot go any further
    if not moreMutations:
      logger.info("Terminating evolution process, there are no more possible mutations")
      return get_best_individual()

    # Avoid huristics when doing random
    if not config._RANDOM_MUTATION:

      # Make note of the under-performers and replace them if it falls in the interval
      replace_lowest(generation)

      # Perform mutation again for those individuals who were replaced or restarted
      for individual in _population:
        if generation == individual.generation - 1:
          mutation(individual, deadlockVotes, dataraceVotes,
            nonFunctionalVotes)

          # If were in the non-functional phase and no more mutants are possible we terminate
          if not _functionalPhase and not mutationSuccess:
            return get_best_individual()

      # Adjust weighting of mutation operators
      deadlockVotes, dataraceVotes, nonFunctionalVotes = adjust_operator_weighting(generation)


def mutation(individual, deadlockVotes, dataraceVotes, nonFunctionalVotes):
  """A mutator for the individual using single mutation with feedback."""

  logger.info("Mutating individual {} at generation {}".format(individual.id,
                                                         individual.generation))

  # Acquire set of operators to use
  if config._RANDOM_MUTATION:
    mutationOperators = config._ALL_MUTATIONS
  elif _functionalPhase:
    mutationOperators = config._FUNCTIONAL_MUTATIONS
  else:
    mutationOperators = config._NONFUNCTIONAL_MUTATIONS

  # Repopulate the individual's genome with new possible mutation locations
  # (Generates all mutations for the individual)
  individual.repopulateGenome(_functionalPhase)

  # Definite check to see if ANY mutants exists for an individual
  checkInd = -1
  mutantsExist = False
  for mutationOp in mutationOperators:
    if mutationOp[1]:
      checkInd += 1
      if len(individual.genome[checkInd]) != 0:
        mutantsExist = True

  # If no mutants exist, reset and re-attempt mutation

  if not mutantsExist:
    logger.debug("No possible mutations for individual")

    # If in non-functional phase then this individual is done
    if not _functionalPhase:
      return False

    # Repopulate the individual's genome with new possible mutation locations
    # (Reset this member back to the pristine project)
    txl_operator.create_local_project(individual.generation, individual.id,
                                    True)
    # Generates all mutations for the pristine individual
    individual.repopulateGenome(_functionalPhase)

    # Definite check to see if ANY mutants exists for an individual
    checkInd = -1
    mutantsExist = False
    for mutationOp in mutationOperators:
      if mutationOp[1]:
        checkInd += 1
        if len(individual.genome[checkInd]) != 0:
          mutantsExist = True

    # If mutants don't exist still then pristine project has a problem
    if not mutantsExist:
      logger.error("A restarted individual has no mutations... terminating")
      raise Exception("No mutations in Functional Phase on pristine project")

  # Pick a mutation operator to apply
  limit = 100  # Number of attempts to find a valid mutation
  successfulCompile = False

  # Hold attempted mutations (operatorIndex[mut#]), so we do not retry them
  attemptedMutations = {}

  # Initialize attemptedMutations hash for valid operators
  operatorIndex = -1
  for mutationOp in mutationOperators:
    if mutationOp[1]:
      operatorIndex += 1
      attemptedMutations[operatorIndex] = set()

  # Keep trying to find a successful mutant within the retry limits
  while limit is not 0 and not successfulCompile:
    # Acquire operator, one of config._MUTATIONS (ASAV, ...)
    selectedOperator = feedback_selection(individual,
      deadlockVotes, dataraceVotes, nonFunctionalVotes)

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
      #logger.debug("No mutations at operatorIndex {}".format(operatorIndex))
      continue

    txl_operator.create_local_project(individual.generation,
                                      individual.id, False)

    # Make it so we do not try the same mutation over and over
    # TODO Could refactor this to work backwards from a set of mutants instead
    #       of trying to do it randomly.
    retry = True
    while retry:

      # Check to see if we have exhausted all mutants for this operator
      if len(attemptedMutations[operatorIndex]) is len(individual.genome[operatorIndex]):
        randomMutant = None
        break

      randomMutant = random.randint(0, len(individual.genome[operatorIndex]) - 1)

      # Make sure we try a new mutation
      if randomMutant not in attemptedMutations[operatorIndex]:

        # Add mutation to set of attemptedMutations
        attemptedMutations[operatorIndex].add(randomMutant)
        retry = False

    # Move to another operator as this one has nothing left to mutate
    if randomMutant is None:
      continue

    txl_operator.move_mutant_to_local_project(individual.generation,
                                              individual.id,
                                              selectedOperator[0], randomMutant + 1)

    # Move the local project to the target's source
    txl_operator.move_local_project_to_workarea(individual.generation,
                                                individual.id)

    logger.debug("Attempting to compile...")

    # Compile target's source
    if txl_operator.compile_project():
      successfulCompile = True
      logger.debug("Success!")

      # Update individual
      individual.lastOperator = selectedOperator
      individual.appliedOperators.append(selectedOperator[0])

      # Switch the appropriate bit to 1 to record which instance is used
      individual.genome[operatorIndex][randomMutant] = 1
    else:
      limit -= 1
      logger.debug("Compiling failed, retrying another mutation")

  # Return true if successful, otherwise false (returned to pristine state)
  if not successfulCompile:
    logger.debug("Couldn't create a compilable mutant project. Resetting to the pristine project/bestIndividual.")
    if _functionalPhase:
      txl_operator.create_local_project(individual.generation, individual.id, True)
    else:
      txl_operator.create_local_project(individual.generation, individual.id,
                                    True, individual.switchGeneration + 1)

    # Update individual to reflect failed mutation
    individual.lastOperator = None
    individual.appliedOperators.append(None)

    return False
  else:
    logger.debug("Selected operator for Individual {} at generation {}: {}, number {}".
    format(individual.id, individual.generation, selectedOperator[0], randomMutant + 1))
    return True


def evaluate(individual, worstScore):
  """Perform the actual evaluation of said individual using ConTest testing.

  The fitness is determined using functional and non-functional fitness values.
  """

  logger.info("Evaluating individual {} on generation {}".format(individual.id,
                                                        individual.generation))

  global _functionalPhase

  # ConTest testing
  contest = tester.Tester()

  if _functionalPhase:
    # Check if we have encountered this mutant already
    hash = hashlist.generate_hash(individual.generation, individual.id)
    if hash is not None:
      hashGen, hashMem =  hashlist.find_hash(hash)
      # If we have, we can skip the contest runs (saves time) and copy the testing
      # results from the first mutatn
      if hashGen != -1 and hashMem != -1:
        logger.debug("Found this mutated project hash in hash list: {}.  Skipping evaluation".format(hash))
        prevIndvidual = _population[hashMem]

        individual.score.append(hashMem.score[hashGen])
        individual.successes.append(hashMem.successes[hashMem])
        individual.timeouts.append(hashMem.timeouts[hashMem])
        individual.dataraces.append(hashMem.dataraces[hashMem])
        individual.deadlocks.append(hashMem.deadlocks[hashMem])
        individual.errors.append(hashMem.errors[hashMem])
      # If we haven't seen this mutant before, evaluate it with contest
      else:
        logger.debug("Didn't find this mutated project hash in hash list: {}.  Adding it".format(hash))
        hashlist.add_hash(hash, individual.generation, individual.id)

        contest.begin_testing(_functionalPhase)

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
      logger.error("Hash value of member {} generation {} is NULL".format(individual.id, individual.generation))
  else:
    # Ensure functionality is still there
    # _functionalPhase is false here
    if contest.begin_testing(_functionalPhase, True,
          config._CONTEST_RUNS * config._CONTEST_VALIDATION_MULTIPLIER):
      logger.debug("Nonfunctional phase: Mutation didn't introduce any bugs")
      #contest.clear_results()

      # Nonfunctional fitness
      individual.score.append(get_average_non_functional_score(contest, individual, config._CONTEST_RUNS * config._CONTEST_VALIDATION_MULTIPLIER))
    else:
      logger.debug("Nonfunctional phase: Mutation introduced a bug")
      individual.score.append(-1)

      # Need to ensure that the project from the last generation is used again
      if individual.generation-1 is 0:
        # Restarting the mutant if at 0th generation
        logger.debug("Nonfunctional phase: Resetting back to pristine")
        txl_operator.create_local_project(individual.generation, individual.id, True)
      else:
        logger.debug("Nonfunctional phase: Resetting back to the previous generation")
        txl_operator.copy_local_project_a_to_b(individual.generation-1,
                                              individual.id,
                                              individual.generation,
                                              individual.id)
      individual.wasRestarted[-1] = True

  contest.clear_results()


def feedback_selection(individual, deadlockVotes, dataraceVotes, nonFunctionalVotes):
  """Given the individual this function will find the next operator to apply.

  The selection of the next operator takes into account the individual's last
  test execution as feedback. The feedback is used to heuristically guide what
  mutation operator to apply next.

  Returns one of ASAV, ...
  """

  global _functionalPhase

  # candidateChoices is a list of config._MUTATIONS
  # {ASAS, ASAV, ...}
  candatateChoices = []

  # Acquire set of operators to use
  if config._RANDOM_MUTATION:
    mutationOperators = config._ALL_MUTATIONS
  elif _functionalPhase:
    mutationOperators = config._FUNCTIONAL_MUTATIONS
  else:
    mutationOperators = config._NONFUNCTIONAL_MUTATIONS

  # Handle mutation selection (using random or heuristics)
  if config._RANDOM_MUTATION:

    for operator in mutationOperators:
        if operator[1]: # If enabled
          candatateChoices.append(operator)

    return candatateChoices[random.randint(0,len(candatateChoices)-1)]

  else:
    opType = 'race'

    # Acquire the deadlock and datarace rates
    if len(individual.deadlocks) == 0:
      deadlockRate = .5
      dataraceRate = .5
    else:
      deadlockRate = individual.deadlocks[-1] / config._CONTEST_RUNS
      dataraceRate = individual.dataraces[-1] / config._CONTEST_RUNS

    # Acquire a random value that is less then the total of the bug rates
    totalBugRate = (deadlockRate + dataraceRate)
    choice = random.uniform(0, totalBugRate)

    # Determine which bug type to use
    if (dataraceRate > deadlockRate):
      # If choice falls past the datarace range then type is lock
      if choice >= dataraceRate:
        opType = 'lock'
    else:
      # If choice falls under the deadlock range then type is lock
      if choice <= deadlockRate:
        opType = 'lock'

    # Select the appropriate operator based on enable/type/functional
    # (See config.py)
    if opType is 'race':
      for operator in mutationOperators:
        if operator[1] and operator[2]:
          # For the functional phase we can now specify what operators are used by
          # the deadlock and data race fixing process (See config.py)
          if _functionalPhase and operator[5]:
              candatateChoices.append(operator)
          if not _functionalPhase:
            candatateChoices.append(operator)
    elif opType is 'lock':
      for operator in mutationOperators:
        if operator[1] and operator[3]:
          if _functionalPhase and operator[6]:
              candatateChoices.append(operator)
          if not _functionalPhase:
            candatateChoices.append(operator)

    # Acquire the operator chances based on what voting condition we have
    if _functionalPhase and opType is 'lock':
      operatorChances = get_operator_chances(candatateChoices, deadlockVotes)
      #logger.debug("Deadlock weighting: {}".format(operatorChances))
    elif _functionalPhase and opType is 'race':
      operatorChances = get_operator_chances(candatateChoices, dataraceVotes)
      #logger.debug("Datarace weighting: {}".format(operatorChances))
    else:
      operatorChances = get_operator_chances(candatateChoices, nonFunctionalVotes)
      #logger.debug("Operator chance for non-functional phase: {}".format(operatorChances))

    # Make selection of operator based on the adjusted weighting
    randomChance = random.randint(0,sum(operatorChances))
    currentRunning = 0  # Keeps track of sum (when we exceed this we are done)
    for i in xrange(len(operatorChances)):
      currentRunning += operatorChances[i]
      if randomChance <= currentRunning:
        selectedOperator = candatateChoices[i]
        break

    logger.debug("Selected operator: {}".format(selectedOperator[0]))
    return selectedOperator


def get_operator_chances(candatateChoices, votes):

  operatorChances = [0] * len(candatateChoices)
  currentValue = len(candatateChoices) + 1
  currentLarge = config._DYNAMIC_RANKING_WINDOW + 1

  # Map the values from largest to their appropriate values
  for op in sorted(votes, key=votes.get, reverse=True):

    # Move the currentValue down by one if the current votes are smaller
    if votes[op] < currentLarge:
      currentValue -= 1

    # Place the current value in the appropriate element for array of chances
    for i in xrange(len(candatateChoices)):
      if candatateChoices[i][0] == op:
        operatorChances[i] = currentValue
    currentLarge = votes[op]

  # Fill in chances where nothing was voted (gives largest unused chance value)
  for operator in operatorChances:
    if operator == 0:
      operatorChances[operatorChances.index(operator)] = currentValue - 1

  return operatorChances


def get_average_non_functional_score(contest, individual, numberOfRuns = config._CONTEST_RUNS):

  logger.info("Getting average non-functional score")

  # This individual's best generation should be the last one compiled
  #contest = tester.Tester()
  #contest.begin_testing(False, False, numberOfRuns)  # Measure performance

  # Get the average of realTime and voluntarySwitches
  avgRealTime = sum(contest.realTime, 0.0) / len(contest.realTime)
  avgVoluntarySwitches = sum(contest.voluntarySwitches, 0.0) / len(contest.voluntarySwitches)

  # Append average data to individual
  individual.realTime.append(avgRealTime)
  individual.voluntarySwitches.append(avgVoluntarySwitches)

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


def adjust_operator_weighting(generation):

  global _population
  global _functionalPhase

  # Hashes of operator_name -> votes
  deadlockVotes = Counter()
  dataraceVotes = Counter()
  nonFunctionalVotes = Counter()

  # Consider that we are not pass the minimum sliding window value
  if generation <= config._DYNAMIC_RANKING_WINDOW:
    beginningGeneration = 1
  else:
    beginningGeneration = generation - config._DYNAMIC_RANKING_WINDOW

  logger.debug("Operator weighting window of {} to {} generations".format(
              beginningGeneration, generation))

  for individual in _population:

    # To ensure that the window will not cross back into the functional phase
    if beginningGeneration < individual.switchGeneration:
      logger.debug("Adjusting weighting window to not cross into functional phase")
      beginningGeneration = individual.switchGeneration

    # Only consider the generations we are concerned with
    for i in xrange(beginningGeneration,generation-1):

      # Only weight operators for valid mutations (ignore failed mutations)
      if individual.lastOperator is not None:

        # Figure if there was any improvement from the last generation
        if _functionalPhase:
          if individual.deadlocks[i+1] < individual.deadlocks[i]:
            logger.debug("Deadlock improvement from individual {} in generation {}".
              format(individual.id, i))
            deadlockVotes[individual.appliedOperators[i]] += 1

          if individual.dataraces[i+1] < individual.dataraces[i]:
            logger.debug("Datarace improvement from individual {} in generation {}".
              format(individual.id, i))
            dataraceVotes[individual.appliedOperators[i]] += 1

        else:
          if individual.score[i+1] > individual.score[i]:
            logger.debug("Non-functional improvement over individual {} in generation {}".
              format(individual.id, i))
            logger.debug("Applied operators: {}".format(individual.appliedOperators))
            j = individual.appliedOperators[i]
            #logger.debug ("      ***** J is {} *****".format(j))
            nonFunctionalVotes[j] += 1

  logger.debug("Deadlock Votes: {}".format(deadlockVotes))
  logger.debug("Datarace Votes: {}".format(dataraceVotes))
  logger.debug("Non-Functional Votes: {}".format(nonFunctionalVotes))

  return deadlockVotes, dataraceVotes, nonFunctionalVotes


def convergence(generation, bestFitness, averageFitness):

  # Alternate termination criteria to check for convergence
  avgFitTest = False
  maxFitTest = False

  # Acquire the last N window values
  windowAverageValues = averageFitness[-config._GENERATIONAL_IMPROVEMENT_WINDOW:]
  windowMaximumValues = bestFitness[-config._GENERATIONAL_IMPROVEMENT_WINDOW:]

  if len(windowAverageValues) == config._GENERATIONAL_IMPROVEMENT_WINDOW:
    if max(windowAverageValues) - min(windowAverageValues) > config._AVG_FITNESS_MIN_DELTA:
      avgFitTest = True
    if max(windowMaximumValues, key=lambda x:x[0])[0] - min(windowMaximumValues,
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


def terminate(individual, generation, generationLimit):

  global _population
  global _functionalPhase

  # Check for terminating conditions
  #for individual in _population:
  if _functionalPhase and individual.successes[-1]/config._CONTEST_RUNS == 1:
    logger.info("Found potential best individual {}".format(individual.id))

    if tester.Tester().begin_testing(True, True,
          config._CONTEST_RUNS * config._CONTEST_VALIDATION_MULTIPLIER):
      tester.Tester().clear_results()
      logger.info("Found best individual {}".format(individual.id))
      individual.validated = True
      return True, individual
    else:
      tester.Tester().clear_results()
      logger.info("Potential best individual still has errors")
  if generation == generationLimit:
    logger.info("Exhausted all generations")
    return True, None
  return False, None


def get_best_individual(beforeMutation=False):

  global _population
  global _functionalPhase

  bestScore = -1
  individualId = -1
  generation = -1
  mod = 0

  # If we have to get the best individual before the mutation step occurs
  if beforeMutation:
    mod = 1

  for individual in _population:

    if _functionalPhase:
      # Consider all generations
      #logger.debug("BUG HUNT get_best_individual 1:  generation: {}".format(individual.generation))
      for i in xrange(0, individual.generation):
        if individual.score[i] > bestScore:
          individualId = individual.id
          generation = i + 1
          bestScore = individual.score[i]

    else:
      # Consider generations over the switch
      #logger.debug("BUG HUNT get_best_individual 2:  {} {} {}".format(individual.switchGeneration, individual.generation, mod))
      #logger.debug(" BUG HUNT Individual: {}".format(individual))
      #logger.debug(" BUG HUNT Best score: {}".format(bestScore))

      #print individual
      for i in xrange(individual.switchGeneration, individual.generation - mod):
        #logger.debug("BUG HUNT i = {}".format(i))
        if individual.score[i] > bestScore:
          #logger.debug("BUG HUNT individual.score[i]: {}".format(individual.score[i]))
          individualId = individual.id
          generation = i + 1   # My guess is that the +1 isn't necessary
          bestScore = individual.score[i]

  for individual in _population:
    if individual.id == individualId:
      logger.info("Found bestIndividual {} @ generation {}".format(individual.id, generation))
      return individual, generation


def replace_lowest(generation):
  """Attempt to replace underperforming members with high-performing members or
  the original buggy program.
  """

  global _population
  global _functionalPhase

  # Determine the number of members to look at for underperforming
  numUnder = int((config._EVOLUTION_POPULATION * config._EVOLUTION_REPLACE_LOWEST_PERCENT)/100)
  if numUnder < 1:
    numUnder = 1

  # Sort population by fitness
  sortedMembers = sorted(_population, key=lambda individual: individual.score[-1])

  # The first numUnder members have their turnsUnderperforming variable incremented
  # as they are the worst performing
  for i in xrange(0, numUnder):
    sortedMembers[i].turnsUnderperforming += 1

  # Check to see if we can replace the weakest individuals
  if generation % config._EVOLUTION_REPLACE_INTERVAL is 0:

    logger.debug("Performing replacement of weakest individuals")

    # Acquire set of operators to use
    if config._RANDOM_MUTATION:
      mutationOperators = config._ALL_MUTATIONS
    elif _functionalPhase:
      mutationOperators = config._FUNCTIONAL_MUTATIONS
    else:
      mutationOperators = config._NONFUNCTIONAL_MUTATIONS

    # Replace or restart members who have underperformed for too long
    for i in xrange(0, numUnder):

      if (sortedMembers[i].turnsUnderperforming < config._EVOLUTION_REPLACE_WEAK_MIN_TURNS):
        continue
      else:
        sortedMembers[i].turnsUnderperforming = 0

      randomNum = random.randint(1, 100)

      # Case 1: Replace an underperforming member with a fit member
      if randomNum <= config._EVOLUTION_REPLACE_WITH_BEST_PERCENT:

        while True:
          # Take a member from the top 10% of the population
          highMember =  random.randint(int(config._EVOLUTION_POPULATION * 0.9),
                            config._EVOLUTION_POPULATION) - 1

          # Ensure that the selected memeber is not the current member
          if highMember is not i:
            break

        # Keep the id of the original member
        lowId = sortedMembers[i].id
        # logger.debug( "[INFO] Replacing ID: {} with {}".format(lowId, sortedMembers[highMember].id)
        sortedMembers[i] = copy.deepcopy(sortedMembers[highMember])
        sortedMembers[i].id = lowId
        sortedMembers[i].wasReplaced[-1] = True

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

        # logger.debug("[INFO] Restarting underperforming member ID: {}".format(sortedMembers[i].id)
        # TODO We don't know in the timeline, when an individual is restarted
        # If in functional restart off of local, otherwise off of best individual
        sortedMembers[i].wasRestarted[-1] = True
        if _functionalPhase:
          # Reset the local project to it's pristine state
          logger.debug("Case 2: Reseting ID {} generation {} back to the pristine project".
            format(sortedMembers[i].id, sortedMembers[i].generation))
          txl_operator.create_local_project(sortedMembers[i].generation,
            sortedMembers[i].id, True)
        else:
          # Reset to best individual
          logger.debug("Case 2: Reseting ID {} generation {} back to the best individual project".
            format(sortedMembers[i].id, sortedMembers[i].generation))
          txl_operator.copy_local_project_a_to_b(sortedMembers[i].switchGeneration,
                                                sortedMembers[i].id,
                                                sortedMembers[i].generation,
                                                sortedMembers[i].id)

      # ALTERNATIVE: Reset the turnsUnderperforming at each interval
      # sortedMembers[i].turnsUnderperforming = 0

  # Resort the population by ID and reassign it to the original variable
  _population = sorted(sortedMembers, key=lambda individual: individual.id)
