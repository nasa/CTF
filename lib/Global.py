# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# Copyright (c) 2019-2020 United States Government as represented by the
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
# Global Test Info object accessible by all plugins.
# Populated by script reader with test header
# info and other useful values for plugins

DEFAULT_CONFIG = "configs/default_config.ini"

Config = configparser.SafeConfigParser(os.environ, interpolation=configparser.ExtendedInterpolation())
parser = argparse.ArgumentParser(description='cFS Test Framework')

parser.add_argument('scripts', nargs='*', type=str,
                    help='List of script paths to run', default=[])

parser.add_argument('--port', type=int,
                    help='UDP port for GUI', default=None)

parser.add_argument("--pluginInfo", type=str, help="Create plugin info files in the directory specified",
                    required=False)

parser.add_argument('--config_file', type=str,
                    help='Config file for CTF', default=DEFAULT_CONFIG)

parser.add_argument('--script_dir', type=str,
                    help='Run all JSON CTF scripts in the given directory', required=False)

class CtfVerificationStage:
    none = 0
    first_ver = 1
    polling = 2
    last_ver = 3

class Global(object):
    args = parser.parse_args()

    if not os.path.exists(args.config_file):
        err = ""
        if args.config_file == DEFAULT_CONFIG:
            err += "Trying to load default config: {}\n".format(os.path.abspath(DEFAULT_CONFIG))
        err += "Config file does not exist....\nFailed to load config file: {}\n.".format(
            os.path.abspath(args.config_file))
        sys.exit(err)
        
    Config.read(args.config_file)

    plugins_available = dict()
    plugin_manager = None

    log_level = Config.get("logging", "log_level", fallback="DEBUG")

    telemetry_watch_list_mids = []
    command_watch_list_mids = []

    current_script_log_dir = ""
    test_log_dir = ""
    CTF_log_dir = ""
    CTF_log_dir_file = None

    time_manager = None
    test_start_time = None

    current_verification_start_time = None
    current_verification_stage = CtfVerificationStage.none

    @staticmethod
    def set_time_manager(time_manager):
        Global.time_manager = time_manager

    @staticmethod
    def get_time_manager():
        return Global.time_manager


def expand_path(path):
    return os.path.expanduser(os.path.expandvars(path))
