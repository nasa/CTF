"""
local_cfs_interface.py: Lower-level interface to communicate with cFS locally (linux).

- Inherits CFS Interface
"""

import os
from io import StringIO
from subprocess import Popen, PIPE, STDOUT
from distutils.spawn import find_executable

# module dependencies
from plugins.cfs.pycfs.cfs_interface import CfsInterface

# external dependencies
from lib.logger import logger as log
from lib.Global import Global


class LocalCfsInterface(CfsInterface):
    def __init__(self, config, telemetry, command, mid_map, ccsds):
        super(LocalCfsInterface, self).__init__(config, telemetry, command, mid_map, ccsds)

        # Are we building a CFS application? If not than hardcode
        # self.init_passed to True so that the code can continue
        # otherwise call the build_cfs function
        if self.config.build_cfs is True:
            self.init_passed = self.build_cfs()
        else:
            self.init_passed = True

    def get_start_string(self, run_args):
        target = self.config.cfs_run_cmd
        if len(run_args) > 0:
            target = target + " " + run_args

        if self.config.cfs_port_arg:
            target += " -p {}".format(self.config.cmd_udp_port)

        debug = ''
        if self.config.cfs_debug:
            debug = "gdb -tui"

        cfs_std_out_filename = "{}_{}".format(self.config.name, self.config.cfs_output_file)
        self.cfs_std_out_path = os.path.join(os.path.abspath(Global.current_script_log_dir), cfs_std_out_filename)

        # TODO - Test use of debug when running embedded
        if not self.config.cfs_run_in_xterm or find_executable('xterm') is None:
            start_string = "./{} | tee -a {}".format(target, self.cfs_std_out_path)
            if self.config.cfs_run_in_xterm:
                log.error("Dependency 'xterm' not found. Attempting to run in an embedded terminal window instead.")
        else:
            start_string = "xterm -l -hold -geometry 130X24+800+0 -e \"%s ./%s |& tee -a %s\"; wait &" % \
                           (debug, target, self.cfs_std_out_path)
        return start_string

    def build_cfs(self):
        # Attempt to build CFS project from config build_cmd
        build_success = True
        cwd = self.config.cfs_build_dir
        log.info("Building Mission FSW")
        log_file = os.path.join(Global.current_script_log_dir, "{}_build_cfs_output.txt".format(self.config.name))
        try:
            with Popen(self.config.cfs_build_cmd, cwd=cwd, shell=True,
                       stdout=PIPE, stderr=STDOUT, universal_newlines=True) as proc, \
                    open(log_file, 'w+') as build_log, \
                    StringIO() as buf:

                # Send process output to both console and log file
                for line in proc.stdout:
                    print(line, end='')
                    buf.write(line)
                build_log.write(buf.getvalue())

                proc.communicate()
                if proc.returncode != 0:
                    log.error("Failed to build CFS Project.")
                    build_success = False
                    return build_success

        except Exception as e:
            log.error("Exception Building CFS Project")
            log.error(e)
            build_success = False
            return build_success

        if not build_success:
            log.error("Failed to Build CFS Project")

        return build_success

    def start_cfs(self, run_args):
        start_string = self.get_start_string(run_args)
        # Did CFS startup and if so what is the pid?
        return_values = {
            "result": None,
            "pid": None
        }

        log.info("Starting CFS Executable")
        log.debug("\t Command : {}".format(start_string))

        # Report an error if given a bad directory
        if not os.path.exists(self.config.cfs_run_dir):
            log.error("Couldn't find CFS run directory")
            return_values["result"] = False
            return return_values

        # Start CFS process
        try:
            cfs_process = Popen(start_string, cwd=self.config.cfs_run_dir,
                                shell=True, universal_newlines=True, preexec_fn=os.setsid)
            return_values["pid"] = cfs_process.pid

        except OSError:
            log.error("OSError: Could not open file while attempting to execute command: {}".format(start_string))
            return_values["result"] = False
            return return_values

        except Exception as e:
            log.error("Error attempting to execute command: {}".format(start_string))
            log.debug(e)
            return_values["result"] = False
            return return_values

        # Check the status of the CFS application
        if cfs_process.poll() is not None:
            log.error("Error Launching CFS Process.\nAttempted to launch: {}, returned: {}"
                      .format(start_string, cfs_process.returncode))
            return_values["result"] = False
            return return_values

        return_values["result"] = True

        return return_values

    # Send a command to enable output and check if we receive a response
    def enable_output(self):
        count = 0
        while True:
            count += 1
            self.output_manager.enable_output()
            Global.time_manager.wait(1)

            if self.tlm_has_been_received:
                return True
            if count > 60:
                log.error("Unable to connect to CFS mission")
                return False
