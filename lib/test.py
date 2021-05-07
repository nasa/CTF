"""
@namespace lib.Test
Represents a single CTF test case
"""

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


import sched
import time

from lib.ctf_global import Global, CtfVerificationStage
from lib.exceptions import CtfTestError, CtfConditionError
from lib.logger import logger as log
from lib.status import StatusDefs


class Test:
    """
    The TestCase class represents a CTF Test Case.
    @note - A test script may have multiple test cases.
    """
    def __init__(self):
        # Test properties
        self.test_info = None
        self.event_list = []
        self.test_result = True
        self.test_aborted = False
        self.test_run = False
        self.num_skipped = 0
        self.num_ran = 0

        # Scheduler for test events
        self.event_schedule = sched.scheduler(time.time, time.sleep)

        # Test start time set when scheduler executes
        self.test_start_time = 0

        self.ctf_verification_timeout = Global.config.getfloat("core", "ctf_verification_timeout")
        self.ctf_verification_poll_period = Global.config.getfloat("core", "ctf_verification_poll_period")
        self.end_test_on_fail = Global.config.getboolean("core", "end_test_on_fail")

        self.ignored_instructions = []

        # to keep backcompatible: older config files may not include ignored_instructions
        temp_list = Global.config.get("core", "ignored_instructions", fallback=None)
        if temp_list is None:
            log.warning("Config file does not include ignored_instructions in section core !")
        else:
            temp_list = temp_list.split(',')
            self.ignored_instructions = [s.strip() for s in temp_list]

        self.verif_list = []

        # Get list of commands that require verification from plugins
        self.verify_required_commands = []
        self.continuous_verification_commands = []
        self.end_test_on_fail_commands = []
        for plugin in Global.plugin_manager.plugins.values():
            self.continuous_verification_commands += plugin.continuous_verification_commands
            self.verify_required_commands += plugin.verify_required_commands
            self.end_test_on_fail_commands += plugin.end_test_on_fail_commands

        self.status_manager = None

    def execute_event(self, test_instruction, command_index):
        """
        Execute a CTF Test Instruction
        """
        # for command in commands:
        instruction = test_instruction["instruction"]
        data = test_instruction.get("data") or {}
        # skip verification commands - handled by execute_verification
        if instruction in self.verify_required_commands:
            return

        # execute command if not verification
        plugin_to_use = Global.plugin_manager.find_plugin_for_command(instruction)
        data_str = str(data).replace("\n", "\n" + " " * 20)
        if plugin_to_use is not None:
            try:
                ret = plugin_to_use.process_command(instruction=instruction, data=data)
            except CtfTestError:
                ret = False

            status = None
            if ret:
                status = StatusDefs.passed
            else:
                status = StatusDefs.failed

            self.status_manager.update_command_status(status, "", index=command_index)
            self.status_manager.end_command()
            log.test(ret, False,
                     "Instruction {}: {}".format(instruction, data_str))
            if ret is None:
                ret = False
            self.test_result &= ret

        else:
            status = StatusDefs.error
            details = "Unknown Command. No plugin to handle {}({})".format(instruction, data_str)
            self.status_manager.update_command_status(status, details, index=command_index)
            self.test_result = False
            self.status_manager.end_command()
            log.test(False, False, details)

    def execute_verification(self, command, command_index, timeout, new_verification=False):
        """
        Execute a CTF Verification Instruction.
        @note - Verification instructions will be executed at the specified poll period until the verification passes
                or a timeout is reached
        """
        if new_verification or Global.current_verification_start_time is None:
            Global.current_verification_start_time = Global.time_manager.exec_time
            log.debug("Setting Verification Start Time = {}".format(Global.current_verification_start_time))

        instruction = command["instruction"]
        data = command["data"]

        log.info("Waiting up to {} time-units for verification of {}: {}".format(timeout, instruction, data))

        self.status_manager.update_command_status(StatusDefs.active, "Waiting for verification", index=command_index)
        num_verify = int(timeout / self.ctf_verification_poll_period) + 1
        verified = False
        for i in range(num_verify):
            plugin_to_use = Global.plugin_manager.find_plugin_for_command(instruction)
            if plugin_to_use is not None:
                if i == 0:
                    Global.current_verification_stage = CtfVerificationStage.first_ver
                elif i == num_verify - 1:
                    Global.current_verification_stage = CtfVerificationStage.last_ver
                else:
                    Global.current_verification_stage = CtfVerificationStage.polling

                try:
                    verified = plugin_to_use.process_command(instruction=instruction, data=data)
                except CtfTestError:
                    verified = False

                if verified is None:
                    verified = False
                    break
                if verified:
                    break
            try:
                self.process_verification_delay()
            except CtfConditionError as exception:
                self.test_result = False
                log.test(False, False, "CtfConditionError: Condition not satisfied: {}".format(exception))

        Global.current_verification_stage = CtfVerificationStage.none

        if not verified:
            self.status_manager.update_command_status(StatusDefs.failed, "", index=command_index)
            self.status_manager.end_command()
            log.test(verified, False,
                     "Verification Failed {}: {}".format(instruction, data))
            self.status_manager.update_command_status(StatusDefs.failed, "Timeout", index=command_index)
        else:
            self.status_manager.update_command_status(StatusDefs.passed, "Verified", index=command_index)
            self.status_manager.end_command()
            log.test(verified, False,
                     "Verification Passed {}: {}".format(instruction, data))

        self.test_result &= verified
        return verified

    @staticmethod
    def process_command_delay(delay):
        """
        Utilize the current CTF time manager to wait a specific amount of time before executing a CTF Test Instruction
        """
        Global.time_manager.wait(delay)

    def process_verification_delay(self):
        """
        Utilize the current CTF time manager to wait for the duration of the polling period before executing a CTF
        Verification Test Instruction
        """

        Global.time_manager.wait(self.ctf_verification_poll_period)

    def run_commands(self):
        """
        Run all CTF Instructions in the current test case
        """
        if len(self.event_list) == 0:
            log.error("Invalid Test Case: {}. Check that the script has been parsed correctly.."
                      .format(self.test_info.get("test_case", "")))
            self.test_result = False
        for i in self.event_list:
            # get command information
            delay = i.delay
            instruction_index = i.command_index
            instruction = i.command["instruction"]

            if i.is_disabled:
                status = StatusDefs.disabled
                details = "Instruction is disabled. Skipping..."
                self.status_manager.update_command_status(status, details, index=instruction_index)
                self.status_manager.end_command()
                log.info("Skipping disabled test instruction {} ".format(instruction))
                self.num_skipped += 1
                continue

            if instruction in self.ignored_instructions:
                log.info("Ignoring test instruction {} ".format(instruction))
                self.num_skipped += 1
                continue

            self.test_run = True
            self.num_ran += 1

            # process the command delay
            log.info("Waiting {} time-units before executing {}".format(delay, instruction))
            try:
                self.process_command_delay(delay)
                Global.time_manager.pre_command()

            except CtfConditionError as exception:
                self.test_result = False
                log.test(False, False, "CtfConditionError: Condition not satisfied: {}".format(exception))

            except CtfTestError as exception:
                log.error("Unknown Error Processing Command Delay & Pre-Command")
                log.debug(exception)

            # Only keep ver start time if next commands wait > 0
            reset_ver_start_time = True
            if i.delay == 0.0:
                reset_ver_start_time = False

            if instruction in self.verify_required_commands:
                timeout = i.command["timeout"] if "timeout" in i.command else self.ctf_verification_timeout
                self.execute_verification(i.command, i.command_index, timeout, reset_ver_start_time)
            elif instruction in self.continuous_verification_commands:
                # ENHANCE - In the future, may implement special logic for continuously verified commands.
                self.execute_event(i.command, instruction_index)
            else:
                self.execute_event(i.command, instruction_index)

            try:
                Global.time_manager.post_command()
            except CtfTestError as exception:
                self.test_result = False
                log.test(False, False, "CtfConditionError: Condition not satisfied: {}".format(exception))

            if (instruction in self.end_test_on_fail_commands or self.end_test_on_fail) and not self.test_result:
                # instruction is already executed in execute_event above
                # the test result is updated in self.test_result
                log.error("Instruction: {} Failed. Aborting test...".format(instruction))
                if self.end_test_on_fail:
                    log.warning("Configuration field \"end_test_on_fail\" enabled. Ending testing.")
                log.error("Test Case: {} Failed.".format(self.test_info.get("test_case", "")))
                self.test_aborted = True
                break

    def run_test(self, status_manager):
        """
        Run all CTF Instructions within a test case
        """
        self.status_manager = status_manager
        test_status = StatusDefs.active
        self.status_manager.update_test_status(test_status, "")
        # self.create_schedule()
        log.info("Test {}: Starting".format(self.test_info.get("test_case", "")))
        log.info(self.test_info.get("description", ""))
        self.test_start_time = time.time()
        try:
            # self.event_schedule.run(blocking=True)
            self.run_commands()
            if self.test_result:
                test_status = StatusDefs.passed
                self.status_manager.update_test_status(test_status, "")
            else:
                test_status = StatusDefs.failed
                self.status_manager.update_test_status(test_status, "")
            if self.test_aborted:
                test_status = StatusDefs.aborted

        except Exception as exception:
            self.test_result = False
            test_status = StatusDefs.error
            self.status_manager.update_test_status(test_status, str(exception))
            raise CtfTestError("Error in run_test") from exception

        log.info("Test {}: {}".format(self.test_info.get("test_case"), test_status))
        log.info("Number instructions To Run:         {}".format(len(self.event_list)))
        log.info("Number instructions Ran:            {}".format(self.num_ran))
        log.info("Number instructions Skipped:        {}".format(self.num_skipped))
        self.status_manager.end_test()
        return test_status
