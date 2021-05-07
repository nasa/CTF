"""
@namespace lib.test_test.py
Unit Test for Test class: Represents a single CTF test case.
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

from math import isclose
import pytest
from unittest.mock import patch, Mock

from lib.ctf_global import Global
from lib.exceptions import CtfTestError, CtfConditionError
from lib.readers.json_script_reader import JSONScriptReader
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
    script_reader = JSONScriptReader('scripts/cfe_6_7_tests/cfe_tests/CfeEsTest.json')
    script_reader.process_tests()
    script_list = [script_reader.script]
    status_manager.set_scripts(script_list)

    event_list = script_reader.script.tests[0].event_list
    test.event_list = event_list

    status_manager.set_start_time()
    test.status_manager = status_manager
    return test


def test_test_init(test_instance):
    """
    test Test class constructor
    """
    assert test_instance.test_info is None
    assert len(test_instance.event_list) == 0
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


def test_test_execute_event(test_instance_inited):
    """
    test Test class method: execute_event
    Execute a CTF Test Instruction
    """
    test_instruction = {'instruction': 'StartCfs', 'data': {'target': ''}, 'wait': 1}

    # test instruction pass
    with patch("lib.plugin_manager.Plugin.process_command", return_value=True):
        assert test_instance_inited.execute_event(test_instruction, 0) is None
    # test instruction fail
    with patch("lib.plugin_manager.Plugin.process_command", return_value=False):
        assert test_instance_inited.execute_event(test_instruction, 1) is None
    # test instruction return None
    with patch("lib.plugin_manager.Plugin.process_command", return_value=None):
        assert test_instance_inited.execute_event(test_instruction, 2) is None
    # raise exception
    test_instruction = {'instruction': 'StartCfs', 'data': {'target': ''}, 'wait': 1}
    with patch("lib.plugin_manager.Plugin.process_command") as mock_process_command:
        mock_process_command.side_effect = CtfTestError("Raise Exception from process_command")
        assert test_instance_inited.execute_event(test_instruction, 3) is None
        mock_process_command.assert_called_once()

    # No test instruction
    test_instruction = {'instruction': 'Mock_StartCfs', 'data': {'target': ''}, 'wait': 1}
    with patch("lib.plugin_manager.Plugin.process_command", return_value=None):
        assert test_instance_inited.execute_event(test_instruction, 3) is None
    # verify_required_commands
    test_instruction = {'instruction': 'CheckNoEvent', 'data': {'target': ''}, 'wait': 1}
    with patch("lib.plugin_manager.Plugin.process_command", return_value=None):
        assert test_instance_inited.execute_event(test_instruction, 4) is None


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
    Run all CTF Instructions in the current test case
    """
    test_instance_inited.test_info = {'test_case': 'CFE-6-7-Plugin-Test-001',
                                      'description': 'Start CFS, Send TO NOOP command'}

    # no test instruction
    test_instance_inited.event_list.clear()
    utils.clear_log()
    assert not test_instance_inited.run_commands()
    assert utils.has_log_level('ERROR')


def test_test_run_commands(test_instance_inited):
    """
    test Test class method: run_commands
    Run all CTF Instructions in the current test case
    """
    test_instance_inited.test_info = {'test_case': 'CFE-6-7-Plugin-Test-001',
                                      'description': 'Start CFS, Send TO NOOP command'}
    with patch("lib.test.Test.execute_verification", return_value=None), \
         patch("lib.test.Test.execute_event", return_value=None):
        assert test_instance_inited.run_commands() is None

    test_instance_inited.event_list[1].is_disabled = True
    test_instance_inited.ignored_instructions = ['SendCfsCommand']
    with patch("lib.test.Test.execute_verification", return_value=None), \
         patch("lib.test.Test.execute_event", return_value=None):
        assert test_instance_inited.run_commands() is None

    test_instance_inited.ignored_instructions = []
    with patch("lib.test.Test.execute_verification", return_value=None), \
         patch("lib.test.Test.execute_event", return_value=None):
        assert test_instance_inited.run_commands() is None

    test_instance_inited.ignored_instructions = []
    test_instance_inited.verify_required_commands = []
    test_instance_inited.continuous_verification_commands = ['CheckTlmValue']
    with patch("lib.test.Test.execute_verification", return_value=None), \
         patch("lib.test.Test.execute_event", return_value=None):
        assert test_instance_inited.run_commands() is None


