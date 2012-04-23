"""This module is responsible for starting the Automatic Concurrency Repair.

The entry point for ARC is found in this module. The configurations are held
within the config.py module.
"""

import config
import argparse
import subprocess
import tempfile
import re
import shutil
import os
import os.path
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

  # Acquire classpath dynamically using 'ant test'
  if config._PROJECT_CLASSPATH is None:
    outFile = tempfile.SpooledTemporaryFile()
    errFile = tempfile.SpooledTemporaryFile()
    antProcess = subprocess.Popen(['ant', '-v', config._PROJECT_TEST], stdout=outFile,
                    stderr=errFile, cwd=config._PROJECT_DIR, shell=False)
    antProcess.wait()
    outFile.seek(0)
    outText = outFile.read()
    outFile.close()
    config._PROJECT_CLASSPATH = re.search("-classpath'\s*\[junit\]\s*'(.*)'", outText).groups()[0]

  # Initial run for ConTest (Acquire dynamic timeout value)
  contestTime = contester.run_test_execution(config._CONTEST_RUNS * config._CONTEST_VALIDATION_MULTIPLIER)
  config._CONTEST_TIMEOUT_SEC = contestTime * config._CONTEST_TIMEOUT_MULTIPLIER
  logger.info("Using a timeout value of {}s".format(config._CONTEST_TIMEOUT_SEC))

  logger.info("Cleaning TMP directory")
  if not os.path.exists(config._TMP_DIR):
    os.makedirs(config._TMP_DIR)
  else:
    shutil.rmtree(config._TMP_DIR)
    os.makedirs(config._TMP_DIR)

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
