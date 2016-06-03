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


## USAGE

Start metlab by typing

    ./MetLab.py

in your terminal from the directory where you installed MetLab. It will launch a GUI, with separated tabs for the three distinct modules.

Alternatively, you can launch MetLab from the finder by right clicking on MetLab.py, and select **open with -> python launcher**

<p style="text-align:center;"><img src=examples/launch.png/ height=350></p>

### Experimental design

The experimental design part of MetLab can be used to approximate the amount of sequencing you need for your project.

Given an estimation of species diversity as well as estimated genome size range the module calculates the probability of covering all included genomes (such as at least one contig is produced from each genome) given a theoretical optimal assembly. If a single run is not sufficient to reach that probability the module goes into iterative state, consecutively adding simulated runs until coverage probability is reach or a maximum of 10 runs are simulated

From the experimental design tab, simply enter the estimated lowest abundance of the viruses you want to detect, and their estimated genome size, then click **calculate**.

<p style="text-align:center;"><img src=examples/exp_design.png/ height=500></p>


### Metagenomic sequencing simulator

The module produces viral datasets from sequencing profiles with realistic error profiling and known taxonomic content. It is especially useful if you want to test a new method of classification.

<p style="text-align:center;"><img src=examples/sim_data.png/ height=500></p>

The module will output one (or two if you selected paired-end read) fastq file(s) and one key file containing the viral composition of your simulated dataset.

The “key file” includes “Genome ID”, “Tax ID”, “Definition”, “Project”, and “No. Reads”, where the “Tax ID” is the NCBI taxonomy identifier, “Project” is the sequencing project identifier, and “No. Reads” is the number of reads from the species that is included in the dataset. The fastq file includes read headers formatted as ```"<record id>|ref:<genome id>-<read nr.>|pos:<start>-<end>”```, where the “record_id” and “genome_id” are the NCBI accession number and genome id respectively, and “pos” is the read position in the record sequence.

<br><br>

Alternatively, the module can be used at a command-line application, by running

    python metlab/metamaker.py

from the metlab main directory.

the options available for the command-line simulator are:

    usage: metamaker.py [-h] [-c CREATE [CREATE ...]] [-d DISTRIBUTION]
                        [-i INSERT] [-k KEYFILE] [-l LENGTH_VAR] [-o OUTPUT] [-p]
                        [-m] [-n NO_READS] [-r READ_LENGTH] [-s NO_SPECIES]
                        [-f PROFILE] [-x TAXA]
                        [-a ERROR_VARIANCE [ERROR_VARIANCE ...]]
                        [-e ERROR_FUNCTION [ERROR_FUNCTION ...]] [-v] [-q]

    optional arguments:
      -h, --help            show this help message and exit
      -c CREATE [CREATE ...], --create CREATE [CREATE ...]
                            Create new profile from file(s). (default: None)
      -d DISTRIBUTION, --distribution DISTRIBUTION
                            Read distribution, 'uniform' or 'exponential'
                            (default: uniform)
      -i INSERT, --insert INSERT
                            Matepair insert size. (default: 3000)
      -k KEYFILE, --keyfile KEYFILE
                            key filename. (default: None)
      -l LENGTH_VAR, --length_var LENGTH_VAR
                            Length variance. (default: 0.0)
      -o OUTPUT, --output OUTPUT
                            Output filename (default: output)
      -p, --progress        Display progress information for long tasks. (default:
                            False)
      -m, --matepair        Generate matepairs. (default: False)
      -n NO_READS, --no_reads NO_READS
                            Number of reads. (default: 50M)
      -r READ_LENGTH, --read_length READ_LENGTH
                            Read length (default: 200)
      -s NO_SPECIES, --no_species NO_SPECIES
                            Number of species. (default: 10)
      -f PROFILE, --profile PROFILE
                            Sequencing profile to use for read generation. Changes
                            default for reads, read_length and error_function.
                            Valid options are Illumina MiSeq, IonTorrent,
                            IonProton, IonTorrent 200bp or IonTorrent 400bp
                            (default: None)
      -x TAXA, --taxa TAXA  Taxonomic identifier of the species to download.
                            (default: viruses)
      -v, --verbose         Increase output Verbosity (default: 0)
      -q, --quiet           Decrease output Verbosity (default: 0)

    quality function arguments:
      Factors for the quality and variance functions

      -a ERROR_VARIANCE [ERROR_VARIANCE ...], --error_variance ERROR_VARIANCE [ERROR_VARIANCE ...]
                            Factors for the error variance approximation equation.
                            (default: [0])
      -e ERROR_FUNCTION [ERROR_FUNCTION ...], --error_function ERROR_FUNCTION [ERROR_FUNCTION ...]
                            Factors for the error approximation equation.
                            (default: [25.0])                        

### Metagenomic analysis pipeline

This module is the core of MetLab and offers different options to analyse metagenomes

The metagenomic analysis pipeline is based on a set of programs suited for metagenomic analysis, where a number of steps are optional, depending on the analysis. The pipeline starts with data pre-processing with Prinseq-Lite. Trimming and filtering options are set to default values (extrapolated from a normal need), but you can easily modify them by expending the **Data filtering** menu. The next steps is host genome mapping with Bowtie2, designed for metagenomic analysis from animal samples. Reads that don’t map to the host genome are extracted using SAMTOOLS, and the analysis continues with these unmapped reads.

The next step is de novo assembly with SPAdes, which is not default but can improve classification in cases where high assembly coverage is available in the sample. The analysis ends with taxonomic classification.

The only mandatory step of the pipeline is the taxonomic classification. MetLab uses [kraken](https://ccb.jhu.edu/software/kraken/) and a combination of [fraggenescan](http://omics.informatics.indiana.edu/FragGeneScan/), [hmmer](http://hmmer.org) and [vFam](http://derisilab.ucsf.edu/software/vFam/) to assign taxonomic information to reads or contigs.

If you want to only assign taxonomic information to your data and skip the quality control and trimming, filtering of the host genome and assembly steps, untick the **Data filtering**, **Reference mapping** and **Assembly** boxes, upload your reads and click **run**!

<p style="text-align:center;"><img src=examples/pipe_class_only.png/ height=500></p>


By default, the standard kraken database is used. If you wish to use our custom database (which we highly recommend!), please refer to [INSTALL.md](INSTALL.md)

In the ouput directory, you can find Krona charts describing both the classification by kraken and by hmmer.
