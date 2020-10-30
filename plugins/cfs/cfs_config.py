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

"""
cfs_config.py: CFS Plugin Config for CTF.

- Defines the expected fields in the cFS config section for
  a base (linux) target, as well as SP0 and Remote SSH targets.
"""


import os
import socket
import traceback

from lib.Global import Config, expand_path
from lib.args_validation import ArgsValidation
from lib.logger import logger as log

# The CFS Configuration classes handle interpreting the respective CFS Target section
#   in the loaded INI config. The INI config could have multiple CFS targets, defined as sections,
#   and each target specifies the needed fields.
# Documentation of the CFS configuration fields can be found in the CFS Plugin README. Refer to INI or README for
# field descriptions.

class CfsConfig(object):
    def __init__(self, name):
        self.sections = Config.sections()
        self.validation = ArgsValidation()
        self.name = name
        # CFS fields
        self.cfs_protocol = None
        self.build_cfs = None
        self.CCSDS_data_dir = None
        self.CCSDS_target = None
        self.log_ccsds_imports = None
        self.cfs_build_dir = None
        self.cfs_build_cmd = None
        self.cfs_run_dir = None
        self.cfs_port_arg = None
        self.cfs_exe = None
        self.cfs_run_args = None
        self.cfs_run_cmd = None
        self.cfs_output_file = None
        self.start_cfs_on_init = None
        self.remove_continuous_on_fail = None
        self.cfs_target_ip = None
        self.ctf_ip = None
        self.cmd_udp_port = None
        self.tlm_udp_port = None
        self.evs_log_file = None
        self.cfs_debug = None
        self.cfs_run_in_xterm = None
        self.tlm_app_choice = None
        self.ccsds_ver = None
        self.evs_event_mid_name = None
        self.evs_messages_clear_after_time = None
        # Logging fields
        self.evs_log_file = None
        self.endianess_of_target = None
        # The following variable is set by the CCSDS Reader Implementation
        self.CCSDS_header_info_included = None

        if self.name in self.sections:
            log.debug("CFS configuration defined for {}.".format(self.name))
            self.configure(self.name)
        else:
            log.warn("No CFS configuration defined in config file for {}.".format(self.name))

    def configure(self, name):
        try:
            self.load_config_data(name)
            if self.get_error_count() == 0:
                self.set_cfs_run_cmd()
                self.set_ctf_ip()
        except Exception as e:
            self.validation.add_error("Config File error: {}".format(e))
            log.debug(traceback.format_exc())

    def load_field(self, section, field_name, config_getter, validate_function=None):
        value = config_getter(section, field_name, fallback=None)
        if value is None and section != "cfs":
            log.warn("Config Value {}:{} does not exist or is not the right type. "
                     "Attempting to load from base section [cfs].".format(section, field_name))
            value = config_getter("cfs", field_name, fallback=None)
        if value is None:
            log.error("Config Value cfs:{} does not exist or is not the right type. "
                      "Needed to configure CFS.".format(field_name))
            return None
        if validate_function is not None:
            try:
                value = validate_function(value)
            except Exception as e:
                value = None

        if value is None:
            log.error("Invalid Config Value at {}:{}.".format(section, field_name))
            return None

        return value

    def load_config_data(self, section_name):
        if section_name in self.sections:
            self.build_cfs = self.load_field(section_name, "build_cfs", Config.getboolean,
                                             self.validation.validate_boolean)

            self.CCSDS_data_dir = self.load_field(section_name, "CCSDS_data_dir", Config.get,
                                                  self.validation.validate_directory)

            self.CCSDS_target = self.load_field(section_name, "CCSDS_target", Config.get)

            self.log_ccsds_imports = self.load_field(section_name, "log_ccsds_imports", Config.getboolean,
                                                     self.validation.validate_boolean)

            self.cfs_build_dir = self.load_field(section_name, "cfs_build_dir", Config.get,
                                                 self.validation.validate_directory)

            self.cfs_build_cmd = self.load_field(section_name, "cfs_build_cmd", Config.get)

            self.cfs_run_dir = self.load_field(section_name, "cfs_run_dir", Config.get, self.validation.expand_directory)

            self.cfs_port_arg = self.load_field(section_name, "cfs_port_arg", Config.getboolean,
                                                self.validation.validate_boolean)

            self.cfs_exe = self.load_field(section_name, "cfs_exe", Config.get)
            self.validation.validate_file(os.path.join(self.cfs_run_dir, self.cfs_exe))

            self.cfs_run_args = self.load_field(section_name, "cfs_run_args", Config.get)

            self.cfs_output_file = self.load_field(section_name, "cfs_output_file", Config.get)

            self.start_cfs_on_init = self.load_field(section_name, "start_cfs_on_init", Config.getboolean,
                                                     self.validation.validate_boolean)

            self.remove_continuous_on_fail = self.load_field(section_name, "remove_continuous_on_fail",
                                                             Config.getboolean, self.validation.validate_boolean)

            self.cfs_target_ip = self.load_field(section_name, "cfs_target_ip", Config.get,
                                                 self.validation.validate_ip)

            self.cmd_udp_port = self.load_field(section_name, "cmd_udp_port", Config.getint,
                                                self.validation.validate_int)

            self.tlm_udp_port = self.load_field(section_name, "tlm_udp_port", Config.getint,
                                                self.validation.validate_int)

            self.evs_log_file = self.load_field(section_name, "evs_log_file", Config.get)

            self.cfs_debug = self.load_field(section_name, "cfs_debug", Config.getboolean,
                                             self.validation.validate_boolean)

            self.cfs_run_in_xterm = self.load_field(section_name, "cfs_run_in_xterm", Config.getboolean,
                                                    self.validation.validate_boolean)

            self.tlm_app_choice = self.load_field(section_name, "tlm_app_choice", Config.get)

            self.ccsds_ver = self.load_field(section_name, "ccsds_ver", Config.getint,
                                             self.validation.validate_int)

            self.evs_messages_clear_after_time = self.load_field(section_name, "evs_messages_clear_after_time",
                                                                 Config.getint, self.validation.validate_number)

            self.evs_event_mid_name = self.load_field(section_name, "evs_event_mid_name", Config.get)

            self.endianess_of_target = self.load_field(section_name, "endianess_of_target", Config.get)
            # endianness value should be lower-case
            if self.endianess_of_target:
                self.endianess_of_target = self.endianess_of_target.lower()
            # Logging data
            self.evs_log_file = self.load_field(section_name, "evs_log_file", Config.get)

            self.cfs_protocol = self.load_field(section_name, "cfs_protocol", Config.get)

        else:
            log.warn("No CFS configuration defined for {}".format(section_name))

        # The following variable is set by the CCSDS Reader Implementation
        self.CCSDS_header_info_included = self.load_field("ccsds", "CCSDS_header_info_included", Config.getboolean,
                                                  self.validation.validate_boolean)

    def set_ctf_ip(self):

        temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        temp_socket.connect((self.cfs_target_ip, 80))
        self.ctf_ip, port = temp_socket.getsockname()

    def set_cfs_run_cmd(self, cfs_exe="", cfs_run_args=""):
        self.cfs_exe = cfs_exe or self.cfs_exe
        self.cfs_run_args = cfs_run_args or self.cfs_run_args
        self.cfs_run_cmd = self.cfs_exe + " " + self.cfs_run_args

    def get_error_count(self):
        return self.validation.get_error_count()


class RemoteCfsConfig(CfsConfig):
    def __init__(self, name):
        super().__init__(name)
        # Overrides
        self.cfs_protocol = "ssh"
        self.cfs_run_in_xterm = False
        # Additional fields
        self.destination = self.load_field(self.name, "destination", Config.get)


class SP0CfsConfig(CfsConfig):
    def __init__(self, name):
        super().__init__(name)
        # Overrides
        self.cfs_protocol = "sp0"
        # Additional fields
        self.auto_run = self.load_field(self.name, "auto_run", Config.getboolean, self.validation.validate_boolean)
        self.reboot = self.load_field(self.name, "reboot", Config.getboolean, self.validation.validate_boolean)
        self.cfs_exe_path = self.load_field(self.name, "cfs_exe_path", Config.get)
        self.cfs_entry_point = self.load_field(self.name, "cfs_entry_point", Config.get)
        self.validation.validate_symbol(self.cfs_entry_point, os.path.join(self.cfs_run_dir, self.cfs_exe))
        self.cfs_startup_time = self.load_field(self.name, "cfs_startup_time", Config.getfloat,
                                                self.validation.validate_number)
        self.log_stdout = self.load_field(self.name, "log_stdout", Config.getboolean, self.validation.validate_boolean)
