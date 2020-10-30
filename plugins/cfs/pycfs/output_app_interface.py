"""
output_app_interface.py: Base-class Lower-level interface to communicate with cFS.
"""
from lib.Global import Global
from lib.logger import logger as log

TO_ENABLE_OUTPUT = "TO_ENABLE_OUTPUT_CC"
TO_ENABLE_OUTPUT_CC = 2
TO_CMD_MID = 0xA00B


class OutputManager(object):
    """Base class that each output application must inherit from. within this class
    you must define the methods that all of your output applications must implement
    """

    def __init__(self, local_ip, local_port, command_interface, ccsds_ver, command_mids=None):
        self.local_ip = local_ip
        self.local_port = local_port
        self.command_interface = command_interface
        self.ccsds_ver = ccsds_ver
        self.command_args = None

    def enable_output(self):
        raise NotImplementedError

    def disable_output(self):
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
        Construct the ToApi class.

        :param local_ip: The IP address we want packets to be forwarded to. Default: 127.0.0.1
        :param local_port: The port we want packets to be forwarded to. Default: 40096
        :param command_interface: An instance of the CommandInterface class (used to send commands to UDP)
        :param ccsds_ver: CCSDS header version (1 or 2)
        """
        OutputManager.__init__(self, local_ip, local_port, command_interface, ccsds_ver)
        for mid, value in mid_map.items():
            if isinstance(value, dict) and TO_ENABLE_OUTPUT in value:
                self.command_args = value[TO_ENABLE_OUTPUT]["ARG_CLASS"]
                self.cc = value[TO_ENABLE_OUTPUT]['CODE']
                self.mid = mid

        if self.command_args is None:
            log.warn("Could not find TO_ENABLE_OUTPUT_CC in MID_Map. Cannot enable output.")
            return

        self.command_args.cDestIp = self.local_ip
        self.command_args.usDestPort = self.local_port
        self.name = name

    def enable_output(self):
        if self.command_args is None:
            log.error("Failed to enable output.")
            return False
        # TODO - This could fail if TO command structure doesn't contain below fields.
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
