"""
@namespace lib.Test
Represents a single CTF test within a script
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


import time

from lib.ctf_global import Global, CtfVerificationStage
from lib.event_types import Instruction
from lib.exceptions import CtfTestError, CtfConditionError
from lib.logger import logger as log
from lib.status import StatusDefs


class Test:
    """
    The Test class represents a CTF Test.
    @note - A test script may have multiple tests.
    """

    def __init__(self):
        """
        Constructor of Test Class: Initiate test properties
        """
        self.test_info = None
        self.instructions = []
        self.test_result = True
        self.test_aborted = False
        self.test_run = False
        self.num_skipped = 0
        self.num_ran = 0

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

        self.current_instruction_index = 0

    def execute_instruction(self, test_instruction, command_index):
        """
        Execute a CTF Test Instruction
        """
        # for command in commands:
        instruction = test_instruction["instruction"]
        data = test_instruction.get("data") or {}

        if instruction in self.verify_required_commands:
            log.error("Instruction {} must be handles by execute_verification")
            return False

        # execute command if not verification
        plugin_to_use = Global.plugin_manager.find_plugin_for_command(instruction)
        data_str = str(data).replace("\n", "\n" + " " * 20)
        if plugin_to_use is not None:
            try:
                instruction_passed = plugin_to_use.process_command(instruction=instruction, data=data)
            except CtfTestError:
                instruction_passed = False

            status = StatusDefs.passed if instruction_passed else StatusDefs.failed

            self.status_manager.update_command_status(status, "", index=command_index)
            self.status_manager.end_command()
            log.test(instruction_passed, False, "Instruction {}: {}".format(instruction, data_str))
            if instruction_passed is None:
                instruction_passed = False
            self.test_result &= instruction_passed

        else:
            status = StatusDefs.error
            details = "Unknown Command. No plugin to handle {}({})".format(instruction, data_str)
            self.status_manager.update_command_status(status, details, index=command_index)
            self.test_result = False
            self.status_manager.end_command()
            log.test(False, False, details)
            instruction_passed = False

        return instruction_passed

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
        Run all CTF Instructions in the current test
        """
        if len(self.instructions) == 0:
            log.error("Invalid Test: {}. Check that the script has been parsed correctly.."
                      .format(self.test_info.get("test_number", "")))
            self.test_result = False

        self.current_instruction_index = 0

        if self.current_instruction_index > len(self.instructions) - 1:
            log.error("No test instructions to execute.")
            return

        while True:
            i = self.instructions[self.current_instruction_index]
            # get command information
            delay = i.delay
            instruction = i.command["instruction"]
            instruction_result = False

            # Update current instruction index globally
            Global.current_instruction_index = self.current_instruction_index

            if i.is_disabled:
                status = StatusDefs.disabled
                details = "Instruction is disabled. Skipping..."
                self.status_manager.update_command_status(status, details, index=self.current_instruction_index)
                self.status_manager.end_command()
                log.info("Skipping disabled test instruction {} ".format(i.command))
                self.num_skipped += 1
                self.current_instruction_index += 1
                continue

            if instruction in self.ignored_instructions:
                log.info("Ignoring test instruction {} ".format(instruction))
                self.num_skipped += 1
                self.current_instruction_index += 1
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
                timeout = i.command.get("verify_timeout", self.ctf_verification_timeout)
                instruction_result = self.execute_verification(i.command,
                                                               i.command_index,
                                                               timeout,
                                                               reset_ver_start_time)
            # this handles continuously verified commands.
            else:
                instruction_result = self.execute_instruction(i.command, self.current_instruction_index)

            try:
                Global.time_manager.post_command()
            except CtfTestError as exception:
                self.test_result = False
                log.test(False, False, "CtfTestError: Condition not satisfied: {}".format(exception))

            if not instruction_result and (instruction in self.end_test_on_fail_commands or self.end_test_on_fail):
                log.error("Instruction: {} Failed. Aborting test...".format(instruction))
                if self.end_test_on_fail:
                    log.warning("Configuration field \"end_test_on_fail\" enabled. Ending testing.")
                log.error("Test: {} Failed.".format(self.test_info.get("test_number", "")))
                self.test_aborted = True
                break

            goto_instruction_index = Global.goto_instruction_index

            if goto_instruction_index:
                if goto_instruction_index < 0 or goto_instruction_index > len(self.instructions) - 1:
                    log.error("Invalid goto instruction index {}. Valid test instructions: [0, {}]".format(
                        goto_instruction_index, len(self.instructions) - 1
                    ))
                    log.error("Test: {} Failed.".format(self.test_info.get("test_number", "")))
                    self.test_aborted = True
                    break

                self.current_instruction_index = goto_instruction_index
                Global.goto_instruction_index = None
            else:
                self.current_instruction_index += 1

            if self.current_instruction_index > len(self.instructions) - 1:
                break

    @staticmethod
    def __check_label_def(name: str, instruction: Instruction, defined: bool, label_map: dict):
        """
        Helper method to check the label definition
        """
        if 'label' not in instruction.command['data'] or instruction.command['data']['label'] == '':
            log.error("{} instruction does not include 'label' {}".format(name, instruction.command))
            raise CtfTestError("Instruction does not include 'label'")
        label = instruction.command['data']['label']
        if not defined and label in label_map:
            log.error("The label '{}' has been already defined in current test script".format(label))
            raise CtfTestError("The label in instruction has been already defined in current test script")
        if defined and label not in label_map:
            log.error("The label '{}' in instruction is not defined by previous instructions".format(label))
            raise CtfTestError("The label in instruction is not defined")

    def process_conditional_branch_label(self):
        """
        Process conditional branch labels defined in test instructions 'IfCondition', 'ElseCondition', 'EndCondition'
        """
        Global.conditional_branch_map.clear()
        label_stack = []
        log.info("Process conditional branch labels defined in test instructions 'IfCondition', 'ElseCondition', "
                 "'EndCondition'")
        for event in self.instructions:
            log.info("Instruction defined in test scripts: {}".format(event.command))
            if event.command['instruction'] == 'IfCondition':
                self.__check_label_def('IfCondition', event, False, Global.conditional_branch_map)
                label = event.command['data']['label']
                Global.conditional_branch_map[label] = {"condition_eval": None, "end_condition_index": None,
                                                        "else_condition_index": None, }
                label_stack.append(label)

            if event.command['instruction'] == 'ElseCondition':
                self.__check_label_def('ElseCondition', event, True, Global.conditional_branch_map)
                label = event.command['data']['label']
                Global.conditional_branch_map[label]['else_condition_index'] = event.command_index

                if len(label_stack) == 0 or label_stack[-1] != label:
                    raise CtfTestError("The label matching fails for ElseCondition")

            if event.command['instruction'] == 'EndCondition':
                self.__check_label_def('EndCondition', event, True, Global.conditional_branch_map)
                label = event.command['data']['label']
                Global.conditional_branch_map[label]['end_condition_index'] = event.command_index

                if len(label_stack) > 0 and label_stack[-1] == label:
                    label_stack.pop()
                else:
                    expected_label = label_stack[-1] if len(label_stack) > 0 else ""
                    log.error("The label matching fails, the actual label: '{}'  "
                              "the expected label: '{}' ".format(label, expected_label))
                    raise CtfTestError("The label matching fails")

        if len(label_stack) != 0:
            log.error("IfCondition & EndCondition not in pairs")
            raise CtfTestError("IfCondition & EndCondition not in pairs")

    def process_control_flow_label(self):
        """
        Process control flow labels defined in test instructions 'BeginLoop' and 'EndLoop'
        """
        Global.label_map.clear()
        Global.goto_label_map.clear()
        label_stack = []
        log.info("Process control flow labels defined in test instructions 'BeginLoop' and 'EndLoop'")

        for event in self.instructions:
            log.info("Instruction defined in test scripts: {}".format(event.command))

            if event.command['instruction'] == 'SetLabel':
                if 'label' not in event.command['data'] or event.command['data']['label'] == '':
                    log.error("SetLabel instruction does not include 'label' {}".format(event.command))
                    raise CtfTestError("SetLabel instruction does not include 'label'")
                label = event.command['data']['label']
                if label in Global.goto_label_map:
                    log.error("The label '{}' has been already defined in current test script".format(label))
                    raise CtfTestError("The label in instruction has been already defined in current test script")

                Global.goto_label_map[label] = event.command_index

            if event.command['instruction'] == 'BeginLoop':
                self.__check_label_def('BeginLoop', event, False, Global.label_map)
                label = event.command['data']['label']
                Global.label_map[label] = {"condition_eval": None, "beginloop_index": event.command_index,
                                                        "endloop_index": None }
                label_stack.append(label)

            if event.command['instruction'] == 'EndLoop':
                self.__check_label_def('EndLoop', event, True, Global.label_map)
                label = event.command['data']['label']
                Global.label_map[label]['endloop_index'] = event.command_index
                if len(label_stack) > 0 and label_stack[-1] == label:
                    label_stack.pop()
                else:
                    expected_label = label_stack[-1] if len(label_stack) > 0 else ""
                    log.error("The label matching fails, the actual label: {}  "
                              "the expected label: {} ".format(label, expected_label))
                    raise CtfTestError("The label matching fails")

        if len(label_stack) != 0:
            log.error("BeginLoop & EndLoop not in pairs")
            raise CtfTestError("BeginLoop & EndLoop not in pairs")

        for label in Global.goto_label_map:
            log.info("Found goto labels in current test script '{}' : {}".format(label, Global.goto_label_map[label]))

        for label in Global.label_map:
            log.info("Found control-flow labels in current "
                     "test script '{}' : {}".format(label, Global.label_map[label]))

    def run_test(self, status_manager):
        """
        Run all CTF Instructions within a test
        """
        self.status_manager = status_manager
        test_status = StatusDefs.active
        self.status_manager.update_test_status(test_status, "")

        log.info("---------- TEST START ----------")
        log.info("Test {}: Starting".format(self.test_info.get("test_number", "")))
        log.info(self.test_info.get("description", ""))
        self.test_start_time = time.time()

        try:
            self.process_control_flow_label()
            self.process_conditional_branch_label()
            self.run_commands()
            if self.test_result:
                test_status = StatusDefs.passed
                self.status_manager.update_test_status(test_status, "")
            else:
                test_status = StatusDefs.failed
                self.status_manager.update_test_status(test_status, "")
            if self.test_aborted:
                test_status = StatusDefs.aborted
                self.status_manager.update_test_status(test_status, "")

        except Exception as exception:
            self.test_result = False
            test_status = StatusDefs.error
            self.status_manager.update_test_status(test_status, str(exception))
            raise CtfTestError("Error in run_test") from exception

        log.info("Test {}: {}".format(self.test_info.get("test_number"), test_status))
        log.info("Number of instructions To Run:         {}".format(len(self.instructions)))
        log.info("Number of instructions Ran:            {}".format(self.num_ran))
        log.info("Number of instructions Skipped:        {}".format(self.num_skipped))
        self.status_manager.end_test()
        log.info("---------- TEST END ----------")
        return test_status
