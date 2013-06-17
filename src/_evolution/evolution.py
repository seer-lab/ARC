"""This module will start the evolution process for ARC.

Copyright David Kelk and Kevin Jalbert, 2012
          David Kelk, 2013
"""

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
  """The actual starting process for ARC's evolutionary process.
  """

  global _population
  global _functionalPhase

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
        bestNonFunctional, bestNonFunctionalGeneration \
          = evolve(bestFunctional.generation, worstScore)
        if bestNonFunctional is None:
          logger.info("***************************************************************")
          logger.info("ERROR: No best individual found during the non-functional phase")
          logger.info("***************************************************************")
          logger.info(bestNonFunctional)
          logger.info("")
        else:
          logger.info("******************************************************")
          logger.info("Best individual found during the non-functional phase:")
          logger.info("******************************************************")
          logger.info(bestNonFunctional)
          logger.info("")

      else:
        bestNonFunctional = bestFunctional
        bestNonFunctionalGeneration = bestFunctionalGeneration

      logger.info("******************************************************")
      logger.info("Copying fixed project Individual:{} Generation:{} to {}"
        .format(bestNonFunctional.id, bestNonFunctionalGeneration,
        config._PROJECT_OUTPUT_DIR))
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
  """This function is the workhorse for ARC. Fixing bugs and optimizing the
  non-functional score are both done here

  Attributes:
    generation (int): Current generation
    worstScore (int?): TODO: Not used

  Returns:
    individual (Individual): Best individual found, or None
  """

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
        return get_best_individual()

      # We can remove mutants for generation n-2. (We must keep generation n-1
      # for the restart case.)
      if individual.generation > 2:
        logger.debug("Cleaning up mutants for generation {} member {}."
          .format(individual.generation - 2, individual.id))
        txl_operator.clean_up_mutants(individual.generation - 2, individual.id)

    averageFitness.append(runningSum / config._EVOLUTION_POPULATION)
    bestFitness.append((highestSoFar, highestID))

    # Check the terminating conditions
    if not _functionalPhase:
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
  """A mutator for the individual using single mutation with feedback.

  Attributes:
    individual (Individual): Who we are scoring
    deadlockVotes, dataraceVotes, nonFunctionalVotes:
      Votes by operator type, eg: ({'ASAT': 1}) See the operator_weighting fn

  Returns:
    boolean: Were any mutants created for the individual?
  """

  logger.info("-------------------------------------------------------------")
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
  totNumMutants = individual.repopulateGenome(_functionalPhase)

  # Check if individual has mutations
  # If no mutants exist, reset and re-attempt mutation
  if totNumMutants == 0:
    logger.debug("No possible mutations for individual")

    # If in non-functional phase then this individual is done
    if not _functionalPhase:
      return False

    # Reset to pristine
    txl_operator.create_local_project(individual.generation, individual.id, True)
    # Generates all mutations for the pristine individual
    totNumMutants = individual.repopulateGenome(_functionalPhase)

    # Check again for mutations
    # If mutants still don't exist, the pristine project has a problem
    if totNumMutants == 0:
      logger.error("A restarted individual has no mutations... terminating")
      raise Exception("No mutations in Functional Phase on pristine project")

  # If we reach this point, there are mutations

  # Hold attempted mutations, so we don't retry them
  # It is a set of sets by operator type
  # {{ASAT operators tried}, {ASIM operators tried}, ...}
  attemptedMutations = {}

  # Initialize attemptedMutations hash for valid operators
  operatorIndex = -1
  for mutationOp in mutationOperators:
    if mutationOp[1]:
      operatorIndex += 1
      attemptedMutations[operatorIndex] = set()

  # Big while loop where we try all mutants in turn
  outerLoopCtr = 0
  innerLoopCtr = 0
  totTriedMutants = 0
  retry = True
  while retry:

    outerLoopCtr += 1
    if outerLoopCtr >= 100:
      retry = False
      logger.debug("Exiting outer loop after 100 iterations")
      logger.debug("  This probably occurred because the remaining mutations were not")
      logger.debug("  compatible with what is trying to be fixed.  For example, if")
      logger.debug("  we are trying to fix data races, we don't remove synchronized")
      logger.debug("  blocks.")
      break

    # Check if we have more mutants to try
    if totTriedMutants >= totNumMutants:
      retry = False
      break

    selectedOperator = feedback_selection(individual,
      deadlockVotes, dataraceVotes, nonFunctionalVotes)
    #logger.debug("Selected operator: {}".format(selectedOperator))

    # Find the integer index of the selectedOperator
    # That is, the index of ASAT, ASM, ...
    operatorIndex = -1
    for mutationOp in mutationOperators:
      if mutationOp[1]:
        operatorIndex += 1
        if mutationOp is selectedOperator:
          break

    # Look for a mutation we haven't tried yet
    if len(attemptedMutations[operatorIndex]) is len(individual.genome[operatorIndex]):
      continue
    # When we get to here we have untried mutations (of a mutator type)
    # to select from
    keepTrying = True
    while keepTrying:
      randomMutant = random.randint(0, len(individual.genome[operatorIndex]) - 1)

      # Make sure we try a new mutation
      if randomMutant not in attemptedMutations[operatorIndex]:

        # Add mutation to set of attemptedMutations
        attemptedMutations[operatorIndex].add(randomMutant)
        keepTrying = False

      innerLoopCtr += 1

      if innerLoopCtr >= 100:
        keepTrying = False
        logger.error("Exiting inner loop after 100 iterations")
        innerLoopCtr = 0

    # When we get here, we have selected a new mutant
    totTriedMutants += 1
    # Create the project, add the mutant
    txl_operator.create_local_project(individual.generation, individual.id, False)

    txl_operator.move_mutant_to_local_project(individual.generation, individual.id,
                                              selectedOperator[0], randomMutant + 1)

    # Move the local project to the target's source
    txl_operator.move_local_project_to_workarea(individual.generation, individual.id)

    logger.debug("Attempting to compile...")

    # Compile target's source
    if txl_operator.compile_project():
      logger.debug("Success!")

      # Update individual
      individual.lastOperator = selectedOperator
      individual.appliedOperators.append(selectedOperator[0])

      # Switch the appropriate bit to 1 to record which instance is used
      individual.genome[operatorIndex][randomMutant] = 1

      logger.debug("Selected operator for Individual {} at generation {}: {}, number {}".
        format(individual.id, individual.generation, selectedOperator[0], randomMutant + 1))
      return True


  # If we weren't able to compile a mutant project, reset it to the pristine and leave
  # it for this generation. We'll try again next generation to do something with it.
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


