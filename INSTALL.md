Install instructions for MetLab
===============================

MetLab requires a number of python modules to work properly, namely:

  * biopython
  * numpy
  * mpmath (optional)

To use the "metapprox" Experimental Design module for approximating sequencing 
need for metagenomic project - users must either compile the c-exension using 
the "install_dependencies.sh"-script, or by installing the mpmath python module.

MetLab works on Linux, or OS X.

Installing on OS X
==================

To install the required python modules run the following commands in the 
terminal:

  $ easy_install pip
  $ pip install biopython
  $ pip install numpy
  $ pip install mpmath

Then run the included "install_dependencies.sh"-script to install dependencies
that are not already in your PATH.

  $ ./install_dependencies.sh

Installing on Linux
===================

This should work on Ubuntu/debian Linux, if you use CentOS you probably know 
how to install python modules already.

  $ sudo apt-get install python-biopython
  $ sudo apt-get install pip
  $ pip install numpy
  $ pip install mpmath

Then run the included "install_dependencies.sh"-script to install dependencies
that are not already in your PATH.

  $ ./install_dependencies.sh