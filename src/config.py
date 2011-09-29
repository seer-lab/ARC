import os

# System variables
_ROOT_DIR = os.getcwd() + os.sep + os.pardir + os.sep +  os.pardir + os.sep
_MAX_MEMORY_MB = 2000
_MAX_CORES = 2
 
# Target project variables
_PROJECT_DIR = _ROOT_DIR + "input/joda-time-2.0/"
_PROJECT_SRC_DIR = _PROJECT_DIR + "src/main/java/" 
_PROJECT_TEST_DIR = _PROJECT_DIR + "src/test/java/"
_PROJECT_CLASS_DIR = _PROJECT_DIR + "bin/"
_PROJECT_PREFIX = "org.joda.time"
_PROJECT_TESTSUITE = "org.joda.time.TestAll"
_PROJECT_CLASSPATH = "/home/jalbert/workspace/arc/input/joda-time-2.0/build/classes:/home/jalbert/workspace/arc/input/joda-time-2.0/build/tests:/home/jalbert/workspace/arc/input/joda-time-2.0/build/classes/org/joda/time/tz/data:/home/jalbert/workspace/arc/input/joda-time-2.0/lib/joda-convert-1.1.jar:/usr/share/java/apache-ant/lib/ant-launcher.jar:/usr/share/java/apache-ant/lib/ant-apache-bsf.jar:/usr/share/java/apache-ant/lib/ant-junit.jar:/usr/share/java/apache-ant/lib/ant.jar:/usr/share/java/apache-ant/lib/ant-apache-xalan2.jar:/usr/share/java/apache-ant/lib/ant-commons-logging.jar:/usr/share/java/apache-ant/lib/ant-jdepend.jar:/usr/share/java/apache-ant/lib/ant-junit4.jar:/usr/share/java/apache-ant/lib/ant-jai.jar:/usr/share/java/apache-ant/lib/ant-javamail.jar:/usr/share/java/apache-ant/lib/ant-apache-bcel.jar:/usr/share/java/apache-ant/lib/ant-jmf.jar:/usr/share/java/apache-ant/lib/ant-commons-net.jar:/usr/share/java/apache-ant/lib/ant-antlr.jar:/usr/share/java/apache-ant/lib/ant-apache-regexp.jar:/usr/share/java/apache-ant/lib/junit.jar:/usr/share/java/apache-ant/lib/ant-swing.jar:/usr/share/java/apache-ant/lib/ant-netrexx.jar:/usr/share/java/apache-ant/lib/ant-testutil.jar:/usr/share/java/apache-ant/lib/ant-apache-oro.jar:/usr/share/java/apache-ant/lib/ant-jsch.jar:/usr/share/java/apache-ant/lib/ant-apache-resolver.jar:/usr/share/java/apache-ant/lib/ant-apache-log4j.jar:/usr/lib/jvm/java-6-openjdk/lib/tools.jar"
# TODO auto figure classpath if Ant or MVN exist

# ConTest variables
_CONTEST_DIR = _ROOT_DIR + "/lib/ConTest/"
_CONTEST_KINGPROPERTY = _CONTEST_DIR + "KingProperties"
_CONTEST_JAR = _CONTEST_DIR + "ConTest.jar"
_CONTEST_RUNS = 20
_CONTEST_TIMEOUT_SEC = 2.5  # If None then it is 2x the normal exection time
_TESTSUITE_AVG = 1  # Number of test executions for finding the average time

# Mutation operator variables

# Pyevolve variables