def feedback_selection(individual, deadlockVotes, dataraceVotes, nonFunctionalVotes):
  """Given the individual this function will find the next operator to apply.
  The operator selected will have generated mutants.

  The selection of the next operator takes into account the individual's last
  test execution as feedback. The feedback is used to heuristically guide what
  mutation operator to apply next.

  Attributes:
    individual (Individual): Who we are scoring
    deadlockVotes, dataraceVotes, nonFunctionalVotes:
      Votes by operator type, eg: ({'ASAT': 1}) See the operator_weighting fn

  Returns:
    selectedOperator: One of ASAT, ASIM, ...
  """

  global _functionalPhase

  # candidateChoices is a list of config._MUTATIONS
  # { [ASAT, True, ...], [ASIM, True, ...], ...}
  candidateChoices = []

  # Acquire set of operators to use
  if config._RANDOM_MUTATION:
    mutationOperators = config._ALL_MUTATIONS
  elif _functionalPhase:
    mutationOperators = config._FUNCTIONAL_MUTATIONS
  else:
    mutationOperators = config._NONFUNCTIONAL_MUTATIONS

  # Case 1: Randomly choose an operator that has generated mutants
  if config._RANDOM_MUTATION:

    checkInd = -1
    for mutationOp in mutationOperators:
      if mutationOp[1]:
        checkInd += 1
        if len(individual.genome[checkInd]) > 0:
          candidateChoices.append(operator)

    return candidateChoices[random.randint(0,len(candidateChoices)-1)]

  # Case 2: Heuristic selection
  opType = 'race'

  # 1. Acquire the deadlock and datarace rates
  if len(individual.deadlocks) == 0:
    deadlockRate = .5
    dataraceRate = .5
  else:
    deadlockRate = individual.deadlocks[-1] / config._CONTEST_RUNS
    dataraceRate = individual.dataraces[-1] / config._CONTEST_RUNS

  # Acquire a random value that is less then the total of the bug rates
  totalBugRate = (deadlockRate + dataraceRate)
  choice = random.uniform(0, totalBugRate)

  # 2. Determine which bug type to use
  if (dataraceRate > deadlockRate):
    # If choice falls past the datarace range then type is lock
    if choice >= dataraceRate:
      opType = 'lock'
  else:
    # If choice falls under the deadlock range then type is lock
    if choice <= deadlockRate:
      opType = 'lock'

  # logger.debug("opType: {}".format(opType))

  # 3. Generate a list of operators that meet all the conditions
  #    (Used for races, enabled, generated mutants, ...)
  if opType is 'race':
    checkInd = -1
    for operator in mutationOperators:
      # Is it enabled
      if operator[1]:
        checkInd += 1
        # Is it enabled for data races and does it have mutants?
        if operator[2] and len(individual.genome[checkInd]) > 0:
          # If it is the functional phase and the operator fixes data races during the
          # functional phase
          if _functionalPhase and operator[5]:
            candidateChoices.append(operator)
          if not _functionalPhase:
            candidateChoices.append(operator)

  elif opType is 'lock':
    checkInd = -1
    for operator in mutationOperators:
      # Is it enabled
      if operator[1]:
        checkInd += 1
        # Is it enabled for data races and does it have mutants?
        if operator[3] and len(individual.genome[checkInd]) > 0:
          # If it is the functional phase and the operator fixes data races during the
          # functional phase
          if _functionalPhase and operator[6]:
            candidateChoices.append(operator)
          if not _functionalPhase:
            candidateChoices.append(operator)

  # logger.debug("Before opChances candidateChoices: {}".format(candidateChoices))
  # logger.debug("                 deadlockVotes:    {}".format(deadlockVotes))
  # logger.debug("                 dataraceVotes:    {}".format(dataraceVotes))

  # 4. Acquire the operator chances based on what voting condition we have
  if _functionalPhase and opType is 'lock':
    operatorChances = get_operator_chances(candidateChoices, deadlockVotes)
    #logger.debug("Deadlock weighting: {}".format(operatorChances))
  elif _functionalPhase and opType is 'race':
    operatorChances = get_operator_chances(candidateChoices, dataraceVotes)
    #logger.debug("Datarace weighting: {}".format(operatorChances))
  else:
    operatorChances = get_operator_chances(candidateChoices, nonFunctionalVotes)
    #logger.debug("Operator chance for non-functional phase: {}".format(operatorChances))

  # 5. Select an operator based on the adjusted weighting

  # logger.debug("selection candidateChoices: {}".format(candidateChoices))
  # logger.debug("           operatorChances: {}".format(operatorChances))

  randomChance = random.randint(0,sum(operatorChances))
  currentRunning = 0  # Keeps track of sum (when we exceed this we are done)
  for i in xrange(len(operatorChances)):
    currentRunning += operatorChances[i]
    if randomChance <= currentRunning:
      selectedOperator = candidateChoices[i]
      break

  logger.debug("Selected operator returned: {}".format(selectedOperator[0]))

  return selectedOperator


