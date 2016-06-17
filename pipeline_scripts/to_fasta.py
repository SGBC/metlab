#!/usr/bin/env python2.7
"""
Simple convertion script for biopython recognized file types to fasta format.
"""

import os
import sys
import gzip
from Bio import SeqIO

def to_fasta(filename, outfile = None):

    try:
        file_in = gzip.open(filename) if filename.endswith(".gz") else open(filename)
    except Exception as e:
        sys.stderr.write("ERROR: Couldn't open input file %s\n" % filename)
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

    ext = filename.rstrip('.gz').split('.')[-1]
    ext = "fastq" if ext in ["fq"] else ext

    if not outfile:
        outfile = filename.split("/")[-1].rstrip('.gz')
        outfile = ".".join( outfile.split(".")[:-1] ) + ".fasta"
        outfile += ".gz" if filename.endswith(".gz") else ""
    file_out = gzip.open(outfile, "w") if outfile.endswith(".gz") else open(outfile, "w")

    print "%s -> %s" % (filename, outfile)
    try:
        for record in SeqIO.parse(file_in, ext):
            SeqIO.write(record, file_out, "fasta")
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        os.remove(outfile)
        sys.exit(1)

if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser( description = __doc__ )

    parser.add_argument("infile", nargs="+", help="Biopython recognized file(s) to convert")
    parser.add_argument("-o", "--output", help="output file name, default is same as in-file")

    args = parser.parse_args()

    for i, filename in enumerate(args.infile):
        outfile = args.output + ".%i" % (i+1) if len(args.infile) > 1 else args.output
        to_fasta(filename, outfile)
