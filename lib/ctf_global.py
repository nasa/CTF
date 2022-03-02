"""
@namespace lib.ctf_global
Exposes CTF global state information for utilization by CTF Plugins.

Global Test Info object accessible by all plugins.
Populated by script reader with test header
info and other useful values for plugins
"""

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

import argparse
import configparser
import os
import sys

from enum import Enum

## Default Config used by CTF if no config_file is provided in the arguments
DEFAULT_CONFIG = "configs/default_config.ini"


class CtfVerificationStage(Enum):
    """
    Static class containing enumerations for verification stages of a CTF verification instruction.

    @note The verification stage enums can be used to check which verification stage a CTF verification instruction is
    on. Different logic can be implemented depending on the verification stage.
    """
    none = 0
    first_ver = 1
    polling = 2
    last_ver = 3


class Global:
    """
    Static class containing globally accessible CTF and plugin data.
    """

    ## Config parser for the designated config file, initialized in load_config
    config = None

    ## Dictionary of loaded plugins. Set by the CTF core after loading plugins.
    plugins_available = dict()

    ## Reference to the plugin manager object. May be used to invoke instructions (or access) other plugins.
    plugin_manager = None

    ## Log directory of current script. Useful when needing to write data to the current log directory.
    current_script_log_dir = ""

    ## Log directory of the complete test run (includes log directory of scripts)
    test_log_dir = ""

    ## Temporary logging directory for CTF. Contents of the temporary directory are moved to the test log directory on
    ## test completion.
    CTF_log_dir = ""

    ## CTF top-level log file. Includes CTF core logs such as initialization and plugin loading/unloading
    CTF_log_dir_file = None

    ## Current time manager used by CTF. Utilized by other plugins to manage time
    time_manager = None

    ## Start time of current test run
    test_start_time = None

    ## Start time of current verification
    current_verification_start_time = None

    ## Current verification stage. Use CtfVerificationStage to evaluate what verification stage CTF is currently at.
    current_verification_stage = CtfVerificationStage.none

    ## [Read-Only] Current Instruction Index, default value is None.
    # current_instruction_index is updated by lib/test.py to track the execution instruction index of the test.
    # Use Utility function "get_current_instruction_index()" to get the index value (int).
    current_instruction_index = None

    ## [Read-Only] Current goto instruction index, default value is None.
    # Control Flow Plugins can set the next instruction index to execute based on user input
    # or logic within the plugin. Do not use it directly
    goto_instruction_index = None

    ## [Read-Only] Variable Storage. Recommend using utility functions to set/get variables.
    variable_store = {}
    label_map = {}
    goto_label_map = {}
    conditional_branch_map = {}

    @staticmethod
    def create_arg_parser():
        """
        Creates and returns an argument parser for command line args.
        """
        parser = argparse.ArgumentParser(description='cFS Test Framework')
        parser.add_argument('scripts', nargs='*', type=str,
                            help='List of script paths to run', default=[])
        parser.add_argument('--port', type=int,
                            help='UDP port for GUI', default=None)
        parser.add_argument("--pluginInfo", type=str, help="Create plugin info files in the directory specified",
                            required=False)
        parser.add_argument('--config_file', type=str,
                            help='Config file for CTF', default=DEFAULT_CONFIG)
        return parser

    @staticmethod
    def load_config(config_file):
        """
        Loads the config file specified and sets the workspace_dir environment variable

        @note - Command line arguments are not visible here, so the status message indicates if the default config
        is being used in case it was not explicitly provided.
        @note - If the config file does not exist, the application will exit with an error.
        @note - The config field cfs:workspace_dir will be set as an environment variable for the current process.

        @return str: An optional status message, since logging will not have been configured yet
        """
        status = ""
        if config_file == DEFAULT_CONFIG:
            status = "Config file may not have been specified. Using default config {}".format(DEFAULT_CONFIG)
        if not os.path.exists(config_file):
            status += "Config file does not exist....\nFailed to load config file: {}\n.".format(
                os.path.abspath(config_file))
            sys.exit(status)

        Global.config = configparser.ConfigParser(os.environ, interpolation=configparser.ExtendedInterpolation())
        Global.config.read(config_file)
        os.environ["workspace_dir"] = Global.config.get("cfs", "workspace_dir", fallback="")

        return status

    @staticmethod
    def set_time_manager(time_manager):
        """
        Sets the currently active time manager.

        @note - A custom plugin time manager *must* inherit from the TimeManager class and implement its methods
        """
        Global.time_manager = time_manager

    @staticmethod
    def get_time_manager():
        """
        Gets the currently active time manager
        """
        return Global.time_manager
