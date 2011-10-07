"""This module holds the 2D variable binary string genome used in ARC.

This genome is based off of a classic 2D binary string representation, but has
the capabilities to have a variable width for each row. In addition, there are
specific attributes used in the ARC evolutionary process.
"""

from pyevolve import GenomeBase
from pyevolve import Consts
from pyevolve import Util
from random import randint


class G2DVariableBinaryString(GenomeBase.GenomeBase):
   """A 2D binary string that has a variable width for each row.

   Additionally, there exists attributes related to ARC evolution.

   Attributes:
    height (int): number of mutation operators used, also the number of rows
    genomeString ([int][int]): actual 2D binary string representation
    id (int): a unique id for this individual
    lastOperator (string): the last used operator for this individual
    appliedOperators ([string]): a list of applied operators to this individual
    lastSuccessRate (double): the last individual had what rate of successes
    lastTimeoutRate (double): the last individual had what rate of timeouts
    lastDataraceRate (double): the last individual had what rate of dataraces
    lastDeadlockRate (double): the last individual had what rate of deadlocks
    lastErrorRate (double): the last individual had what rate of errors
   """

   def __init__(self, height):
      """Initializes the genome using the possible TXL mutation locations."""

      GenomeBase.GenomeBase.__init__(self)

      self.genomeString = []

      # The number of mutation operators in use
      self.height = height

      # Additional information that is tracked
      self.id = None
      self.lastOperator = None
      self.appliedOperators = None
      self.lastSuccessRate = None
      self.lastTimeoutRate = None
      self.lastDataraceRate = None
      self.lastDeadlockRate = None
      self.lastErrorRate = None

      # Repopulate genome with new possible mutation operator locations
      self.repopulateGenome()

   def returnHits(self):
      """Stub to return an array of random mutation operator location."""

      return [randint(0, 10), randint(0, 10), randint(0, 10)]

   def repopulateGenome(self):
      """This function will re-populate the genomeString with location values.

      The values are all zero, though the number of values per row indicates
      the number of possible mutations that can occur for that operator (row).
      """

      # Delete old genome and recreate an empty one
      del self.genomeString[:]
      self.genomeString = [None] * self.height

      # Figure out the number of new possible mutation operator locations
      hits = self.returnHits()  # TODO Acquired using TXL mutation locater
      for i in xrange(len(hits)):
         self.genomeString[i] = [0] * hits[i]

   def __repr__(self):
      """Return a string representation of this genome """

      ret = GenomeBase.GenomeBase.__repr__(self)
      ret += " -----Genome-----\n"
      i = 0
      for line in self.genomeString:
         i += 1
         ret += " Op" + repr(i) + ": "
         for item in line:
            ret += "[{}]".format(item)
         ret += "\n"
      ret += "\n"
      ret += " Id: {}\n".format(self.id)
      ret += " Last Operator: {}\n".format(self.lastOperator)
      ret += " Applied Operators: {}\n".format(self.appliedOperators)
      ret += " Last Success Rate: {}\n".format(self.lastSuccessRate)
      ret += " Last Timeout Rate: {}\n".format(self.lastTimeoutRate)
      ret += " Last Datarace Rate: {}\n".format(self.lastDataraceRate)
      ret += " Last Deadlock Rate: {}\n".format(self.lastDeadlockRate)
      ret += " Last Error Rate: {}\n".format(self.lastErrorRate)
      return ret

   def copy(self, genome):
      """Copies this genome's values onto the specified genome."""

      GenomeBase.GenomeBase.copy(self, genome)
      genome.height = self.height
      genome.id = self.id
      genome.lastOperator = self.lastOperator
      genome.appliedOperators = self.appliedOperators
      genome.lastSuccessRate = self.lastSuccessRate
      genome.lastTimeoutRate = self.lastTimeoutRate
      genome.lastDataraceRate = self.lastDataraceRate
      genome.lastDeadlockRate = self.lastDeadlockRate
      genome.lastErrorRate = self.lastErrorRate
      for i in xrange(self.height):
         genome.genomeString[i] = self.genomeString[i][:]

   def clone(self):
      """Creates and returns a new clone of this genome."""

      newcopy = G2DVariableBinaryString(self.height)
      self.copy(newcopy)

      # Not sure if it is needed
      newcopy.id = self.id
      newcopy.lastOperator = self.lastOperator
      newcopy.appliedOperators = self.appliedOperators
      newcopy.lastSuccessRate = self.lastSuccessRate
      newcopy.lastTimeoutRate = self.lastTimeoutRate
      newcopy.lastDataraceRate = self.lastDataraceRate
      newcopy.lastDeadlockRate = self.lastDeadlockRate
      newcopy.lastErrorRate = self.lastErrorRate
      
      return newcopy