def get_operator_chances(candidateChoices, votes):
  """Score each operator based on how successful it is. For example,
  ASAT might get 5 points, ASIM 8 points, ...

  Attributes:
    candidateChoices: List of operators to weight
    votes: Votes by operator type, eg: ({'ASAT': 1})
  Returns:
    operatorChances: Score of each operator, eg: ({'ASIM': 3})
  """

  # candidateChoices is a list of config._MUTATIONS
  # { [ASAT, True, ...], [ASIM, True, ...], ...}

  # logger.debug("entry candidateChoices: {}".format(candidateChoices))
  # logger.debug("                 votes: {}".format(votes))

  operatorChances = [0] * len(candidateChoices)
  currentValue = len(candidateChoices) + 1
  currentLarge = config._DYNAMIC_RANKING_WINDOW + 1

  # Map the values from largest to their appropriate values
  for op in sorted(votes, key=votes.get, reverse=True):

    # Move the currentValue down by one if the current votes are smaller
    if votes[op] < currentLarge:
      currentValue -= 1

    # Place the current value in the appropriate element for array of chances
    for i in xrange(len(candidateChoices)):
      if candidateChoices[i][0] == op:
        operatorChances[i] = currentValue
    currentLarge = votes[op]

    # logger.debug("Sorting candidateChoices {}".format(candidateChoices))
    # logger.debug("        operatorChances  {}".format(operatorChances))
    # logger.debug("        votes            {}".format(votes))

  # It is possible to have arrived here with operator chances being [0].
  # That is, there was only one applicable operator and it will be chosen
  # 0% of the time. Give each operator a weighting of atleast 1.
  for operator in operatorChances:
    if operator <= 0:
      operatorChances[operatorChances.index(operator)] = 1

  # logger.debug("Returned operatorChances: {}".format(operatorChances))

  return operatorChances


