from _contest import contester
import argparse

def main():
  # Start the Contest setup
  contester.setup()
  contester.run_contest()

# If this module is ran as main
if __name__ == '__main__':

  # Define the argument options to be parsed
  parser = argparse.ArgumentParser(
    description = "ARC: Automatically Repair Concurrency bugs in Java "\
                  "<https://github.com/sqrg-uoit/arc>",
    version = "ARC 0.1.0",
    usage = "python arc.py")

  # Parse the arguments passed from the shell
  options = parser.parse_args()

  main()
