#!/usr/bin/env python2.7

import sys
import subprocess

if len(sys.argv) < 2:
    print "USAGE: %s kraken_report" % (sys.argv[0])
    sys.exit(0)

levels = []
out_temp = open(sys.argv[1] + "_temp", 'w')

with open(sys.argv[1], 'r') as file:
    for i, row in enumerate(file):
        cols = row.strip().split("\t")
        level = len(cols[-1].split("  "))-1
        if level:
            while len(levels) < level:
                levels += [""]
            levels[level-1] = cols[-1].split("  ")[-1]
            out_temp.write("\t".join(cols[:-1] + levels[:level]))
            out_temp.write("\n")
        else:
            out_temp.write("\t".join(cols))
            out_temp.write("\n")
out_temp.close()


out_temp = open(sys.argv[1] + "_temp", 'r')
out = open(sys.argv[1].split('.')[0] + ".krona.in", 'w')

subprocess.call(['cut', '-f3,6-'], stdin=out_temp, stdout=out)
out.close()
