# MetLab
MetLab - Metagenomics Analysis Pipeline

MetLab is a convenient tool for performing basic metagenomic tasks.
The tool has three distinct parts:

  * Experimental design

    This part of the tool is based on Wendl, et _al._ "Coverage theories for
    metagenomic DNA sequencing based on a generalization of Stevens' theorem"
    (http://www.ncbi.nlm.nih.gov/pubmed/22965653). It can be used to approximate
    the amount of sequencing needed to answer a given metagenomic question.

  * Metagenomic sequencing simulator

    This tool can be used to create a statistical profile from real world
    sequencing data, and may then be used to download random viral genomes and
    create simulated data sets.

  * Metagenomic analysis pipeline

    The main function of the MetLab is to run a metagenomic classification
    pipeline. The pipeline is based on input from NGS sequencing data, and
    can perform data cleaning and pre-processing, host-genome mapping to
    remove contamination, assembly, as well as taxonomic binning.

## Installation

For Installing MetLab, please refer to [INSTALL.md](INSTALL.md)

The custom Kraken database can be found below:

* [superdb](http://77.235.253.14/metlab/superdb_20150723.tar.gz)
* [mini superdb](http://77.235.253.14/metlab/mini_super_20150723.tar.gz)

## USAGE
