#!/usr/bin/env python2.7
# -*- coding: utf-8 

import os
import sys
import json
import time
import shlex
import socket
import sqlite3
import logging
import threading
from external import External

DATABASE="metlab.sqlite3"

DATABASE_SCHEMA=[
"""CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    name TEXT, 
    directory TEXT, 
    started INTEGER, 
    finished INTEGER);""",
"""CREATE TABLE IF NOT EXISTS steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    project_id INTEGER, 
    command TEXT, 
    FOREIGN KEY(project_id) REFERENCES projects(id) );""",
"""CREATE TABLE IF NOT EXISTS paths (
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    name INTEGER, 
    path TEXT);"""]

def metlab_controller(socket_name = "metlab.sock"):
    
    try: # Fork a child process so the parent can exit.
       pid = os.fork()
    except OSError as e:
       raise Exception("%d: %s" % (e.errno, e.strerror))
    if (pid == 0):
       os.setsid()
    else:
       os._exit(0)
    
    controller = MetLabController(socket_name = socket_name)
    controller.run()

class Group(object):
    
    def __init__(self, data):
        self.name     = data.get('name', "")
        self.enabled  = True
        self.optional = data.get('optional', False)
        self.commands = []
        
        for cmd in data['commands']:
            self.commands += [Command(cmd)]

class Command(object):
    
    def __init__(self, data = {}):
        self.base_command = data['command']
        self.input = data.get('in', [])
        self.output = data.get('out', {})
        self.options = {}
        self.command = self.base_command
        
        self._parse_options(data.get('options', {}))
        self.update_command()
    
    def __repr__(self):
        return self.command
    
    def _get_brackets(self, string, brackets="<>"):
        output = {}
        start = None
        
        for i, c in enumerate(string):
            if c == brackets[0]:
                start = i
            elif c == brackets[1] and start != None:
                output[(start,i+1)] = string[start+1:i]
        return output
    
    def _parse_options(self, options):
        for option, value in options.iteritems():
            if unicode(value).startswith(u"./"):
                self.options[option] = "%s/%s" % (os.path.abspath("."), value[2:])
            else:
                self.options[option] = value
    
    def update_command(self, options_in = {}):
        options = dict(options_in)
        options.update(self.options)
        command = list(self.base_command % options)
        
        # sort out conditional brackets {}
        brackets = self._get_brackets(command, "{}")
        
        for pos in sorted(brackets.keys(), reverse=True):
            variables = self._get_brackets(brackets[pos], "<>")
            
            contitional = False
            for var_pos in variables:
                if var_pos[0] == 0:
                    conditional = variables[var_pos]
                    break
            if not conditional:
                continue
            
            cond_options = shlex.split( "".join(brackets[pos][var_pos[1]:]).strip() )
            
            if options.get("".join(conditional), False):
                command[pos[0]:pos[1]] = list(cond_options[0])
            else:
                command[pos[0]:pos[1]] = list(cond_options[1])
        
        # sort out optional brackets []
        brackets = self._get_brackets(command, "[]")
        for pos in sorted(brackets.keys(), reverse=True):
            value = str("".join(brackets[pos]))
            if value.endswith("None"):
                command[pos[0]:pos[1]] = []
            elif value.endswith(">"):
                sub_value = self._get_brackets(value)
                for key, sub_value in sub_value.iteritems():
                    break
                if sub_value in options and options[sub_value]:
                    command[pos[0]:pos[1]] = list("%s <%s>" % (value[:key[0]], sub_value))
                else:
                    command[pos[0]:pos[1]] = []
        
        # sort out variable brackets <>
        brackets = self._get_brackets(command, "<>")
        for pos in sorted(brackets.keys(), reverse=True):
            value = str("".join(brackets[pos]))
            if value in options and options[value]:
                command[pos[0]:pos[1]] = options[value]
        
        # update output values (simplified syntax from the commands)
        for key, value in self.output.iteritems():
            
            if value:
                # sort out conditional brackets {}
                if value[0] == "{" and value[-1] == "}":
                    condition = value[2:value.find(">")]
                    cond_options = shlex.split( value[value.find(">")+1:-1] )
                    if condition in options and options[condition]:
                        value = cond_options[0]
                    else:
                        value = cond_options[1]
            
                #sort out variable brackets <>
                value = list(value)
                brackets = self._get_brackets(value, "<>")
                for pos in sorted(brackets.keys(), reverse=True):
                    item = str("".join(brackets[pos]))
                    if item in options:
                        value[pos[0]:pos[1]] = options[item]
                value = "".join(value)
            
            if key in options_in:
                options_in[key] = value
        
        # set new command
        self.command = "".join(command)
        
        # return updated input options
        return options_in
    