def test_test_run_commands_exception (test_instance_inited,utils):
    """
    test Test class method: run_commands -- raise exception
    Run all CTF Instructions in the current test case
    """
    utils.clear_log()
    test_instance_inited.test_info = {'test_case': 'CFE-6-7-Plugin-Test-001',
                                      'description': 'Start CFS, Send TO NOOP command'}
    with patch("lib.test.Test.process_command_delay") as mock_process_command_delay, \
        patch("lib.test.Test.execute_verification", return_value=None), \
         patch("lib.test.Test.execute_event", return_value=None):
        mock_process_command_delay.side_effect = CtfTestError("Raise Exception from process_command_delay")
        assert test_instance_inited.run_commands() is None
        assert utils.has_log_level('ERROR')

    # another exception
    with patch("lib.test.Test.process_command_delay") as mock_process_command_delay, \
        patch("lib.test.Test.execute_verification", return_value=None), \
         patch("lib.test.Test.execute_event", return_value=None):
        mock_process_command_delay.side_effect = CtfConditionError('Mock exception from process_command_delay', False)
        assert test_instance_inited.run_commands() is None

    # another exception
    test_instance_inited.end_test_on_fail = True
    utils.clear_log()
    with patch("lib.ctf_global.Global.time_manager.post_command") as mock_post_command, \
        patch("lib.test.Test.execute_verification", return_value=None), \
         patch("lib.test.Test.execute_event", return_value=None):
        mock_post_command.side_effect = CtfTestError('Mock exception from time_manager.post_command')
        assert test_instance_inited.run_commands() is None
        assert utils.has_log_level('ERROR')


def test_test_run_test_fail(test_instance_inited):
    """
    test Test class method: run_test  test fail
    Run all CTF Instructions within a test case
    """
    test_instance_inited.test_info = {'test_case': 'CFE-6-7-Plugin-Test-001',
                                      'description': 'Start CFS, Send TO NOOP command'}
    with patch("lib.test.Test.run_commands", return_value=None):
        test_instance_inited.test_result = False
        assert test_instance_inited.run_test(test_instance_inited.status_manager) == 'failed'


def test_test_run_test_abort(test_instance_inited):
    """
    test Test class method: run_test  test abort
    Run all CTF Instructions within a test case
    """
    test_instance_inited.test_info = {'test_case': 'CFE-6-7-Plugin-Test-001',
                                      'description': 'Start CFS, Send TO NOOP command'}
    with patch("lib.test.Test.run_commands", return_value=None):
        test_instance_inited.test_aborted = True
        assert test_instance_inited.run_test(test_instance_inited.status_manager) == 'aborted'


def test_test_run_test_pass(test_instance_inited):
    """
    test Test class method: run_test
    Run all CTF Instructions within a test case
    """
    test_instance_inited.test_info = {'test_case': 'CFE-6-7-Plugin-Test-001',
                                      'description': 'Start CFS, Send TO NOOP command'}
    with patch("lib.test.Test.run_commands", return_value=None):
        test_instance_inited.test_result = True
        assert test_instance_inited.run_test(test_instance_inited.status_manager) == 'passed'


def test_test_run_test_exception(test_instance_inited):
    """
    test Test class method: run_test -- raise exception from run_commands
    Run all CTF Instructions within a test case
    """
    test_instance_inited.test_info = {'test_case': 'CFE-6-7-Plugin-Test-001',
                                      'description': 'Start CFS, Send TO NOOP command'}

    with patch("lib.test.Test.run_commands") as mock_run_commands:
        mock_run_commands.side_effect = Exception
        with pytest.raises(CtfTestError):
            test_instance_inited.run_test(test_instance_inited.status_manager)
            mock_run_commands.assert_called_once()
