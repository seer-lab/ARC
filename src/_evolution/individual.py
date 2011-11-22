"""This module holds the 2D variable binary string genome used in ARC.

This genome is based off of a classic 2D binary string representation, but has
the capabilities to have a variable width for each row. In addition, there are
specific attributes used in the ARC evolutionary process.
"""

from _txl import txl_operator
import sys

sys.path.append("..")  # To allow importing parent directory module
import config

import logging
logger = logging.getLogger('arc')

class Individual():
  """A 2D binary string that has a variable width for each row.

  Additionally, there exists attributes related to ARC evolution.

  Attributes:
  height (int): number of mutation operators used, also the number of rows
  genome ([int][int]): a 2D binary string of txl mutation locations
  id (int): a unique id for this individual
  lastOperator (string): the last used operator for this individual
  appliedOperators ([string]): a list of applied operators to this individual
  lastSuccessRate (double): the last individual had what rate of successes
  lastTimeoutRate (double): the last individual had what rate of timeouts
  lastDataraceRate (double): the last individual had what rate of dataraces
  lastDeadlockRate (double): the last individual had what rate of deadlocks
  lastErrorRate (double): the last individual had what rate of errors
  """

  def __init__(self, height, id):
    """Initializes the individual using the possible TXL mutation locations."""

    self.genome = []

    # The number of mutation operators in use
    self.height = height

    # Additional information that is tracked
    self.id = id
    self.generation = 0
    self.lastOperator = ""
    self.appliedOperators = []

    self.successes = []
    self.timeouts = []
    self.dataraces = []
    self.deadlocks = []
    self.errors = []
    self.realTime = []
    self.wallTime = []
    self.voluntarySwitches = []
    self.involuntarySwitches = []
    self.percentCPU = []
    self.goodRuns = []  # True || False

    self.score = []
    self.switchGeneration = 0

    self.turnsUnderperforming = 0

  def repopulateGenome(self, functionalPhase):
    """This function will re-populate the genome with location values.

    The values are all zero, though the number of values per row indicates
    the number of possible mutations that can occur for that operator (row).
    """

    # Acquire set of operators to use
    if functionalPhase:
      mutationOperators = config._FUNCTIONAL_MUTATIONS
    else:
      mutationOperators = config._NONFUNCTIONAL_MUTATIONS

    # Delete old genome and recreate an empty one
    del self.genome[:]
    self.genome = [None] * self.height

    # Figure out the number of new possible mutation operator locations
    txl_operator.mutate_project(self.generation, self.id, mutationOperators)
    hits = txl_operator.generate_representation(self.generation, self.id,
                                                mutationOperators)

    # Populate the genome string with the number of hits
    # for i in xrange(len(hits)):
    #    self.genome[i] = [0] * hits[i]
    i = 0
    for mutationOp in mutationOperators:
      if mutationOp[1]:
        self.genome[i] = [0] * hits[mutationOp[0]]
        i += 1


  def __repr__(self):
    """Return a string representation of this individual """

    ret = " -----Individual-----\n"
    i = 0
    for line in self.genome:
       i += 1
       ret += " Op" + repr(i) + ": "  # TODO Use the actual op name
       for item in line:
          ret += "[{}]".format(item)
       ret += "\n"
    ret += "\n"
    ret += " Id: {}\n".format(self.id)
    ret += " Generation: {}\n".format(self.generation)
    ret += " Switch Generation: {}\n".format(self.switchGeneration)
    ret += " Last Operator: {}\n".format(self.lastOperator)
    ret += " Applied Operators: {}\n".format(self.appliedOperators)
    ret += " Successes: {}\n".format(self.successes)
    ret += " Real Time: {}\n".format(self.realTime)
    ret += " Wall Time: {}\n".format(self.wallTime)
    ret += " Voluntary Switches: {}\n".format(self.voluntarySwitches)
    ret += " Involuntary Switches: {}\n".format(self.involuntarySwitches)
    ret += " Percent CPU {}\n".format(self.percentCPU)
    ret += " Score: {}\n".format(self.score)
    return ret


  def clone(self, height, i):
    newIndividual = Individual(height, 0)
    newIndividual.id = i
    newIndividual.generation = self.generation
    newIndividual.lastOperator = self.lastOperator
    newIndividual.appliedOperators = self.appliedOperators[:]
    newIndividual.successes = self.successes[:]
    newIndividual.timeouts = self.timeouts[:]
    newIndividual.dataraces = self.dataraces[:]
    newIndividual.deadlocks = self.deadlocks[:]
    newIndividual.errors = self.errors[:]
    newIndividual.realTime = self.realTime[:]
    newIndividual.wallTime = self.wallTime[:]
    newIndividual.voluntarySwitches = self.voluntarySwitches[:]
    newIndividual.involuntarySwitches = self.involuntarySwitches[:]
    newIndividual.percentCPU = self.percentCPU[:]
    newIndividual.goodRuns = self.goodRuns[:]
    newIndividual.score = self.score[:]
    newIndividual.switchGeneration = self.switchGeneration
    return newIndividual