class PipelineHandler(object):
    
    def __init__(self, json_file = None, variables = None):
        self.vars = variables if variables else {}
        self.input = {}
        self.required_vars = []
        self.optional_vars = []
        self.json_file = json_file
        self.version = None
        if json_file:
            return self.load(json_file)
    
    def enable_group(self, i, value = True):
        if i < len(self.groups):
            self.groups[i].enabled = bool(value)
    
    def load(self, json_file = None):
        if json_file:
            self.json_file = json_file
        if not self.json_file:
            return 1
        with open(self.json_file) as f:
            self.required_vars = []
            self.optional_vars = []
            self.pipeline = json.loads(f.read())
            self.version = self.pipeline['version'] if 'version' in self.pipeline else None
            self.input = self.pipeline['input']
            self.groups = []
            for data in self.pipeline['groups']:
                group = Group(data)
                self.groups += [group]
    
    def set(self, key, value):
        self.vars[key] = value
    
    def toggle_group(self, i):
        if i < len(self.groups):
            self.groups[i].enabled = not self.groups[i].enabled
    
    def update_variables(self):
        variable_pool = dict(self.vars)
        for group in self.groups:
            if not group.enabled:
                continue
            for command in group.commands:
                variable_pool = command.update_command(variable_pool)

class RunController(threading.Thread):
    
    def __init__(self, log_level = logging.INFO, log_name = "MetLab"):
        super(RunController, self).__init__()
        self.log_name = log_name
        self.log = logging.getLogger( log_name )
        self.log.setLevel( log_level )
        self._stop = threading.Event()
        self.current = None
        self.state = 'idle'
        self.run_queue = {}
        self.retval = {}
        self.process_counter = 0
        self.wd = None
        self._init_db()
    
    def _init_db(self):
        for table in DATABASE_SCHEMA:
            self._query( table )
    
    def _query(self, query, *args):
        con = None
        data = None
        
        try:
            con = sqlite3.connect( DATABASE )
            cur = con.cursor()
            cur.execute(query, tuple(args))
            data = cur.fetchall()
            if not data:
                con.commit()
        except sqlite3.Error as e:
            self.log.error("Database error: %s" % e)
        except Exception as e:
            self.log.error("Exception in _query: %s" % e)
        finally:
            if con:
                con.close()
        return data
    
    def get_paths(self):
        return self._query("SELECT `name`,`path` FROM paths")
    
    def get_retval(self, pid):
        if int(pid) in self.retval:
            return self.retval[int(pid)]
        return None
    
    def queue(self, cmd):
        pid = self.process_counter
        if cmd[0][0] == '.':
            cmd[0] = os.path.abspath(cmd[0])
        self.run_queue[pid] = cmd
        self.log.info("adding step: %s" % cmd)
        if hasattr(self, "project_id"):
            self._query("INSERT INTO steps(project_id, command) VALUES (?, ?)", str(self.project_id), " ".join(cmd))
        self.process_counter += 1
        return pid
    
    def clear(self):
        self.run_queue = {}
    
    def run(self, wd = None):
        self.log.info("Starting RunController")
        try:
            while True:
                time.sleep(0.2)
                if self._stop.isSet():
                    break
                if self.current and self.current.status == 'completed':
                    if self.current.retval:
                        self.retval[self.current.pid] = self.current.retval
                        self.log.info("Retval: %s" % self.current.retval)
                    self.current_process = None
                    self.current.join()
                    self.current = None
                if self.current and self.current.status in ['failed', 'aborted']:
                    self.log.error("%s %s" % (self.current.name, self.current.status))
                    self.current_process = None
                    self.current.join()
                    self.current = None
                    self.run_queue.clear()
                if self.run_queue and not self.current:
                    pid = sorted(self.run_queue.keys())[0]
                    cmd = self.run_queue[pid]
                    if cmd[0] == 'mkdir':
                        try:
                            os.stat(cmd[1])
                        except:
                            os.makedirs(cmd[1])
                    elif cmd[0] == 'cd':
                        os.chdir(cmd[1])
                    else:
                        self.current = External(cmd[0], cmd[1:], pid = pid, log_name = self.log_name)
                        cwd = os.getcwd()
                        if self.wd:
                            os.chdir(self.wd)
                        self.current.start()
                        while not self.current.started:
                            time.sleep(0.1)
                        os.chdir(cwd)
                    del self.run_queue[pid]
                    self.state = 'running'
                if not self.run_queue and not self.current and self.state == 'running':
                    self.state = 'finished'
            if self.current:
                self.current.stop()
                self.current.join()
        except Exception as e:
            print "RunController: %s" % e
        self.log.info("RunController finishing")
    
    def set_wd(self, dir_name):
        if dir_name[0] == ".":
            self.wd = "%s%s" % (os.getcwd(), dir_name[1:])
        elif dir_name[0] != "/":
            self.wd = "%s/%s" % (os.getcwd(), dir_name)
        else:
            self.wd = dir_name
    
    def stop(self):
        self._stop.set()
    
    def stop_current(self):
        if self.current:
            self.current.stop()
    
    def start_project(self, name):
        self.queue(["mkdir", name])
        self._query("INSERT INTO projects (name, directory, started) VALUES ('%s', '%s', %i)" % (name, self.wd, time.time()))
        self.project_id = self._query("SELECT id FROM projects ORDER BY id DESC LIMIT 1")[0][0]
        self.log.info("Settings project_id = %i" % self.project_id)

