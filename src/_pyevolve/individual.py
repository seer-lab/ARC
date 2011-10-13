"""This module holds the 2D variable binary string genome used in ARC.

This genome is based off of a classic 2D binary string representation, but has
the capabilities to have a variable width for each row. In addition, there are
specific attributes used in the ARC evolutionary process.
"""

from _txl import txl_operator
import sys

sys.path.append("..")  # To allow importing parent directory module
import config

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
    self.lastSuccessRate = 0.0
    self.lastTimeoutRate = 0.0
    self.lastDataraceRate = 0.0
    self.lastDeadlockRate = 0.0
    self.lastErrorRate = 0.0

    # Repopulate genome with new possible mutation operator locations
    self.repopulateGenome()

  def repopulateGenome(self):
    """This function will re-populate the genome with location values.

    The values are all zero, though the number of values per row indicates
    the number of possible mutations that can occur for that operator (row).
    """

    # Delete old genome and recreate an empty one
    del self.genome[:]
    self.genome = [None] * self.height

    # Figure out the number of new possible mutation operator locations
    workingFile = config._PROJECT_SRC_DIR + "Deadlock2.java"  # TODO Auto it
    txl_operator.generate_all_mutants(self.generation, self.id, workingFile)
    hits = txl_operator.generate_representation(self.generation, 
                                                self.id, workingFile)

    # Populate the genome string with the number of hits
    for i in xrange(len(hits)):
       self.genome[i] = [0] * hits[i]

  def __repr__(self):
    """Return a string representation of this individual """

    ret = " -----Individual-----\n"
    i = 0
    for line in self.genome:
       i += 1
       ret += " Op" + repr(i) + ": "
       for item in line:
          ret += "[{}]".format(item)
       ret += "\n"
    ret += "\n"
    ret += " Id: {}\n".format(self.id)
    ret += " Generation: {}\n".format(self.generation)
    ret += " Last Operator: {}\n".format(self.lastOperator)
    ret += " Applied Operators: {}\n".format(self.appliedOperators)
    ret += " Last Success Rate: {}\n".format(self.lastSuccessRate)
    ret += " Last Timeout Rate: {}\n".format(self.lastTimeoutRate)
    ret += " Last Datarace Rate: {}\n".format(self.lastDataraceRate)
    ret += " Last Deadlock Rate: {}\n".format(self.lastDeadlockRate)
    ret += " Last Error Rate: {}\n".format(self.lastErrorRate)
    return ret