def evaluate(individual, worstScore):
  """Determine the fitness of the individual.  (Functional or non-functional)

  Attributes:
    individual (Individual): Who we are scoring
    worstScore: TODO: Argument not used
  Returns:
    No return value
  """

  logger.info("Evaluating individual {} on generation {}".format(individual.id,
                                                        individual.generation))

  global _functionalPhase

  # ConTest testing
  contest = tester.Tester()

  if _functionalPhase:
    # Check if we have encountered this mutant already
    md5Hash = hashlist.generate_hash(individual.generation, individual.id)
    if md5Hash is not None:
      hashGen, hashMem =  hashlist.find_hash(md5Hash)
      # If we have, we can skip the contest runs (saves time) and copy the testing
      # results from the first mutatn
      if hashGen != -1 and hashMem != -1:
        logger.debug("This is the same as generation {}, member {}.  Skipping evaluation".format(hashGen, hashMem))
        prevIndvidual = _population[hashMem]

        logger.debug("hashGen  : {}".format(hashGen))
        logger.debug("Score    : {}".format(prevIndvidual.score))
        logger.debug("Successes: {}".format(prevIndvidual.successes))
        logger.debug("Timeouts : {}".format(prevIndvidual.timeouts))

        if len(prevIndvidual.score) == 0 or len(prevIndvidual.score) < hashGen:
          individual.score.append(0)
        else:
          individual.score.append(prevIndvidual.score[hashGen- 1])

        if len(prevIndvidual.successes) == 0 or len(prevIndvidual.successes) < hashGen:
          individual.successes.append(0)
        else:
          individual.successes.append(prevIndvidual.successes[hashGen - 1])

        if len(prevIndvidual.timeouts) == 0 or len(prevIndvidual.timeouts) < hashGen:
          individual.timeouts.append(0)
        else:
          individual.timeouts.append(prevIndvidual.timeouts[hashGen - 1])

        if len(prevIndvidual.dataraces) == 0 or len(prevIndvidual.dataraces) < hashGen:
          individual.dataraces.append(0)
        else:
          individual.dataraces.append(prevIndvidual.dataraces[hashGen - 1])

        if len(prevIndvidual.deadlocks) == 0 or len(prevIndvidual.deadlocks) < hashGen:
          individual.deadlocks.append(0)
        else:
          individual.deadlocks.append(prevIndvidual.deadlocks[hashGen - 1])

        if len(prevIndvidual.errors) == 0 or len(prevIndvidual.errors) < hashGen:
          individual.errors.append(0)
        else:
          individual.errors.append(prevIndvidual.errors[hashGen - 1])

      # If we haven't seen this mutant before, evaluate it with contest
      else:
        logger.debug("Didn't find this mutated project hash in hash list: {}.  Adding it".format(md5Hash))
        hashlist.add_hash(md5Hash, individual.generation, individual.id)

        contest.begin_testing(_functionalPhase, False)

        individual.score.append((contest.successes * config._SUCCESS_WEIGHT) + \
                                (contest.timeouts * config._TIMEOUT_WEIGHT))

        # Store results into genome
        individual.successes.append(contest.successes)
        individual.timeouts.append(contest.timeouts)
        individual.dataraces.append(contest.dataraces)
        individual.deadlocks.append(contest.deadlocks)
        individual.errors.append(contest.errors)
    else:
      logger.error("Hash value of member {} generation {} is NULL".format(
        individual.id, individual.generation))

  else: # Non-functional phase
    # Ensure functionality is still there
    if contest.begin_testing(False, True, config._CONTEST_RUNS * config._CONTEST_VALIDATION_MULTIPLIER):
      logger.debug("Nonfunctional phase: Mutation didn't introduce any bugs")

      # Nonfunctional fitness
      individual.score.append(get_average_non_functional_score(contest,
        individual, config._CONTEST_RUNS * config._CONTEST_VALIDATION_MULTIPLIER))
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


