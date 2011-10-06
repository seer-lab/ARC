"""Run TXL to create the mutant programs.  Count the number of instances of each and return the count in a list.

"""

import sys
import subprocess
import tester
import os
import timeit
import tempfile

import config

def generate_mutants(self, generation, member):
      # Loop over the selected operators in the config file
      for i in range(1, ... + 1):	
         # If the operator is selected

         # Look for a /temp/[generation]/[member]/[OPNAME] directory.  

         # If it doesn't exist, create it

         # If it exists, delete any files and subdirectories in it

         # Start a TXL process to generate mutants in 
         # /temp/[generation]/[member]/[OPNAME]
         process = subprocess.Popen(['txl', '-v',
                        '-Xmx{}m'.format(config._PROJECT_TEST_MB), '-cp',
                        config._PROJECT_CLASSPATH, '-javaagent:' +
                        config._CONTEST_JAR, '-Dcontest.verbose=0',
                        config._PROJECT_TESTSUITE], stdout=outFile,
                        stderr=errFile, cwd=config._PROJECT_DIR, shell=False)

      
def count_mutants(self, generation, member):


