"""
@namespace lib.test_test.py
Unit Test for Test class: Represents a single CTF test.
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

from math import isclose
import pytest
from unittest.mock import patch, Mock

from lib.ctf_global import Global
from lib.event_types import Instruction
from lib.exceptions import CtfTestError, CtfConditionError
from lib.readers.json_script_reader import JSONScriptReader
from lib.status import ObjectFactory
from lib.status_manager import StatusManager
from lib.test import Test


@pytest.fixture(name="test_instance")
def _test_instance():
    return Test()


@pytest.fixture(name="test_instance_inited")
def _test_instance_inited():
    Global.set_time_manager(Mock())
    test = Test()
    status_manager = StatusManager(port=None)
    script_reader = JSONScriptReader('functional_tests/cfe_6_7_tests/cfe_tests/CfeEsTest.json')
    script_reader.process_tests()
    script_list = [script_reader.script]
    status_manager.set_scripts(script_list)

    instructions = script_reader.script.tests[0].instructions
    test.instructions = instructions

    status_manager.start()
    test.status_manager = status_manager
    test.end_test_on_fail = False
    return test


def test_test_init(test_instance):
    """
    test Test class constructor
    """
    assert test_instance.test_info is None
    assert len(test_instance.instructions) == 0
    assert test_instance.test_result
    assert not test_instance.test_aborted
    assert not test_instance.test_run
    assert test_instance.num_skipped == 0
    assert test_instance.num_ran == 0
    assert test_instance.test_start_time == 0
    assert len(test_instance.ignored_instructions) == 1
    assert isclose(test_instance.ctf_verification_poll_period, 0.5)


def test_test_init_warning(utils):
    """
    test Test class constructor -- warning
    """
    utils.clear_log()
    with patch("lib.ctf_global.Global.config") as mock_config:
        mock_config.get.return_value = None
        test = Test()
        assert utils.has_log_level('WARNING')


def test_objectfactory_exception():
    """
    test ObjectFactory static class method: create_object
    """
    with pytest.raises(CtfTestError):
        ObjectFactory.create_object('unknown')


def test_test_execute_instruction(test_instance_inited):
    """
    test Test class method: execute_instruction
    Execute a CTF Test Instruction
    """
    test_instruction = {'instruction': 'StartCfs', 'data': {'target': ''}, 'wait': 1}
    test_instance_inited.test_info = {'test_number': 'CFE-6-7-Plugin-Test-001',
                                      'description': 'Start CFS, Send TO NOOP command'}

    # test instruction pass
    with patch("lib.plugin_manager.Plugin.process_command", return_value=True):
        assert test_instance_inited.execute_instruction(test_instruction, 0) is True
    # test instruction fail
    with patch("lib.plugin_manager.Plugin.process_command", return_value=False):
        assert test_instance_inited.execute_instruction(test_instruction, 1) is False
    # test instruction return None
    with patch("lib.plugin_manager.Plugin.process_command", return_value=None):
        assert test_instance_inited.execute_instruction(test_instruction, 2) is False
    # raise exception
    test_instruction = {'instruction': 'StartCfs', 'data': {'target': ''}, 'wait': 1}
    with patch("lib.plugin_manager.Plugin.process_command") as mock_process_command:
        mock_process_command.side_effect = CtfTestError("Raise Exception from process_command")
        assert test_instance_inited.execute_instruction(test_instruction, 3) is False
        mock_process_command.assert_called_once()

    # No test instruction
    test_instruction = {'instruction': 'Mock_StartCfs', 'data': {'target': ''}, 'wait': 1}
    with patch("lib.plugin_manager.Plugin.process_command", return_value=None):
        assert test_instance_inited.execute_instruction(test_instruction, 3) is False
    # verify_required_commands
    test_instruction = {'instruction': 'CheckNoEvent', 'data': {'target': ''}, 'wait': 1}
    with patch("lib.plugin_manager.Plugin.process_command", return_value=None):
        assert test_instance_inited.execute_instruction(test_instruction, 4) is False


def test_test_execute_verification_fail(test_instance_inited):
    """
    test Test class method: execute_verification:  verification fail
    Execute a CTF Verification Instruction.
    """
    command = {'instruction': 'CheckTlmValue', 'data': {'target': '', 'mid': 'TO_HK_TLM_MID', 'args': [
        {'compare': '==', 'variable': 'usCmdCnt', 'value': [2.0]}]}, 'wait': 1,
               'args': [{'compare': '==', 'variable': 'usCmdCnt', 'value': [2.0]}]}
    command_index = 6
    timeout = 5.0
    new_verification = True

    with patch("lib.plugin_manager.Plugin.process_command", return_value=None):
        assert not test_instance_inited.execute_verification(command, command_index, timeout, new_verification)

    with patch("lib.plugin_manager.Plugin.process_command", return_value=False):
        assert not test_instance_inited.execute_verification(command, command_index, timeout, new_verification)

    with patch("lib.plugin_manager.Plugin.process_command") as mock_process_command:
        mock_process_command.side_effect = CtfTestError("Raise Exception from process_command")
        assert not test_instance_inited.execute_verification(command, command_index, timeout, new_verification)


def test_test_execute_verification_pass(test_instance_inited):
    """
    test Test class method: execute_verification:  verification pass
    Execute a CTF Verification Instruction.
    """
    command = {'instruction': 'CheckTlmValue', 'data': {'target': '', 'mid': 'TO_HK_TLM_MID', 'args': [
        {'compare': '==', 'variable': 'usCmdCnt', 'value': [2.0]}]}, 'wait': 1,
               'args': [{'compare': '==', 'variable': 'usCmdCnt', 'value': [2.0]}]}
    command_index = 6
    timeout = 5.0
    new_verification = True

    with patch("lib.plugin_manager.Plugin.process_command", return_value=True):
        assert test_instance_inited.execute_verification(command, command_index, timeout, new_verification)


def test_test_execute_verification_exception(test_instance_inited):
    """
    test Test class method: execute_verification:  exception when calling process_verification_delay
    Execute a CTF Verification Instruction.
    """
    command = {'instruction': 'CheckTlmValue', 'data': {'target': '', 'mid': 'TO_HK_TLM_MID', 'args': [
        {'compare': '==', 'variable': 'usCmdCnt', 'value': [2.0]}]}, 'wait': 1,
               'args': [{'compare': '==', 'variable': 'usCmdCnt', 'value': [2.0]}]}
    command_index = 6
    timeout = 5.0
    new_verification = True

    with patch("lib.plugin_manager.Plugin.process_command", return_value=False), \
         patch("lib.test.Test.process_verification_delay") as mock_process_verification_delay:
        mock_process_verification_delay.side_effect = CtfConditionError('Mock exception', False)
        assert not test_instance_inited.execute_verification(command, command_index, timeout, new_verification)


def test_test_process_command_delay(test_instance):
    """
    test Test class static  method: process_command_delay
    Utilize the current CTF time manager to wait a specific amount of time before executing a CTF Test Instruction
    """
    assert Test.process_command_delay(1) is None


def test_test_process_verification_delay(test_instance):
    """
    test Test class method: process_verification_delay
    Utilize the current CTF time manager to wait a specific amount of time before executing a CTF Test Instruction
    """
    assert test_instance.process_verification_delay() is None


def test_test_run_commands_fail(test_instance_inited, utils):
    """
    test Test class method: run_commands -- test fail
    Run all CTF Instructions in the current test
    """
    test_instance_inited.test_info = {'test_number': 'CFE-6-7-Plugin-Test-001',
                                      'description': 'Start CFS, Send TO NOOP command'}

    # no test instruction
    test_instance_inited.instructions.clear()
    utils.clear_log()
    assert not test_instance_inited.run_commands()
    assert utils.has_log_level('ERROR')


def test_test_run_commands(test_instance_inited):
    """
    test Test class method: run_commands
    Run all CTF Instructions in the current test
    """
    test_instance_inited.test_info = {'test_number': 'CFE-6-7-Plugin-Test-001',
                                      'description': 'Start CFS, Send TO NOOP command'}
    with patch("lib.test.Test.execute_verification", return_value=None), \
         patch("lib.test.Test.execute_instruction", return_value=None):
        assert test_instance_inited.run_commands() is None

    test_instance_inited.instructions[0].is_disabled = True
    test_instance_inited.ignored_instructions = ['SendCfsCommand','EnableCfsOutput']
    with patch("lib.test.Test.execute_verification", return_value=None), \
         patch("lib.test.Test.execute_instruction", return_value=None):
        assert test_instance_inited.run_commands() is None

    test_instance_inited.ignored_instructions = ['EnableCfsOutput']
    with patch("lib.test.Test.execute_verification", return_value=None), \
         patch("lib.test.Test.execute_instruction", return_value=None):
        assert test_instance_inited.run_commands() is None

    test_instance_inited.ignored_instructions = []
    test_instance_inited.verify_required_commands = []
    test_instance_inited.continuous_verification_commands = ['CheckTlmValue']
    with patch("lib.test.Test.execute_verification", return_value=None), \
         patch("lib.test.Test.execute_instruction", return_value=None):
        assert test_instance_inited.run_commands() is None


def test_test_run_commands_looping(test_instance_inited, utils):
    """
    test Test class method: run_commands
    Run all CTF Instructions in the current test, and test control flow statement
    """
    test_instance_inited.test_info = {'test_number': 'CFE-6-7-Plugin-Test-001',
                                      'description': 'Start CFS, Send TO NOOP command'}
    Global.goto_instruction_index = -1
    test_instance_inited.instructions[0].is_disabled = True
    utils.clear_log()
    with patch("lib.test.Test.execute_verification", return_value=None), \
         patch("lib.test.Test.execute_instruction", return_value=None):
        assert test_instance_inited.run_commands() is None
        assert utils.has_log_level('ERROR')

    Global.goto_instruction_index = 10
    with patch("lib.test.Test.execute_verification", return_value=None), \
         patch("lib.test.Test.execute_instruction", return_value=None):
        assert test_instance_inited.run_commands() is None
    Global.goto_instruction_index = None


def test_test_process_conditional_branch_label(test_instance_inited):
    """
    test Test class method: process_conditional_branch_label
    Process control flow labels defined in test instructions 'IfCondition',  'ElseCondition' and 'EndCondition'
    """
    if_instruction = {"instruction": "IfCondition",
                      "data": {"conditions": [{"variable": "my_var", "compare": "<", "value": 3}],
                               "label": "label_1"}}
    else_instruction = {"instruction": "ElseCondition", "data": {"label": "label_1"}, "wait": 1}
    end_instruction = {"instruction": "EndCondition", "data": {"label": "label_1"}}
    cmd = Instruction(1.0, if_instruction, 0, 18, False)
    test_instance_inited.instructions.append(cmd)
    cmd = Instruction(1.0, else_instruction, 0, 19, False)
    test_instance_inited.instructions.append(cmd)
    cmd = Instruction(1.0, end_instruction, 0, 20, False)
    test_instance_inited.instructions.append(cmd)
    assert test_instance_inited.process_conditional_branch_label() is None
    test_instance_inited.instructions.clear()


def test_test_process_conditional_branch_label_exception(test_instance_inited,utils):
    """
    test Test class method: process_conditional_branch_label -- raise exception
    Process control flow labels defined in test instructions 'IfCondition',  'ElseCondition' and 'EndCondition'
    """
    if_instruction_1 = {"instruction": "IfCondition",
                      "data": {"conditions": [{"variable": "my_var", "compare": "<", "value": 3}],
                               "label": "label_1"}}
    else_instruction_1 = {"instruction": "ElseCondition", "data": {"label": "label_1"}, "wait": 1}
    if_instruction_2 = {"instruction": "IfCondition",
                      "data": {"conditions": [{"variable": "my_var", "compare": "<", "value": 3}],
                               "label": "label_2"}}
    else_instruction_2 = {"instruction": "ElseCondition", "data": {"label": "label_2"}, "wait": 1}
    end_instruction = {"instruction": "EndCondition", "data": {"label": "label_1"}}
    cmd = Instruction(1.0, if_instruction_1, 0, 18, False)
    test_instance_inited.instructions.append(cmd)
    cmd = Instruction(1.0, if_instruction_2, 0, 19, False)
    test_instance_inited.instructions.append(cmd)
    cmd = Instruction(1.0, else_instruction_1, 0, 20, False)
    test_instance_inited.instructions.append(cmd)
    cmd = Instruction(1.0, else_instruction_2, 0, 21, False)
    test_instance_inited.instructions.append(cmd)
    cmd = Instruction(1.0, end_instruction, 0, 22, False)
    test_instance_inited.instructions.append(cmd)
    utils.clear_log()
    with pytest.raises(CtfTestError):
        test_instance_inited.process_conditional_branch_label()
        assert utils.has_log_level('ERROR')
    test_instance_inited.instructions.clear()


def test_test_process_conditional_branch_label_exception_2(test_instance_inited,utils):
    """
    test Test class method: process_conditional_branch_label -- raise exception
    Process control flow labels defined in test instructions 'IfCondition',  'ElseCondition' and 'EndCondition'
    """
    end_instruction = {"instruction": "EndCondition", "data": {"label": "label_1"}}
    cmd = Instruction(1.0, end_instruction, 0, 18, False)
    test_instance_inited.instructions.append(cmd)
    utils.clear_log()
    with pytest.raises(CtfTestError):
        test_instance_inited.process_conditional_branch_label()
        assert utils.has_log_level('ERROR')
    test_instance_inited.instructions.clear()


def test_test_process_conditional_branch_label_exception_3(test_instance_inited,utils):
    """
    test Test class method: process_conditional_branch_label -- raise exception
    Process control flow labels defined in test instructions 'IfCondition',  'ElseCondition' and 'EndCondition'
    """
    if_instruction_1 = {"instruction": "IfCondition",
                      "data": {"conditions": [{"variable": "my_var", "compare": "<", "value": 3}],
                               "label": "label_1"}}
    cmd = Instruction(1.0, if_instruction_1, 0, 18, False)
    test_instance_inited.instructions.append(cmd)
    utils.clear_log()
    with pytest.raises(CtfTestError):
        test_instance_inited.process_conditional_branch_label()
        assert utils.has_log_level('ERROR')
    test_instance_inited.instructions.clear()


def test_test_process_conditional_branch_label_exception_4(test_instance_inited,utils):
    """
    test Test class method: process_conditional_branch_label -- raise exception
    Process control flow labels defined in test instructions 'IfCondition',  'ElseCondition' and 'EndCondition'
    """
    if_instruction_1 = {"instruction": "IfCondition",
                      "data": {"conditions": [{"variable": "my_var", "compare": "<", "value": 3}],
                               "label": "label_1"}}
    if_instruction_2 = {"instruction": "IfCondition",
                      "data": {"conditions": [{"variable": "my_var", "compare": "<", "value": 3}],
                               "label": "label_2"}}
    end_instruction_1 = {"instruction": "EndCondition", "data": {"label": "label_1"}}
    test_instance_inited.instructions.clear()
    cmd = Instruction(1.0, if_instruction_1, 0, 18, False)
    test_instance_inited.instructions.append(cmd)
    cmd = Instruction(1.0, if_instruction_2, 0, 19, False)
    test_instance_inited.instructions.append(cmd)
    cmd = Instruction(1.0, end_instruction_1, 0, 22, False)
    test_instance_inited.instructions.append(cmd)
    utils.clear_log()
    with pytest.raises(CtfTestError):
        test_instance_inited.process_conditional_branch_label()
        assert utils.has_log_level('ERROR')
    test_instance_inited.instructions.clear()


def test_test_process_control_flow_label_pass(test_instance_inited):
    """
    test Test class method: process_control_flow_label
    Process control flow labels defined in test instructions 'BeginLoop' and 'EndLoop'
    """
    begin_loop = {"instruction": "BeginLoop",
                  "data": {"label": "LOOP_1", "conditions": [{"name": "my_var", "operator": "<", "value": 3}]
                           }, "wait": 1}
    end_loop = {"instruction": "EndLoop", "data": {"label": "LOOP_1"}, "wait": 1}
    label = {"instruction": "SetLabel", "data": {"label": "label_1"}}
    cmd = Instruction(1.0, begin_loop, 0, 18, False)
    test_instance_inited.instructions.append(cmd)
    cmd = Instruction(1.0, end_loop, 0, 19, False)
    test_instance_inited.instructions.append(cmd)
    cmd = Instruction(1.0, label, 0, 20, False)
    test_instance_inited.instructions.append(cmd)
    assert test_instance_inited.process_control_flow_label() is None


def test_test_process_control_flow_label_exception(test_instance_inited, utils):
    """
    test Test class method: process_control_flow_label -- raise exception
    Process control flow labels defined in test instructions 'BeginLoop' and 'EndLoop'
    """
    utils.clear_log()
    begin_loop = {"instruction": "BeginLoop",
                  "data": {"label": "", "conditions": [{"name": "my_var", "operator": "<", "value": 3}]
                           }, "wait": 1}
    end_loop = {"instruction": "EndLoop", "data": {"label": ""}, "wait": 1}
    label = {"instruction": "SetLabel", "data": {"label": ""}}
    cmd = Instruction(1.0, begin_loop, 0, 18, False)
    test_instance_inited.instructions.append(cmd)
    with pytest.raises(CtfTestError):
        test_instance_inited.process_control_flow_label()
        assert utils.has_log_level('ERROR')

    utils.clear_log()
    test_instance_inited.instructions[18].command["data"]["label"] = "LOOP1"
    cmd = Instruction(1.0, end_loop, 0, 19, False)
    test_instance_inited.instructions.append(cmd)
    with pytest.raises(CtfTestError):
        test_instance_inited.process_control_flow_label()
        assert utils.has_log_level('ERROR')

    utils.clear_log()
    test_instance_inited.instructions[19].command["data"]["label"] = "LOOP1"
    cmd = Instruction(1.0, label, 0, 20, False)
    test_instance_inited.instructions.append(cmd)
    with pytest.raises(CtfTestError):
        test_instance_inited.process_control_flow_label()
        assert utils.has_log_level('ERROR')


def test_test_process_control_flow_label_exception2(test_instance_inited, utils):
    """
    test Test class method: process_control_flow_label -- raise additional exception
    Process control flow labels defined in test instructions 'BeginLoop' and 'EndLoop'
    """
    begin_loop = {"instruction": "BeginLoop",
                  "data": {"label": "LOOP_1", "conditions": [{"name": "my_var", "operator": "<", "value": 3}]
                           }, "wait": 1}
    label = {"instruction": "SetLabel", "data": {"label": "label_1"}}

    cmd = Instruction(1.0, label, 0, 18, False)
    test_instance_inited.instructions.append(cmd)
    cmd = Instruction(1.0, label, 0, 19, False)
    test_instance_inited.instructions.append(cmd)

    utils.clear_log()
    with pytest.raises(CtfTestError):
        test_instance_inited.process_control_flow_label()
        assert utils.has_log_level('ERROR')

    utils.clear_log()
    test_instance_inited.instructions.pop()
    cmd = Instruction(1.0, begin_loop, 0, 19, False)
    test_instance_inited.instructions.append(cmd)
    cmd = Instruction(1.0, begin_loop, 0, 20, False)
    test_instance_inited.instructions.append(cmd)
    with pytest.raises(CtfTestError):
        test_instance_inited.process_control_flow_label()
        assert utils.has_log_level('ERROR')


def test_test_process_control_flow_label_exception3(test_instance_inited, utils):
    """
    test Test class method: process_control_flow_label -- raise additional exception
    Process control flow labels defined in test instructions 'BeginLoop' and 'EndLoop'
    """
    begin_loop = {"instruction": "BeginLoop",
                  "data": {"label": "LOOP_1", "conditions": [{"name": "my_var", "operator": "<", "value": 3}]
                           }, "wait": 1}
    begin_loop2 = {"instruction": "BeginLoop",
                   "data": {"label": "LOOP_2", "conditions": [{"name": "my_var", "operator": "<", "value": 3}]
                            }, "wait": 1}
    end_loop = {"instruction": "EndLoop", "data": {"label": "LOOP_2"}, "wait": 1}

    cmd = Instruction(1.0, end_loop, 0, 18, False)
    test_instance_inited.instructions.append(cmd)
    utils.clear_log()
    with pytest.raises(CtfTestError):
        test_instance_inited.process_control_flow_label()
        assert utils.has_log_level('ERROR')

    test_instance_inited.instructions.pop()
    cmd = Instruction(1.0, begin_loop2, 0, 18, False)
    test_instance_inited.instructions.append(cmd)
    cmd = Instruction(1.0, begin_loop, 0, 19, False)
    test_instance_inited.instructions.append(cmd)
    cmd = Instruction(1.0, end_loop, 0, 20, False)
    test_instance_inited.instructions.append(cmd)
    utils.clear_log()
    with pytest.raises(CtfTestError):
        test_instance_inited.process_control_flow_label()
        assert utils.has_log_level('ERROR')


def test_test_process_control_flow_label_exception4(test_instance_inited, utils):
    """
    test Test class method: process_control_flow_label -- raise additional exception
    Process control flow labels defined in test instructions 'BeginLoop' and 'EndLoop'
    """
    begin_loop = {"instruction": "BeginLoop",
                  "data": {"label": "LOOP_1", "conditions": [{"name": "my_var", "operator": "<", "value": 3}]
                           }, "wait": 1}
    cmd = Instruction(1.0, begin_loop, 0, 18, False)
    test_instance_inited.instructions.append(cmd)
    utils.clear_log()
    with pytest.raises(CtfTestError):
        test_instance_inited.process_control_flow_label()
        assert utils.has_log_level('ERROR')


def test_test_run_commands_exception(test_instance_inited, utils):
    """
    test Test class method: run_commands -- raise exception
    Run all CTF Instructions in the current test
    """
    utils.clear_log()
    test_instance_inited.test_info = {'test_number': 'CFE-6-7-Plugin-Test-001',
                                      'description': 'Start CFS, Send TO NOOP command'}
    with patch("lib.test.Test.process_command_delay") as mock_process_command_delay, \
            patch("lib.test.Test.execute_verification", return_value=None), \
            patch("lib.test.Test.execute_instruction", return_value=None):
        mock_process_command_delay.side_effect = CtfTestError("Raise Exception from process_command_delay")
        assert test_instance_inited.run_commands() is None
        assert utils.has_log_level('ERROR')

    # another exception
    with patch("lib.test.Test.process_command_delay") as mock_process_command_delay, \
            patch("lib.test.Test.execute_verification", return_value=None), \
            patch("lib.test.Test.execute_instruction", return_value=None):
        mock_process_command_delay.side_effect = CtfConditionError('Mock exception from process_command_delay', False)
        assert test_instance_inited.run_commands() is None

    # another exception
    test_instance_inited.end_test_on_fail = True
    utils.clear_log()
    with patch("lib.ctf_global.Global.time_manager.post_command") as mock_post_command, \
            patch("lib.test.Test.execute_verification", return_value=None), \
            patch("lib.test.Test.execute_instruction", return_value=None):
        mock_post_command.side_effect = CtfTestError('Mock exception from time_manager.post_command')
        assert test_instance_inited.run_commands() is None
        assert utils.has_log_level('ERROR')


def test_test_run_test_fail(test_instance_inited):
    """
    test Test class method: run_test  test fail
    Run all CTF Instructions within a test
    """
    test_instance_inited.test_info = {'test_number': 'CFE-6-7-Plugin-Test-001',
                                      'description': 'Start CFS, Send TO NOOP command'}
    with patch("lib.test.Test.run_commands", return_value=None):
        test_instance_inited.test_result = False
        assert test_instance_inited.run_test(test_instance_inited.status_manager) == 'failed'


def test_test_run_test_abort(test_instance_inited):
    """
    test Test class method: run_test  test abort
    Run all CTF Instructions within a test
    """
    test_instance_inited.test_info = {'test_number': 'CFE-6-7-Plugin-Test-001',
                                      'description': 'Start CFS, Send TO NOOP command'}
    with patch("lib.test.Test.run_commands", return_value=None):
        test_instance_inited.test_aborted = True
        assert test_instance_inited.run_test(test_instance_inited.status_manager) == 'aborted'


def test_test_run_test_pass(test_instance_inited):
    """
    test Test class method: run_test
    Run all CTF Instructions within a test
    """
    test_instance_inited.test_info = {'test_number': 'CFE-6-7-Plugin-Test-001',
                                      'description': 'Start CFS, Send TO NOOP command'}
    with patch("lib.test.Test.run_commands", return_value=None):
        test_instance_inited.test_result = True
        assert test_instance_inited.run_test(test_instance_inited.status_manager) == 'passed'


def test_test_run_test_exception(test_instance_inited):
    """
    test Test class method: run_test -- raise exception from run_commands
    Run all CTF Instructions within a test
    """
    test_instance_inited.test_info = {'test_number': 'CFE-6-7-Plugin-Test-001',
                                      'description': 'Start CFS, Send TO NOOP command'}

    with patch("lib.test.Test.run_commands") as mock_run_commands:
        mock_run_commands.side_effect = Exception
        with pytest.raises(CtfTestError):
            test_instance_inited.run_test(test_instance_inited.status_manager)
            mock_run_commands.assert_called_once()
