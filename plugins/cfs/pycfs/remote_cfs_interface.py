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
remote_cfs_interface.py: Lower-level interface to communicate with cFS remotely over SSH.

- Inherits Cfs Interface - extends some of it's functionality specifically for SSH.
"""
import os

from lib.ctf_global import Global
from lib.logger import logger as log
from plugins.cfs.pycfs.local_cfs_interface import LocalCfsInterface


class RemoteCfsInterface(LocalCfsInterface):
    """
    RemoteCfsInterface implements lower-level interface to communicate with cFS remotely over SSH.
    Inherits Cfs Interface - extends some of it's functionality specifically for SSH.
    """

    def __init__(self, config, telemetry, command, mid_map, ccsds, execution):
        """
        Constructor implementation for RemoteCfsInterface.
        Pass arguments to base class.
        """
        self.execution_controller = execution
        super().__init__(config, telemetry, command, mid_map, ccsds)

    def get_start_string(self, run_args):
        """
        Build the start string for starting cFS instance.
        @param run_args: run_args is used to build start string
        @return string: command to start cFS instance, including remote cFS path.
        """
        target = self.config.cfs_run_cmd

        if len(run_args) > 0:
            target = target + " " + run_args

        if self.config.cfs_port_arg:
            target += " -p {}".format(self.config.cmd_udp_port)

        cfs_std_out_filename = "{}_{}".format(self.config.name, self.config.cfs_output_file)
        self.cfs_std_out_path = os.path.join("/tmp", cfs_std_out_filename)
        start_string = "./{} >> {}".format(target, self.cfs_std_out_path)
        return start_string

    def start_cfs(self, run_args):
        """
         Start the remote cfs instance process.
         @param run_args: run_args is used to build the start_string.
         @return dictionary: the return result_values is a dictionary, including 'results': True if cfs instance
                 starts successfully, otherwise False;  and 'pid': the pid of cfs instance process.
         """
        start_string = self.get_start_string(run_args)
        return_values = {
            "result": None,
            "pid": None
        }

        log.info("Starting Remote CFS Mission")

        result = self.execution_controller.run_command_persistent(start_string, cwd=self.config.cfs_run_dir)
        return_values['pid'] = self.execution_controller.get_last_pid()

        if result and return_values['pid'] is not None:
            self.is_running = True
            Global.time_manager.wait_seconds(1)
            result = self.execution_controller.run_command("ps -p {} > /dev/null 2>&1".format(return_values['pid']))

        return_values['result'] = result
        return return_values

    def build_cfs(self):
        """
        Build remote cfs image. The path of cFS source is configured in config init file.
        The build output folder is also configured in init file.
        @return bool: True if build succeed, otherwise False
        """
        log.info("Building Remote CFS")

        build_out_file = os.path.join("/tmp", "{}_build_cfs_output.txt".format(self.config.name))
        build_command = "{} 2>&1 | tee {}".format(self.config.cfs_build_cmd, build_out_file)
        build_success = self.execution_controller.run_command(build_command, cwd=self.config.cfs_build_dir)

        log.debug("Build process completed")
        Global.time_manager.wait_seconds(1)

        stdout_final_path = os.path.join(Global.current_script_log_dir, os.path.basename(build_out_file))
        if not os.path.exists(stdout_final_path):
            if not self.execution_controller.get_file(build_out_file, stdout_final_path, {'delete': True}):
                log.warning("Cannot move CFS build output file to script log directory.")
                if self.execution_controller.last_result:
                    log.debug(self.execution_controller.last_result.stdout.strip())

        if not build_success:
            log.error("Failed to build Remote CFS!")

        return build_success
