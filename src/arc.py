"""This module is responsible for starting the Automatic Concurrency Repair.

The entry point for ARC is found in this module. The configurations are held
within the config.py module.
"""

import config
import argparse
from _contest import contester
from _evolution import evolution
from _txl import txl_operator

import logging
logger = logging.getLogger('arc')

def main():
  """The entry point to ARC, to start the evolutionary approach."""

  # Setup ConTest
  contester.setup()

  # Compiling initial project
  txl_operator.compile_project()

  # Initial run for ConTest
  contester.test_execution(config._CONTEST_RUNS * config._CONTEST_VALIDATION_MULTIPLIER)

  # Run evolution
  evolution.start()

# If this module is ran as main
if __name__ == '__main__':

  # Define the argument options to be parsed
  parser = argparse.ArgumentParser(
    description="ARC: Automatically Repair Concurrency bugs in Java "\
                  "<https://github.com/sqrg-uoit/arc>",
    version="ARC 0.2.0",
    usage="python arc.py")

  # Parse the arguments passed from the shell
  options = parser.parse_args()

  main()
