#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
MetaMaker is a basic tool for simulating metagenomic datasets. It downloads a 
number of genomes, splits them into reads and creates a fastq output file 
simulating a sequencing run.
"""

import os
import sys
import time
import json
import numpy
import random
import logging
import threading
import curses.ascii
from Bio import Entrez, SeqIO

# Please add your own e-mail address here!
# It makes the people at Entrez super happy!
Entrez.email = "MetaMaker@slu.se"

class MetaMaker( threading.Thread ):
    """
    Viral Metagenomic dataset simulator.

This module can be used to simulate metagenomic datasets from sequencing profiles, 
as well as create sequencing profiles from sequence data.
    """
    
    def __init__(self, outfile = "output", num_genomes = 10, log = None, log_level = logging.INFO, profile_dir = "profiles"):
        """
        Reads arguments and sets default settings.
        """
        threading.Thread.__init__(self)
        
        self.num_genomes  = num_genomes
        self.outfile      = outfile if outfile.endswith("fastq") else "%s.fastq" % outfile
        self.keyfile      = outfile if outfile.endswith("key") else "%s.key" % outfile
        self.taxa         = 'viruses'
        self.reads        = 1000
        self.read_length  = 200
        self.length_var   = 0
        self.quality_mean = [25]
        self.quality_var  = [10]
        self.distribution = 'uniform'
        self.progress     = False
        self.profile_dir  = profile_dir
        self.matepair     = True
        self.insert_size  = 500
        
        self.log = log if log else logging.getLogger( __name__ )
        self.log.setLevel( log_level )
        if not log:
            self.log_handler = logging.StreamHandler()
            self.log_handler.setLevel( log_level )
            self.log_handler.setFormatter( logging.Formatter( '%(asctime)s %(levelname)s: %(message)s', "%H:%M:%S" ) )
        self.log.addHandler(self.log_handler)
        
        self.quality_cache = []
        self.variance_cache = []
        self._progress = 0
        self._stop = threading.Event()
        self.running = False
    
    def _get_tax_id(self, data):
        """
        Attempts to get taxonomic id from NCBI, given some data.
        """
        organism = data['Organism_Name']
        for retries in xrange(5):
            try:
                search = Entrez.read(Entrez.esearch('taxonomy', organism))
                data   = Entrez.read(Entrez.esummary(db='taxonomy',
                                                     id=search['IdList'][0]))
                if data[0]['ScientificName'] != organism:
                    raise Exception("Something went wrong in the search!")
                return data[0]['TaxId']
            except Exception as e:
                pass
        
        return None
    
    def _list_ncbi(self, max = 10000):
        """
        Lists (searches) NCBI entries for the specified taxa.
        """
        self.log.info('Getting list of %s from NCBI' % self.taxa)
        term = "%s[Organism]" % self.taxa
        handle = Entrez.esearch("genome", term = term, retmax = max)
        results = Entrez.read(handle)
        self.log.info(' + Found %i %s' % (len(results['IdList']), self.taxa))
        return results['IdList']
    
    def _list(self):
        """
        Wrapper function in case more sources are added.
        """
        id_list  = []
        id_list += self._list_ncbi()
        return id_list
    
    def _make_dataset(self):
        """
        Creates the metadata for the project.
        """
        dataset = []
        avg_reads = self.reads/self.num_genomes
        
        if self.distribution.lower() == 'exponential':
            n = self.reads**(1.0/(self.num_genomes-1))
        
        ids = self._list()
        last = 0
        i = 0
        self.log.info("Making dataset")
        while i < self.num_genomes:
            if self._stop.isSet():
                break
            if ids:
                genome_id = random.choice(ids)
                ids.remove(genome_id)
            else:
                raise Exception('Not enough genomes.')
            
            new = True
            for prev in dataset:
                if prev['genome_id'] == genome_id:
                    new = False
                    break
            if not new:
                continue
            
            summary = Entrez.read(Entrez.esummary(db="genome", id=genome_id))[0]
            self.log.debug(" + Trying: %s" % summary['Organism_Name'])
            
            
            # Get a taxonomy id if we're printing a key-file
            tax_id = self._get_tax_id(summary)
            if not tax_id:
                self.log.debug("   - Failed: no tax id")
                continue
            
            # Make sure we have a nucleotide id to download the data later.
            nuc_id = None
            search_term = "%s[Organism] complete genome" % summary['Organism_Name']
            try:
                project_data = Entrez.read(Entrez.esearch("nucleotide", search_term))
                nuc_id = project_data['IdList'][0]
            except Exception as e:
                self.log.debug("   - Failed: no nuc id")
                continue
            
            self.log.info(" * Added %s to dataset" % summary['Organism_Name'])
            data = {'genome_id':genome_id, 'def':summary['DefLine'], 
                    'organism':summary['Organism_Name'],
                    'project':summary['ProjectID'], 
                    'nuc_id':nuc_id,
                    'tax_id':tax_id}
            
            if self.distribution.lower() == 'uniform':
                data['reads'] = avg_reads
            elif self.distribution.lower() == 'exponential':
                data['reads'] = max(1, int(round(n**i - last)))
                last += data['reads']
            else:
                self.log.warning("WARNING: couldn't understand distribution '%s', Defaulting to: Uniform" % \
                                 self.distribution)
                data['reads'] = avg_reads
            dataset += [data]
            i += 1
        return dataset
    
    def _make_read(self, seq):
        """
        Extracts a single, or mate-paired read from a sequence, and returns the 
        read sequence as well as the position metadata.
        """
        length = int(self.read_length)
        stdev  = numpy.sqrt(self.length_var)
        
        read_length = length + int(numpy.random.normal(0, stdev)) if stdev else length
        if self.matepair:
            mate_length = length + int(numpy.random.normal(0, stdev)) if stdev else length
            min_length = max(read_length, mate_length, self.insert_size)
        else:
            min_length  = read_length
    
        start = random.randint(0, max(0, len(seq)-min_length))
        read_pos = (start, start + read_length)
        read_seq = seq[read_pos[0]:read_pos[1]]
        read_qual = self._make_quality(read_seq)
        output = [(read_seq, read_pos, read_qual)]
    
        if self.matepair:
            mate_start = start + min_length - mate_length
            mate_pos = (mate_start, mate_start+mate_length)
            mate_seq = seq[mate_pos[0]:mate_pos[1]]
            mate_qual = self._make_quality(mate_seq)
            output += [(mate_seq, mate_pos, mate_qual)]
        return output
    
    def _make_quality(self, seq):
        """
        Simulates read quality from an error function.
        Qualities are in Sanger Fastq format (Phred+33), i.e. quality is 
        represented by an integer from 0 to 93, represented by the ascii 
        characters 33-126. 
        Errors are represented as 10^-0.0 (random base) to 10^-9.3 (super 
        accurate).
        
        ref: http://www.ncbi.nlm.nih.gov/pmc/articles/PMC2847217/?tool=pubmed
        
        This might be re-written in the future using Biopythons QualityIO,
        http://www.biopython.org/DIST/docs/api/Bio.SeqIO.QualityIO-module.html
        """
        
        output = ""
        for i, q in enumerate(seq):
            if len(self.quality_cache) <= i:
                f = numpy.poly1d(self.quality_mean)
                self.quality_cache += [f(len(self.quality_cache))]
            if len(self.variance_cache) <= i:
                v = numpy.poly1d(self.quality_var)
                self.variance_cache += [v(len(self.variance_cache))]
            
            quality = self.quality_cache[i]
            var = numpy.random.normal(0, numpy.sqrt(self.variance_cache[i]))
            if not numpy.isnan(var):
                quality += var
            quality = min(93, max(int(quality), 0))
            output += "%c" % (33+quality)
            
        return output
    
    def _write_csv(self, dataset, separator = ','):
        """
        Writes a csv file 
        """
        self.log.info('Creating Key file')
        header = ['Genome ID', 'Tax ID', 'Definition', 'Organism', 'No. Reads']
        with open(self.keyfile, 'w') as key:
            key.write( "%s\n" % (separator.join(header)) )
            for i in dataset:
                data = [i['genome_id'], i['tax_id'], i['def'], 
                        i['organism'],   i['reads']]
                key.write( "%s\n" % (separator.join(map(str,data))) )
    
    def load_profile(self, profile_name):
        """
        Loads the run values from a MetaMaker profile into the system.
        """
        profiles = self.get_profiles(None, self.profile_dir)
        if profile_name in profiles:
            profile = profiles[profile_name]
            
            self.reads        = profile['default_reads']
            self.read_length  = profile['read_length_mean']
            self.length_var   = profile['read_length_var']
            self.quality_mean = profile['quality_mean']
            self.quality_var  = profile['quality_var']
            
            self.log.info("Using profile '%s'" % profile_name)
            self.log.info(" + Number of reads: %.1e" % self.reads)
            self.log.info(" + Read length    : %i±%i Bp" % (self.read_length, numpy.sqrt(self.length_var),))
        else:
            self.log.warning("Unknown profile '%s', ignoring." % profile_name)
    
    def progress(self):
        """
        Returns the progress of the current action.
        """
        return self._progress
    
    @staticmethod
    def get_profiles(return_format = None, profile_dir = 'profiles'):
        """
        Returns a list of allowed sequencing profiles.
        """
        profiles = {}
        
        try:
            for profile in os.listdir(profile_dir):
                if profile.split('.')[-1].lower() == 'json' and profile[0] != '.':
                    data = json.load(open("%s/%s" % (profile_dir, profile)))
                    profiles[data['key']] = data
        except:
            return profiles
        
        if return_format == "human":
            keys = profiles.keys()
            if len(profiles) < 2:
                return keys[0]
            return ", ".join(keys[:-1]) + " or " + keys[-1]
        if return_format == "keys":
            return profiles.keys()
        return profiles
    
    @staticmethod
    def parse_profile(infiles, output = None, profile_dir = 'profiles'):
        min_length  = 1e12
        max_length  = 0
        length_mean = 0
        length_var  = 0
        
        min_qual    = None
        max_qual    = None
        qual_mean   = None
        qual_var    = 0
        count       = []
        
        for infile in infiles:
            for i, record in enumerate(SeqIO.parse(infile, 'fastq')):
                qual = numpy.array(record.letter_annotations['phred_quality'], 
                                   float)
                length_mean += len(record.seq)
                length_var  += len(record.seq)**2
                if len(record.seq) < min_length:
                    min_length = len(record.seq)
                if len(record.seq) > max_length:
                    max_length = len(record.seq)
            
                if qual_mean == None:
                    qual_mean = numpy.array(qual)
                    max_qual  = qual
                    min_qual  = qual
                    qual_var  = qual**2
                else:
                    for p, q in enumerate(qual):
                        if p >= len(qual_mean):
                            qual_mean = numpy.append(qual_mean, q)
                            max_qual  = numpy.append(max_qual,  q)
                            min_qual  = numpy.append(min_qual,  q)
                            qual_var  = numpy.append(qual_var, q**2)
                        else:
                            qual_mean[p] += q
                            qual_var[p] += q**2
                            if q > max_qual[p]:
                                max_qual[p] = q
                            if q < min_qual[p]:
                                min_qual[p] = q
            
                # counter to keep track of how many values are stored for each 
                # nucleotide position
                for p, q in enumerate(qual):
                    if p >= len(count):
                        count = numpy.append(count, 1.0)
                    else:
                        count[p] += 1.0
        
        # convenience variables
        tot = float(count[0]) # total number of reads
        
        mean_reads  = round(tot / len(infiles))
        length_mean = length_mean / tot
        length_var  = length_var / tot - length_mean**2
        qual_mean   = qual_mean / count
        qual_var    = qual_var / count - qual_mean**2
        
        if not output:
            output = infiles[0].split('/')[-1].split('.')[0]
        
        # least squares approximation coefficients
        
        m = numpy.polyfit(range(1,len(qual_mean)+1), qual_mean, 4)
        v = numpy.polyfit(range(1,len(qual_var )+1), qual_var,  2)
        
        # Save profile
        profile = {"key": output,
                   "default_reads": mean_reads,
                   "read_length_mean": length_mean,
                   "read_length_var": length_var,
                   "quality_mean": list(m),
                   "quality_var": list(v),
                  }

        if not output.endswith(".json"):
            output = "%s.json" % output
        with open("%s/%s" % (profile_dir, output), 'w') as out:
            out.write(json.dumps(profile, indent=True))
    
    def run(self):
        """
        Starts the job of creating a metagenomic sample set.
        """
        try:
            if self.running:
                self.log.error('Already running MetaMaker, can\'t start again.')
            self.log.info("Running MetaMaker")
            self.running = True
            if self.matepair:
                base = ".".join(self.outfile.split('.')[:-1])
                self.log.info('output: %s.1.fastq & %s.2.fastq, key-file: %s' % 
                             (base, base, self.keyfile) )
            else:
                self.log.info('output: %s, key-file: %s' % 
                             (self.outfile, self.keyfile) )
            
            dataset = self._make_dataset()
            
            # Print debug information about the dataset
            self.log.debug('DATASET:')
            tot_reads = 0
            for i in dataset:
                self.log.debug("%i\t%s" % (i['reads'], i['def']))
                tot_reads += i['reads']
            self.log.debug("TOTAL READS: %i" % tot_reads)
            
            # Create the key file
            if self.keyfile:
                self._write_csv(dataset)
                
            # Start creating the fastq output file.
            if self.matepair:
                base = ".".join(self.outfile.split('.')[:-1])
                out = open("%s.1.fastq" % base, 'w')
                mate = open("%s.2.fastq" % base, 'w')
            else:
                out = open(self.outfile, 'w')
            for metadata in dataset:
                if self._stop.isSet():
                    break
                self._progress = 0.0
                
                self.log.info("* Parsing %s" % metadata['def'])
                self.log.info("  * Downloading")
                
                for tries in xrange(5):
                    if self._stop.isSet():
                        break
                    try: 
                        data = Entrez.efetch(db="nucleotide", id=metadata['nuc_id'], 
                                             rettype="gb",    retmode="text")
                        break
                    except Exception as e:
                        self.log.warning(e)
                        self.log.info(project_data)
                        self.log.info("    * Retrying")
                        pass
                
                self.log.info("  * Creating Reads" )
                
                for record in SeqIO.parse(data,"gb"):
                    if self._stop.isSet():
                        break
                    # TODO: make use of several records if present
                    for i in xrange(int(metadata['reads'])):
                        if self._stop.isSet():
                            break
                        seqs = []
                        while not seqs:
                            if self._stop.isSet():
                                break
                            seqs = self._make_read(record.seq)
                    
                        # apply quality to read(s)
                        first = True
                        for seq, pos, quality in seqs:
                            if self._stop.isSet():
                                break
                            seq = list(seq)
                            for j, q in enumerate(quality):
                                if numpy.random.random() < (10**-((ord(q)-33)/10.0)):
                                    seq[j] = 'actg'[numpy.random.randint(4)]
                            seq = "".join(seq)
                            header = "@%s|ref:%s-%i|pos:%i-%i" % (record.id, 
                                                            metadata['genome_id'],
                                                            i, pos[0], pos[1])
                            if self.matepair:
                                if first:
                                    out.write("%s/1\n" % header)
                                    out.write("%s\n" % seq)
                                    out.write("+\n%s\n" % quality)
                                else:
                                    mate.write("%s/2\n" % header)
                                    mate.write("%s\n" % seq)
                                    mate.write("+\n%s\n" % quality)
                            else:
                                out.write("%s\n" % header)
                                out.write("%s\n" % seq)
                                out.write("+\n%s\n" % quality)
                            first = False
                        self._progress = (i+1)/float(int(metadata['reads']))
                    break
            
            out.close()
            if self.matepair:
                mate.close()
            self._progress = -1
            self.log.info("Finished. All went well!")
            if self.matepair:
                base = ".".join(self.outfile.split('.')[:-1])
                self.log.info("Results saved to %s.1.fastq & %s.2.fastq" % 
                              (base, base))
            else:
                self.log.info("Results saved to %s" % self.outfile)
        except RuntimeError as e:
            pass
        except Exception as e:
            self.log.error(e)
        self.running = False
    
    def set(self, key, value):
        """
        Sets a value in the settings.
        """
        if getattr(self, key, None) != None:
            if key == 'keyfile' and value and not value.endswith('.csv'):
                value = "%s.csv" % value
            setattr(self, key, value)
        else:
            raise Exception("Unknown key '%s'." % key)
    
    def set_log(self, name, level=logging.INFO, handler = None):
        """
        Sets up logging using the given log name and level.
        """
        self.log = logging.getLogger( name )
        if handler:
            handler.setLevel( level )
            self.log.addHandler( handler )
    
    def stop(self):
        self._stop.set()

if __name__ == '__main__':
    
    import argparse

    parser = argparse.ArgumentParser( description = __doc__,
                      formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    parser.add_argument("-c", "--create", help="Create new profile from file(s).", nargs="+", default=None)
    parser.add_argument("-d", "--distribution", help="Read distribution, 'uniform' or 'exponential'", default="uniform")
    parser.add_argument("-i", "--insert", help="Matepair insert size.", type=int, default=3000)
    parser.add_argument("-k", "--keyfile", help="key filename.", default=None)
    parser.add_argument("-l", "--length_var", help="Length variance.", default=0.0, type=float)
    parser.add_argument("-o", "--output", help="Output filename", default="output")
    parser.add_argument("-p", "--progress", default=False, action='store_true', help="Display progress information for long tasks.")
    parser.add_argument("-m", "--matepair", help="Generate matepairs.", action="store_true", default=False)
    parser.add_argument("-n", "--no_reads", help="Number of reads.", default="50M")
    parser.add_argument("-r", "--read_length", help="Read length", default="200")
    parser.add_argument("-s", "--no_species", help="Number of species.", default=10, type=int)
    parser.add_argument("-f", "--profile", default=None,
                        help=("Sequencing profile to use for read generation. Changes default for "
                              "reads, read_length and error_function. Valid options are %s") % \
                              MetaMaker.get_profiles('human'))
    parser.add_argument("-x", "--taxa", default="viruses", help=("Taxonomic identifier of the species to download."))
    
    
    funcs = parser.add_argument_group("quality function arguments", "Factors for the quality and variance functions")
    
    funcs.add_argument("-a", "--error_variance", nargs="+", type=float, default = [0],
                        help=("Factors for the error variance approximation equation.") )
    funcs.add_argument("-e", "--error_function", nargs="+", type=float, default = [25.0], 
                        help="Factors for the error approximation equation.")
    
    parser.add_argument("-v", "--verbose", action = "count", default = 0, help="Increase output Verbosity")
    parser.add_argument("-q", "--quiet",   action = "count", default = 0, help="Decrease output Verbosity")
    
    args = parser.parse_args()
    
    for arg in ['no_reads', 'read_length']:
        if eval("args.%s" % arg)[-1] in ['K', 'k']:
            exec("args.%s = int(args.%s[:-1])*1000" % (arg, arg))
        elif eval("args.%s" % arg)[-1] in ['M', 'm']:
            exec("args.%s = int(args.%s[:-1])*1000000" % (arg, arg))
        elif eval("args.%s" % arg)[-1] in ['G', 'g']:
            exec("args.%s = int(args.%s[:-1])*1000000000" % (arg, arg))
        else:
            exec("args.%s = int(args.%s)" % (arg, arg))

    level = 50-(2+args.verbose-args.quiet)*10
    level = 10 if level < 10 else level
    
    log = logging.getLogger( "MetaMaker" )
    log.setLevel( level )
    
    formatter = logging.Formatter( ('%(asctime)s | %(name)s '
                                    '%(levelname)s: %(message)s') )
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel( level )
    console_handler.setFormatter(formatter)
    
    log.addHandler(console_handler)
    
    app = MetaMaker( args.output, args.no_species )
    if args.create:
        app.parse_profile(args.create, args.output)
    else:
        if args.profile:
            app.load_profile( args.profile )
        
        app.set('keyfile',      args.keyfile)
        app.set('taxa',         args.taxa)
        app.set('reads',        args.no_reads)
        app.set('read_length',  args.read_length)
        app.set('length_var',   args.length_var)
        app.set('quality_mean', args.error_function)
        app.set('distribution', args.distribution)
        app.set('matepair',     args.matepair)
        app.set('insert_size',  args.insert)
        app.set('progress',     args.progress)
        app.run()