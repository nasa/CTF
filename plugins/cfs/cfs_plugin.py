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
cfs_plugin.py: CFS Plugin Implementation for CTF.

- Defines the CFS Plugin command map with the CTF instructions for cFS.
- When enabled, this plugin will override the default CTF time manager,
  and utilizes the CfsTimeManager.
- Implements the Register, Build, Start, and Shutdown cFS functionality
  for multiple cFS targets. Implements Send Command, Check Tlm
  (once or continuous) functionality.
"""

# TODO - Potentially support multiple names for the cfs instructions.
#               Currently it is either a single target, or all

import json

from lib.Global import Global, Config, CtfVerificationStage
from lib.logger import logger as log
from lib.plugin_manager import Plugin, ArgTypes
from plugins.cfs.cfs_time_manager import CfsTimeManager
from plugins.cfs.pycfs.cfs_controllers import CfsController, RemoteCfsController
from plugins.cfs.cfs_config import CfsConfig, RemoteCfsConfig, SP0CfsConfig
try:
    from plugins.cfs.pycfs.cfs_controllers import SP0CfsController
except ImportError:
    SP0CfsController = None

from copy import deepcopy


class CfsPlugin(Plugin):

    FALLBACK_TARGET_NAME = 'cfs'
    protocols = {
        "local": (CfsConfig, CfsController),
        "ssh": (RemoteCfsConfig, RemoteCfsController)
    }
    if SP0CfsController:
        protocols["sp0"] = (SP0CfsConfig, SP0CfsController)

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

        # TODO - instruction parameters are duplicated here and in function signatures
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
            "SendCfsCommand":
                (self.send_cfs_command,
                 [ArgTypes.cmd_mid, ArgTypes.cmd_code, ArgTypes.cmd_arg, ArgTypes.string]),
            # SendCfsCommand: Sends a CFS command with an invalid length to induce an error
            # - mid: The message ID of the command
            # - cc: The command code for the command
            # - args: Either an array or dictionary object containing the command arguments
            # - payload_length: The length in bytes of the command message to send
            # - target: (Optional) A previously registered target name, or empty for all registered targets
            "SendInvalidLengthCfsCommand":
                (self.send_cfs_command,
                 [ArgTypes.cmd_mid, ArgTypes.cmd_code, ArgTypes.cmd_arg, ArgTypes.number, ArgTypes.string]),
            # CheckTlmValue: Checks that a telemetry message matching the given parameters has been received
            # - mid: The telemetry message ID to check
            # - args: an array of argument objects that describe the values to be checked
            # - target: (Optional) A previously registered target name, or empty for all registered targets
            "CheckTlmValue":
                (self.check_tlm_value, [ArgTypes.tlm_mid, ArgTypes.comparison, ArgTypes.string]),
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
            # - app: The app that sent the event message
            # - id: The Event ID, taken from an EVS enum, to represent the criticality level of a message
            # - msg: The expected message of the event
            # - is_regex: (Optional) True if msg is to be used for a regex match instead of string comparison
            # - msg_args: (Optional) Arguments that will be inserted into msg, similar to printf() functions
            # - target: (Optional) A previously registered target name, or empty for all registered targets
            "CheckEvent":
                (self.check_event,
                 [ArgTypes.string, ArgTypes.string, ArgTypes.string, ArgTypes.boolean, ArgTypes.cmd_arg, ArgTypes.string]),
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

        self.verify_required_commands = ["CheckTlmValue", "CheckEvent"]
        # TODO - Utilize the commands below in the time manager, so that continuous instructions can be
        #              implemented here, and utilized by the time manager.
        self.continuous_commands = ["CheckTlmContinuous"]

    def initialize(self) -> bool:
        """Initializes the plugin by creating the CfsTimeManager.
        This method is intended to be called by the plugin manager before the test script runs.
        """
        # TODO - May want to have a single CTF time manager, that allows adding and removal
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

        if target == "":
            return self.load_configured_targets(target)

        if target in self.targets:
            log.error("CFS target {} is already registered".format(target))
            return False

        if target == self.FALLBACK_TARGET_NAME:
            cfs_protocol = 'local'
        elif target not in Config.sections():
            log.error("No CFS configuration defined in config file for {}.".format(target))
            return False
        else:
            cfs_protocol = Config.get(target, "cfs_protocol", fallback=None)

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

        log.info("Register for {} finished.".format(target))
        return status

    def load_configured_targets(self, target: str = None) -> bool:
        """Configures targetS based on the config file. Any section starting with 'cfs_' will be interpreted
        as a target configuration. If no such sections are found, a single target named 'cfs' will be configured
        as a local target using the values of the [cfs] section."""
        log.debug("CfsPlugin.load_configured_targets")

        target_instances = [target] if target else [section for section in Config.sections() if section.startswith("cfs_")]

        if not len(target_instances):
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

        # Collect the results of enable_cfs_output on each specified target, and check that all passed
        status = [t.enable_cfs_output() for t in self.get_cfs_targets(target)]
        return all(status) if status else False

    def send_cfs_command(self, mid: str, cc: int, args: dict, target: str = None,
                         payload_length: int = None, ctype_args: bool = False) -> bool:
        """Implements the instruction SendCfsCommand
        ctype_args is a flag to zero out the message structure for internal validation,
        and is not intended to be used by test instructions."""
        if not ctype_args:
            log.debug("SendCfsCommand - Target: {}, MID: {}, CC: {}, Args: {}, Set Length: {}, CType Args: {}"
                      .format(target, mid, cc, json.dumps(args), payload_length, ctype_args))

        # Make a copy of arguments since send_cfs_command may change arguments structure
        args_copy = deepcopy(args)

        # Collect the results of send_cfs_command on each specified target, and check that all passed
        status = [t.send_cfs_command(mid, cc, args_copy, payload_length, ctype_args) for t in self.get_cfs_targets(target)]

        return all(status) if status else False

    def check_tlm_value(self, mid: str, args: dict, target: str = None) -> bool:
        """Implements the instruction CheckTlmValue."""
        if Global.current_verification_stage == CtfVerificationStage.first_ver:
            log.info("CheckTlmValue: CFS Target: {}, MID {}, Args {}".format(target, mid, json.dumps(args)))

        # Collect the results of check_tlm_value on each specified target, and check that all passed
        status = [t.check_tlm_value(mid, args) for t in self.get_cfs_targets(target)]
        return all(status) if status else False

    def check_tlm_continuous(self, verification_id: str, mid: str, args: dict, target: str = None) -> bool:
        """Implements the instruction CheckTlmContinuous."""
        log.info("CheckTlmContinuous for target: {}, Verification ID: {}, MID: {}, Args: {}"
                 .format(target, verification_id, mid, json.dumps(args)))

        # Collect the results of check_tlm_continuous on each specified target, and check that all passed
        status = [t.check_tlm_continuous(verification_id, mid, args) for t in self.get_cfs_targets(target)]
        return all(status) if status else False

    def remove_check_tlm_continuous(self, verification_id: str, target: str = None) -> bool:
        """Implements the instruction RemoveCheckTlmContinuous."""
        log.info("RemoveCheckTlmContinuous for target: {}, Verification ID: {}".format(target, verification_id))

        # Collect the results of remove_check_tlm_continuous on each specified target, and check that all passed
        status = [t.remove_check_tlm_continuous(verification_id) for t in self.get_cfs_targets(target)]
        return all(status) if status else False

    def check_event(self, app: str, id: str, msg: str, is_regex: bool = False,
                    msg_args: str = None, target: str = None) -> bool:
        """Implements the instruction CheckEvent.
        'id' shadows the built-in function target but is kept because it exists in legacy test scripts."""
        log.info("CheckEvent for target - {}, APP {}, ID {}, MSG {}, Msg Args {}"
                 .format(target, app, id, msg, json.dumps(msg_args)))

        # Collect the results of check_event on each specified target, and check that all passed
        status = [t.check_event(app, id, msg, is_regex, msg_args) for t in self.get_cfs_targets(target)]
        return all(status) if status else False

    def shutdown_cfs(self, target: str = None) -> bool:
        """Implements the instruction ShutdownCfs.
        This is non-destructive; the target still exists and can be restarted.
        Any running targets will be stopped automatically on plugin shutdown."""
        log.info("ShutdownCfs for target: {}".format(target))

        # Collect the results of shutdown_cfs on each specified target, and check that all passed
        status = [t.shutdown_cfs() for t in self.get_cfs_targets(target)]
        return all(status) if status else False

    def archive_cfs_files(self, source_path: str, target: str = None) -> bool:
        """Implements the instruction ArchiveCfsFiles.
        Copies files from a source directory that have been modified
        during the test run into the test script's log directory"""
        log.info("ArchiveCfsFiles for target: {}, Source Path: {}".format(target, source_path))

        # Collect the results of archive_cfs_files on each specified target, and check that all passed
        status = [t.archive_cfs_files(source_path) for t in self.get_cfs_targets(target)]
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
