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
output_app_interface.py: Base-class Lower-level interface to communicate with cFS.
"""
from lib.ctf_global import Global
from lib.logger import logger as log

TO_ENABLE_OUTPUT = "TO_ENABLE_OUTPUT_CC"
TO_ENABLE_OUTPUT_CC = 2
TO_CMD_MID = 0xA00B


class OutputManager:
    """
    Base class that each output application must inherit from.
    within this class, define the methods that all of the output applications must implement
    """

    def __init__(self, local_ip, local_port, command_interface, ccsds_ver, command_mids=None):
        """
        Constructor implementation for OutputManager class. It sets up the local_ip, local_port, command_interface,
        ccsds version, command_args, command_mids.
        """
        self.local_ip = local_ip
        self.local_port = local_port
        self.command_interface = command_interface
        self.ccsds_ver = ccsds_ver
        self.command_args = None
        self.command_mids = command_mids

    def enable_output(self):
        """
        Define abstract enable_output method, the inherited class must implement
        """
        raise NotImplementedError

    def disable_output(self):
        """
        Define abstract disable_output method, the inherited class must implement
        """
        raise NotImplementedError


class ToApi(OutputManager):
    """
    Construct the ToApi class

    For CFS, TO is used to extract command and telemetry CCSDS packets from the software bus, and is sent over UDP
    to the CFS test framework.
    """

    def __init__(self, local_ip="", local_port=0, command_interface=None,
                 ccsds_ver=0, mid_map=None, name=None):
        """
        Constructor of the ToApi class.

        @param local_ip: The IP address we want packets to be forwarded to. Default: 127.0.0.1
        @param local_port: The port we want packets to be forwarded to. Default: 40096
        @param command_interface: An instance of the CommandInterface class (used to send commands to UDP)
        @param ccsds_ver: CCSDS header version (1 or 2)
        """
        OutputManager.__init__(self, local_ip, local_port, command_interface, ccsds_ver)
        for mid, value in mid_map.items():
            if isinstance(value, dict) and TO_ENABLE_OUTPUT in value:
                self.command_args = value[TO_ENABLE_OUTPUT]["ARG_CLASS"]
                self.cmd_cc = value[TO_ENABLE_OUTPUT]['CODE']
                self.mid = mid

        if self.command_args is None:
            log.warning("Could not find TO_ENABLE_OUTPUT_CC in MID_Map. Cannot enable output.")
            return

        self.name = name

    def disable_output(self):
        """
        disable_output cFS instruction is not implemented in ToApi class, always return True.
        @return bool: always return True
        """
        return True

    def enable_output(self):
        """
        Implement enable_output method for ToApi class.
        Build "SendCfsCommand" instruction with command code "TO_ENABLE_OUTPUT",
        search for a plugin to send out the instruction.
        @return bool: True if a plugin send out instruction successfully; otherwise False
        """

        if self.command_args is None:
            log.error("Failed to enable output.")
            return False
        # ENHANCE - This could fail if TO command structure doesn't contain below fields.
        #           Error will be reported, however, from the cfs_plugin. Maybe allow user to configure
        #           args for TO. Maybe provide CTF "functions" JSON file that receives input in the test script.
        instruction = {
            "data": {
                "target": self.name,
                "cc": TO_ENABLE_OUTPUT,
                "args": {"cDestIp": self.local_ip, "usDestPort": self.local_port},
                "mid": self.mid
            },
            "instruction": "SendCfsCommand"
        }

        return Global.plugin_manager.find_plugin_for_command_and_execute(instruction)
