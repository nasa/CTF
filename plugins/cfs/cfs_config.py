"""
cfs_config.py: CFS Plugin Config for CTF.

- Defines the expected fields in the cFS config section for
  a base (linux) target, as well as Remote SSH targets.
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

import os
import socket
import traceback
from pprint import pformat

from lib.ctf_global import Global
from lib.args_validation import ArgsValidation
from lib.logger import logger as log
from lib.exceptions import CtfTestError
from lib.ctf_utility import expand_path


class CfsConfig:
    """
     The CFS Configuration classes handle interpreting the respective CFS Target section
     in the loaded INI config. The INI config could have multiple CFS targets, defined as sections,
     and each target specifies the needed fields.
     Documentation of the CFS configuration fields can be found in the CFS Plugin README. Refer to INI or README for
     field descriptions.
    """
    # pylint: disable=too-many-instance-attributes

    def __init__(self, name):
        """
         Constructor for CfsConfig class.  Assign all Cfs config attributes to default None.
         """
        self.sections = Global.config.sections()
        self.validation = ArgsValidation()
        self.name = name
        # CFS fields
        self.cfs_protocol = None
        self.build_cfs = None
        self.ccsds_data_dir = None
        self.ccsds_target = None
        self.log_ccsds_imports = None
        self.cfs_build_dir = None
        self.cfs_build_cmd = None
        self.cfs_run_dir = None
        self.cfs_port_arg = None
        self.cfs_exe = None
        self.cfs_run_args = None
        self.cfs_ram_drive_path = None
        self.cfs_run_cmd = None
        self.cfs_output_file = None
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
        self.evs_long_event_mid_name = None
        self.evs_short_event_mid_name = None
        self.evs_messages_clear_after_time = None
        self.endianess_of_target = None
        # The following variable is set by the CCSDS Reader Implementation
        self.ccsds_header_info_included = None
        self.telemetry_debug = None

        try:
            self.configure(self.name)
        except CtfTestError:
            log.debug("CtfTestError exception raised in CfsConfig constructor")

    def configure(self, name):
        """
        Setup CfsConfig attributes based on INI file
        """
        try:
            self.load_config_data(name)
            if self.get_error_count() == 0:
                self.set_cfs_run_cmd()
                self.set_ctf_ip()
            log.debug("CfsConfig for target {} resolved the following values:\n{}".format(name, pformat(vars(self))))
        except Exception as exception:
            self.validation.add_error("Config File error: {}".format(exception))
            log.debug(traceback.format_exc())
            raise CtfTestError("Error in configure") from exception

    def load_field(self, section, field_name, config_getter, validate_function=None):
        """
        Interpret field attribute of loaded CFS target config section.
        @param section: loaded Json CFS target section.
        @param field_name: the field name for loaded attribute.
        @param config_getter: the function to get an option value for a given section.
        @param validate_function: the function to validate the field attribute (Optional).
        @return Any: field attribute with matching name
        """

        value = config_getter(section, field_name, fallback=None)
        if value is None and section != "cfs":
            log.info("Config Value {}:{} does not exist or is not the right type. "
                     "Attempting to load from base section [cfs].".format(section, field_name))
            value = config_getter("cfs", field_name, fallback=None)
        if value is None:
            log.error("Config Value cfs:{} does not exist or is not the right type. "
                      "Needed to configure CFS.".format(field_name))
            self.validation.add_error("field {}".format(field_name))
            return None
        if validate_function is not None:
            try:
                value = validate_function(value)
            except (TypeError, OSError, socket.error, IOError):
                value = None

        if value is None:
            log.error("Invalid Config Value at {}:{}.".format(section, field_name))
            return None

        return value

    def load_config_data(self, section_name):
        """
        From loaded sections of INI config, interpret CFS target config attributes, including
        build_cfs, CCSDS_data_dir, CCSDS_target, etc.
        @param section_name: loaded Json CFS target section.
        @return None
        """
        if section_name in self.sections:
            self.build_cfs = self.load_field(section_name, "build_cfs", Global.config.getboolean,
                                             self.validation.validate_boolean)

            self.ccsds_data_dir = self.load_field(section_name, "CCSDS_data_dir", Global.config.get,
                                                  self.validation.validate_directory)

            self.ccsds_target = self.load_field(section_name, "CCSDS_target", Global.config.get)

            self.log_ccsds_imports = self.load_field(section_name, "log_ccsds_imports", Global.config.getboolean,
                                                     self.validation.validate_boolean)

            self.cfs_build_dir = self.load_field(section_name, "cfs_build_dir", Global.config.get,
                                                 self.validation.validate_directory)

            self.cfs_build_cmd = self.load_field(section_name, "cfs_build_cmd", Global.config.get)

            self.cfs_run_dir = self.load_field(section_name, "cfs_run_dir", Global.config.get,
                                               expand_path)

            self.cfs_port_arg = self.load_field(section_name, "cfs_port_arg", Global.config.getboolean,
                                                self.validation.validate_boolean)

            self.cfs_exe = self.load_field(section_name, "cfs_exe", Global.config.get)
            self.validation.validate_file(os.path.join(self.cfs_run_dir, self.cfs_exe))

            self.cfs_run_args = self.load_field(section_name, "cfs_run_args", Global.config.get)

            self.cfs_ram_drive_path = self.load_field(section_name, "cfs_ram_drive_path", Global.config.get)

            self.cfs_output_file = self.load_field(section_name, "cfs_output_file", Global.config.get)

            self.remove_continuous_on_fail = self.load_field(section_name, "remove_continuous_on_fail",
                                                             Global.config.getboolean, self.validation.validate_boolean)

            self.cfs_target_ip = self.load_field(section_name, "cfs_target_ip", Global.config.get,
                                                 self.validation.validate_ip)

            self.cmd_udp_port = self.load_field(section_name, "cmd_udp_port", Global.config.getint,
                                                self.validation.validate_int)

            self.tlm_udp_port = self.load_field(section_name, "tlm_udp_port", Global.config.getint,
                                                self.validation.validate_int)

            self.evs_log_file = self.load_field(section_name, "evs_log_file", Global.config.get)

            self.cfs_debug = self.load_field(section_name, "cfs_debug", Global.config.getboolean,
                                             self.validation.validate_boolean)

            self.cfs_run_in_xterm = self.load_field(section_name, "cfs_run_in_xterm", Global.config.getboolean,
                                                    self.validation.validate_boolean)

            self.tlm_app_choice = self.load_field(section_name, "tlm_app_choice", Global.config.get)

            self.ccsds_ver = self.load_field(section_name, "ccsds_ver", Global.config.getint,
                                             self.validation.validate_int)

            self.evs_messages_clear_after_time = self.load_field(section_name, "evs_messages_clear_after_time",
                                                                 Global.config.getint, self.validation.validate_number)

            self.evs_long_event_mid_name = self.load_field(section_name, "evs_event_mid_name", Global.config.get)

            self.evs_short_event_mid_name = self.load_field(section_name, "evs_short_event_mid_name", Global.config.get)

            self.endianess_of_target = self.load_field(section_name, "endianess_of_target", Global.config.get)
            # endianness value should be lower-case
            if self.endianess_of_target:
                self.endianess_of_target = self.endianess_of_target.lower()
            # Logging data
            self.evs_log_file = self.load_field(section_name, "evs_log_file", Global.config.get)

            self.cfs_protocol = self.load_field(section_name, "cfs_protocol", Global.config.get)

            self.telemetry_debug = self.load_field(section_name, "telemetry_debug", Global.config.getboolean,
                                                   self.validation.validate_boolean)

        else:
            log.warning("No CFS configuration defined for {}".format(section_name))
            self.validation.add_error("section {}".format(section_name))

        # The following variable is set by the CCSDS Reader Implementation
        self.ccsds_header_info_included = self.load_field("ccsds", "CCSDS_header_info_included",
                                                          Global.config.getboolean, self.validation.validate_boolean)

    def set_ctf_ip(self):
        """
        Get the IP address through a temporary created socket to CFS target, and assign the ip to config attribute
        @return None
        """
        temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        temp_socket.connect((self.cfs_target_ip, 80))
        self.ctf_ip = temp_socket.getsockname()[0]

    def set_cfs_run_cmd(self, cfs_exe="", cfs_run_args=""):
        """
        Set CFS config attribute cfs_exe, cfs_run_args, and cfs_run_cmd.
        if passed arguments are empty string, use the config attributes from INI file
        @param cfs_exe: CFS executable name. if it is empty string, use the field from INI file
        @param cfs_run_args: CFS executable arguments. if it is empty string, use the field from INI file
        @return None
        """
        self.cfs_exe = cfs_exe or self.cfs_exe
        self.cfs_run_args = cfs_run_args or self.cfs_run_args
        self.cfs_run_cmd = (self.cfs_exe + " " + self.cfs_run_args).strip()

    def get_error_count(self):
        """
        Return field validation error counts.
        @return field validation error counts
        """
        return self.validation.get_error_count()


class RemoteCfsConfig(CfsConfig):
    """
    CFS Configuration for SSH targets, inherited from CfsConfig class.
    """

    def __init__(self, name):
        """
        Constructor for RemoteCfsConfig Class. Override cfs_protocol attribute to ssh.
        """
        self.destination = None
        super().__init__(name)

        # Overrides
        self.cfs_protocol = "ssh"
        self.cfs_run_in_xterm = False

    def load_config_data(self, section_name):
        """
        From loaded sections of INI config, interpret CFS target config attributes, including
        build_cfs, CCSDS_data_dir, CCSDS_target, etc.
        @param section_name: loaded Json CFS target section.
        @return None
        """
        super().load_config_data(section_name)

        if section_name in self.sections:
            self.destination = self.load_field(self.name, "destination", Global.config.get)
