#Information
This program will automatically repair concurrency Java bugs using a genetic algorithmic approach.

#Pre-Requirements
This program was developed using Python 2.7. This version should be used for best results due to compatibility.

Two external tools are necessary as well:

1. IBM's [ConTest](http://www.alphaworks.ibm.com/tech/contest?open&S_TACT=105AGX59&S_CMP=GR&ca=dgr-lnxw03awcontest "ConTest")
2. [TXL](http://www.txl.ca/ndownload.html "TXL")

#Execution
1. Download the source code and place it into a directory of choice.
2. Download IBM's [ConTest](http://www.alphaworks.ibm.com/tech/contest?open&S_TACT=105AGX59&S_CMP=GR&ca=dgr-lnxw03awcontest "ConTest"), and place the _ConTest.jar_ and the _KingProperties_ files into the ```/lib/ConTest/``` directory.
3. Download and install [TXL](http://www.txl.ca/ndownload.html "TXL").
4. Place the target project's source code in the ```/input/source/``` directory.
5. Place the target project's class files in the ```/input/class/``` directory.
5. Execute using the following command from the root directory, ```python arc.py [options] [-s sourceDir] [-t testDir] [-o outputDir] [-m mainClass]```.

#Options
To see a list of the options run the following command ```python arc.py -h```
