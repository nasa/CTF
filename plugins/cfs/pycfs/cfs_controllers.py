# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# Copyright (c) 2019-2021 United States Government as represented by the
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
cfs_controllers.py: CFS Controller Implementation for CTF.

- When the CFS plugin registers a target, a cFS controller object is instantiated.
- After the cfs_plugin receives a test instruction, the cFS controller handles all
  lower-level functionality beneath the plugin.
- On controller initialization, telem/command interfaces are established, CCSDS message
  definitions are parsed to build the mid map, and controller becomes ready to send commands
  and verify telemetry.
- Controller implements the specific functionality needed to execute the cFS plugin instructions
- Controller manages cFS process, and will shutdown the target at the end of the test script or on
  ShutdownCfs instruction.
"""

import ctypes
import json
import os
import re
import shutil
import time
from subprocess import run, PIPE, STDOUT
import traceback
from ast import literal_eval
from pathlib import Path

from lib.exceptions import CtfParameterError, CtfTestError
from lib.ctf_global import Global, CtfVerificationStage
from lib.logger import logger as log
from plugins.ccsds_plugin.ccsds_packet_interface import import_ccsds_header_types
from plugins.ccsds_plugin.readers.ccdd_export_reader import CCDDExportReader
from plugins.cfs.pycfs.local_cfs_interface import LocalCfsInterface
from plugins.cfs.pycfs.command_interface import CommandInterface
from plugins.cfs.pycfs.tlm_listener import TlmListener
from plugins.ssh.ssh_plugin import SshController, SshConfig
from plugins.cfs.pycfs.remote_cfs_interface import RemoteCfsInterface

try:
    from plugins.sp0_plugin.sp0.sp0_cfs_interface import SP0CfsInterface
except ImportError:
    SP0CfsInterface = None

MACRO_MARKER = '#'


class CfsController:
    """
    CfsController class Definition: CFS Controller Implementation for CTF.

    @note When the CFS plugin registers a target, a cFS controller object is instantiated.
    @note After the cfs_plugin receives a test instruction, the cFS controller handles all
      lower-level functionality beneath the plugin.
    @note On controller initialization, telem/command interfaces are established, CCSDS message
      definitions are parsed to build the mid map, and controller becomes ready to send commands
      and verify telemetry.
    @note Controller implements the specific functionality needed to execute the cFS plugin instructions
    @note Controller manages cFS process, and will shutdown the target at the end of the test script or on
         ShutdownCfs instruction.
    """

    def __init__(self, config):
        """
        Constructor implementation for CfsController class. Assign default values for CfsController properties
        """
        self.config = config
        self.cfs_process_list = []
        self.cfs = None
        self.ccsds_reader = None
        self.mid_map = None
        self.macro_map = None
        self.first_call_flag = True
        self.mid_pkt_count = None
        self.cfs_running = False

    def process_ccsds_files(self):
        """
        Create mid map for CFS plugin, if map does not exist, create ccsds_reader from INIT config file.
        """
        if self.mid_map is None:
            log.info("Creating MID Map from CCDD Data at {}".format(self.config.ccsds_data_dir))
            self.ccsds_reader = CCDDExportReader(self.config)
            self.mid_map, self.macro_map = self.ccsds_reader.get_ccsds_messages_from_dir(self.config.ccsds_data_dir)
        else:
            log.debug("MID Map is already populated; skipping CCDD Data...")

    def initialize(self):
        """
        Initialize CfsController instance, including the followings: create mid map; import ccsds header;
        create command interface; create telemetry interface; create local CFS interface
        """
        log.debug("Initializing CfsController")
        self.process_ccsds_files()

        try:
            ccsds = import_ccsds_header_types()
        except CtfTestError:
            ccsds = None
            log.warning("Error: import_ccsds_header_types ")

        if not (ccsds and ccsds.CcsdsPrimaryHeader and ccsds.CcsdsCommand and ccsds.CcsdsTelemetry):
            log.error("Unable to import required CCSDS header types")
            return False

        log.info("Starting Local CFS Interface to {}:{}".format(self.config.cfs_target_ip, self.config.cmd_udp_port))
        command = CommandInterface(ccsds, self.config.cmd_udp_port, self.config.cfs_target_ip,
                                   self.config.endianess_of_target)
        telemetry = TlmListener(self.config.ctf_ip, self.config.tlm_udp_port)
        self.cfs = LocalCfsInterface(self.config, telemetry, command, self.mid_map, ccsds)
        result = self.cfs.init_passed
        if not result:
            log.error("Failed to initialize LocalCfsInterface")

        if result:
            log.info("CfsController Initialized")
        return result

    def build_cfs(self):
        """
        Implementation of CFS plugin instructions build_cfs. When CFS plugin instructions (build_cfs) is executed,
        it calls CfsController instance's build_cfs function.
        """
        log.info("Building CFS on {}".format(self.config.name))
        return self.cfs.build_cfs()

    def start_cfs(self, run_args):
        """
        Implementation of CFS plugin instructions start_cfs. When CFS plugin instructions (start_cfs) is executed,
        it calls CfsController instance's start_cfs function.
        """
        log.info("Starting CFS on {}".format(self.config.name))
        result = {}
        try:
            result = self.cfs.start_cfs(run_args)
        except CtfTestError:
            result["result"] = False
            log.error("Error: cfs.start_cfs exception caught!")

        if result["result"]:
            # If CFS properly launches the pid will be stored for later use
            self.cfs_process_list.append(result["pid"])
            Global.time_manager.wait(3)
        else:
            log.error("Failed to start CFS!")
            return False
        self.cfs_running = result["result"]
        return self.cfs_running

    def enable_cfs_output(self):
        """
        Implementation of CFS plugin instructions enable_cfs_output.  When CFS plugin instructions
        (enable_cfs_output) is executed, it calls CfsController instance's enable_cfs_output function.
        """
        log.info("Enabling CFS output on {}".format(self.config.name))
        return self.cfs.enable_output()

    # noinspection PyProtectedMember
    # pylint: disable=protected-access
    def send_cfs_command(self, mid, cc, args, header_args=None, payload_length=None, ctype_args=False):
        """
        Implementation of CFS plugin instructions send_cfs_command.  When CFS plugin instructions
        (send_cfs_command) is executed, it calls CfsController instance's send_cfs_command function.

        @note When using CCSDS version 2 subsysId, endian and systemId will all be given a value when the function
        below is called. If using CCSDS version 1 these 3 variables are not needed and will be assigned a default
        value of 'None' to prevent any issues.
        @note If ctype_args is true, CFS Plugin will use the "args" parameters as the raw ctype Structure to be sent
        """
        # pylint: disable=invalid-name, protected-access
        if not ctype_args:
            log.info("Sending CFS Command to target: {}, {}:{} with Args: {}".format(self.config.name, mid,
                                                                                     cc, json.dumps(args)))
        if not isinstance(mid, str):
            for key, value in self.mid_map.items():
                if value.get("MID") == mid:
                    mid = key
                    break
        if not self.mid_available(mid):
            return False
        # Use the incoming 'mid' string to retrieve the int value of the mid we are looking for
        # and all command codes associated with it.
        cmd_message = self.mid_map[mid]
        cmd_mid = cmd_message["MID"]
        arg_size = 0
        arg_data = bytes()
        # retrieve variables from appropriate dictionaries
        if not isinstance(cc, int):
            if cc in cmd_message["CC"]:
                code_dict = cmd_message["CC"][cc]
            else:
                log.error("Could not find Command Code {}  in MID Map".format(cc))
                return False
            arg_class = code_dict["ARG_CLASS"]
            cc = code_dict["CODE"]
        else:
            arg_class = None

        # If we are passing ctypes arguments from the MID map internally,
        # we don't need to construct the message...
        if ctype_args:
            log.info("Sending Command with internal CTF cTypes Argument...")
            if isinstance(args, ctypes.Structure):
                arg_size = ctypes.sizeof(args)

        # If length does not equal None than the test is attempting to send an invalid length command
        # for testing purposes
        elif payload_length is not None:
            arg_data = bytearray(payload_length)
        elif arg_class is not None:
            try:
                # ENHANCE - Backwards compatibility with the editor output of empty args = []
                if isinstance(args, list) and len(args) == 0:
                    args = {}
                if isinstance(args, dict):
                    args = self.resolve_args_from_dict(args, arg_class)
                else:
                    assert len(arg_class._fields_) == 1, 'Raw values can only be used for types with a single field'
                    args = arg_class(self.resolve_simple_type(args, arg_class._fields_[0][1]))
            except Exception as exception:
                log.error("Failed to build command message from args: {}".format(exception))
                raise CtfTestError("Error in send_cfs_command") from exception

            if args is not None:
                try:
                    arg_size = ctypes.sizeof(args)
                except TypeError as exception:
                    log.error("Failed to build command message: {}".format(exception))
                    return False

        if arg_size > 0:
            buf = (ctypes.c_char * ctypes.sizeof(args)).from_buffer_copy(args)
            ctypes.memset(buf, 0, len(buf))
            buf_offset = 0

            # ENHANCE - Verify that ctypes handles bit-fields. If not, add ability to handle them
            # noinspection PyProtectedMember
            def handle_field(arg_val, field, offset):
                # Disable all the protected-access warnings in this function
                # pylint: disable=protected-access
                field_name = field[0]
                field_type = field[1]
                if isinstance(field_name, int):
                    field_val = arg_val[field_name]
                else:
                    field_val = getattr(arg_val, field_name)
                field_length = ctypes.sizeof(field_type)

                if isinstance(field_type, type(self.ccsds_reader.ctype_structure)):
                    for field_id in field_type._fields_:
                        offset = handle_field(field_val, field_id, offset)

                # This indicates a custom array type - need to recurse using the indexed inner type
                elif hasattr(field_type, '_length_') and not hasattr(field_type._type_, '_type_'):
                    for type_id in range(int(field_type._length_)):
                        offset = handle_field(field_val, (type_id, field_val._type_), offset)

                if isinstance(field_type, type(self.ccsds_reader.ctype_structure)) or \
                        (hasattr(field_type, '_length_') and not hasattr(field_type._type_, '_type_')):
                    return offset

                mytype = field_type._type_
                if isinstance(mytype, type(ctypes.c_char)):
                    for j in range(field_length):
                        if j < len(field_val):
                            if not isinstance(field_val, bytes) and not isinstance(field_val, ctypes.Array):
                                field_val = field_val.encode()
                            buf[offset] = ctypes.c_char(field_val[j])
                        else:
                            buf[offset] = 0
                        offset += 1
                else:
                    buf[offset:offset + field_length] = bytes(field_type(field_val))
                    offset += field_length
                return offset

            for i in args._fields_:  # pylint: disable=protected-access
                buf_offset = handle_field(args, i, buf_offset)

            arg_data = buf.raw

        log.debug("Sending bytes: {}".format(arg_data))
        result = self.cfs.send_command(cmd_mid, cc, arg_data, header_args)

        if not result:
            log.error("Failed to send command message: MID {}, CC {}, args {}".format(cmd_mid, cc, args))
        return result

    # ENHANCE - We can move the resolve functions to the ccsds_interface/manager. Maybe those functions
    #        can be used from other plugins in the future. It could be that the mid_map and macro map
    #        live in the ccsds_plugin and is utilized by cfs. May be long-term suggestion here.
    def resolve_macros(self, arg):
        """
        Implementation of helper function resolve_macros.
        search macro_map to convert arg to string.
        """
        if isinstance(arg, str):
            while arg.count(MACRO_MARKER) > 1:
                macro = arg.split(MACRO_MARKER, 1)[1].split(MACRO_MARKER, 1)[0]
                if macro in self.macro_map:
                    arg = arg.replace("{}{}{}".format(MACRO_MARKER, macro, MACRO_MARKER), str(self.macro_map[macro]))
                else:
                    raise CtfParameterError("Unknown macro '{}' in arg {}. Use format #MACRO#".format(macro, arg), arg)
        return arg

    # noinspection PyProtectedMember
    def resolve_simple_type(self, arg, arg_type):
        """
        Implementation of helper function resolve_simple_type.
        Resolves any macros in arg and converts it to a type appropriate for arg_class
        """
        # pylint: disable=protected-access
        arg = self.resolve_macros(arg)
        if arg_type == ctypes.c_bool:
            if isinstance(arg, int):
                arg = bool(arg)
            elif isinstance(arg, str) and arg.lower() in ['true', 'false']:
                arg = arg.lower() == 'true'
            else:
                raise CtfParameterError("Invalid value for bool: {}".format(arg), arg)
        elif arg_type in [ctypes.c_char, ctypes.c_char_p, ctypes.c_wchar, ctypes.c_wchar_p]:
            arg = str(arg).encode()
        elif arg_type in [ctypes.c_float, ctypes.c_double, ctypes.c_longdouble]:
            arg = float(arg)
        else:
            arg = int(str(arg), 0)
        return arg

    # noinspection PyProtectedMember
    def resolve_args_from_dict(self, args, args_class):
        """
        Implementation of helper function resolve_args_from_dict.
        Convert argument args to args_class
        """
        # pylint: disable=protected-access
        for key, value in list(args.items()):
            name = self.resolve_macros(key)
            index = None
            # indexed args of the form 'name[offset]' will be handled differently below
            if re.match(r"^[\w]+\[\d+\]$", name):
                index = int(name[name.find('[') + 1:name.find(']')])
                name = name.split('[')[0]
            field_class = self.field_class_by_name(name, args_class)

            # If we're dealing with an indexed arg, the array container will be an extra layer in
            # the ctype hierarchy. We must ensure that exactly one such container is maintained to
            # contain any such args at the correct index. The actual field_class of the arg will be
            # the inner _type_ class
            if index is not None:
                if name not in args:
                    args[name] = field_class()
                else:
                    assert isinstance(args[name], field_class)
                field_class = field_class._type_  # pylint: disable=protected-access
            else:
                # handle default value to the array. For example, the args element is "DataArray": 200
                # instead of "DataArray[1]": 200. So the index is None, and field_class is array.
                if hasattr(field_class, '_length_'):
                    value = self.resolve_macros(value)
                    # resolve_macros may convert macros to str,  need to convert str to element type
                    # if it can be converted into int
                    if isinstance(value, str) and value.isdigit():
                        value = int(value)
                    if not isinstance(value, str):
                        log.debug("Assign default value '{}' for array {}".format(value, field_class))
                        args[name] = field_class()
                        array_element_type = field_class._type_
                        array_element_value = self.resolve_simple_type(value, array_element_type)
                        # dynamic initialization of ctypes array from list of ctypes value
                        args[name] = field_class(*[array_element_type(array_element_value)] * field_class._length_)
                        continue

            if isinstance(value, (list, tuple)):
                raise CtfParameterError("Dictionary containing list is not a supported args format."
                                        " Use dictionaries with fully qualified names.", value)

            if isinstance(value, dict):
                args[key] = self.resolve_args_from_dict(value, field_class)
            else:
                field_class = field_class._type_ if hasattr(field_class, '_length_') else field_class
                args[key] = self.resolve_simple_type(value, field_class)

            # If we've created an indexed arg, it must now be moved into the array container
            # because args_class cannot handle the array syntax. Since we cannot remove the
            # key during iteration it will be set to None and ignored when args_class is created.
            if index is not None:
                args[name][index] = args[key]
                del args[key]

        return args_class(**args)

    # noinspection PyProtectedMember
    @staticmethod
    def field_class_by_name(name, args_class):
        """
        Implementation of helper function field_class_by_name.
        Return a field with matching name.
        """
        for field in args_class._fields_:  # pylint: disable=protected-access
            if field[0] == name:
                return field[1]
        raise CtfParameterError("No field {} in {}".format(name, args_class.__name__), name)

    def check_tlm_value(self, mid, args=None):
        """
        Implementation of CFS plugin instructions check_tlm_value. When CFS plugin instructions (check_tlm_value)
        is executed, it calls CfsController instance's check_tlm_value function.
        """
        if not self.mid_available(mid):
            if Global.current_verification_stage == CtfVerificationStage.first_ver:
                log.error("MID {} not in the mid_map.".format(mid))
            return False

        mid = self.mid_map[mid]
        current_mid_value = mid["MID"]

        if current_mid_value not in self.cfs.received_mid_packets_dic.keys():
            if Global.current_verification_stage == CtfVerificationStage.first_ver:
                log.error("Messages never received for MID {}:{}.".format(mid, current_mid_value))
                return False

        args = self.convert_check_tlm_args(args) if args else None
        result = self.cfs.check_tlm_value(mid, args)

        if result:
            log.info("PASSED Final Check for MID:{}, Args:{}".format(mid, args))

        return result

    def get_tlm_value(self, mid, tlm_variable):
        """
        Implementation of CFS plugin instructions get_tlm_value. When CFS plugin method (get_tlm_value)
        is executed, it calls CfsController instance's get_tlm_value function.
        """
        if not self.mid_available(mid):
            log.error("MID {} not in the mid_map.".format(mid))
            return None

        mid = self.mid_map[mid]
        current_mid_value = mid["MID"]

        if current_mid_value not in self.cfs.received_mid_packets_dic.keys():
            log.error("Messages never received for MID {}:{}.".format(mid, current_mid_value))
            return None

        result = self.cfs.get_tlm_value(mid, tlm_variable)
        return result

    def check_tlm_continuous(self, v_id, mid, args):
        """
        Implementation of CFS plugin instructions check_tlm_continuous. When CFS plugin instructions
        (check_tlm_continuous) is executed, it calls CfsController instance's check_tlm_continuous function.
        """
        log.info("Adding continuous telemetry check {} on {}".format(v_id, self.config.name))
        if not self.mid_available(mid):
            log.error("MID {} not in the mid_map.".format(mid))
            return False

        mid = self.mid_map[mid]
        current_mid_value = mid["MID"]

        if current_mid_value not in self.cfs.received_mid_packets_dic.keys():
            log.error("Messages never received for MID {}:{}.".format(mid, current_mid_value))
            return False

        args = self.convert_check_tlm_args(args)
        return self.cfs.add_tlm_condition(v_id, mid, args)

    def convert_check_tlm_args(self, args):
        """
        Implementation of helper function convert_check_tlm_args.
        Convert telemetry data args with "value" to a list
        """
        for i, arg in enumerate(args):
            arg["variable"] = self.resolve_macros(arg["variable"])
            if isinstance(arg["value"], list):
                for j in range(len(arg["value"])):
                    arg["value"][j] = self.resolve_macros(arg["value"][j])
                    args[i] = arg
            else:
                args[i]["value"] = self.resolve_macros(arg["value"])

        return [args] if isinstance(args, dict) else args

    def remove_check_tlm_continuous(self, v_id):
        """
        Implementation of CFS plugin instructions remove_check_tlm_continuous. When CFS plugin instructions
        (remove_check_tlm_continuous) is executed, it calls CfsController instance's function.
        """
        log.info("Removing continuous telemetry check {} on {}".format(v_id, self.config.name))
        return self.cfs.remove_tlm_condition(v_id)

    def check_event(self, app, id, msg=None, is_regex=False, msg_args=None):
        """
        Checks for an EVS event message in the telemetry packet history,
        assuming a particular structure for CFE_EVS_LongEventTlm_t.
        This can be generified in the future to determine the structure from the MID map.
        """
        # pylint: disable=invalid-name,redefined-builtin
        log.info("Checking event on {}".format(self.config.name))
        if msg_args is not None and len(msg_args) > 0:
            try:
                msg = msg % literal_eval(msg_args)
            except (ValueError, SyntaxError):
                log.error("Failed to check Event ID {} in App {} with message: '{}' with msg_args = {}".format(
                    id, app, msg, msg_args))
                log.debug(traceback.format_exc())
                return False

        if not str(id).isnumeric():
            id = self.resolve_macros(id)

        # ENHANCE - Should use the mid_map and EVS event name to determine these...
        # These are the values that will be used to look through the telemetry packets
        # for the expected packet
        args = [
            {"compare": "streq", "variable": "Payload.PacketID.AppName", "value": app},
            {"compare": "==", "variable": "Payload.PacketID.EventID", "value": id}
        ]

        result = self.cfs.check_tlm_value(self.cfs.evs_short_event_msg_mid, args, discard_old_packets=False)
        if result:
            log.info("Received EVS_ShortEventTlm_t. Ignoring 'Message' field...")
        else:
            if msg:
                compare = "regex" if is_regex else "streq"
                args.append({"compare": compare, "variable": "Payload.Message", "value": msg})
                result = self.cfs.check_tlm_value(self.cfs.evs_long_event_msg_mid, args, discard_old_packets=False)
            else:
                log.warning("No msg provided; any message for App {} and Event ID {} will be matched.".format(app, id))
                result = self.cfs.check_tlm_value(self.cfs.evs_long_event_msg_mid, args, discard_old_packets=False)

        return result

    def archive_cfs_files(self, source_path):
        """
        Implementation of CFS plugin instructions archive_cfs_files. When CFS plugin instructions
        (archive_cfs_files) is executed, it calls CfsController instance's archive_cfs_files function.
        """
        log.info("Archiving CFS files from {}".format(self.config.name))
        artifacts_path = os.path.join(Global.current_script_log_dir, "artifacts")
        if not os.path.exists(artifacts_path):
            os.makedirs(artifacts_path)
        try:
            start_time = time.mktime(Global.test_start_time)
            for file in Path(source_path).iterdir():
                if start_time < file.stat().st_mtime:
                    shutil.move(str(file), artifacts_path)
                    log.info("Copied {} to {}".format(file.name, artifacts_path))
            return True
        except (OverflowError, ValueError, IOError, OSError, TypeError) as exception:
            log.error("Failed to archive files: {}".format(exception))
            return False

    def shutdown_cfs(self):
        """
        Implementation of CFS plugin instructions shutdown_cfs. When CFS plugin instructions
        (shutdown_cfs) is executed, it calls CfsController instance's shutdown_cfs function.
        """
        log.info("Shutting down CFS on {}".format(self.config.name))

        # Close the command socket, close the telemetry socket and write the CFS EVS Log File
        if self.cfs:
            self.cfs.stop_cfs()

        # check whether cFS instance exists
        pidof_cfs = "pidof {}".format(self.config.cfs_run_cmd)
        pid = run(pidof_cfs, stdout=PIPE, stderr=STDOUT, shell=True, check=False).stdout.decode()
        if pid == "":
            log.error("CFS executable {} had already terminated!".format(self.config.cfs_run_cmd))
            self.cfs_process_list = []
            self.cfs_running = False
            return True

        kill_string = "kill -9 $(pidof {})".format(self.config.cfs_exe)
        status = os.system(kill_string) == 0
        if not status:
            log.error("Failed to kill process {}. CFS may have already exited.")
        self.cfs_process_list = []
        self.cfs_running = False
        return status

    def shutdown(self):
        """
        This function will shut down the CFS application being tested even if the JSON test file does not
        include the shutdown test command
        """
        log.info("Shutting down controller for {}".format(self.config.name))
        if self.cfs:
            if self.cfs_running:
                try:
                    self.shutdown_cfs()
                except CtfTestError:
                    log.error("Error: Shutting down controller for {}".format(self.config.name))

            self.cfs = None

    def mid_available(self, mid_name):
        """
        Implementation of helper function mid_available.
        Check whether mid_name is in mid_map dictionary.
        """
        available = False
        try:
            available = mid_name in self.mid_map
        except TypeError as exception:
            log.error("Failed to query the CFS Plugin MID Map.")
            if self.mid_map is None:
                log.error("Ensure CCDD Export Directory is valid...")
            log.debug(exception)

        if not available:
            log.error("{0} not in MID Map. Ensure {0} is defined in CCSDS Exports.".format(mid_name))

        return available


class RemoteCfsController(CfsController):
    """
    RemoteCfsController class Definition:

    @note RemoteCfsController class is inherited from CfsController class. It only redefines a few functions,
          including __init__, initialize, archive_cfs_files, shutdown_cfs, shutdown.
    @note SP0CfsController is initiated when INI config file uses 'ssh' protocol.
    """

    def __init__(self, config):
        """
        Constructor implementation for RemoteCfsController class.
        """
        super().__init__(config)
        self.execution = None

    def initialize(self):
        """
        Initialize CfsController instance, including the followings: create mid map; import ccsds header;
        create ssh CFS command interface; create telemetry interface;
        """
        log.debug("Initializing RemoteCfsController")
        self.process_ccsds_files()

        try:
            ccsds = import_ccsds_header_types()
        except CtfTestError:
            ccsds = None
            log.warning("Error: import_ccsds_header_types")

        if not (ccsds and ccsds.CcsdsPrimaryHeader and ccsds.CcsdsCommand and ccsds.CcsdsTelemetry):
            log.error("Unable to import required CCSDS header types")
            return False

        log.info("Starting Remote CFS Interface to {}:{}".format(self.config.cfs_target_ip, self.config.cmd_udp_port))
        self.execution = SshController(SshConfig())
        result = self.execution.init_connection(self.config.destination)
        if not result:
            log.error("Failed to initialize SshController")
        else:
            command = CommandInterface(ccsds, self.config.cmd_udp_port, self.config.cfs_target_ip)
            telemetry = TlmListener(self.config.ctf_ip, self.config.tlm_udp_port)
            self.cfs = RemoteCfsInterface(self.config, telemetry, command, self.mid_map, ccsds, self.execution)
            result = self.cfs.init_passed
            if not result:
                log.error("Failed to initialize RemoteCfsInterface")
            else:
                log.warning("Not starting CFS executable... Expecting \"StartCfs\" in test script...")

        if result:
            log.info("RemoteCfsController Initialized")
        return result

    def archive_cfs_files(self, source_path):
        """
        Implementation of CFS plugin instructions archive_cfs_files. When CFS plugin instructions
        (archive_cfs_files) is executed, it calls RemoteCfsController instance's archive_cfs_files function.
        """
        artifacts_path = os.path.join(Global.current_script_log_dir, "artifacts")

        if not os.path.exists(artifacts_path):
            os.makedirs(artifacts_path)

        elapsed_min = (time.mktime(time.localtime()) - time.mktime(Global.test_start_time)) / 60
        results_file = "/tmp/files_since_{}".format(time.strftime("%Y%m%d-%H%M%S", Global.test_start_time))
        find_cmd = "find . ! -path . -mmin -{:.2f} > {}".format(elapsed_min, results_file)

        run_command_result = None
        if self.execution.run_command(find_cmd, source_path):
            args = {
                "rsync_opts": "--files-from={}".format(results_file)
            }
            run_command_result = self.execution.get_file(source_path, artifacts_path, args)
        else:
            log.error("Unable to find files to archive.")
            run_command_result = False
        return run_command_result

    def shutdown_cfs(self):
        """
        Implementation of CFS plugin instructions shutdown_cfs. When CFS plugin instructions
        (shutdown_cfs) is executed, it calls RemoteCfsController instance's shutdown_cfs function.
        """
        log.info("Shutting down CFS on {}".format(self.config.name))

        if self.cfs:
            self.cfs.stop_cfs()

        kill_string = "kill -9 $(pidof {})".format(self.config.cfs_exe)
        try:
            result = self.execution.run_command(kill_string)
        except Exception as exception:
            log.error("Failed to kill process {}: {}".format(self.config.cfs_exe, exception))
            self.cfs_process_list = []
            self.cfs_running = False
            raise CtfTestError('Error in shutdown_cfs') from exception

        self.cfs_process_list = []
        self.cfs_running = False
        return result

    def shutdown(self):
        """
        This function will shut down the CFS application being tested even if the JSON test file does not
        include the shutdown test command
        """
        log.info("Shutting down controller for {}".format(self.config.name))
        if self.cfs:
            if self.cfs_running:
                try:
                    self.shutdown_cfs()
                except CtfTestError:
                    log.info("Error: Shutting down controller for {}".format(self.config.name))

            # Wait 2 time units for shutdown to complete
            Global.time_manager.wait_seconds(2)

            stdout_final_path = os.path.join(Global.current_script_log_dir, os.path.basename(self.cfs.cfs_std_out_path))
            if not os.path.exists(stdout_final_path):
                if not self.execution.get_file(self.cfs.cfs_std_out_path, stdout_final_path, {'delete': True}):
                    log.info("Cannot move CFS stdout file to script log directory.")
                else:
                    log.info("Successfully copied CFS stdout file from remote SSH Target. Removing remote file")
                    self.execution.run_command("rm {}".format(self.cfs.cfs_std_out_path))

            self.cfs = None


if SP0CfsInterface:
    class SP0CfsController(CfsController):
        """
        SP0CfsController class Definition: CFS Controller Implementation for SP0CfsController.

        @note SP0CfsController class is inherited from CfsController class. It only redefines a few functions,
              including __init__, initialize, archive_cfs_files, shutdown_cfs, shutdown.
        @note SP0CfsController is initiated when INI config file uses 'sp0' protocol.
        """

        def __init__(self, config):
            """
            Constructor implementation for SP0CfsController class.
            """
            super().__init__(config)
            self.sp0_plugin = None

        def initialize(self):
            """
            Initialize CfsController instance, including the followings: create mid map; import ccsds header;
            create sp0 CFS command interface; create telemetry interface;
            """
            log.debug("Initializing SP0CfsController")
            self.process_ccsds_files()

            try:
                ccsds = import_ccsds_header_types()
            except CtfTestError:
                ccsds = None
                log.warning("Error: import_ccsds_header_types ")

            if not (ccsds and ccsds.CcsdsPrimaryHeader and ccsds.CcsdsCommand and ccsds.CcsdsTelemetry):
                log.error("Unable to import required CCSDS header types")
                return False

            log.info("Starting SP0 CFS Interface to {}:{}".format(self.config.cfs_target_ip, self.config.cmd_udp_port))
            result = self.sp0_plugin = Global.plugin_manager.find_plugin_for_command("SP0_Register")
            if not result:
                log.error("Failed to connect to SP0 plugin.")
            else:
                result = self.sp0_plugin.sp0_register_from_config(self.config.name, self.config)
                if not result:
                    log.error("Failed SP0 Configuration.")
                else:
                    command = CommandInterface(ccsds, self.config.cmd_udp_port, self.config.cfs_target_ip)
                    telemetry = TlmListener(self.config.ctf_ip, self.config.tlm_udp_port)
                    self.cfs = SP0CfsInterface(self.config, telemetry, command, self.mid_map, ccsds, self.sp0_plugin)
                    result = self.cfs.init_passed
                    if not result:
                        log.error("Failed to initialize SP0CfsInterface")
                    else:
                        log.warning("Not starting CFS executable... Expecting \"StartCfs\" in test script...")

            if result:
                log.info("SP0CfsController Initialized")
            return result

        # ENHANCE - need a mechanism to find only files that have been modified since test start
        def archive_cfs_files(self, source_path):
            """
            Implementation of CFS plugin instructions archive_cfs_files. When CFS plugin instructions
            (archive_cfs_files) is executed, it calls SP0CfsController instance's archive_cfs_files function.
            """
            artifacts_path = os.path.join(Global.current_script_log_dir, "artifacts")

            if not os.path.exists(artifacts_path):
                os.makedirs(artifacts_path)

            return self.sp0_plugin.get_files(source_path, artifacts_path, self.config.name)

        def shutdown_cfs(self):
            """
            Implementation of CFS plugin instructions shutdown_cfs. When CFS plugin instructions
            (shutdown_cfs) is executed, it calls SP0CfsController instance's shutdown_cfs function.
            """
            log.info("Shutting down CFS on {}".format(self.config.name))

            # ENHANCE - Pull CFS stdout from SP0. Requires run_application to pipe output of process...
            # stdout_final_path = os.path.join(Global.current_script_log_dir,
            #                                  os.path.basename(self.cfs.cfs_std_out_path))
            #
            # if not os.path.exists(stdout_final_path):
            #     if not self.sp0_plugin.get_file(self.cfs.cfs_std_out_path, stdout_final_path):
            #         log.info("Cannot move CFS stdout file to script log directory.")
            #         if self.sp0_plugin.last_result[self.config.name]:
            #             log.debug(self.sp0_plugin.last_result[self.config.name].stdout.strip())

            if self.cfs and self.cfs_running:
                if self.config.stop_command:
                    log.info("Sending Stop Command '{}'...".format(self.config.stop_command))
                    self.sp0_plugin.send_command(self.config.stop_command + "\n", timeout=2, name=self.config.name)
                self.cfs.stop_cfs()
                self.cfs_running = False

                # Wait 2 time units for shutdown to complete
                Global.time_manager.wait_seconds(2)

        def shutdown(self):
            """
            This function will shut down the CFS application being tested even if the JSON test file does not
            include the shutdown test command
            """
            log.info("Shutting down controller for {}".format(self.config.name))
            if self.cfs:
                if self.cfs_running:
                    self.shutdown_cfs()
                self.cfs = None