def get_average_non_functional_score(contest, individual, numberOfRuns = config._CONTEST_RUNS):
  """Calculate the non-functional score of the individual

  Precondition:
    contest.begin_testing should be called before so the test information is
      available
  Attributes:
    contest (Tester): Instance that did the testing in the Precondition
    individual (Individual): Who we are scoring
    numberOfRuns: TODO: Argument not used
  Returns:
    avgFitness (int): Nonfunctional fitness score
  """

  logger.info("Getting average non-functional score")

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
  # Uncertainties in both
  uncRT = (maxRT - minRT) / avgRealTime
  uncVS = (maxVS - minVS) / avgVoluntarySwitches

  # Determine which one is more significant
  sigNum = 0.0
  sigUnc = 0.0
  otherNum = 0.0
  otherUnc = 0.0

  # Voluntary switches are more significant
  # TODO: In a real program, how do avgRealTime and avgVoluntarySwitches
  #       compare? Is one going to consistently be larger than the other?
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
  """During different stages of the ES, different operators may be more
  successful.  Look back config._DYNAMIC_RANKING_WINDOW generations to
  score how successful we have been at fixing data races and deadlocks.

  Attributes:
    generation (int): Current generation
  Returns:
    deadlockVotes, dataraceVotes, nonFunctionalVotes:
      Votes by operator type, eg: ({'ASAT': 1})
  """

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

    # Only weight operators for valid mutations (ignore failed mutations)
    if individual.lastOperator is None:
      continue

    # Different members will have .deadlock and .datarace arrays of different
    # lengths. For example, member 1 might have [3, 5, 1] while member 2
    # might have [2, 1]
    upperBound = 0
    if _functionalPhase:
      if len(individual.deadlocks) < generation:
        upperBound = len(individual.deadlocks) - 1
      else:
        upperBound = generation - 1
    else: # Nonfunctional
      if len(individual.score) < generation:
        upperBound = len(individual.score) - 1
      else:
        upperBound = generation - 1

    for i in xrange(beginningGeneration, upperBound):

      #logger.debug("individual.deadlocks: {}".format(individual.deadlocks))
      #logger.debug("individual.dataraces: {}".format(individual.dataraces))

      # Figure if there was any improvement from the last generation
      if _functionalPhase:
        if individual.deadlocks[i+1] < individual.deadlocks[i]:
          logger.debug("Deadlock improvement from individual {} in generation {}".
            format(individual.id, i))
          deadlockVotes[individual.appliedOperators[i]] += 1

          #logger.debug("deadlockVotes: {}".format(deadlockVotes))

        if individual.dataraces[i+1] < individual.dataraces[i]:
          logger.debug("Datarace improvement from individual {} in generation {}".
            format(individual.id, i))
          dataraceVotes[individual.appliedOperators[i]] += 1

          #logger.debug("dataraceVotes: {}".format(dataraceVotes))

      else: # Nonfunctional phase
        if individual.score[i+1] > individual.score[i]:
          logger.debug("Non-functional improvement over individual {} in generation {}".
            format(individual.id, i))
          nonFunctionalVotes[j] += 1

  logger.debug("Deadlock Votes: {}".format(deadlockVotes))
  logger.debug("Datarace Votes: {}".format(dataraceVotes))
  logger.debug("Non-Functional Votes: {}".format(nonFunctionalVotes))

  return deadlockVotes, dataraceVotes, nonFunctionalVotes


