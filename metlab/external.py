#!/usr/bin/env python2.7

import os
import time
import logging
import threading
from subprocess import Popen, PIPE

class External(threading.Thread):
    
    def __init__(self, name="", args = [], log_name = "external", pid = 0, log_level = logging.INFO):
        threading.Thread.__init__(self)
        self.name = name
        self.args = args
        self.pid = pid
        self.log = logging.getLogger( log_name )
        self.log.setLevel( log_level )
        self.status = "idle"
        self.retval = None
        self._stop = threading.Event()
        self.started = False
        
        self.log.info("External: %s" % name)
        self.log.info("    args: %s" % args)
    
    def run(self):
        try:
            self.status = "running"
            self.log.info("Starting %s" % self.name)
            self.log.info("cmd: %s" % ([self.name] + self.args))
            try:
                if self.args[-1].startswith(">"):
                    self.process = Popen([self.name] + self.args[:-1], stdout=open(self.args[-1][1:], "w"), stderr=PIPE)
                else:
                    self.process = Popen([self.name] + self.args, stdout=PIPE)
                self.started = True
                self.retval = self.process.communicate()[0].strip()
            except Exception as e:
                self.log.error(e)
            
            if self._stop.isSet():
                self.log.info("%s aborted" % self.name)
                self.process.kill()
                self.status = "aborted"
            else:
                self.log.info("Finished Running %s" % self.name)
        except Exception as e:
            self.status = "aborted"
            print e
        self.status = "completed"
        return self.retval
    
    def stop(self):
        self.process.kill()
        self._stop.set()