class MetLabController(object):
    
    def __init__(self, log_level = logging.INFO, log_name = "MetLab", socket_name = "metlab.sock"):
        self.socket_name = socket_name
        self.log_name    = log_name
        self.log_format  = "%(asctime)s, %(levelname)s: %(message)s"
        self.date_format = "%Y-%m-%d %H:%M:%S"
        self.log_level   = log_level
        self._start_log()
        self.log.info("Started MetLab Controller")
        self.queue = []
    
    def close(self):
        try:
            os.remove(self.socket_name)
        except OSError:
            pass
        if getattr(self, 'run_controller', False):
            try:
                self.log.info("Stopping RunController thread.")
                self.run_controller.stop()
                self.run_controller.join()
                self.log.info("Successfully joined RunController thread.")
            except Exception as e:
                self.log.warning(e)
                self.log.warning("RunController thread did not join properly.")
    
    def _start_log(self):
        self.log_handler = logging.FileHandler("metlab.log")
        self.log_handler.setFormatter( logging.Formatter(self.log_format, self.date_format) )
        self.log_handler.setLevel( self.log_level )
        self.log = logging.getLogger( self.log_name )
        self.log.setLevel( self.log_level )
        self.log.addHandler( self.log_handler )
        self.log.info(" ==================== NEW SESSION ==================== ")
    
    def run(self):
        self.log.info("Running MetLab Controller")
        try:
            os.remove(self.socket_name)
        except OSError:
            pass
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(self.socket_name)
        self.server.listen(1)
        self.running = True
        self.run_controller = RunController()
        self.run_controller.start()
        self.log.info("Waiting for connection")
        while self.running:
            self.server.settimeout(10.0)
            try:
                os.stat(self.socket_name)
                conn, addr = (None, None)
                conn, addr = self.server.accept()
                conn.settimeout(10.0)
                self.server.settimeout(0.0)
                self.log.info("User connected")
            except OSError as e:
                self.log.error(e)
                self.log.warning("Socket removed. Closing.")
                break
            except KeyboardInterrupt as e:
                self.log.info("Stopped by User")
                break
            except socket.timeout as e:
                if self.run_controller.state != 'running':
                    self.log.info("No jobs. Exiting.")
                    break
                pass
            while True and conn:
                try:
                    data = conn.recv(1024)
                except socket.timeout as e:
                    self.log.warning("Connection timed out.")
                    self.log.info("Waiting for connection")
                    break
                except KeyboardInterrupt as e:
                    self.running = False
                    self.log.info("Stopped by User")
                    break
                
                data = shlex.split(data)
                cmd = data[0] if data else ""
                args = data[1:] if len(data) > 1 else []
                
                if cmd == 'start':
                    reply = self.run_controller.queue(args)
                elif cmd in ['exit', 'close']:
                    self.log.info("User disconnected")
                    if cmd == 'close':
                        self.log.info("Closing Controller")
                        self.running = False
                    else:
                        self.log.info("Waiting for connection")
                    conn.send("bye")
                    break
                elif cmd == 'status':
                    reply = self.run_controller.state
                elif cmd == 'retval':
                    reply = self.run_controller.get_retval(args[0])
                elif cmd == 'queue':
                    current = self.run_controller.current.name if self.run_controller.current else "None"
                    queue = [(current, "running"),]
                    queue += [(v[0], "waiting") for k,v in self.run_controller.run_queue.iteritems()]
                    reply = "|".join(map(str, queue))
                elif cmd == 'set_wd':
                    self.run_controller.set_wd(args[0])
                    reply = "Seems fair."
                elif cmd == 'stop':
                    self.run_controller.clear()
                    self.run_controller.stop_current()
                    reply = "I'll ask the controller to stop."
                elif cmd == 'new':
                    self.run_controller.start_project(args[0])
                    reply = 'Great! Will do!'
                elif cmd == 'cd':
                    self.run_controller.change_directory(args[0])
                    reply = 'Sure, why not!'
                elif cmd == 'paths':
                    reply = self.run_controller.get_paths()
                else:
                    reply = "%s: %s" % (cmd, " ".join(args))
                self.log.debug("Server got: '%s', sending '%s'" % (data, reply))
                try:
                    conn.send(str(reply))
                except Exception as e:
                    self.log.info("%s" % type(e))
                    self.log.warning(e)
                    break
        self.close()

if __name__ == '__main__':
    
    #server = MetLabController()
    #server.run()
    
    programs = {'prinseq-lite':'./apps/prinseq-lite.pl'}
    
    parser = PipelineHandler("pipeline.json", programs)
    parser.set('reads','thefilename.fastq')
    parser.set('paired reads','theotherfilename.fastq')
    parser.load("pipeline.json")
    