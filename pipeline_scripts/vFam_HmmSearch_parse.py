#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import division
import argparse
import logging
from collections import defaultdict
import ast


class vFam_HmmSearch_parse( object ):

    """vFam HMMsearch results parser for tblout output """

    __name__ = "vFam_HmmSearch_parse"
    __version__ = "0.1.0"

    def __init__(self, tbloutfile, annotdir, evalue, outfile, krona_input):
        self.resfile = tbloutfile
        self.annotdir = annotdir
        self.evalue = float(evalue)
        self.outfile = outfile
        self.krona_in = krona_input


    def run(self):
        if not hasattr(self, "log"):
    		self.set_log()
        self.log.info("\n%s" % self.welcome())

        dic_res = self.read_tblout()
        vFam_dic = self.create_vFam_dic(dic_res)
        self.write_output_file(dic_res, vFam_dic)
        self.vfam_to_krona(self.outfile)
        print(len(dic_res.keys()))

    def read_tblout(self):

        with open(self.resfile) as f:
            #HoneyBee_reads_454_good_Am_bt2_rep_c4930_1_465_+    -          vFam_1015            -               0.13    9.0  12.0      0.13    9.0  12.0   1.1   1   0   0   1   1   1   0 -
            lst_res = []
            for line in f:
                if line.startswith('#'):
                    pass
                else:
                    line = line.split()
                    #print line
                    subj_seq = line[0]
                    vFam_q = line[2]
                    evalue = float(line[4])
                    if evalue<=self.evalue:
                        lst_res.append((subj_seq, (vFam_q, evalue)))
            f.close()
        # dict creation to store seq_headers(keys) with list of matching (vFam, evalue)
        dic_res = defaultdict(list)
        for seqh, efam in lst_res:
            dic_res[seqh].append(efam)

        new_dic = {}
        for seqh, efam in dic_res.iteritems():
            if len(efam)>1:
                # find the minimum evalue in the list of tuples (vfam, evalue)
                mineval = min([efam[x][1] for x in range(len(efam))])
                # find the vFam associated with the best evalue
                vFam_mineval = efam[[val[1] for val in efam].index(mineval)][0]
                new_lst = [vFam_mineval, mineval]
            else:
                new_lst = list(efam[0])

            ## new_dic containing the best match list as value:
            ## vFam (idx 0) and the associated eval (idx 1)
            new_dic[seqh] = new_lst

        return new_dic

    def create_vFam_dic(self, res_dic):
        vFam_dic = {}
        for seq, lst in res_dic.items():
            vfam_id = lst[0]
            if vfam_id not in vFam_dic.keys():
                # get info with annotation file for vfam_id
                vfam_obj = self.retrieve_annotations(vfam_id)
                vFam_dic[vfam_id] = vfam_obj

        return vFam_dic

    def retrieve_annotations(self,vfam_id):
        vfam_obj = vFam(vfam_id)
        # vFam_1005_annotations.txt
        annot_file = self.annotdir+"/"+vfam_id+"_annotations.txt"
        with open(annot_file) as f:
            vfam_obj.cluster = int(f.readline().split("\t")[1])
            vfam_obj.num_seq = int(f.readline().split("\t")[1])
            vfam_obj.length = int(f.readline().split("\t")[1])
            vfam_obj.rel_ent_pos = float(f.readline().split("\t")[1])
            vfam_obj.tot_rel_ent = float(f.readline().split("\t")[1])
            families = f.readline()
            genera = f.readline()
        f.close()

        vfam_obj.fam_dic = eval(families.split("\t")[1][:-1])
        vfam_obj.gen_dic = eval(genera.split("\t")[1][:-1])

        return vfam_obj

    def write_output_file(self, res_dic, vfam_dic):
        savefile = open(self.outfile, 'w')

        head = ["seq_header", "best_vFam", "evalue", "families", "genera", "\n"]
        savefile.write("\t".join(head))

        for seq, res in res_dic.items():
            line = [seq, res[0], str(res[1]), str(vfam_dic[res[0]].fam_dic), str(vfam_dic[res[0]].gen_dic), "\n"]

            savefile.write("\t".join(line))

        savefile.close()

    def vfam_to_krona(self, vfam_file):
        vfam_dic = defaultdict(int)
        families_dic = {}
        genera_dic = {}
        with open(vfam_file, 'r') as vfam_file:
            vfam_file.readline()  # get rid of the header
            for line in vfam_file:
                splitted_line = line.split('\t')

                vfam = splitted_line[1]
                vfam_dic[vfam] += 1

                families = ast.literal_eval(splitted_line[3])  # safe eval of dict
                families_dic[vfam] = families
                genera = ast.literal_eval(splitted_line[4])
                genera_dic[vfam] = genera

        with open(self.krona_in, 'w') as o:
            for vfam, n_reads in vfam_dic.items():
                fam_total = sum(families_dic[vfam].values())
                for fam, fam_prop in families_dic[vfam].items():
                    gen_total = sum(genera_dic[vfam].values())
                    for genera, gen_prop in genera_dic[vfam].items():
                        n = (n_reads * (fam_prop / fam_total)) * (gen_prop / gen_total)
                        o.write('%.3f\t%s\t%s\t%s\n' % (n, fam, vfam, genera))


    def set_log(self, name = None, level = logging.INFO, handler = None):
        "Sets up logging using the given log name and level."
        name = self.__name__ if not name else name
        self.log = logging.getLogger(name)
    	if handler:
    		handler.setLevel(level)
    		self.log.addHandler(handler)

    def welcome(self, width = 80):
    	format_string = "{:%i}" % (width - 4)
    	msg  = "%s\n" % ("*"*width)
    	msg += "* %s *\n" % (format_string.format(("%s. v. %s" \
                            % (self.__name__, self.__version__))))
    	msg += "* %s *\n" % (format_string.format(""))
    	msg += "*"*width
    	return msg

def parser():
    parser = argparse.ArgumentParser(description = vFam_HmmSearch_parse.__doc__)

    parser.add_argument("-t", "--tblout", help = "HMM search tblout output file")
    parser.add_argument("-a", "--annotdir", help = "vFam annotations directory")
    parser.add_argument("-e", "--evalue", help = "evalue treshold to retrieve hits")
    #parser.add_argument("-s", "--seqfile", help = "Protein database sequences file")
    parser.add_argument("-o", "--outfile", help = "Output file")
    parser.add_argument("-k", "--krona_input", help = "Output file for Krona")
    parser.add_argument("-v", "--verbose", action = "count", default = 2, help="Increase output Verbosity")
    parser.add_argument("-q", "--quiet", action = "count", default = 0, help="Decrease output Verbosity")

    args = parser.parse_args()
    return args

class vFam(object):
    def __init__(self, vFam_id):
        self.id = vFam_id
        self.cluster = 0
        self.num_seq = 0
        self.length = 0
        self.rel_ent_pos = 0.0
        self.tot_rel_ent = 0.0
        self.fam_dic = {}
        self.gen_dic = {}


if __name__ == '__main__':

    args = parser()

    app = vFam_HmmSearch_parse(args.tblout, args.annotdir, args.evalue, args.outfile, args.krona_input)
    log_name = app.__name__
    level = max(10, 50-(args.verbose-args.quiet)*10)

    print(log_name)

    log = logging.getLogger(log_name)
    log.setLevel(level)
    formatter = logging.Formatter( ('%(asctime)s %(levelname)s: %(message)s') )

    console_handler = logging.StreamHandler()
    console_handler.setLevel( level )
    console_handler.setFormatter(formatter)
    log.addHandler(console_handler)

    app.set_log(log_name, level, console_handler)
    app.run()
