#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
"""
MetLab is a tool for doing metagenomic experimental design, simulation and 
validation, with a focus on virus identification.
"""

import re
import os
import numpy
import socket
import logging
import sqlite3
import subprocess
import multiprocessing
import tkFileDialog
import ttk
from Tkinter import *
from time import sleep
from controller import metlab_controller, DATABASE
from controller import PipelineHandler
from metamaker import MetaMaker

    
def open_in_file_browser(path):
    system = os.uname()[0]
    if system == 'Darwin':
        subprocess.call(["open", "-R", path])
    elif system == 'Linux':
        subprocess.call(["xdg-open", path])
    

def bp_to_int(value, suffix="KMGTP"):
    try:
        exp = (suffix.index(value[-1].upper())+1)*3 if value[-1].upper() in suffix else 1
        return int(float(value[:-1])*(10**exp))
    except:
        return -1

def check_if_exists(command, paths = None):
    try:
        os.stat(command)
        found = True
    except OSError as e:
        found = False
        if paths:
            for name, path in paths:
                if command == name:
                    found = path
                    break
        if not found:
            for path in os.environ["PATH"].split(os.pathsep):
                path = path.strip('"')
                exe_file = os.path.join(path, command)
                if os.path.isfile(exe_file):
                    found = exe_file
    return found

class GUILog(logging.Handler):
    """
    Log handler to print log messages to TkInter GUI console
    """
    def __init__(self, console):
        """
        Init function, just stores the console and calls super.
        """
        logging.Handler.__init__(self)
        self.console = console
        self.max_lines = 200
        self.lines = 0
    
    def emit(self, message):
        """
        Appends log message to the console.
        """
        formattedMessage = "\n%s" % self.format(message)
        
        self.console.configure(state=NORMAL)
        self.console.insert(END, formattedMessage)
        self.lines += 1
        while self.lines >= self.max_lines:
            self.console.delete("1.0", "2.0")
            self.lines -= 1
        self.console.configure(state=DISABLED)
        self.console.see(END)

class OptionFrame( Frame ):
    """A basic frame that can be enabled and expanded/contracted"""

    def __init__(self, parent, title="", optional = False, opt_func = None, *args, **options):
        Frame.__init__(self, parent, *args, **options)
        
        self.expanded = IntVar()
        self.expanded.set(0)
        
        self.enabled = IntVar()
        self.enabled.set(1)
        
        self.header = ttk.Frame(self)
        
        if optional:
            title_line = ttk.Checkbutton(self.header, text=title, variable=self.enabled, command=opt_func)
        else:
            title_line = ttk.Label(self.header, text="      %s" % (title))
        
        title_line.pack(side="top", fill=X)
        
        self.toggle_button = ttk.Checkbutton(self.header, width=2, text='+', 
                                         command=self.toggle_expanded, variable=self.expanded, style='Toolbutton')
        self.toggle_button.pack(side="left", fill=X)
        self.header.pack(fill=X, expand=1)
        
        self.sub_frame = Frame(self)
    
    def active(self):
        return bool(self.enabled.get())
    
    def toggle_expanded(self):
        if bool(self.expanded.get()):
            self.sub_frame.pack(fill=X, expand=1)
            self.toggle_button.configure(text='-')
        else:
            self.sub_frame.forget()
            self.toggle_button.configure(text='+')

