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
cfs_plugin.py: CFS Plugin Implementation for CTF.

- Defines the CFS Plugin command map with the CTF instructions for cFS.
- When enabled, this plugin will override the default CTF time manager,
  and utilizes the CfsTimeManager.
- Implements the Register, Build, Start, and Shutdown cFS functionality
  for multiple cFS targets. Implements Send Command, Check Tlm
  (once or continuous) functionality.
"""

# ENHANCE - Potentially support multiple names for the cfs instructions.
#               Currently it is either a single target, or all

import json
from copy import deepcopy

from lib.ctf_global import Global, CtfVerificationStage
from lib.ctf_utility import resolve_variable
from lib.exceptions import CtfTestError
from lib.logger import logger as log
from lib.plugin_manager import Plugin, ArgTypes
from plugins.cfs.cfs_config import CfsConfig, RemoteCfsConfig
from plugins.cfs.cfs_time_manager import CfsTimeManager
from plugins.cfs.pycfs.cfs_controllers import CfsController, RemoteCfsController


def _resolve_tlm_args_values(event_args):
    # args will be modified during parameter evaluation, keep the original args for re-evaluation during loop
    copied_args = deepcopy(event_args)

    if isinstance(copied_args, dict):
        for key, value in copied_args.items():
            copied_args[key] = resolve_variable(value)
    elif isinstance(copied_args, list):
        for arg in copied_args:
            for key, value in arg.items():
                # corner case : arg['value'] is a single element list
                if isinstance(value, list) and len(value) == 1:
                    arg[key] = value[0]
                arg[key] = resolve_variable(arg[key])

    return copied_args


class CfsPlugin(Plugin):
    """
    The CFS Plugin provides CFS command/telemetry support for CTF.

     @note The CFS plugin draws many default values from the CTF config file.
            The section [cfs] defines defaults for all CFS targets and is always required.

     @note If multiple CFS targets are to be registered, for each target name,
            the plugin will load values from a correspondingly named section.

     @note If no targets are explicitly registered by name by the time StartCfs is first executed,
           the plugin will automatically configure targets for each config section beginning with cfs_.
           If no such sections are found, the plugin will configure a single target using the [cfs] config section.
           If the cfs_protocol field is not found in the cfs section, a local target will be registered.

     @note The precedence of values is first the named config section, if any, and then the [cfs] config section.
           A target cannot be registered, explicitly nor automatically, without a correspondingly named config section.
    """
    FALLBACK_TARGET_NAME = 'cfs'

    def __init__(self):
        """Constructor for CfsPlugin.
        Most importantly populates the command map and verify required commands,
        which serve as the interface to the plugin manager.
        """
        super().__init__()
        self.name = "CFS Plugin"
        self.description = "Provide CFS command/telemetry support for CTF"
        self.targets = {}
        self.has_attempted_register = False

        self.protocols = {
            "local": (CfsConfig, CfsController),
            "ssh": (RemoteCfsConfig, RemoteCfsController)
        }

        # ENHANCE - instruction parameters are duplicated here and in function signatures
        # See the CFS Plugin README for full documentation of the test instructions
        self.command_map = {
            # RegisterCfs: Declares a CFS target to be loaded according to the config file section of the same name
            # - target: (string) A unique name to identify the target in later instructions
            "RegisterCfs":
                (self.register_cfs, [ArgTypes.string]),
            # BuildCfs: Builds a CFS target
            # - target: (Optional) A previously registered target name, or empty for all registered targets
            "BuildCfs":
                (self.build_cfs, [ArgTypes.string]),
            # StartCfs: Starts a CFS target
            # - target: (Optional) A previously registered target name, or empty for all registered targets
            "StartCfs":
                (self.start_cfs, [ArgTypes.string, ArgTypes.string]),
            # EnableCfsOutput: Enables CFS output
            # - target: (Optional) A previously registered target name, or empty for all registered targets
            "EnableCfsOutput":
                (self.enable_cfs_output, [ArgTypes.string]),
            # SendCfsCommand: Sends a CFS command
            # - mid: The message ID of the command
            # - cc: The command code for the command
            # - args: Either an array or dictionary object containing the command arguments
            # - target: (Optional) A previously registered target name, or empty for all registered targets
            # - header: (Optional) An object where the key is the header field name, and the value is the field value.
            "SendCfsCommand":
                (self.send_cfs_command,
                 [ArgTypes.cmd_mid, ArgTypes.cmd_code, ArgTypes.cmd_arg, ArgTypes.string, ArgTypes.string]),
            # SendCfsCommandWithPayloadLength: Sends a CFS command with a user-specified payload length
            # - mid: The message ID of the command
            # - cc: The command code for the command
            # - args: Either an array or dictionary object containing the command arguments
            # - target: (Optional) A previously registered target name, or empty for all registered targets
            # - header: (Optional) An object where the key is the header field name, and the value is the field value.
            # - payload_length: The length in bytes of the command payload to send (truncated or padded as needed)
            "SendCfsCommandWithPayloadLength":
                (self.send_cfs_command,
                 [ArgTypes.cmd_mid, ArgTypes.cmd_code, ArgTypes.cmd_arg,
                  ArgTypes.string, ArgTypes.string, ArgTypes.number]),
            # SendCfsCommandWithRawPayload: Sends a CFS command truncated to the size of a single hexadecimal value
            # - mid: The message ID of the command
            # - cc: The command code for the command
            # - hex_buffer: A string of hexadecimal characters representing the raw byte value of the command payload
            # - target: (Optional) A previously registered target name, or empty for all registered targets
            # - header: (Optional) An object where the key is the header field name, and the value is the field value.
            "SendCfsCommandWithRawPayload":
                (self.send_raw_cfs_command,
                 [ArgTypes.cmd_mid, ArgTypes.cmd_code, ArgTypes.string, ArgTypes.string, ArgTypes.string]),
            # CheckTlmValue: Checks that a telemetry message matching the given parameters has been received
            # - mid: The telemetry message ID to check
            # - args: an array of argument objects that describe the values to be checked
            # - target: (Optional) A previously registered target name, or empty for all registered targets
            "CheckTlmValue":
                (self.check_tlm_value, [ArgTypes.tlm_mid, ArgTypes.comparison, ArgTypes.string]),
            # CheckTlmPacket: Checks that a telemetry message has been received
            # - mid: The telemetry message ID to check
            # - target: (Optional) A previously registered target name, or empty for all registered targets
            "CheckTlmPacket":
                (self.check_tlm_packet, [ArgTypes.tlm_mid, ArgTypes.string]),
            # CheckTlmValue: Checks that a telemetry message has not been received
            # - mid: The telemetry message ID to check
            # - target: (Optional) A previously registered target name, or empty for all registered targets
            "CheckNoTlmPacket":
                (self.check_no_tlm_packet, [ArgTypes.tlm_mid, ArgTypes.string]),
            # CheckTlmContinuous: Similar to CheckTlmValue except the check is performed
            # each time telemetry is received, until the test ends or the check is removed by 'RemoveCheckTlmContinuous'
            # - verification_id: A unique string to identify this check within the test
            # - mid: The telemetry message ID to check
            # - args: an array of argument objects that describe the values to be checked
            # - target: (Optional) A previously registered target name, or empty for all registered targets
            "CheckTlmContinuous":
                (self.check_tlm_continuous, [ArgTypes.string, ArgTypes.tlm_mid, ArgTypes.comparison, ArgTypes.string]),
            # RemoveCheckTlmContinuous
            # - verification_id: The ID of a check previously added by 'CheckTlmContinuous'
            # - target: (Optional) A previously registered target name, or empty for all registered targets
            "RemoveCheckTlmContinuous":
                (self.remove_check_tlm_continuous, [ArgTypes.string, ArgTypes.string]),
            # CheckEvent: Checks that an event message matching the given parameters has been received
            # - args: an array of argument objects that describe the events to be checked
            #   - app: The app that sent the event message
            #   - id: The Event ID, taken from an EVS enum, to represent the criticality level of a message
            #   - msg: The expected message of the event
            #   - is_regex: (Optional) True if msg is to be used for a regex match instead of string comparison
            #   - msg_args: (Optional) Arguments that will be inserted into msg, similar to printf() functions
            # - target: (Optional) A previously registered target name, or empty for all registered targets
            "CheckEvent":
                (self.check_event,
                 [ArgTypes.event, ArgTypes.string]),
            # CheckNoEvent: Checks that an event message matching the given parameters is not received
            # user needs to ensure the previous messages are cleared from buffer before calling CheckNoEvent instruction
            # - args: an array of argument objects that describe the events to be checked
            #   - app: The app that sent the event message
            #   - id: The Event ID, taken from an EVS enum, to represent the criticality level of a message
            #   - msg: The expected message of the event
            #   - is_regex: (Optional) True if msg is to be used for a regex match instead of string comparison
            #   - msg_args: (Optional) Arguments that will be inserted into msg, similar to printf() functions
            # - target: (Optional) A previously registered target name, or empty for all registered targets
            "CheckNoEvent":
                (self.check_noevent,
                 [ArgTypes.event, ArgTypes.string]),

            # ArchiveCfsFiles: Copies files from a directory that have been modified
            # during the current test run into the test run's log directory
            # - source_path: A directory path from which to copy files
            # - target: (Optional) A previously registered target name, or empty for all registered targets
            "ArchiveCfsFiles":
                (self.archive_cfs_files, [ArgTypes.string, ArgTypes.string]),
            # ShutdownCfs: Shuts down a CFS target
            # - target: (Optional) A previously registered target name, or empty for all registered targets
            "ShutdownCfs":
                (self.shutdown_cfs, [ArgTypes.string]),
        }

        self.verify_required_commands = ["CheckTlmValue",
                                         "CheckTlmPacket",
                                         "CheckNoTlmPacket",
                                         "CheckEvent",
                                         "CheckNoEvent"]
        # ENHANCE - Utilize the commands below in the time manager, so that continuous instructions can be
        #              implemented here, and utilized by the time manager.
        self.continuous_commands = ["CheckTlmContinuous"]

        self.end_test_on_fail_commands = ["RegisterCfs", "StartCfs"]

    def initialize(self) -> bool:
        """Initializes the plugin by creating the CfsTimeManager.
        This method is intended to be called by the plugin manager before the test script runs.
        """
        # ENHANCE - May want to have a single CTF time manager, that allows adding and removal
        #              of pre/post-command callbacks.
        #              When re-adding Trick CFS, the Trick cfs_time_manager should be the only time manager
        #              used. There is a potential that the cfs_time_manager is used instead. Need to figure out
        #              how to select a time manager.

        Global.set_time_manager(CfsTimeManager(self.targets))
        log.info("Initialized CfsPlugin")
        return True

    def register_cfs(self, target: str) -> bool:
        """Implements the RegisterCfs instruction.
        The value of 'target' must match a section in the config file from which this target will be configured.
        The value of 'cfs_protocol' in this section determines the type of config and controller objects to be
        constructed, except in the case of 'cfs' which is reserved for automatic configuration when no targets
        are explicitly configured."""
        log.info("RegisterCfs for target: {}".format(target))
        self.has_attempted_register = True

        if '$' in target:
            target = resolve_variable(target)

        if target == "":
            return self.load_configured_targets(target)

        # ENHANCE - Allow clean disconnect and reinit of registered targets consistent with SP0 behavior
        if target in self.targets:
            log.error("CFS target {} is already registered".format(target))
            return False

        if target == self.FALLBACK_TARGET_NAME:
            cfs_protocol = Global.config.get(target, "cfs_protocol", fallback="local")
        elif target not in Global.config.sections():
            log.error("No CFS configuration defined in config file for {}.".format(target))
            return False
        else:
            cfs_protocol = Global.config.get(target, "cfs_protocol", fallback=None)

        if not cfs_protocol or cfs_protocol.lower() not in self.protocols:
            log.error("Missing or invalid protocol for CFS target {}".format(target))
            return False

        log.debug("Registering target {} with {} protocol".format(target, cfs_protocol))
        config_type, controller_type = self.protocols[cfs_protocol.lower()]
        config = config_type(target)

        if config.get_error_count() > 0:
            status = False
        else:
            controller = controller_type(config)
            status = controller.initialize()
            if status:
                self.targets[target] = controller
            else:
                log.error("Register for {} failed.".format(target))

        log.info("Register for {} finished with status {}.".format(target, status))
        return status

    def load_configured_targets(self, target: str = None) -> bool:
        """Configures targetS based on the config file. Any section starting with 'cfs_' will be interpreted
        as a target configuration. If no such sections are found, a single target named 'cfs' will be configured
        as a local target using the values of the [cfs] section."""
        log.debug("CfsPlugin.load_configured_targets")

        target_instances = [target] if target else \
            [section for section in Global.config.sections() if section.startswith("cfs_")]

        if not target_instances:
            log.info("No CFS targets found in config file. Registering default local target.")
            return self.register_cfs(self.FALLBACK_TARGET_NAME)

        log.debug("Found {} CFS targets in config file. Registering...".format(len(target_instances)))
        return all(self.register_cfs(target_instance) for target_instance in target_instances)

    def get_cfs_targets(self, target: str = None) -> list:
        """Helper method to get a list of targets, containing the
        named target or all registered targets if no target is provided."""

        targets = []
        if target:
            if target in self.targets:
                targets = [self.targets[target]]
            else:
                log.error("CFS target {} not found.".format(target))
        else:
            if len(self.targets) > 0:
                targets = list(self.targets.values())
            else:
                log.error("No Cfs target Registered")

        return targets

    def build_cfs(self, target: str = None) -> bool:
        """Implements the instruction BuildCfs.
        If RegisterCfs has not yet been used, the plugin will first
        attempt to register any targets defined in the config file.
        """
        log.info("BuildCfs for Target: {}".format(target))

        target = resolve_variable(target)

        if not self.has_attempted_register:
            if not self.load_configured_targets(target):
                log.error("Failed to configure CFS target(s) {} from config file.".format(target))
                return False

        # Collect the results of build_cfs on each specified target, and check that all passed
        status = [t.build_cfs() for t in self.get_cfs_targets(target)]
        return all(status) if status else False

    def start_cfs(self, target: str = None, run_args: str = "") -> bool:
        """Implements the instruction StartCfs.
        If RegisterCfs has not yet been used, the plugin will first
        attempt to register any targets defined in the config file.
        """
        log.info("StartCfs for target: {}".format(target))
        target = resolve_variable(target)

        if not self.has_attempted_register:
            if not self.load_configured_targets(target):
                log.error("Failed to configure CFS target(s) {} from config file.".format(target))
                return False

        # Collect the results of start_cfs on each specified target, and check that all passed
        status = [t.start_cfs(run_args) for t in self.get_cfs_targets(target)]
        return all(status) if status else False

    def enable_cfs_output(self, target: str = None) -> bool:
        """Implements the instruction EnableCfsOutput."""
        log.info("EnableCfsOutput for target: {}".format(target))
        target = resolve_variable(target)

        # Collect the results of enable_cfs_output on each specified target, and check that all passed
        status = [t.enable_cfs_output() for t in self.get_cfs_targets(target)]
        return all(status) if status else False

    def send_cfs_command(self, mid: str, cc: int, args: any, target: str = None, header: dict = None,
                         payload_length: int = None, ctype_args: bool = False) -> bool:
        """Implements the instruction SendCfsCommand
        ctype_args is a flag to zero out the message structure for internal validation,
        and is not intended to be used by test instructions."""
        # pylint: disable=invalid-name
        if not ctype_args:
            log.debug("SendCfsCommand - Target: {}, MID: {}, CC: {}, Args: {}, Set Length: {}, CType Args: {}"
                      .format(target, mid, cc, json.dumps(args), payload_length, ctype_args))

        target = resolve_variable(target)
        copied_args = deepcopy(args)

        def _resolve_cfs_args_value(cmd_args):
            # corner case: empty list, dic, str ...
            # ValidateCfsCcsdsData instruction constructs arguments by code, args generated by it is not dict type
            if not cmd_args or not isinstance(cmd_args, dict):
                return

            for key, value in cmd_args.items():
                if isinstance(value, list):
                    for sub_arg in value:
                        _resolve_cfs_args_value(sub_arg)
                elif isinstance(value, dict):
                    _resolve_cfs_args_value(value)
                else:
                    cmd_args[key] = resolve_variable(value)

        _resolve_cfs_args_value(copied_args)

        # Collect the results of send_cfs_command on each specified target, and check that all passed
        # Make a copy of arguments since send_cfs_command may change arguments structure
        status = [t.send_cfs_command(mid, cc, deepcopy(copied_args), header, payload_length, ctype_args)
                  for t in self.get_cfs_targets(target)]

        return all(status) if status else False

    def send_raw_cfs_command(self, mid: str, cc: int, hex_buffer: str, target: str = None, header: dict = None) -> bool:
        """Implements the instruction SendCfsCommandWithRawPayload."""
        # pylint: disable=invalid-name
        target = resolve_variable(target)
        status = [t.send_raw_cfs_command(mid, cc, hex_buffer, header) for t in self.get_cfs_targets(target)]

        return all(status) if status else False

    def check_tlm_value(self, mid: str, args: list, target: str = None) -> bool:
        """Implements the instruction CheckTlmValue."""
        if Global.current_verification_stage == CtfVerificationStage.first_ver:
            log.info("CheckTlmValue: CFS Target: {}, MID {}, Args {}".format(target, mid, json.dumps(args)))

        target = resolve_variable(target)
        # Collect the results of check_tlm_value on each specified target, and check that all passed
        copied_args = _resolve_tlm_args_values(args)
        status = [t.check_tlm_value(mid, copied_args) for t in self.get_cfs_targets(target)]

        return all(status) if status else False

    def check_tlm_packet(self, mid: str, target: str = None) -> bool:
        """Implements the instruction CheckTlmPacket."""
        if Global.current_verification_stage == CtfVerificationStage.first_ver:
            log.info("CheckTlmPacket: CFS Target: {}, MID {}".format(target, mid))

        target = resolve_variable(target)
        # Collect the results of check_tlm_value on each specified target, and check that all passed
        status = [t.check_tlm_value(mid) for t in self.get_cfs_targets(target)]
        return all(status) if status else False

    def check_no_tlm_packet(self, mid: str, target: str = None) -> bool:
        """Implements the instruction CheckNoTlmPacket."""
        if Global.current_verification_stage == CtfVerificationStage.first_ver:
            log.info("CheckNoTlmPacket: CFS Target: {}, MID {}".format(target, mid))

        target = resolve_variable(target)
        # Collect the results of check_tlm_value on each specified target, and check that all did not pass
        status = [t.check_tlm_value(mid) for t in self.get_cfs_targets(target)]
        result = False
        if any(status):
            log.info("CheckNoTlmPacket found a packet with MID {}".format(mid))
            result = False
        else:
            # Check_noevent is to verify No event happens during the CtfVerificationStage.
            # This function will be called a few times by test.py, it only returns True at the end of verification stage
            if Global.current_verification_stage == CtfVerificationStage.last_ver:
                log.info("CheckNoTlmPacket found no packet")
                result = True

        return result

    def get_tlm_value(self, mid: str, tlm_variable: str, is_header: bool = False, target: str = None):
        """Get the latest telemetry value with matching mid and named parameter"""
        tlm_value = None
        log.debug("get_tlm_value for target: {},  mid: {}, tlm_variable: {}, is_header : {}"
                  .format(target, mid, tlm_variable, is_header))
        # Get the latest telemetry value from cfs target
        cfs_target = self.get_cfs_targets(target)
        if cfs_target:
            tlm_value = cfs_target[0].get_tlm_value(mid, tlm_variable, is_header)
        log.debug("get_tlm_value's return tlm_value: {} ({})".format(tlm_value, type(tlm_value).__name__))
        return tlm_value

    def check_tlm_continuous(self, verification_id: str, mid: str, args: dict, target: str = None) -> bool:
        """Implements the instruction CheckTlmContinuous."""
        log.info("CheckTlmContinuous for target: {}, Verification ID: {}, MID: {}, Args: {}"
                 .format(target, verification_id, mid, json.dumps(args)))

        target = resolve_variable(target)
        # args will be modified during parameter evaluation, keep the original args for re-evaluation during loop
        copied_args = deepcopy(args)

        for arg in copied_args:
            if 'value' in arg:
                arg['value'] = resolve_variable(arg['value'])

        # Collect the results of check_tlm_continuous on each specified target, and check that all passed
        status = [t.check_tlm_continuous(verification_id, mid, copied_args) for t in self.get_cfs_targets(target)]
        return all(status) if status else False

    def remove_check_tlm_continuous(self, verification_id: str, target: str = None) -> bool:
        """Implements the instruction RemoveCheckTlmContinuous."""
        log.info("RemoveCheckTlmContinuous for target: {}, Verification ID: {}".format(target, verification_id))

        target = resolve_variable(target)
        # Collect the results of remove_check_tlm_continuous on each specified target, and check that all passed
        status = [t.remove_check_tlm_continuous(verification_id) for t in self.get_cfs_targets(target)]
        return all(status) if status else False

    def check_event(self, args: list, target: str = None) -> bool:
        """Implements the instruction CheckEvent.
        'id' shadows the built-in function target but is kept because it exists in legacy test scripts."""
        log.info("CheckEvent: CFS Target {}, Args {}"
                 .format(target, json.dumps(args)))

        target = resolve_variable(target)
        # Collect the results of check_event on each specified target, and check that all passed
        copied_args = _resolve_tlm_args_values(args)
        status = [t.check_event(**event) for event in copied_args for t in self.get_cfs_targets(target)]
        return all(status) if status else False

    def check_noevent(self, args: list, target: str = None) -> bool:
        """Implements the instruction CheckNoEvent.
        'id' shadows the built-in function target but is kept because it exists in legacy test scripts."""
        log.info("CheckNoEvent: CFS Target {}, Args {}"
                 .format(target, json.dumps(args)))

        target = resolve_variable(target)
        # Collect the results of check_event on each specified target, and check that all passed
        copied_args = _resolve_tlm_args_values(args)
        status = [t.check_event(**event) for event in copied_args for t in self.get_cfs_targets(target)]
        result = False
        if any(status):
            log.info("CheckNoEvent found the event!")
        else:
            # Check_noevent is to verify No event happens during the CtfVerificationStage.
            # This function will be called a few times by test.py, it only returns True at the end of verification stage
            if Global.current_verification_stage == CtfVerificationStage.last_ver:
                log.info("CheckNoEvent did not find the event")
                result = True

        return result

    def shutdown_cfs(self, target: str = None) -> bool:
        """Implements the instruction ShutdownCfs.
        This is non-destructive; the target still exists and can be restarted.
        Any running targets will be stopped automatically on plugin shutdown."""
        log.info("ShutdownCfs for target: {}".format(target))

        target = resolve_variable(target)
        # Collect the results of shutdown_cfs on each specified target, and check that all passed
        status = [t.shutdown_cfs() for t in self.get_cfs_targets(target)]
        return all(status) if status else False

    def archive_cfs_files(self, source_path: str, target: str = None) -> bool:
        """Implements the instruction ArchiveCfsFiles.
        Copies files from a source directory that have been modified
        during the test run into the test script's log directory"""
        log.info("ArchiveCfsFiles for target: {}, Source Path: {}".format(target, source_path))

        target = resolve_variable(target)
        # Collect the results of archive_cfs_files on each specified target, and check that all passed
        status = []
        for cfs_target in self.get_cfs_targets(target):
            try:
                status.append(cfs_target.archive_cfs_files(source_path))
            except CtfTestError:
                status.append(False)
                log.error("Error: ArchiveCfsFiles for target {}, Source Path: {}".format(cfs_target, source_path))

        return all(status) if status else False

    def shutdown(self) -> None:
        """Shuts down the plugin, releasing target resources.
        Only runs when the plugin itself is shutting down.
        To shut down individual targets, use shutdown_cfs.
        """
        log.debug("CfsPlugin.shutdown")
        for target in self.targets:
            log.debug("Shutting down CFS target: {}".format(target))
            self.targets[target].shutdown()

        # Controller resources are now freed, as they are all shut down and available for garbage collection
        self.targets.clear()
