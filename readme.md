## Introduction
Welcome to this readme of SLM.py, a python codebase to help automating and experimenting with Santec SLM. 
This readme will guide you through the structure of this library, installing and using it, as well as adding custom features. 


## Structure
This library is mainly divided into three parts:
1. (interface.py): An interface that translates C-based Santec SLM API into python functions. This can be used independently of everything else, if one wishes to include into existing automation tool, for example.
2. (pzp.py, patterns.py) Ready to use ([Puzzlepiece](https://github.com/jdranczewski/puzzlepiece)) pieces to efficiently operate SLM. Basic phase pattern generators are included.
3. (calib_tools.py, utility.py): Higher level tools to calibrate SLM. Specific to the Generalised Ultrafast Pulse Shaping Project for Probing Metamaterials, although some of them are useful for general cases.


## Installing
Please clone this repository under the name "SantecSLM" in your working directory. Then the modules will be accessible via "import SantecSLM". You additionally need the .dll driver provoded by Santec, placed anywhere but its path will be asked on runtime.


