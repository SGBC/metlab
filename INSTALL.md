Installation instructions for MetLab
===============================

MetLab requires a number of python modules to work properly, namely:

  * biopython
  * numpy
  * mpmath (optional)

To use the "metapprox" Experimental Design module for approximating sequencing
need for metagenomic project - users must either compile the c-exension using
the "install_dependencies.sh"-script, or by installing the mpmath python module.

MetLab installation was tested on Mac OSX 10.10.5, Ubuntu 14.04 and Centos 7.

Installing on OS X
==================

To install the required python modules run the following commands in the
terminal:

    easy_install pip
    pip install biopython
    pip install numpy
    pip install mpmath

Then run the included "install_dependencies.sh"-script to install dependencies
that are not already in your PATH.

    ./install_dependencies.sh

Installing on Ubuntu
===================

    sudo apt-get install python-biopython  
    curl -O https://bootstrap.pypa.io/get-pip.py
    sudo python get-pip.py
    sudo pip install numpy
    sudo pip install mpmath

Then run the included "install_dependencies.sh"-script to install dependencies
that are not already in your PATH.

    ./install_dependencies.sh

Installing on CentOS
===================
