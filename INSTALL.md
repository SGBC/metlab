Installation instructions for MetLab
===============================

MetLab requires a number of python modules to work properly, namely:

  * biopython
  * numpy
  * mpmath (optional)

To use the "metapprox" Experimental Design module for approximating sequencing
need for metagenomic project - OSX users must either compile the c-extensions using
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

    sudo apt-get install sqlite3 python-biopython python-tk
    curl -O https://bootstrap.pypa.io/get-pip.py
    sudo python get-pip.py
    sudo pip install numpy
    sudo pip install mpmath

To build the metapprox module, you'll also need gmp, mpfr and python-dev:

    sudo apt-get install libgmp3-dev libmpfr-dev python-dev

Then run the included "install_dependencies.sh"-script to install dependencies
that are not already in your PATH.

    ./install_dependencies.sh

Installing on CentOS
===================

    sudo yum install ncurses-devel python-biopython tkinter
    curl -O https://bootstrap.pypa.io/get-pip.py
    sudo python get-pip.py
    sudo pip install mpmath

To build the metapprox module, you'll also need gmp, mpfr and python-dev:

    sudo yum install gmp-devel mpfr-devel

Then run the included "install_dependencies.sh"-script to install dependencies
that are not already in your PATH.

    ./install_dependencies.sh


Custom Kraken Databases
===================


Although the default kraken database gives decent results, it was not designed with viruses in mind. We provide two databases enriched in Viruses.

Theses databases are built using combination of RefSeq (Archea + Bacteria) and the phages and viral divisions of GenBank. They can be found below:  

| Database | size (tar.gz) | size (unpacked)
--- | --- | ---
|[ superdb](http://77.235.253.14/metlab/superdb_20150723.tar.gz) | 42G | 86.3G
|[ mini superdb](http://77.235.253.14/metlab/mini_super_20150723.tar.gz) | 4G | 13.2G

Once downloaded, unpack the archive and modify the kraken_db path in the 'Run pipelines' module to point to the correct folder.