class InfoFrame( Frame ):
    """A simple list to select form, and an information page to the side"""
    
    def __init__(self, parent, title="", *args, **options):
        Frame.__init__(self, parent, *args, **options)
        
        header = Frame(self, bg="white")
        Label(header, text=title, font=("Helvetica", 16)).pack(side='top', anchor='nw', pady=4)
        header.pack(side="top", anchor="nw", fill=X)
        
        self.info = Frame(self)
        self.info_label = StringVar()
        Label(self.info, textvar=self.info_label).pack(side="top")
        self.info.pack(side="right", anchor="nw", fill=BOTH)
        
        self.list = Frame(self)
        self.list.pack(side="left", anchor="nw", fill=BOTH)
        
        self.info_frames = {}
        self.active_item = None
        self.active_info = None
    
    def delete(self, project_id):
        try:
            con = sqlite3.connect( DATABASE )
            cur = con.cursor()
            cur.execute("DELETE FROM projects WHERE id=%i" % project_id)
            cur.execute("DELETE FROM steps WHERE project_id=%i" % project_id)
            con.commit()
        except sqlite3.Error as e:
            print "Database error: %s" % e
        except Exception as e:
            print "Exception in query: %s" % e
        finally:
            if con:
                con.close()
    
    def remove(self, label, info, item):
        label.pack_forget()
        info.pack_forget()
        self.delete(item["id"])
    
    def add(self, item):
        item_label = Label(self.list, text=item["name"], justify="right", cursor="dotbox")
        item_label.bind("<Button-1>", self._click)
        item_label.pack(side="top", fill=X, anchor="nw", padx=(5,15))
        
        info = Frame(self.info)
        Label(info, text="Executed commands:").pack(side="top", anchor="nw", padx=(0,20))
        steps = Text(info, bg="grey", fg="blue", font=("Courier", 12), height=len(item["steps"])+1)
        steps.configure(state=NORMAL)
        for step in item["steps"]:
            steps.insert(END, " $ %s %s\n" % (step.split()[0].split("/")[-1], " ".join(step.split()[1:])))
        steps.see(END)
        steps.configure(state=DISABLED)
        steps.pack(side="top", anchor="nw")
        
        result_frame = Frame(info)
        
        Label(result_frame, text="Results directory: ").pack(side="left", anchor="nw", padx=(0,20))
        Label(result_frame, text=item["path"]).pack(side="left", anchor="nw", padx=(0,20))
        Button(result_frame, text="Open", command=lambda p=item["path"]:  open_in_file_browser(p) ).pack(side="left", anchor="nw", padx=(0,20))
        result_frame.pack(side="top", anchor="nw")
        
        Button(info, text="Delete run", command=lambda p=item: self.remove(item_label, info, p) ).pack(side="top", anchor="nw", padx=(0,20))
        
        self.info_frames[str(item_label)] = info
    
    def _click(self, event):
        if self.active_item:
            self.active_item.configure(relief=FLAT)
        if self.active_info:
            self.active_info.pack_forget()
        self.info_label.set(event.widget.cget("text"))
        event.widget.configure(relief=SUNKEN)
        self.active_item = event.widget

        self.active_info = self.info_frames[str(event.widget)]
        self.active_info.pack(side="top")

class MetLabInterface(object):
    
    def __init__(self, socket_name = "metlab.sock"):
        self.socket_name = socket_name
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.controller_status = None
        self.threads = []
    
    def _start_controller(self):
        controller = multiprocessing.Process(target = metlab_controller, args   = (self.socket_name,))
        controller.start()
    
    def ask(self, msg):
        self.send(msg.strip() + "\n")
        return self.recv()
    
    def close(self, stop_running = False):
        try:
            if stop_running or self.ask("status") != 'running':
                self.ask("close")
            else:
                self.ask("exit")
            for thread in self.threads:
                thread.stop()
                thread.join()
        except Exception as e:
            print e
    
    def connect(self):
        try:
            os.stat(self.socket_name)
        except:
            self._start_controller()
            sleep(0.1)
        self.socket.connect(self.socket_name)
    
    def recv(self):
        return self.socket.recv(4096).strip()
    
    def send(self, cmd):
        self.socket.send(cmd)
    
    def status(self):
        self.controller_status = self.ask("status")
        return self.controller_status
    

