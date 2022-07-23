# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# Copyright (c) 2019-2022 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration. All Rights Reserved.
#
# This software is governed by the NASA Open Source Agreement (NOSA) License and may be used,
# distributed and modified only pursuant to the terms of that agreement.
# See the License for the specific language governing permissions and limitations under the
# License at https://software.nasa.gov/ .
#
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either expressed or implied.

"""
@namespace plugins.cfs.pycfs.local_cfs_interface

local_cfs_interface.py: Lower-level interface to communicate with cFS locally (linux).

- Inherits CFS Interface
"""

import os
from io import StringIO
from pathlib import Path
from shutil import rmtree
from subprocess import run, Popen, PIPE, STDOUT
from distutils.spawn import find_executable
import time

# module dependencies
from plugins.cfs.pycfs.cfs_interface import CfsInterface
from lib.ctf_utility import set_variable
from lib.ctf_global import Global
from lib.exceptions import CtfTestError
from lib.logger import logger as log


class LocalCfsInterface(CfsInterface):
    """
    Lower-level interface to communicate with cFS locally (linux)
    """

    def __init__(self, config, telemetry, command, mid_map, ccsds):
        """
        Constructor implementation for LocalCfsInterface Class.
        if configured to build cfs, build cfs. otherwise set init_passed to True
        """
        super().__init__(config, telemetry, command, mid_map, ccsds)

        # Are we building a CFS application? If not than hardcode
        # self.init_passed to True so that the code can continue
        # otherwise call the build_cfs function
        if self.config.build_cfs is True:
            try:
                self.init_passed = self.build_cfs()
            except CtfTestError:
                self.init_passed = False
        else:
            self.init_passed = True

    def get_start_string(self, run_args):
        """
        Get the command string/path to start cfs (linux)
        @param run_args: run_time argument to start cfs
        @return String: full command string to start cfs
        """
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
        # define build-in variable for CFS stdout folder
        cfs_std_output_file = "_CTF_"+self.config.name.upper()+"_CFS_OUTPUT_FILE"
        set_variable(cfs_std_output_file, "=", self.cfs_std_out_path, "string")

        # ENHANCE - Test use of debug when running embedded
        if not self.config.cfs_run_in_xterm or find_executable('xterm') is None:
            start_string = "./{} >> {} 2>&1".format(target, self.cfs_std_out_path)
            if self.config.cfs_run_in_xterm:
                log.error("Dependency 'xterm' not found. Attempting to run in an embedded terminal window instead.")
        else:
            start_string = "xterm -T {} -l -geometry 130X24+800+0 -e \"script -c \'{} ./{}\' -q -f {}\"" \
                .format(self.config.cfs_exe, debug, target, self.cfs_std_out_path)
        log.info("Starting CFS with command: {}".format(start_string))
        return start_string

    def build_cfs(self):
        """
        Build cfs image. The path of cFS source is configured in config init file.
        The build output folder is also configured in init file.
        @return bool: True if build succeed, otherwise False
        """
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

        except Exception as exception:
            log.error("Exception Building CFS Project")
            log.error(exception)
            raise CtfTestError('Error from build_cfs') from exception

        return build_success

    def start_cfs(self, run_args):
        """
        Start the cfs instance process.
        @param run_args: run_args is used to build the start_string.
        @return dictionary: the return result_values is a dictionary, including 'results': True if cfs instance
                starts successfully, otherwise False;  and 'pid': the pid of cfs instance process.
        """

        # Remove ram drive if not a processor reset
        if "RPR" not in self.config.cfs_run_args:
            ram_drive_path = self.config.cfs_ram_drive_path
            if ram_drive_path:
                log.info("Removing ram drive {} before startup since -RPR arg was not included".format(ram_drive_path))
                rmtree(Path(ram_drive_path), ignore_errors=True)

        start_string = self.get_start_string(run_args)
        # Did CFS startup and if so what is the pid?
        return_values = {
            "result": None,
            "pid": None
        }

        # check whether CFS Executable has already started
        pidof_cfs = "pidof {}".format(self.config.cfs_run_cmd)
        pid = run(pidof_cfs, stdout=PIPE, stderr=STDOUT, shell=True, check=False).stdout.decode()
        if pid != "":
            log.error("CFS executable {} has already started! its pid is {}".format(self.config.cfs_run_cmd, pid))
            return_values["result"] = False
            return return_values

        log.info("Starting CFS Executable")
        log.debug("\t Command : {}".format(start_string))

        # Report an error if given a bad directory
        if not os.path.exists(self.config.cfs_run_dir):
            log.error("Couldn't find CFS run directory {}".format(self.config.cfs_run_dir))
            return_values["result"] = False
            return return_values

        # Start CFS process
        try:
            cfs_process = Popen(start_string, cwd=self.config.cfs_run_dir,
                                shell=True, universal_newlines=True)
            return_values["pid"] = cfs_process.pid

        except Exception as exception:
            log.error("Error attempting to execute command: {}".format(start_string))
            log.debug(exception)
            return_values["result"] = False
            raise CtfTestError("Error in start_cfs") from exception

        time.sleep(2)

        # Check the status of the CFS application
        if cfs_process.poll() is not None:
            log.error("Error Launching CFS Process.\nAttempted to launch: {}, returned: {}"
                      .format(start_string, cfs_process.returncode))
            return_values["result"] = False
            return return_values

        return_values["result"] = True
        self.is_running = True

        return return_values