def convergence(generation, bestFitness, averageFitness):
  """The population could stagnate. That is, there is no (or little)
  improvement in fitness over config._GENERATIONAL_IMPROVEMENT_WINDOW
  generations.

  Attributes:
    generation (int): Current generation
    bestFitness (int): Highest fitness score in population
    averageFitness(int): Average fitness of population
  Returns:
    boolean: Do we stop?
  """

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
  """Check to see if we should stop the algorithm.

  Attributes:
    generation (int): Current generation
    generationLimit (int): Max number of generations allotted
  Returns:
    boolean:    Do we stop?
    individual: Correct individual, nor None if it still has bugs
  """

  global _population
  global _functionalPhase

  # If an individual passes the base number of tests
  if _functionalPhase and individual.successes[-1]/config._CONTEST_RUNS == 1:
    logger.info("Found potential best individual {}".format(individual.id))

    # ... and the individual passes the extended number of tests, we have
    # found a fix for the dataraces(s) and deadlock(s)
    if tester.Tester().begin_testing(True, True, config._CONTEST_RUNS * config._CONTEST_VALIDATION_MULTIPLIER):
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


def get_best_individual():
  """Return the highest scoring individual.

  Returns:
    individual: Highest scorer, or None
    generation: Generation where high score occurs, or 0
  """

  global _population
  global _functionalPhase

  bestScore = -2
  bestIndividual = None
  generation = -1

  for individual in _population:
    # Determine the upper bound for xrange below
    upperBound = 0
    if len(individual.score) < individual.generation:
      upperBound = len(individual.score) - 1
    else:
      upperBound = individual.generation - 1

    for i in xrange(0, upperBound):
      if individual.score[i] > bestScore:
        bestIndividual = individual
        generation = i + 1
        bestScore = individual.score[i]

  if bestIndividual is not None:
    return bestIndividual, generation
  else:
    return None, 0


def replace_lowest(generation):
  """Attempt to replace underperforming members with high-performing members or
  the original buggy program.

  Attributes:
    generation (int): Current generation of the ES

  Returns:
    No return arguments
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
  if generation % config._EVOLUTION_REPLACE_INTERVAL is not 0:
    _population = sorted(sortedMembers, key=lambda individual: individual.id)
    return

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
        logger.debug("Case 2a: Reseting ID {} generation {} back to the pristine project".
          format(sortedMembers[i].id, sortedMembers[i].generation))
        txl_operator.create_local_project(sortedMembers[i].generation,
          sortedMembers[i].id, True)
      else:
        # Reset to best individual
        logger.debug("Case 2b: Reseting ID {} generation {} back to the best individual project".
          format(sortedMembers[i].id, sortedMembers[i].generation))
        txl_operator.copy_local_project_a_to_b(sortedMembers[i].switchGeneration,
                                              sortedMembers[i].id,
                                              sortedMembers[i].generation,
                                              sortedMembers[i].id)

    # ALTERNATIVE: Reset the turnsUnderperforming at each interval
    # sortedMembers[i].turnsUnderperforming = 0

  # Resort the population by ID and reassign it to the original variable
  _population = sorted(sortedMembers, key=lambda individual: individual.id)