class MetLabGUI(MetLabInterface):
    
    __name__ = "MetLabGUI"
    __version__ = "0.2.0"
    
    def __init__(self):
        super(MetLabGUI, self).__init__()
        
        self.profile_dir = "profiles"
        self.jobs = {}
        
        self.gui = Tk()
        self.gui.wm_title("%s v. %s" % (self.__name__, self.__version__))
        self.gui.wm_minsize(450, 600)
        
        # load program paths
        paths = {}
        
        # Load pipeline
        self.pipeline = PipelineHandler("pipeline.json", paths)
        
        # GUI layout 
        frames = self._layout_basic()
        
        self._frame_experimental_design ( frames[0] )
        self._frame_simulation ( frames[1] )
        self._frame_pipeline ( frames[2] )
        
        # Start log
        self.log = logging.getLogger( self.__name__ )
        self.log.setLevel( logging.INFO )
        self.log_handler = GUILog(self.console)
        self.log_handler.setLevel( logging.INFO )
        self.log_handler.setFormatter( logging.Formatter( '%(asctime)s %(levelname)s: %(message)s', "%H:%M:%S" ) )
        self.log.addHandler(self.log_handler)
        
        self.log.info(__doc__)
        
        # create database while we're in a user-owned process, and check if we 
        # have any finished projects
        self.projects = []
        for project in self._get_projects():
            self.projects += [project]
        
        # Add results pane
        self._frame_results ( frames[3] )
        
        # start backend
        self.connect()
        
        # check if all pipeline programs are available
        self.log.info("Checking pipeline programs")
        db_paths = eval(self.ask("paths"))
        
        for group in self.pipeline.pipeline["groups"]:
            for i, command in enumerate([c["command"].split()[0].strip("<").rstrip(">") for c in group["commands"]]):
                path = check_if_exists(command, db_paths)
                if path:
                    self.log.info(" * %s: Found" % (command.split("/")[-1]))
                    self.pipeline.set(command, path)
                else:
                    self.log.warn(" ! %s: Not Found" % (command.split("/")[-1]))
        
        # start the mainloop
        self._stay_alive()
        self.gui.mainloop()
    
    def __del__(self):
        self.close()
    
    def _run(self, cmd, formatting, callbacks):
        pid = self.ask("start %s" % cmd)
        self.jobs[pid] = (formatting,callbacks)
    
    def _experimental_design_calculate(self, limit = 0.1, max_runs = 10):
        
        a = float(self.experimental_design['abundance'].get())/100.0
        L = bp_to_int(self.experimental_design['genome_size'].get())
        
        for name, profile in self.profiles.iteritems():
            l = profile['read_length_mean']
            R = profile['default_reads']
            self.log.info("Calculating probabilities for %s runs" % name)
            self._run("./metlab/metamath.py -L %s -l %s -R %s -a %s -m %i -p %s" % (L,l,R,a,max_runs,limit),
                      ("(%i runs)", "%3.5f"),
                      (self.experimental_design['probability_comment'][name],
                       self.experimental_design['probabilities'][name])
                     )
    
    def _frame_experimental_design(self, parent):
        """
        Experimental design

        This module can help in experimental design of a metagenomic experiment by 
        estimating the probability of getting a full coverage 1X alignment of a member 
        of the metagenomic community.

        Input variables are the extimated abundance of the target species in percent, 
        and the approximate genome size of this species. This can be though of as the 
        limit of high probability detection for the metagenomic sequencing. 

        The output will be the probaiblity of reaching full coverage in a theoretical 
        assembly, using the sequencing profiles defined in the MetaMaker module. If a 
        sequencing technology gets too low a probability, the calculation will run 
        again, adding one more run, up to a maximum of ten runs.
        """
        # app pane
        app_pane = Frame(parent)
        
        try:
            import metamath
            
            # Settings pane
            settings_pane = Frame(app_pane, width=400)
            self.experimental_design = {}
            self.experimental_design['abundance']   = StringVar(settings_pane)
            self.experimental_design['genome_size'] = StringVar(settings_pane)
            self.experimental_design['abundance'].set(1.0)
            self.experimental_design['genome_size'].set("1M")
        
            # Input abundance
            abundance_pane = Frame(settings_pane)
            Label(abundance_pane, text="Lowest Abundance:").pack(side='left', anchor='nw', pady=4)
            Entry(abundance_pane, textvariable=self.experimental_design['abundance'], width=10
                  ).pack(side='left', anchor='nw')
            Label(abundance_pane, text="%").pack(side='left', anchor='nw', pady=4)
            abundance_pane.pack(side='top', anchor='nw')
        
            # Input genome size
            genome_size_pane = Frame(settings_pane)
            Label(genome_size_pane, text="Approx. genome size:").pack(side='left', anchor='nw', pady=4)
            Entry(genome_size_pane, textvariable=self.experimental_design['genome_size'], width=10
                  ).pack(side='left', anchor='nw')
            Label(genome_size_pane, text="bp").pack(side='left',anchor='nw', pady=4)
            genome_size_pane.pack(side='top', anchor='nw')
        
            arg_in = Button(settings_pane, text="Calculate", command=self._experimental_design_calculate
                            ).pack(side='left', anchor='nw')
        
            settings_pane.pack(side='left', anchor='nw')
        
            # Output
            output_pane = Frame(app_pane, width=400)
            self.experimental_design['probabilities'] = {}
            self.experimental_design['probability_comment'] = {}
            if not getattr(self, 'profiles', False):
                self.profiles = MetaMaker.get_profiles(profile_dir = self.profile_dir)
            for name in self.profiles:
                self.experimental_design['probabilities'][name] = StringVar(output_pane)
                self.experimental_design['probability_comment'][name] = StringVar(output_pane)
                self.experimental_design['probabilities'][name].set('-')
        
                temp_pane = Frame(output_pane)
                Label(temp_pane, text=name).pack(side='left', anchor='ne', pady=4)
                Entry(temp_pane, textvariable=self.experimental_design['probabilities'][name], width=10
                      ).pack(side='right', anchor='ne')
                Label(temp_pane, textvariable=self.experimental_design['probability_comment'][name],
                      ).pack(side='right', anchor="ne", pady=4)
                temp_pane.pack(side='top', anchor='ne')
                output_pane.pack(side='right', anchor='ne')
        except:

            warning_pane = Frame(app_pane)
            Label(warning_pane, text="""\n\tThe experimental design module requires the metapprox or mpmath library.""", font=("Helvetica", 16), fg="red", justify=LEFT).pack(side='left', anchor='nw')
            warning_pane.pack(side='top', fill=X, anchor='nw')
            pass
        app_pane.pack(side='top', fill=X, anchor='nw')
        
        # Help
        help_pane = Frame(parent)
        Label(help_pane, text=self._frame_experimental_design.__doc__, justify=LEFT).pack(side='left', anchor='nw')
        help_pane.pack(side='top', fill=X, anchor='nw')
    
    def _frame_pipeline(self, parent):
        # Queue pane
        
        queue_frame = Frame(parent)
        header = Frame(queue_frame)
        Label(header, text="Current queue").pack(side="left", anchor="nw", fill=X)
        header.pack(side="top", fill=X)
        separator = Frame(queue_frame, height=2, bd=1, relief=SUNKEN)
        separator.pack(side="top", fill=X, padx=5, pady=5)
        
        self.queue = Frame(queue_frame, name="queue")
        self.queue.pack(anchor="nw", fill=BOTH)
        
        separator = Frame(queue_frame, height=2, bd=1, relief=SUNKEN)
        separator.pack(side="top", fill=X, padx=5, pady=5)
        
        Button(queue_frame, text="Stop", command=self._stop_pipeline).pack(side="right", anchor="ne", padx=20, fill=X)
        queue_frame.pack(side="right", anchor="ne", fill=BOTH, expand=True)
        
        # Run pane
        new_run = Frame(parent)
        header = Frame(new_run)
        self.pipeline_name= StringVar(header)
        
        default_name = "pipeline_run"
        value = 1
        try:
            while True:
                os.stat("%s_%03i" % (default_name, value))
                value += 1
        except Exception as e:
            pass
        
        self.pipeline_name.set("%s_%03i" % (default_name, value))
        Label(header, text="MetLab Pipeline Version %s" % self.pipeline.version).pack(side='top',anchor='ne',pady=4)
        Label(header, text="Run Name:").pack(side="left", anchor="nw")
        Entry(header, textvariable=self.pipeline_name, width=40).pack(side='left', anchor='nw')
        header.pack(side="top", fill=X, anchor='nw')
        
        pipeline_input = Frame(new_run)
        
        Label(pipeline_input, text="Pipeline Input:", font=("Helvetica", 16) ).pack(side="top", anchor="nw")
        self.arg_info = {}
        self.arg_value = {}
        for item, item_type in self.pipeline.input.iteritems():
            arg_pane = Frame(pipeline_input)
            self.arg_value[item] = StringVar(arg_pane)
            if item_type == 'file':
                Label(arg_pane, text=item).pack(side='left', anchor="nw")
                arg_in = Button(arg_pane, text="Open file", command= lambda i=str(item): self._open_file(i) )
                arg_in.pack(side='left', anchor="nw")
                self.arg_info[item] = StringVar(arg_pane)
                self.arg_info[item].set("")
                arg_info = Label(arg_pane, textvariable=self.arg_info[item]).pack(side='left', anchor="nw")
            else:
                Label(arg_pane, text=item).pack(side='left', anchor="nw")
                self.arg_value[item].set(str(item_type))
                Entry(arg_pane, textvariable=self.arg_value[item]).pack(side='left', anchor='nw')
                
            arg_pane.pack(side="top", anchor="nw")
        pipeline_input.pack(side="top", anchor="nw")
        
        groups = Frame(new_run)
        self.group_options = {}
        for i,group in enumerate(self.pipeline.groups):
            
            group_frame = OptionFrame(groups, group.name, group.optional, opt_func = lambda g=i:self.pipeline.toggle_group(g))
            
            self.group_options[group.name] = {}
            for command in group.commands:
                for option, value in command.options.iteritems():
                    self.group_options[group.name][option] = StringVar(groups)
                    cmd_frame = Frame(group_frame.sub_frame)
                    Label(cmd_frame, text="        %s: " % option).pack(side='left', anchor='nw')
                    Entry(cmd_frame, textvariable=self.group_options[group.name][option]).pack(side='left', anchor='nw')
                    self.group_options[group.name][option].set(value)
                    cmd_frame.pack(side='top', anchor='nw', fill=X)
            group_frame.pack(side="top", anchor="nw", fill=X)

        groups.pack(side="top", fill=X, anchor="nw")
        
        controls = Frame(new_run)
        
        Button(controls, text="Run", command=self._run_pipeline).pack(side="right", anchor="ne", padx=20)
        controls.pack(side="bottom", fill=X, anchor="sw")
        
        new_run.pack(side="left", anchor="nw")
    
    def _frame_results(self, parent):
        # Results pane
        
        result_list = InfoFrame(parent, "Available Runs")
        for project in self.projects:
            result_list.add(project)
        
        result_list.pack(side="left", anchor="nw", fill=BOTH)
    
    def _frame_simulation(self, parent):
        
        self.simulation = {}
        
        # help frame
        help_frame = Frame(parent)
        Label(help_frame, text=MetaMaker.__doc__, justify=LEFT).pack(side='top', fill=X, anchor='nw')
        help_frame.pack(side='right', fill=X, anchor='nw')
        
        # Profile description pane
        profile_frame = Frame(parent, width=300)
        self.simulation['read_length']     = StringVar(profile_frame)
        self.simulation['read_length_sd']  = StringVar(profile_frame)
        self.simulation['no_reads']        = StringVar(profile_frame)
        self.simulation['simulation_name'] = StringVar(profile_frame)
        self.simulation['no_species']      = StringVar(profile_frame)
        self.simulation['species_dist']    = StringVar(profile_frame)
        self.simulation['taxa']            = StringVar(profile_frame)
        self.simulation['matepair']        = StringVar(profile_frame)
        self.simulation['insert']          = StringVar(profile_frame)
        self.simulation['matepair'].set(False)
        self.simulation['insert'].set(500)
        
        # Create header with profile selector.
        selection_frame = Frame(profile_frame)
        Label(selection_frame, text="Select profile:").pack(side='left', anchor='nw', pady=4)
        self.simulation['profiles'] = StringVar()
        self.simulation['profiles'].trace("w", self._simulation_change_profile)
        
        if not getattr(self, 'profiles', False):
            self.profiles = MetaMaker.get_profiles(profile_dir = self.profile_dir)
        if self.profiles:
            self.simulation['profiles'].set(self.profiles.keys()[0])
            selection_drop = OptionMenu(selection_frame, self.simulation['profiles'], *self.profiles)
        else:
            self.simulation['profiles'].set("No Profiles")
            selection_drop = OptionMenu(selection_frame, self.simulation['profiles'], "No Profiles")
        
        selection_drop.pack(side="left", anchor="nw")
        selection_frame.pack(side='top', anchor='nw')
        
        # add settings
        
        read_length_pane    = Frame(profile_frame)
        Label(read_length_pane, text="Read Length:").pack(side='left', anchor='nw', pady=4)
        Entry(read_length_pane, textvariable=self.simulation['read_length'], width=10
              ).pack(side='left', anchor='nw')
        Label(read_length_pane, text="bp").pack(side='left',anchor='nw', pady=4)
        read_length_pane.pack(side='top', anchor='nw')
        
        read_length_sd_pane    = Frame(profile_frame)
        Label(read_length_sd_pane, text="Read Length stdev.:").pack(side='left', anchor='nw', pady=4)
        Entry(read_length_sd_pane, textvariable=self.simulation['read_length_sd'], width=10
              ).pack(side='left', anchor='nw')
        read_length_sd_pane.pack(side='top', anchor='nw')
        
        read_no_pane    = Frame(profile_frame)
        Label(read_no_pane, text="Number of Reads:").pack(side='left', anchor='nw', pady=4)
        Entry(read_no_pane, textvariable=self.simulation['no_reads'], width=10).pack(side='left', anchor='nw')
        read_no_pane.pack(side='top', anchor='nw')
        
        # non profile-dependent things
        
        sim_name_pane    = Frame(profile_frame)
        Label(sim_name_pane, text="Simulation Name:").pack(side='left',
                                                            anchor='nw', pady=4)
        Entry(sim_name_pane, textvariable=self.simulation['simulation_name'], width=10
              ).pack(side='left', anchor='nw')
        sim_name_pane.pack(side='top', anchor='nw')
        
        num_species_pane    = Frame(profile_frame)
        Label(num_species_pane, text="Number of Species:").pack(side='left', anchor='nw', pady=4)
        Entry(num_species_pane, textvariable=self.simulation['no_species'], width=10
              ).pack(side='left', anchor='nw')
        num_species_pane.pack(side='top', anchor='nw')
        self.simulation['no_species'].set(10)
        
        dist = ["uniform", "exponential"]
        self.simulation['species_dist'].set(dist[0])
        taxa_pane     = Frame(profile_frame)
        Label(taxa_pane, text="Species distribution:").pack(side='left', anchor='nw', pady=4)
        taxa_selector = OptionMenu(taxa_pane, self.simulation['species_dist'], *dist
                                   ).pack(side='left', anchor='nw')
        taxa_pane.pack(side='top', anchor='nw')
        
        taxa = ["viruses"]
        self.simulation['taxa'].set(taxa[0])
        taxa_pane     = Frame(profile_frame)
        Label(taxa_pane, text="Species taxa:").pack(side='left', anchor='nw', pady=4)
        taxa_selector = OptionMenu(taxa_pane, self.simulation['taxa'], *taxa).pack(side='left', anchor='nw')
        taxa_pane.pack(side='top', anchor='nw')
        
        # Mate-pair settings
        
        matepair_pane    = Frame(profile_frame)
        Label(matepair_pane, text="Matepair:").pack(side='left', anchor='nw', pady=4)
        Checkbutton(matepair_pane, variable=self.simulation['matepair'], onvalue=True, offvalue=False
                    ).pack(side='left', anchor='nw', pady=4)
        Label(matepair_pane, text="Insert:").pack(side='left', anchor='nw', pady=4)
        Entry(matepair_pane, textvariable=self.simulation['insert'], width=10
              ).pack(side='left', anchor='nw')
        matepair_pane.pack(side='top', anchor='nw')
        
        arg_in = Button(profile_frame, text="Generate", command=self._run_simulation
                        ).pack(side='left', anchor='nw')
        
        profile_frame.pack(side='left', anchor='nw')
        
        return
    
    def _get_projects(self, last = False):
        try:
            con = sqlite3.connect( DATABASE )
            cur = con.cursor()
            query = "SELECT id, name, directory FROM projects"
            query += " ORDER BY id DESC LIMIT 1;" if last else ""
            cur.execute(query)
            
            projects = {}
            for pid, name, path in cur.fetchall():
                projects[pid] = {'name':name, 'path':path, 'steps':[], "id":pid}
            cur.execute("SELECT project_id, command FROM steps ORDER BY id ASC")
            for pid, command in cur.fetchall():
                if pid not in projects:
                    continue
                projects[pid]["steps"] += [command]
            return projects.values()
            
        except sqlite3.Error as e:
            self.log.error("Database error: %s" % e)
        except Exception as e:
            self.log.error("Exception in query: %s" % e)
        finally:
            if con:
                con.close()
        os.chmod(DATABASE, 0666)
        return []
    
    def _layout_basic(self):
        """
        Defines the basic layout of the application.
        """
        
        main = ttk.Notebook(self.gui)
        main.pack(fill='both', expand='yes')
        
        # create a child frame for each application pane
        frames = (Frame(), Frame(), Frame(), Frame())
        
        # add the pages to the handler
        main.add(frames[0], text='Experimental Design')
        main.add(frames[1], text='Simulate Datasets')
        main.add(frames[2], text='Run Pipelines')
        main.add(frames[3], text='Result Summary')
        
        # Add the log handler.
        log = ttk.Notebook(self.gui)
        log.pack(fill='both', expand='yes')
        log_frame = Frame()
        log.add(log_frame, text='Log')
        
        # ... and the logging console
        self.console = Text(log_frame, name="console", height=10)
        self.console.pack(side='bottom', anchor='sw', expand='yes', fill=BOTH)
        
        return frames
    
    def _open_file(self, *args):
        self.infile = "'%s'" % tkFileDialog.askopenfilename() # quote name in case of whitespace
        if args[0] in self.arg_info:
            self.arg_value[args[0]].set(self.infile.strip('\''))
            self.arg_info[args[0]].set("[%s]" % self.infile.split('/')[-1].strip('\''))
    
    def _simulation_change_profile(self, *args):
        result = self.simulation['profiles'].get()
        
        read_mean = self.profiles[result]['read_length_mean']
        read_sd = self.profiles[result]['read_length_var']**.5
        no_reads = self.profiles[result]['default_reads']
        self.simulation['read_length'].set("%.1f" % read_mean)
        self.simulation['read_length_sd'].set( "%.1f" % read_sd)
        self.simulation['no_reads'].set( int(no_reads) )
    
    def _run_pipeline(self):
        pipeline_name = self.pipeline_name.get().replace(" ", "_")
        for item in self.arg_value:
            value = self.arg_value[item].get()
            if value.startswith("."):
                value = os.path.abspath(value)
            self.pipeline.set( item, value )
        
        for i,group in enumerate(self.pipeline.groups):
            for c, command in enumerate(group.commands):
                for option, value in command.options.iteritems():
                    self.pipeline.groups[i].commands[c].options[option] = self.group_options[group.name][option].get()
        
        self.pipeline.update_variables()
        self.ask("set_wd %s" % pipeline_name)
        self.ask("new %s" % pipeline_name)
        for group in self.pipeline.groups:
            if not group.enabled:
                continue
            for command in group.commands:
                self.log.info("Queuing command: %s" % command)
                self.ask("start %s" % command)
    
    def _run_simulation(self):
        
        result  = self.simulation['profiles'].get()
        profile = self.profiles[result]
        
        read_mean  = float(self.simulation['read_length'].get())
        read_var   = float(self.simulation['read_length_sd'].get())**2
        no_reads   = int(self.simulation['no_reads'].get())
        no_species = int(self.simulation['no_species'].get())
        sim_name   = self.simulation['simulation_name'].get()
        sim_taxa   = self.simulation['taxa'].get()
        dist       = self.simulation['species_dist'].get()
        matepair   = bool(int(self.simulation['matepair'].get()))
        insert     = int(self.simulation['insert'].get())
        
        # some sanity checking
        sim_name = sim_name if sim_name else "%i_%s" % (no_species, sim_taxa)
        
        self.log.info("READS mean: %s" % read_mean)
        self.log.info("       var: %s" % read_var)
        self.log.info("        no: %s" % no_reads)
        self.log.info("   SPECIES: %s" % no_species)
        self.log.info("      NAME: %s" % sim_name)
        self.log.info("      TAXA: %s" % sim_taxa)
        self.log.info("      DIST: %s" % dist)
        self.log.info(" Mate-Pair: %s" % matepair)
        self.log.info("    Insert: %s" % insert)
        
        #cmd = "./metlab/metamaker.py -r %s -l %s -n %s -s %s -o %s -x %s -d %s %s -i %s" % 
        #      (read_mean, read_var, no_reads, no_species, sim_name, sim_taxa, dist, "-m" if matepair else "", insert)
        
        app = MetaMaker( outfile = sim_name, num_genomes = no_species )
        app.set_log(self.__name__, handler=self.log_handler)
        app.set('taxa', sim_taxa)
        app.set('reads', no_reads)
        app.set('read_length', read_mean)
        app.set('length_var', read_var)
        app.set('quality_mean', map(float, profile['quality_mean']))
        app.set('quality_var', map(float, profile['quality_var']))
        app.set('distribution', dist)
        app.set('progress', True)
        app.set('matepair', matepair)
        app.set('insert_size', insert)
        app.start()
        self.threads += [app]
    
    def _set_queue(self, queue):
        for child in self.queue.winfo_children():
            child.destroy()
        
        if queue != ["('None', 'running')"]:
            for item in queue:
                item, status = eval(item)
                item = item.split('/')[-1]
                queue_item = Frame(self.queue)
                item_label = Label(queue_item, text="%s:     %s" % (item, status))
                item_label.pack(side="left", anchor="nw")
                queue_item.pack(side='top', anchor='nw', fill=X)
    
    def _stay_alive(self, interval = 1):
        self.status()
        finished = []
        for job in self.jobs:
            retval =  self.ask("retval %s" % job)
            if retval != "None":
                formatting, controllers = self.jobs[job]
                return_values = eval(retval)
                for i, controller in enumerate(controllers):
                    controller.set(formatting[i] % return_values[i])
                finished += [job]
        
        queue = self.ask("queue").split("|")
        self._set_queue(queue)
        for job in finished:
            del self.jobs[job]
        self.gui.after(int(interval*1000), self._stay_alive)
    
    def _stop_pipeline(self):
        self.log.debug(self.ask("stop"))
    

if __name__ == '__main__':
    
    import argparse
    
    parser = argparse.ArgumentParser( description = __doc__ )
    parser.add_argument("-g", "--gui", help="Start graphical interface", action="store_true")
    
    args = parser.parse_args()
    
    if args.gui:
        test = MetLabGUI()
    else:
        test = MetLabInterface()
        test.connect()
        reply = None
        while reply != "bye":
            try:
                cmd = raw_input("> ")
                if cmd:
                    reply = test.ask(cmd)
                    print "< %s" % reply
            except Exception as e:
                print e
                break